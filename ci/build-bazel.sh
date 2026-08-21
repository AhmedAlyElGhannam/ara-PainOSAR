#!/usr/bin/env bash
#
# Stage 2b: compile with Bazel.
#
# Bazel resolves its own version from .bazelversion via bazelisk, so this
# script never pins a version itself.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_tool bazel

cd "${REPO_ROOT}"

BAZEL_CONFIG=()
[[ "${CI:-0}" == "1" ]] && BAZEL_CONFIG=(--config=ci)

log "bazel $(bazel --version 2>/dev/null || echo 'version pending download')"

log "build //... (-j${JOBS})"
bazel "${BAZEL_CONFIG[@]}" build --jobs="${JOBS}" //...

BINARY="$(bazel "${BAZEL_CONFIG[@]}" cquery --output=files //platform/app:telemetry_cli 2>/dev/null | tail -1)"
[[ -n "${BINARY}" && -x "${BINARY}" ]] || die "bazel did not produce //platform/app:telemetry_cli"

log "bazel build passed: ${BINARY}"
