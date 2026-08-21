#!/usr/bin/env bash
#
# Stage 2a: compile with CMake.
#
# Out-of-tree build under build/cmake. Ninja rather than Make: it parallelises
# better and its output is quieter, which matters when you are reading a
# Jenkins console log.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tool cmake
require_tool g++

cd "${REPO_ROOT}"

CMAKE_BUILD_DIR="${BUILD_DIR}/cmake"
BUILD_TYPE="${BUILD_TYPE:-Debug}"

log "gcc $(g++ -dumpfullversion) / cmake $(cmake --version | head -1 | awk '{print $3}')"

# A stale cache is a classic phantom failure: CMake keeps the old compiler path
# and flags even after the image changes underneath it. Configuring from clean
# in CI costs seconds and removes the whole category.
if [[ "${CI:-0}" == "1" ]]; then
    rm -rf "${CMAKE_BUILD_DIR}"
fi

log "configure"
cmake -S . -B "${CMAKE_BUILD_DIR}" \
    -G Ninja \
    -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DTELEMETRY_BUILD_TESTS=ON

# Remove the outputs before building. If the build then fails, nothing is left
# on disk -- so a later test stage cannot silently run yesterday's binary and
# report green. Ninja leaves the previous artefacts in place on failure, which
# is exactly how a failed build turns into a passing test run.
rm -f "${CMAKE_BUILD_DIR}/platform/app/telemetry_cli"
find "${CMAKE_BUILD_DIR}" -name '*_tests' -type f -delete 2>/dev/null || true

log "build (-j${JOBS} of $(nproc) visible CPUs)"
cmake --build "${CMAKE_BUILD_DIR}" --parallel "${JOBS}"

# Assert the sanitizer actually made it into the binary. Passing
# -fsanitize=address to the compiler but not the linker is the most common way
# to end up with a build that looks instrumented and is not.
BINARY="${CMAKE_BUILD_DIR}/platform/app/telemetry_cli"
[[ -x "${BINARY}" ]] || die "expected binary not produced: ${BINARY}"

if command -v nm >/dev/null 2>&1; then
    # grep -c, not grep -q: -q closes the pipe on the first match, which sends
    # SIGPIPE to nm, and under `set -o pipefail` that turns a correctly
    # instrumented binary into a spurious "no __asan symbols" failure. -c reads
    # nm's output to the end, so the count is the only thing the assertion trusts.
    asan_symbols="$(nm -D "${BINARY}" 2>/dev/null | grep -c '__asan' || true)"
    if [[ "${asan_symbols}" -eq 0 ]]; then
        die "binary contains no AddressSanitizer symbols; check link options"
    fi
    log "AddressSanitizer symbols present (${asan_symbols})"
fi

log "cmake build passed: ${BINARY}"
