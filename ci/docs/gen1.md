# telemetry

A small C++20 telemetry parser, used here as the carrier for a self-hosted
Jenkins CI pipeline.

## Layout

```
CMakeLists.txt         owns policy: toolchain, flags, GoogleTest. Declares no targets.
BUILD.bazel            root package marker; targets live under platform/
.clang-format          layout rules clang-format can rewrite
.bazelrc               Bazel flags, mirrored from CMakeLists.txt
.bazelversion          pins Bazel; bazelisk reads this
Jenkinsfile            the pipeline

ci/                    everything Jenkins runs (see scripts below)
  checks/              the style checker and its own test suite
  docs/                setup notes

platform/
  ara/                 the modules; adding one is a single add_subdirectory line
    <module>/
      include/ara/<module>/   public headers, path mirrors the namespace
      src/                    implementation
      test/                   unit tests for this module only
      CMakeLists.txt          declares ara::<module>
      BUILD.bazel             cc_library + cc_test
  app/                 the shipped executable; composes modules, is not one
  test/                integration tests (pytest, black-box against the binary)
```

### Adding a module

Four things, no changes anywhere else:

1. `platform/ara/<name>/` with `include/ara/<name>/`, `src/`, `test/`
2. a `CMakeLists.txt` declaring the library and an `ara::<name>` alias
3. a `BUILD.bazel` with `cc_library` + `cc_test`
4. one `add_subdirectory(<name>)` line in `platform/ara/CMakeLists.txt`

CTest discovers the new unit tests automatically, and `bazel test //...`
picks up the new `cc_test` with no registration at all.

## Running it locally

Everything CI does, you can do on your own machine. That is the point.

```bash
# The whole pipeline, in order
ci/test-checks.sh
ci/check-flags.sh
ci/check-format.sh
ci/build-cmake.sh
ci/build-bazel.sh
ci/test-unit.sh
ci/test-integration.sh

# Or inside the exact CI image
docker build -t telemetry-ci ci/
docker run --rm -v "$PWD:/src" -w /src telemetry-ci ci/check-format.sh
```

Fix formatting in place:

```bash
clang-format -i --style=file:.clang-format $(git ls-files '*.cpp' '*.h')
```

## Style rules

clang-format owns layout. `ci/checks/style_check.py` owns the invariants
clang-format cannot express:

| Rule | Meaning |
|------|---------|
| R001 | no tabs in indentation |
| R002 | indentation is a multiple of 4 spaces |
| R003 | include guard named after the file's full path |
| R004 | file ends with exactly one newline |
| R005 | never more than two consecutive blank lines |
| R006 | opening brace always starts on its own line |
| R007 | no trailing whitespace |

R003 derives the guard from the path: `include/sensor_reader.h`
requires `INCLUDE_SENSOR_READER_H`. Moving a header changes its required guard. `#pragma once` is rejected.

R002 exempts continuation lines. clang-format aligns wrapped stream chains and
concatenated string literals to columns that are not multiples of 4; without
the exemption the two tools would demand different columns and the file could
not be made to pass both. `test_no_conflict_with_clang_format` guards this.

## Build flags

Every build uses `-g -fsanitize=address -fno-omit-frame-pointer -O0`.

`-fsanitize=address` must appear at **link** time as well as compile time.
`ci/build-cmake.sh` asserts the resulting binary contains `__asan` symbols, so
a half-instrumented build fails rather than quietly testing nothing.

`CMakeLists.txt` and `.bazelrc` each hold their own copy of the flag set.
`ci/check-flags.sh` asserts they match `REQUIRED_FLAGS` in `ci/lib.sh`.

## Running on a development machine

This setup is tuned to share a workstation with the editor rather than own a
dedicated box. Three things follow from that.

**The build is capped, not throttled.** The Jenkins agent runs with
`--cpus=4 --memory=16g`. With two Jenkins executors that is at most 8 cores in
flight, leaving 4 for the editor and language server. `--cpu-shares=512`
deprioritises the build when the host is busy without capping it when idle.

**nproc lies inside the container.** `--cpus` is a CFS quota; it does not
change how many CPUs the kernel reports. `nproc` inside a container limited to
4 CPUs on a 12-core host still says 12, so `-j$(nproc)` oversubscribes 3x.
`detect_jobs` in `ci/lib.sh` reads the cgroup quota instead. Bazel has the same
blind spot, which is why `.bazelrc` sets `--jobs`, `--local_cpu_resources` and
`--local_ram_resources` explicitly under `:ci`.

**Three numbers must stay in step:** `--cpus` in the `Jenkinsfile`, `--jobs`
and `--local_cpu_resources` in `.bazelrc`. Changing one alone reintroduces the
oversubscription.

### Local loop

```bash
ci/run-all.sh                # every stage, same order as Jenkins
ci/run-all.sh --keep-going   # see all failures at once, not one per run
ci/run-all.sh --docker       # inside the exact CI image
ci/run-all.sh --fast         # skip Bazel
```

If `ci/run-all.sh` is green, the Jenkins run is a formality. It calls the same
scripts, so there is no second implementation to drift.

### Security, on a machine that matters

Adding `jenkins` to the `docker` group is effectively granting root: anyone who
reaches the Docker socket can mount `/` and read your SSH keys, cloud
credentials and home directory. On a scratch laptop that is a small blast
radius. On your development machine it is not.

Two mitigations, both worth the effort here:

- **Rootless Docker** for the Jenkins user removes the docker-group-is-root
  escalation almost entirely.
- **Fork PR trust.** On a public repo, set *Discover pull requests from forks*
  to **Nobody** until you have thought about it. The default lets a stranger's
  PR modify `ci/build-cmake.sh` and run it on your machine with your token.

## Verifying a CI change

A check that passes proves nothing. Before merging a change to `ci/`:

1. `ci/test-checks.sh` — the checkers' own suite, every rule has a negative test
2. Break something on purpose and watch the stage go red
3. Confirm the status reaches GitHub and the merge button locks
