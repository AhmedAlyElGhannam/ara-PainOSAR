"""Tests for the style checker itself.

A style check is a classifier. Proving it passes on clean code is half the
job; the half people skip is proving it *fails* on dirty code. Every rule
below has a test that feeds it a known violation and asserts it goes red.

test_no_conflict_with_clang_format is the most important test in this file.
It asserts that clang-format's own output always satisfies the checker. If it
ever fails, some file in the project has become unfixable -- formatting it
breaks the check and satisfying the check breaks formatting.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import style_check  # noqa: E402

CLANG_FORMAT = shutil.which("clang-format")
REPO_ROOT = Path(__file__).resolve().parents[2]


def write(root: Path, relative: str, body: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def rules_for(path: Path, root: Path) -> set[str]:
    return {violation.rule for violation in style_check.check_file(path, root)}


# --------------------------------------------------------------------------
# Guard-name derivation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("include/telemetry/sensor_reader.h", "INCLUDE_TELEMETRY_SENSOR_READER_H"),
        ("src/detail/impl.hpp", "SRC_DETAIL_IMPL_HPP"),
        ("include/a-b/c.d.h", "INCLUDE_A_B_C_D_H"),
        ("top.h", "TOP_H"),
    ],
)
def test_guard_name_follows_full_path(tmp_path: Path, relative: str, expected: str) -> None:
    path = write(tmp_path, relative, "")
    assert style_check.guard_for(path, tmp_path) == expected


# --------------------------------------------------------------------------
# One negative test per rule
# --------------------------------------------------------------------------


def test_r001_rejects_tab_indentation(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "void f()\n{\n\treturn;\n}\n")
    assert "R001" in rules_for(path, tmp_path)


def test_r002_rejects_indent_that_is_not_a_multiple_of_four(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "void f()\n{\n   return;\n}\n")
    assert "R002" in rules_for(path, tmp_path)


def test_r002_accepts_four_and_eight(tmp_path: Path) -> None:
    body = "void f()\n{\n    if (x)\n    {\n        return;\n    }\n}\n"
    path = write(tmp_path, "src/a.cpp", body)
    assert "R002" not in rules_for(path, tmp_path)


def test_r003_rejects_wrong_guard_name(tmp_path: Path) -> None:
    body = "#ifndef NOPE_H\n#define NOPE_H\n\nint x = 0;\n\n#endif  // NOPE_H\n"
    path = write(tmp_path, "include/telemetry/a.h", body)
    assert "R003" in rules_for(path, tmp_path)


def test_r003_rejects_pragma_once(tmp_path: Path) -> None:
    path = write(tmp_path, "include/telemetry/a.h", "#pragma once\n\nint x = 0;\n")
    assert "R003" in rules_for(path, tmp_path)


def test_r003_rejects_missing_endif(tmp_path: Path) -> None:
    body = "#ifndef INCLUDE_TELEMETRY_A_H\n#define INCLUDE_TELEMETRY_A_H\n\nint x = 0;\n"
    path = write(tmp_path, "include/telemetry/a.h", body)
    assert "R003" in rules_for(path, tmp_path)


def test_r003_accepts_correct_guard(tmp_path: Path) -> None:
    body = (
        "#ifndef INCLUDE_TELEMETRY_A_H\n"
        "#define INCLUDE_TELEMETRY_A_H\n"
        "\n"
        "int x = 0;\n"
        "\n"
        "#endif  // INCLUDE_TELEMETRY_A_H\n"
    )
    path = write(tmp_path, "include/telemetry/a.h", body)
    assert "R003" not in rules_for(path, tmp_path)


def test_r003_ignores_leading_licence_comment(tmp_path: Path) -> None:
    body = (
        "// Copyright notice.\n"
        "#ifndef INCLUDE_TELEMETRY_A_H\n"
        "#define INCLUDE_TELEMETRY_A_H\n"
        "\n"
        "int x = 0;\n"
        "\n"
        "#endif  // INCLUDE_TELEMETRY_A_H\n"
    )
    path = write(tmp_path, "include/telemetry/a.h", body)
    assert "R003" not in rules_for(path, tmp_path)


def test_r004_rejects_missing_trailing_newline(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int x = 0;")
    assert "R004" in rules_for(path, tmp_path)


def test_r004_rejects_extra_blank_line_at_eof(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int x = 0;\n\n")
    assert "R004" in rules_for(path, tmp_path)


def test_r004_accepts_single_trailing_newline(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int x = 0;\n")
    assert "R004" not in rules_for(path, tmp_path)


def test_r005_rejects_three_blank_lines(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int a = 0;\n\n\n\nint b = 0;\n")
    assert "R005" in rules_for(path, tmp_path)


def test_r005_accepts_two_blank_lines(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int a = 0;\n\n\nint b = 0;\n")
    assert "R005" not in rules_for(path, tmp_path)


def test_r006_rejects_brace_on_control_statement_line(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "void f()\n{\n    if (x) {\n        return;\n    }\n}\n")
    assert "R006" in rules_for(path, tmp_path)


def test_r006_rejects_brace_on_function_line(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "void f() {\n    return;\n}\n")
    assert "R006" in rules_for(path, tmp_path)


def test_r006_allows_aggregate_initialiser(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int arr[] = {1, 2, 3};\n")
    assert "R006" not in rules_for(path, tmp_path)


def test_r006_ignores_brace_inside_string_literal(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", 'const char* s = "if (x) {";\n')
    assert "R006" not in rules_for(path, tmp_path)


def test_r007_rejects_trailing_whitespace(tmp_path: Path) -> None:
    path = write(tmp_path, "src/a.cpp", "int x = 0;   \n")
    assert "R007" in rules_for(path, tmp_path)


# --------------------------------------------------------------------------
# Raw strings must be exempt from every line-shape rule
# --------------------------------------------------------------------------


def test_raw_string_body_is_exempt(tmp_path: Path) -> None:
    body = 'const char* s = R"(\n   odd indent\n\tand a tab   \n)";\n'
    path = write(tmp_path, "src/a.cpp", body)
    assert rules_for(path, tmp_path) == set()


# --------------------------------------------------------------------------
# Misconfiguration must fail loudly, never pass silently
# --------------------------------------------------------------------------


def test_zero_files_discovered_exits_two(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    assert style_check.main(["--root", str(tmp_path / "empty")]) == 2


def test_clean_tree_exits_zero(tmp_path: Path) -> None:
    write(tmp_path, "src/a.cpp", "int x = 0;\n")
    assert style_check.main(["--root", str(tmp_path)]) == 0


def test_dirty_tree_exits_one(tmp_path: Path) -> None:
    write(tmp_path, "src/a.cpp", "int x = 0;")
    assert style_check.main(["--root", str(tmp_path)]) == 1


# --------------------------------------------------------------------------
# The conflict guard
# --------------------------------------------------------------------------

TRICKY_SOURCES = [
    # Concatenated string literals align to an arbitrary column.
    'void f()\n{\n    std::string m = "aaaaaaaaaaaaaaaaaaaaaaaaa" "bbbbbbbbbbbbbbbbbbbbbbbbbbbbb"'
    ' "ccccccccccccccccccccccc";\n}\n',
    # Stream chains align to the first insertion operator.
    "void f()\n{\n    stream << alpha_value << beta_value << gamma_value << delta_value"
    " << epsilon_value << zeta;\n}\n",
    # Long boolean conditions wrap.
    "void f()\n{\n    if (alpha_value > beta_value && gamma_value < delta_value"
    " && epsilon_value == zeta_value)\n    {\n        return;\n    }\n}\n",
    # Constructor initialiser lists.
    "class C\n{\n    C(int a, int b, int c) : alpha_(a), beta_(b), gamma_(c), delta_(0),"
    " epsilon_(0), zeta_(0)\n    {\n    }\n};\n",
    # Lambdas, aggregate initialisers, block comments, raw strings.
    'void f()\n{\n    auto g = [&](int x) { return x; };\n    int arr[] = {1, 2, 3};\n'
    '    /* block\n     * comment\n     */\n    const char* r = R"(\traw\n)";\n}\n',
    # Nested templates that force wrapping.
    "void f()\n{\n    std::map<std::string, std::vector<std::pair<int, double>>> lookup_table_name"
    " = build();\n}\n",
]


@pytest.mark.skipif(CLANG_FORMAT is None, reason="clang-format not installed")
@pytest.mark.parametrize("source", TRICKY_SOURCES)
def test_no_conflict_with_clang_format(tmp_path: Path, source: str) -> None:
    """clang-format's output must always satisfy the checker.

    If this fails, the two tools disagree about a column and the affected file
    cannot be made to pass both. Fix by widening CONTINUATION_PREFIXES or by
    changing .clang-format -- never by ignoring the file.
    """
    style = REPO_ROOT / ".clang-format"
    formatted = subprocess.run(
        [CLANG_FORMAT, f"--style=file:{style}", "--assume-filename=src/probe.cpp"],
        input=source,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    path = write(tmp_path, "src/probe.cpp", formatted)
    violations = style_check.check_file(path, tmp_path)
    assert violations == [], "\n".join(item.render(tmp_path) for item in violations)


@pytest.mark.skipif(CLANG_FORMAT is None, reason="clang-format not installed")
def test_project_sources_survive_a_format_round_trip(tmp_path: Path) -> None:
    """Formatting the real project must not introduce checker violations."""
    style = REPO_ROOT / ".clang-format"
    sources = [
        path
        for path in REPO_ROOT.rglob("*")
        if path.suffix in style_check.ALL_SUFFIXES
        and not style_check.is_excluded(path, REPO_ROOT)
    ]
    assert sources, "no project sources found -- this test would pass vacuously"

    for source in sources:
        relative = source.relative_to(REPO_ROOT)
        formatted = subprocess.run(
            [CLANG_FORMAT, f"--style=file:{style}", f"--assume-filename={relative}"],
            input=source.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        path = write(tmp_path, str(relative), formatted)
        violations = style_check.check_file(path, tmp_path)
        assert violations == [], "\n".join(item.render(tmp_path) for item in violations)
