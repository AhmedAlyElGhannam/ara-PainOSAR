"""Shared fixtures for the integration suite.

The suite exercises the built binary as a black box, so it needs to know where
that binary is. Both build systems put it somewhere different, so the path is
passed in via TELEMETRY_BINARY rather than guessed.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--binary",
        action="store",
        default=None,
        help="path to the telemetry_cli binary under test",
    )


@pytest.fixture(scope="session")
def binary(request: pytest.FixtureRequest) -> Path:
    """Resolve the binary under test, failing loudly if it is missing.

    A missing binary must abort the suite, not skip it. A skipped integration
    suite reports green, which is exactly the silent pass these tests exist to
    prevent.
    """
    candidate = request.config.getoption("--binary") or os.environ.get("TELEMETRY_BINARY")
    if not candidate:
        pytest.exit(
            "No binary under test. Pass --binary or set TELEMETRY_BINARY. "
            "Refusing to run a vacuous integration suite.",
            returncode=2,
        )

    path = Path(candidate).resolve()
    if not path.is_file():
        pytest.exit(f"Binary under test does not exist: {path}", returncode=2)
    if not os.access(path, os.X_OK):
        pytest.exit(f"Binary under test is not executable: {path}", returncode=2)
    return path


@pytest.fixture(scope="session")
def asan_env() -> dict[str, str]:
    """Environment that turns any sanitizer finding into a non-zero exit."""
    env = dict(os.environ)
    env["ASAN_OPTIONS"] = "detect_leaks=1:abort_on_error=0:exitcode=99"
    return env


@pytest.fixture(scope="session", autouse=True)
def require_real_shell() -> None:
    if shutil.which("sh") is None:
        pytest.exit("No shell available", returncode=2)
