#!/usr/bin/env bash
#
# Stage 1: formatting and style.
#
# Two tools, deliberately. clang-format owns layout it can rewrite; the Python
# checker owns invariants clang-format cannot express (include-guard naming,
# indentation arithmetic, end-of-file shape).
#
# Runs in about two seconds, so it goes first: there is no point compiling a
# branch that will be rejected on whitespace.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tool clang-format
require_tool python3

cd "${REPO_ROOT}"

# Both discovery paths must agree on what this project owns. git ls-files
# already respects .gitignore; the find fallback has to prune build trees by
# hand or it walks into vendored upstream sources.
mapfile -t SOURCES < <(
    if git rev-parse --git-dir >/dev/null 2>&1; then
        git ls-files --cached --others --exclude-standard \
            '*.c' '*.cc' '*.cpp' '*.cxx' '*.h' '*.hh' '*.hpp' '*.hxx'
    else
        find . \
            \( -type d \( -name .git -o -name build -o -name _deps -o -name out \
                          -o -name 'bazel-*' -o -name third_party -o -name vendor \) -prune \) \
            -o -type f \( -name '*.c' -o -name '*.cc' -o -name '*.cpp' -o -name '*.cxx' \
                          -o -name '*.h' -o -name '*.hh' -o -name '*.hpp' -o -name '*.hxx' \) -print
    fi
)

if [[ "${#SOURCES[@]}" -eq 0 ]]; then
    die "no C++ sources found. The check is misconfigured, not passing."
fi

log "clang-format ($(clang-format --version)) on ${#SOURCES[@]} file(s)"

FORMAT_FAILED=0
for source in "${SOURCES[@]}"; do
    if ! diff -u --label "${source}" --label "${source} (formatted)" \
            "${source}" <(clang-format --style=file:.clang-format "${source}") > /tmp/fmt.diff; then
        cat /tmp/fmt.diff
        FORMAT_FAILED=1
    fi
done
rm -f /tmp/fmt.diff

if [[ "${FORMAT_FAILED}" -ne 0 ]]; then
    warn "run 'clang-format -i --style=file:.clang-format \$(git ls-files \"*.cpp\" \"*.h\")' to fix"
fi

log "project style rules"
STYLE_FAILED=0
python3 ci/checks/style_check.py --root . || STYLE_FAILED=$?

if [[ "${STYLE_FAILED}" -eq 2 ]]; then
    die "style_check reported a configuration error"
fi

if [[ "${FORMAT_FAILED}" -ne 0 || "${STYLE_FAILED}" -ne 0 ]]; then
    die "formatting stage failed"
fi

log "formatting stage passed"
