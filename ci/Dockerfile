# syntax=docker/dockerfile:1
#
# The build environment, versioned with the code that uses it.
#
# Pin to a digest once this stabilises:
#   docker pull gcc:16
#   docker inspect --format='{{index .RepoDigests 0}}' gcc:16
#   FROM gcc@sha256:<digest>
# A floating tag means an upstream rebuild can change your compiler without a
# commit in this repository, which is exactly the class of "worked yesterday"
# failure the container was supposed to eliminate.
FROM gcc:16

# Versions live here so a toolchain bump is a one-line, reviewable diff.
ARG CMAKE_VERSION=3.31.6
ARG CLANG_FORMAT_VERSION=20.1.7
ARG BAZELISK_VERSION=1.28.1
ARG GOOGLETEST_TAG=v1.17.0

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        ninja-build \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# CMake and clang-format come from PyPI rather than apt. Both ship real
# binaries there, and pinning an exact version is the whole point: a
# clang-format minor bump can reformat the entire codebase, which would turn
# every open pull request red at once.
RUN pip3 install --break-system-packages --no-cache-dir \
        "cmake==${CMAKE_VERSION}" \
        "clang-format==${CLANG_FORMAT_VERSION}"

# Python test tooling.
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --break-system-packages --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Bazelisk resolves the Bazel version from .bazelversion in the repo, so the
# image does not pin Bazel itself -- the repository does.
RUN ARCH="$(dpkg --print-architecture)" \
    && case "${ARCH}" in \
         amd64) BAZELISK_ARCH=amd64 ;; \
         arm64) BAZELISK_ARCH=arm64 ;; \
         *) echo "unsupported architecture: ${ARCH}" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /usr/local/bin/bazel \
        "https://github.com/bazelbuild/bazelisk/releases/download/v${BAZELISK_VERSION}/bazelisk-linux-${BAZELISK_ARCH}" \
    && chmod 0755 /usr/local/bin/bazel

# Vendor GoogleTest so CMake builds need no network. CMakeLists.txt points
# FetchContent at this directory when it exists.
RUN git clone --depth 1 --branch "${GOOGLETEST_TAG}" \
        https://github.com/google/googletest.git /opt/googletest \
    && rm -rf /opt/googletest/.git

# Jenkins launches this image with -u <uid>:<gid> matching the host jenkins
# user, which will not exist inside the container. Every path the build writes
# to therefore has to be world-writable, and HOME has to point somewhere real
# or Bazel and pip both fail with confusing permission errors.
RUN mkdir -p /var/cache/bazel/disk /var/cache/bazel/repo /home/builder \
    && chmod -R 0777 /var/cache/bazel /home/builder

ENV HOME=/home/builder \
    CC=gcc \
    CXX=g++ \
    ASAN_OPTIONS=detect_leaks=1:abort_on_error=0

WORKDIR /src

# Fail the image build rather than the pipeline if a tool is missing.
RUN gcc --version && g++ --version && cmake --version \
    && clang-format --version && python3 --version && pytest --version
