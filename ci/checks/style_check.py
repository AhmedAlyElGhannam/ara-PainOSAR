#!/usr/bin/env python3
"""Project-specific C++ style checks.

These are the rules that clang-format cannot express or cannot enforce on its
own. clang-format owns *layout*; this script owns *invariants*.

Rules
-----
R001  no tab characters in leading indentation
R002  leading indentation is a multiple of 4 spaces
R003  every header has an include guard named after its full path
R004  every file ends with exactly one newline
R005  never more than two consecutive blank lines
R006  an opening brace never shares a line with the statement it opens
R007  no trailing whitespace at end of line

Exit codes
----------
0  all files clean
1  at least one violation
2  the check itself is misconfigured (no files found, bad arguments)

Exit code 2 matters: a style checker that silently examines zero files and
reports success is worse than no checker at all.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

INDENT_WIDTH = 4
MAX_CONSECUTIVE_BLANK_LINES = 2
HEADER_SUFFIXES = (".h", ".hpp", ".hh", ".hxx")
SOURCE_SUFFIXES = (".c", ".cc", ".cpp", ".cxx")
ALL_SUFFIXES = HEADER_SUFFIXES + SOURCE_SUFFIXES

# R002 governs *nesting* indentation, not *continuation* indentation.
#
# When clang-format wraps a long expression it aligns the continuation to a
# column derived from the expression itself -- the first `<<` of a stream
# chain, the opening quote of a concatenated literal, the `*` of a block
# comment body. Those columns are arbitrary and frequently not multiples of 4.
#
# This exemption is not cosmetic. Without it clang-format and this checker
# would demand different columns for the same line, and the file would be
# literally unfixable: formatting it breaks the check, satisfying the check
# breaks formatting. test_style_check.py::test_no_conflict_with_clang_format
# guards the property.
#
# A line is treated as a continuation when it starts with one of these tokens.
# Ordered longest-first so that `<<` is matched before `<`.
CONTINUATION_PREFIXES = (
    "<<", ">>", "->", "&&", "||", "==", "!=", "<=", ">=", "::",
    '"', "'", "*", "/", "+", "-", "&", "|", "^", "?", ":", ".",
    "<", ">", "%", "~", ",", ")", "]", "=",
)

# Directories that contain code this project did not write and must not police.
# Build trees are the dangerous one: CMake's FetchContent drops upstream
# GoogleTest sources under build/_deps, and Bazel leaves bazel-* symlinks in
# the workspace root. Walking into either turns the format stage red on code
# nobody in this repository can fix.
EXCLUDED_DIR_NAMES = frozenset(
    {
        ".git",
        "_deps",
        "bazel-bin",
        "bazel-out",
        "bazel-testlogs",
        "build",
        "cmake-build-debug",
        "cmake-build-release",
        "external",
        "out",
        "third_party",
        "vendor",
    }
)

CONTROL_KEYWORDS = ("if", "else", "for", "while", "switch", "do", "try", "catch")
CONTROL_BRACE_RE = re.compile(
    r"^\s*(?:\}\s*)?(?:" + "|".join(CONTROL_KEYWORDS) + r")\b.*\{\s*$"
)
FUNCTION_BRACE_RE = re.compile(r"^\s*[A-Za-z_~].*\)\s*(?:const\s*)?(?:noexcept\s*)?\{\s*$")
RAW_STRING_OPEN_RE = re.compile(r'R"([^(\s\\]{0,16})\(')


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    rule: str
    message: str

    def render(self, root: Path) -> str:
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"{shown}:{self.line}: [{self.rule}] {self.message}"


# How much of a header's path feeds the include guard.
#
#   "repo"     full path from the repository root -- the rule as originally
#              stated. With modular nesting this gets long:
#              PLATFORM_ARA_SENSOR_INCLUDE_ARA_SENSOR_SENSOR_READER_H
#
#   "include"  path relative to the nearest enclosing include/ directory,
#              which is also the string you type in the #include directive:
#              ARA_SENSOR_SENSOR_READER_H
#
# Both are collision-free, because two headers with the same include-relative
# path could not both be included anyway. Flip this one constant to switch;
# the checker then tells every header what to change to.
GUARD_STYLE = "repo"


def guard_for(path: Path, root: Path) -> str:
    """Derive the include guard from the header's path.

    See GUARD_STYLE above for which portion of the path is used.
    """
    relative = path.resolve().relative_to(root.resolve())

    if GUARD_STYLE == "include":
        parts = list(relative.parts)
        for index in range(len(parts) - 1, -1, -1):
            if parts[index] == "include":
                relative = Path(*parts[index + 1 :])
                break

    token = re.sub(r"[^0-9A-Za-z]+", "_", str(relative))
    token = re.sub(r"_+", "_", token).strip("_")
    return token.upper()


def classify_lines(lines: list[str]) -> list[bool]:
    """Return a mask marking lines that sit inside a raw string literal body.

    Raw strings may contain any indentation at all, so R001/R002/R006/R007 must
    not look at them.
    """
    inside = [False] * len(lines)
    terminator: str | None = None
    for index, line in enumerate(lines):
        if terminator is None:
            match = RAW_STRING_OPEN_RE.search(line)
            if match:
                terminator = f'){match.group(1)}"'
                if terminator in line[match.end():]:
                    terminator = None
                else:
                    # The opening line itself is real code; the body starts next.
                    continue
        else:
            inside[index] = True
            if terminator in line:
                terminator = None
    return inside


def strip_strings_and_comments(line: str) -> str:
    """Blank out string/char literal bodies and comments so brace scanning is safe."""
    out: list[str] = []
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if char == "/" and index + 1 < length and line[index + 1] == "/":
            break
        if char == "/" and index + 1 < length and line[index + 1] == "*":
            end = line.find("*/", index + 2)
            index = length if end == -1 else end + 2
            continue
        if char in "\"'":
            quote = char
            out.append(" ")
            index += 1
            while index < length:
                if line[index] == "\\":
                    index += 2
                    continue
                if line[index] == quote:
                    break
                index += 1
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def check_indentation(path: Path, lines: list[str], raw_mask: list[bool]) -> list[Violation]:
    found: list[Violation] = []
    in_block_comment = False
    for number, line in enumerate(lines, start=1):
        if raw_mask[number - 1]:
            continue
        stripped = line.strip()
        if not stripped:
            continue

        was_in_comment = in_block_comment
        opens = line.count("/*")
        closes = line.count("*/")
        if opens > closes:
            in_block_comment = True
        elif closes >= opens and closes > 0:
            in_block_comment = False

        indent = line[: len(line) - len(line.lstrip())]
        if "\t" in indent:
            found.append(
                Violation(path, number, "R001", "tab character in indentation; use 4 spaces")
            )
            continue
        if was_in_comment or stripped.startswith(CONTINUATION_PREFIXES):
            continue
        if stripped.startswith("#"):
            continue
        if len(indent) % INDENT_WIDTH != 0:
            found.append(
                Violation(
                    path,
                    number,
                    "R002",
                    f"indented {len(indent)} spaces; must be a multiple of {INDENT_WIDTH}",
                )
            )
    return found


def check_header_guard(path: Path, root: Path, lines: list[str]) -> list[Violation]:
    if path.suffix not in HEADER_SUFFIXES:
        return []

    expected = guard_for(path, root)

    if any(line.strip() == "#pragma once" for line in lines):
        return [
            Violation(
                path,
                1,
                "R003",
                f"uses '#pragma once'; this project requires '#ifndef {expected}'",
            )
        ]

    ifndef_index: int | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        if stripped.startswith("*") or stripped.endswith("*/"):
            continue
        if stripped.startswith("#ifndef"):
            ifndef_index = index
        break

    if ifndef_index is None:
        return [
            Violation(
                path,
                1,
                "R003",
                f"missing include guard; expected '#ifndef {expected}' as the first directive",
            )
        ]

    found_guard = lines[ifndef_index].split(maxsplit=1)
    actual = found_guard[1].strip() if len(found_guard) > 1 else ""
    if actual != expected:
        return [
            Violation(
                path,
                ifndef_index + 1,
                "R003",
                f"guard is '{actual}'; expected '{expected}' (derived from the file path)",
            )
        ]

    define_line = ""
    for line in lines[ifndef_index + 1 :]:
        if line.strip():
            define_line = line.strip()
            break
    if define_line != f"#define {expected}":
        return [
            Violation(
                path,
                ifndef_index + 2,
                "R003",
                f"'#ifndef {expected}' must be followed immediately by '#define {expected}'",
            )
        ]

    last = ""
    last_number = len(lines)
    for offset, line in enumerate(reversed(lines)):
        if line.strip():
            last = line.strip()
            last_number = len(lines) - offset
            break
    if not last.startswith("#endif"):
        return [
            Violation(
                path,
                last_number,
                "R003",
                f"file must end with '#endif  // {expected}'",
            )
        ]
    return []


def check_file_ending(path: Path, text: str) -> list[Violation]:
    if text == "":
        return [Violation(path, 1, "R004", "file is empty; expected at least a newline")]
    line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
    if not text.endswith("\n"):
        return [Violation(path, line_count, "R004", "file does not end with a newline")]
    if text.endswith("\n\n"):
        return [
            Violation(path, line_count, "R004", "file ends with blank lines; keep exactly one newline")
        ]
    return []


def check_blank_line_runs(path: Path, lines: list[str]) -> list[Violation]:
    found: list[Violation] = []
    run = 0
    for number, line in enumerate(lines, start=1):
        if line.strip():
            run = 0
            continue
        run += 1
        if run == MAX_CONSECUTIVE_BLANK_LINES + 1:
            found.append(
                Violation(
                    path,
                    number,
                    "R005",
                    f"more than {MAX_CONSECUTIVE_BLANK_LINES} consecutive blank lines",
                )
            )
    return found


def check_brace_placement(path: Path, lines: list[str], raw_mask: list[bool]) -> list[Violation]:
    found: list[Violation] = []
    for number, line in enumerate(lines, start=1):
        if raw_mask[number - 1]:
            continue
        code = strip_strings_and_comments(line).rstrip()
        if not code.endswith("{"):
            continue
        if code.strip() == "{":
            continue
        # Aggregate initialisers and lambda captures legitimately keep the brace
        # on the line; only statement and function bodies are checked.
        if "=" in code.split("{")[0]:
            continue
        if "]" in code.split("{")[0] and "(" not in code.split("]")[0]:
            continue
        if CONTROL_BRACE_RE.match(code) or FUNCTION_BRACE_RE.match(code):
            found.append(
                Violation(
                    path,
                    number,
                    "R006",
                    "opening brace must start on its own line",
                )
            )
    return found


def check_trailing_whitespace(path: Path, lines: list[str], raw_mask: list[bool]) -> list[Violation]:
    found: list[Violation] = []
    for number, line in enumerate(lines, start=1):
        if raw_mask[number - 1]:
            continue
        if line != line.rstrip():
            found.append(Violation(path, number, "R007", "trailing whitespace"))
    return found


def check_file(path: Path, root: Path) -> list[Violation]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    raw_mask = classify_lines(lines)

    violations: list[Violation] = []
    violations += check_file_ending(path, text)
    violations += check_header_guard(path, root, lines)
    violations += check_indentation(path, lines, raw_mask)
    violations += check_blank_line_runs(path, lines)
    violations += check_brace_placement(path, lines, raw_mask)
    violations += check_trailing_whitespace(path, lines, raw_mask)
    return sorted(violations, key=lambda item: (str(item.path), item.line, item.rule))


def is_excluded(path: Path, root: Path) -> bool:
    """True when the path sits inside a directory this project does not own."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in relative.parts)


def discover(root: Path, explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(item).resolve() for item in explicit]

    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            check=True,
            text=True,
        )
        candidates = [root / item for item in result.stdout.split("\0") if item]
    except (subprocess.CalledProcessError, FileNotFoundError):
        candidates = [item for item in root.rglob("*") if item.is_file()]

    return sorted(
        item.resolve()
        for item in candidates
        if item.suffix in ALL_SUFFIXES and item.is_file() and not is_excluded(item, root)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root (default: cwd)")
    parser.add_argument("files", nargs="*", help="specific files; default is every tracked source")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="do not fail when zero files are discovered (used by the checker's own tests)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    files = discover(root, args.files)

    if not files and not args.allow_empty:
        print(
            "style_check: no C++ files found — the check is misconfigured, "
            "not passing. Verify --root and the file globs.",
            file=sys.stderr,
        )
        return 2

    violations: list[Violation] = []
    for path in files:
        violations += check_file(path, root)

    for violation in violations:
        print(violation.render(root))

    print(
        f"\nstyle_check: {len(files)} file(s) examined, {len(violations)} violation(s).",
        file=sys.stderr,
    )
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
