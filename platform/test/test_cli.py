"""End-to-end tests: drive the built binary through stdin/stdout.

These complement the gtest unit suite. Unit tests check functions in isolation;
these check that the program as shipped reads its input, writes its output, and
uses its exit codes the way the contract says.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def run(binary: Path, stdin: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_formats_a_single_record(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "1700000000,21.5,C\n", asan_env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "INFO 1700000000 21.5C"


def test_escalates_severity_by_value(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "1,10.0,C\n2,75.0,C\n3,150.0,C\n", asan_env)
    assert result.returncode == 0, result.stderr

    lines = result.stdout.strip().splitlines()
    assert [line.split()[0] for line in lines] == ["INFO", "WARN", "ERROR"]


def test_malformed_record_sets_exit_code_one(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "1,1.0,C\nnot-a-record\n", asan_env)
    assert result.returncode == 1
    assert "rejected 1" in result.stderr


def test_empty_input_is_not_an_error(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "", asan_env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_blank_lines_are_skipped_silently(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "1,1.0,C\n\n\n2,2.0,C\n", asan_env)
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.strip().splitlines()) == 2


@pytest.mark.parametrize("size", [1000, 5000])
def test_handles_large_input_without_sanitizer_findings(
    binary: Path, asan_env: dict[str, str], size: int
) -> None:
    """A sanitizer finding exits 99 (see the asan_env fixture), never 0."""
    payload = "".join(f"{index},{index % 200}.5,C\n" for index in range(size))
    result = run(binary, payload, asan_env)

    assert result.returncode == 0, f"exit {result.returncode}\n{result.stderr}"
    assert len(result.stdout.strip().splitlines()) == size


def test_unit_field_is_passed_through(binary: Path, asan_env: dict[str, str]) -> None:
    result = run(binary, "1,1.0,kPa\n", asan_env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("kPa")
