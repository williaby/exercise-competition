"""Fixtures for Playwright E2E tests.

Starts a real Uvicorn server in a subprocess with a temporary SQLite
database so Playwright can drive a real browser against it.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time

import pytest


def _find_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 15) -> None:
    """Wait until the server is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    msg = f"Server at {host}:{port} did not start within {timeout}s"
    raise RuntimeError(msg)


@pytest.fixture(scope="session")
def base_url(tmp_path_factory) -> str:
    """Start a Uvicorn server in a subprocess and return its base URL.

    Uses a temporary SQLite database. The subprocess is killed when the
    session ends, keeping it fully isolated from the test process event loop.
    """
    db_path = tmp_path_factory.mktemp("e2e") / "e2e.db"
    port = _find_free_port()

    env = {
        **os.environ,
        "EXERCISE_COMPETITION_DATABASE_URL": f"sqlite:///{db_path}",
        "EXERCISE_COMPETITION_RATE_LIMIT_RPM": "10000",
    }

    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            "uvicorn",
            "exercise_competition.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        _wait_for_server("127.0.0.1", port)
    except RuntimeError:
        proc.kill()
        raise

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
