// Pipeline as code.
//
// This file is deliberately thin. Every stage is one line calling a script in
// ci/, because a script can be run on a laptop in two seconds and a Jenkins
// stage can only be run by pushing a commit and waiting. When a build fails at
// 11pm you want `docker run <image> ci/build-cmake.sh`, not eight debug
// commits.
//
// Stage order is fail-fast: cheapest and most certain first.

pipeline
{
    agent
    {
        // Jenkins builds this image from the repo, so the toolchain is
        // versioned with the code that needs it. Changing a compiler version
        // and the code that requires it lands in a single reviewable commit.
        dockerfile
        {
            dir 'ci'
            filename 'Dockerfile'
            // Running on the development machine, so the build is capped
            // rather than allowed to take everything.
            //
            //   --cpus=4      of 12. Two Jenkins executors means at most 8
            //                 cores in flight, leaving 4 for the editor,
            //                 language server and browser. Note that this is
            //                 a CFS quota: nproc inside the container still
            //                 reports 12, which is why ci/lib.sh reads the
            //                 cgroup instead of trusting nproc.
            //   --memory=16g  of 64. AddressSanitizer roughly triples the
            //                 resident set, and the cap turns a runaway build
            //                 into one dead container instead of a machine
            //                 that swaps until it is unusable.
            //   --cpu-shares  deprioritises the build when the host is busy,
            //                 without capping it when the host is idle.
            //
            // Keep --cpus in step with --jobs / --local_cpu_resources in the
            // :ci section of .bazelrc.
            //
            // The cache mounts survive the container: a disposable
            // environment that keeps its compiler cache.
            args '''
                -e HOME=/home/builder
                --cpus=4
                --memory=16g
                --memory-swap=16g
                --cpu-shares=512
                -v telemetry-bazel-cache:/var/cache/bazel
                -v telemetry-ccache:/home/builder/.ccache
                -e CCACHE_DIR=/home/builder/.ccache
                -e CCACHE_MAXSIZE=20G
            '''
            reuseNode true
        }
    }

    options
    {
        timestamps()
        ansiColor('xterm')
        timeout(time: 45, unit: 'MINUTES')
        // Disk is the resource a laptop CI runs out of first, months in,
        // with a confusing error rather than "disk full".
        buildDiscarder(logRotator(numToKeepStr: '30', artifactNumToKeepStr: '10'))
        disableConcurrentBuilds(abortPrevious: true)
        skipDefaultCheckout(false)
    }

    environment
    {
        CI = '1'
        BUILD_DIR = "${env.WORKSPACE}/build"
        RESULTS_DIR = "${env.WORKSPACE}/build/test-results"
        ASAN_OPTIONS = 'detect_leaks=1:abort_on_error=0'
    }

    stages
    {
        stage('Self-test')
        {
            // The checkers are classifiers, so they have their own suite
            // proving they go red on known-bad input. Runs first and takes
            // under a second: a checker that silently passes everything is
            // worse than no checker, and this is what catches it.
            steps
            {
                sh 'ci/test-checks.sh'
            }
        }

        stage('Flag parity')
        {
            // CMakeLists.txt and .bazelrc each carry their own copy of the
            // mandated flag set. Nothing forces them to agree; this does.
            steps
            {
                sh 'ci/check-flags.sh'
            }
        }

        stage('Format')
        {
            steps
            {
                sh 'ci/check-format.sh'
            }
        }

        stage('Build')
        {
            // Both build systems are shipped, so both are built. A green CMake
            // build says nothing about whether the Bazel build even links.
            parallel
            {
                stage('CMake')
                {
                    steps
                    {
                        sh 'ci/build-cmake.sh'
                    }
                }
                stage('Bazel')
                {
                    steps
                    {
                        sh 'ci/build-bazel.sh'
                    }
                }
            }
        }

        stage('Unit tests')
        {
            steps
            {
                sh 'ci/test-unit.sh'
            }
        }

        stage('Integration tests')
        {
            // Slowest and flakiest, so last. No point spending minutes here on
            // a branch that failed to compile.
            steps
            {
                sh 'ci/test-integration.sh'
            }
        }
    }

    post
    {
        always
        {
            // allowEmptyResults stays false on purpose. An empty result set
            // means the tests did not run, which is a failure, not a pass.
            junit(
                testResults: 'build/test-results/*.xml',
                allowEmptyResults: false,
                skipPublishingChecks: false
            )

            archiveArtifacts(
                artifacts: 'build/test-results/*.xml, build/cmake/compile_commands.json',
                allowEmptyArchive: true,
                fingerprint: false
            )
        }

        cleanup
        {
            // The workspace goes; the named cache volumes above do not.
            cleanWs(
                deleteDirs: true,
                notFailBuild: true,
                patterns: [[pattern: 'build/**', type: 'INCLUDE']]
            )
        }
    }
}
