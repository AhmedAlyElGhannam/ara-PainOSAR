#!/usr/bin/env bash
#
# Stage 0: test the CI's own checkers.
#
# This is the answer to "how do I know a CI change works". The style checker is
# a classifier, so it has its own suite proving it goes red on known-bad input
# and green on known-good input, plus a guard asserting clang-format's output
# always satisfies it.
#
# It runs first and takes under a second. A broken checker that silently passes
# everything is worse than no checker at all, and this is what catches it.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tool python3

cd "${REPO_ROOT}"

log "self-test: ci/checks"

python3 -m pytest ci/checks \
    --junitxml="${RESULTS_DIR}/pytest-ci-selftest.xml" \
    -q \
    --color=no

log "CI self-test passed"
