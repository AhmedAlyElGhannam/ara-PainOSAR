#!/usr/bin/env bash
#
# Stage 4: integration tests (pytest) against the built binary.
#
# Last, because it is the slowest and the most likely to be flaky. There is no
# value in spending minutes here on a branch that failed to compile.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tool python3

cd "${REPO_ROOT}"

BINARY="${TELEMETRY_BINARY:-${BUILD_DIR}/cmake/platform/app/telemetry_cli}"
[[ -x "${BINARY}" ]] || die "binary under test missing: ${BINARY} (run ci/build-cmake.sh first)"

log "pytest against ${BINARY}"

python3 -m pytest platform/test \
    --binary="${BINARY}" \
    --junitxml="${RESULTS_DIR}/pytest-integration.xml" \
    --timeout=120 \
    -v \
    --color=no

python3 - "${RESULTS_DIR}/pytest-integration.xml" <<'PYEOF'
import sys
import xml.etree.ElementTree as ET

path = sys.argv[1]
root = ET.parse(path).getroot()
suites = root.findall(".//testsuite") or [root]
total = sum(int(suite.get("tests", "0")) for suite in suites)
if total == 0:
    sys.exit(f"{path} reports 0 tests; the suite did not actually run")
print(f"pytest: {total} test(s)")
PYEOF

log "integration test stage passed"
