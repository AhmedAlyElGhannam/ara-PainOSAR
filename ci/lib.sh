#!/usr/bin/env bash
# Shared helpers. Sourced by every ci/*.sh script; not executable on its own.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

BUILD_DIR="${BUILD_DIR:-${REPO_ROOT}/build}"
RESULTS_DIR="${RESULTS_DIR:-${BUILD_DIR}/test-results}"
readonly BUILD_DIR RESULTS_DIR

# The flag set every build must use. Defined once; both build systems and this
# file are checked against each other by ci/check-flags.sh.
readonly REQUIRED_FLAGS="-g -fsanitize=address -fno-omit-frame-pointer -O0"

# Docker's --cpus flag sets a CFS quota; it does not change how many CPUs the
# kernel reports. nproc inside a container limited to --cpus=4 on a 12-core
# host still says 12, so a naive -j$(nproc) oversubscribes by 3x and the build
# spends its time context-switching while the rest of the machine stalls.
# Read the quota instead, and fall back to nproc when there is no limit.
detect_jobs()
{
    local quota period

    if [[ -r /sys/fs/cgroup/cpu.max ]]; then
        read -r quota period < /sys/fs/cgroup/cpu.max
        if [[ "${quota}" != "max" && "${period}" -gt 0 ]]; then
            echo $(( quota / period > 0 ? quota / period : 1 ))
            return
        fi
    fi

    if [[ -r /sys/fs/cgroup/cpu/cpu.cfs_quota_us && -r /sys/fs/cgroup/cpu/cpu.cfs_period_us ]]; then
        quota=$(< /sys/fs/cgroup/cpu/cpu.cfs_quota_us)
        period=$(< /sys/fs/cgroup/cpu/cpu.cfs_period_us)
        if [[ "${quota}" -gt 0 && "${period}" -gt 0 ]]; then
            echo $(( quota / period > 0 ? quota / period : 1 ))
            return
        fi
    fi

    nproc
}

# Explicit JOBS always wins; otherwise honour the container's CPU budget.
JOBS="${JOBS:-$(detect_jobs)}"
readonly JOBS

log()
{
    printf '\n\033[1m==> %s\033[0m\n' "$*"
}

warn()
{
    printf '\033[33mwarning:\033[0m %s\n' "$*" >&2
}

die()
{
    printf '\033[31merror:\033[0m %s\n' "$*" >&2
    exit 1
}

require_tool()
{
    command -v "$1" >/dev/null 2>&1 || die "required tool not found: $1"
}

# Fail loudly when a step produced no test results. A test stage that ran zero
# tests and reported success is the single most dangerous CI failure mode:
# the gate stays green while protecting nothing.
require_nonempty_results()
{
    local pattern="$1"
    local description="$2"
    # shellcheck disable=SC2086
    local count
    count=$(find ${pattern%/*} -name "${pattern##*/}" -type f 2>/dev/null | wc -l)
    if [[ "${count}" -eq 0 ]]; then
        die "${description} produced no result files (${pattern}). Treating as failure, not success."
    fi
    log "${description}: ${count} result file(s)"
}

mkdir -p "${RESULTS_DIR}"
