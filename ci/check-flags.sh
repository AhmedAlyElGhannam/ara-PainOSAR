#!/usr/bin/env bash
#
# Guards against the two build systems drifting apart.
#
# CMakeLists.txt and .bazelrc each carry their own copy of the mandated flag
# set. Nothing in either file forces them to agree, so this asserts it. Without
# this check the two systems silently build different binaries and only one of
# them is the one you test.
#
# Comments are stripped before matching. A plain substring grep would happily
# find "-fsanitize=address" inside "# -fsanitize=address must also be passed
# at link time" and report parity for a build that has the flag commented out.
# That is the exact silent-pass this check exists to prevent, so it must not
# commit it itself.

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

cd "${REPO_ROOT}"

strip_comments()
{
    sed 's/#.*//' "$1"
}

# Match the flag as a whole token: preceded by start-of-line, whitespace or
# '=', and followed by whitespace or end-of-line. Substring matching would let
# "-g" match inside an unrelated longer flag.
has_flag()
{
    local file="$1" flag="$2"
    # A flag may be terminated by whitespace, end-of-line, a CMake closing
    # paren, a comma or a quote. Requiring whitespace alone rejects the last
    # entry of a CMake list -- "-fno-omit-frame-pointer)" -- and that false
    # positive would block every merge until someone reformatted the list.
    strip_comments "${file}" \
        | grep -qE -- "(^|[[:space:]]|=)${flag}([[:space:]]|[)\",]|$)"
}

MISSING=()

for flag in ${REQUIRED_FLAGS}; do
    has_flag CMakeLists.txt "${flag}" || MISSING+=("CMakeLists.txt: ${flag}")
    has_flag .bazelrc "${flag}" || MISSING+=(".bazelrc: ${flag}")
done

# AddressSanitizer at link time is the one people forget. Compile-only
# instrumentation links fine and detects nothing.
strip_comments CMakeLists.txt | grep -qE 'target_link_options.*telemetry_flags|^\s*-fsanitize=address' \
    || MISSING+=("CMakeLists.txt: no target_link_options carrying -fsanitize=address")
strip_comments .bazelrc | grep -qE -- '--linkopt=-fsanitize=address' \
    || MISSING+=(".bazelrc: -fsanitize=address missing from linkopt")

if [[ "${#MISSING[@]}" -gt 0 ]]; then
    printf 'required flag missing from build configuration:\n' >&2
    printf '  %s\n' "${MISSING[@]}" >&2
    die "build systems disagree with ci/lib.sh REQUIRED_FLAGS"
fi

log "flag parity verified: ${REQUIRED_FLAGS}"
