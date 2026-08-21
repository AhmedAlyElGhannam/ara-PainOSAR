#!/usr/bin/env bash
#
# Run the whole pipeline locally, in the same order Jenkins does.
#
# On a development machine this is the loop that matters: you run it before
# pushing, and if it is green the Jenkins run is a formality. Every stage is
# the same script Jenkins calls, so there is no second implementation that can
# drift.
#
#   ci/run-all.sh              run every stage, stop at the first failure
#   ci/run-all.sh --keep-going run every stage, report a summary at the end
#   ci/run-all.sh --docker     run inside the CI image instead of the host
#   ci/run-all.sh --fast       skip the Bazel build (CMake only)
#
# --keep-going is the one to use while fixing a CI change: you want to see all
# the damage at once, not discover it one stage per run.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

KEEP_GOING=0
USE_DOCKER=0
FAST=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep-going) KEEP_GOING=1 ;;
        --docker)     USE_DOCKER=1 ;;
        --fast)       FAST=1 ;;
        -h|--help)    sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *)            die "unknown option: $1" ;;
    esac
    shift
done

cd "${REPO_ROOT}"

if [[ "${USE_DOCKER}" -eq 1 ]]; then
    require_tool docker
    log "building CI image"
    docker build -t telemetry-ci:local ci/

    log "re-running inside the container"
    exec docker run --rm \
        --cpus=4 \
        --memory=16g \
        -v "${REPO_ROOT}:/src" \
        -w /src \
        -v telemetry-ccache:/home/builder/.ccache \
        -e CCACHE_DIR=/home/builder/.ccache \
        telemetry-ci:local \
        ci/run-all.sh $([[ "${KEEP_GOING}" -eq 1 ]] && echo --keep-going) \
                      $([[ "${FAST}" -eq 1 ]] && echo --fast)
fi

STAGES=(
    "self-test:ci/test-checks.sh"
    "flag-parity:ci/check-flags.sh"
    "format:ci/check-format.sh"
    "build-cmake:ci/build-cmake.sh"
)

if [[ "${FAST}" -eq 0 ]] && command -v bazel >/dev/null 2>&1; then
    STAGES+=("build-bazel:ci/build-bazel.sh")
fi

STAGES+=(
    "unit:ci/test-unit.sh"
    "integration:ci/test-integration.sh"
)

RESULTS=()
FAILED=0
STARTED_AT=$(date +%s)

for entry in "${STAGES[@]}"; do
    name="${entry%%:*}"
    script="${entry#*:}"

    log "stage: ${name}"
    stage_start=$(date +%s)

    if bash "${script}"; then
        RESULTS+=("PASS ${name} ($(( $(date +%s) - stage_start ))s)")
    else
        status=$?
        RESULTS+=("FAIL ${name} (exit ${status}, $(( $(date +%s) - stage_start ))s)")
        FAILED=1
        if [[ "${KEEP_GOING}" -eq 0 ]]; then
            break
        fi
    fi
done

printf '\n\033[1m=== summary (%ss total, -j%s) ===\033[0m\n' \
    "$(( $(date +%s) - STARTED_AT ))" "${JOBS}"
for result in "${RESULTS[@]}"; do
    if [[ "${result}" == PASS* ]]; then
        printf '  \033[32m%s\033[0m\n' "${result}"
    else
        printf '  \033[31m%s\033[0m\n' "${result}"
    fi
done
printf '\n'

exit "${FAILED}"
