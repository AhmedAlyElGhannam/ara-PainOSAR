#!/usr/bin/env bash
#
# Stage 3: unit tests (GoogleTest), through both build systems.
#
# Each ara module owns its own test binary, so this drives CTest rather than
# invoking a binary by path. CTest knows every registered test, which means
# adding a module needs no change here -- gtest_discover_tests in the module's
# test/CMakeLists.txt is the only registration point.
#
# Both build systems are run because both are shipped. A green CMake suite says
# nothing about whether the Bazel build even links.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

cd "${REPO_ROOT}"

CMAKE_BUILD_DIR="${BUILD_DIR}/cmake"

# ---- CMake / CTest -------------------------------------------------------
[[ -d "${CMAKE_BUILD_DIR}" ]] || die "no CMake build tree at ${CMAKE_BUILD_DIR} (run ci/build-cmake.sh first)"

log "gtest via CTest"
ctest --test-dir "${CMAKE_BUILD_DIR}" \
    --output-junit "${RESULTS_DIR}/ctest.xml" \
    --output-on-failure \
    --parallel "${JOBS}" \
    --no-tests=error

# --no-tests=error above already fails an empty run, but the XML is what
# Jenkins ingests, so assert on the artefact Jenkins will actually read.
python3 - "${RESULTS_DIR}/ctest.xml" <<'PYEOF'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
root = ET.parse(path).getroot()
suites = root.findall(".//testsuite") or [root]
total = sum(int(s.get("tests", "0")) for s in suites)
failures = sum(int(s.get("failures", "0")) for s in suites)
if total == 0:
    sys.exit(f"{path} reports 0 tests; the suite did not actually run")
print(f"ctest: {total} test(s), {failures} failure(s)")
PYEOF

# ---- Bazel ---------------------------------------------------------------
if command -v bazel >/dev/null 2>&1; then
    BAZEL_CONFIG=()
    [[ "${CI:-0}" == "1" ]] && BAZEL_CONFIG=(--config=ci)

    log "gtest via Bazel"
    bazel "${BAZEL_CONFIG[@]}" test --jobs="${JOBS}" //... || BAZEL_STATUS=$?

    TESTLOGS="$(bazel info bazel-testlogs 2>/dev/null || echo '')"
    if [[ -n "${TESTLOGS}" && -d "${TESTLOGS}" ]]; then
        index=0
        while IFS= read -r xml; do
            cp "${xml}" "${RESULTS_DIR}/bazel-${index}.xml"
            index=$((index + 1))
        done < <(find "${TESTLOGS}" -name 'test.xml' -type f)
        log "collected ${index} bazel result file(s)"
    fi

    [[ "${BAZEL_STATUS:-0}" -eq 0 ]] || die "bazel test failed with status ${BAZEL_STATUS}"
else
    warn "bazel not installed; skipping the Bazel unit run"
fi

require_nonempty_results "${RESULTS_DIR}/*.xml" "unit test stage"
log "unit test stage passed"
