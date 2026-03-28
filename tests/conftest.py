"""Pytest configuration and shared fixtures for Exercise Competition tests.

This module provides:
- Test fixture paths and directories
- Pytest markers for test categorization
- Shared fixtures for common test resources
- Temporary directory management
"""

from pathlib import Path

import pytest

# ============================================================================
# Test Fixture Paths
# ============================================================================

# Root paths
PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "data" / "test_fixtures"
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"


# ============================================================================
# Pytest Markers
# ============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom CLI options."""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Include Playwright E2E browser tests (runs in subprocess server)",
    )


_E2E_PATH_MARKER = "/e2e/"


def _is_e2e(item: pytest.Item) -> bool:
    return _E2E_PATH_MARKER in str(item.fspath)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Exclude E2E tests unless --run-e2e is passed, and run them last."""
    if config.getoption("--run-e2e"):
        # Keep all tests, but ensure E2E runs after async unit tests
        # to avoid event loop conflicts between Playwright and pytest-asyncio
        e2e = [item for item in items if _is_e2e(item)]
        non_e2e = [item for item in items if not _is_e2e(item)]
        items[:] = non_e2e + e2e
    else:
        # Exclude E2E entirely (default — fast feedback loop)
        items[:] = [item for item in items if not _is_e2e(item)]


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers for test pyramid.

    Test Pyramid Markers:
        unit: Fast, isolated tests (no external dependencies)
        integration: Tests verifying component interaction
        security: Security-focused assertion tests
        perf: Performance and load tests
        slow: Tests that take significant time

    Args:
        config: Pytest configuration object.
    """
    # Test type markers (for test pyramid)
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (fast, isolated, no external dependencies)",
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (moderate speed, may use fixtures)",
    )
    config.addinivalue_line(
        "markers",
        "security: Security-focused tests (auth, input validation, etc.)",
    )
    config.addinivalue_line(
        "markers",
        "perf: Performance and load tests (benchmarking, stress testing)",
    )
    config.addinivalue_line(
        "markers",
        "performance: Alias for perf marker",
    )

    # Execution modifier markers
    config.addinivalue_line(
        "markers",
        "slow: Slow tests (can be excluded with -m 'not slow')",
    )
    config.addinivalue_line(
        "markers",
        "smoke: Smoke tests for quick sanity checks",
    )
    config.addinivalue_line(
        "markers",
        "regression: Regression tests for previously fixed bugs",
    )


# ============================================================================
# Fixture Directory Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return path to test fixtures directory.

    Returns:
        Path object pointing to the test fixtures directory.
    """
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def benchmarks_dir() -> Path:
    """Return path to benchmarks directory.

    Returns:
        Path object pointing to the benchmarks directory.
    """
    return BENCHMARKS_DIR


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Return temporary directory for test outputs.

    Creates and returns a clean temporary directory for each test to write
    output files.

    Args:
        tmp_path: Pytest's built-in tmp_path fixture.

    Returns:
        Path object pointing to the temporary output directory.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> Path:
    """Return temporary directory for caching.

    Creates and returns a clean temporary cache directory for each test.

    Args:
        tmp_path: Pytest's built-in tmp_path fixture.

    Returns:
        Path object pointing to the temporary cache directory.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


# ============================================================================
# Logging Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def setup_logging() -> None:
    """Setup test logging configuration.

    Automatically applied to all tests to ensure consistent logging setup.
    """
    from exercise_competition.utils.logging import setup_logging

    setup_logging(level="DEBUG", json_logs=False, include_timestamp=False)


def _find_rate_limiter():
    """Walk the middleware chain to find the RateLimitMiddleware instance."""
    from exercise_competition.main import app
    from exercise_competition.middleware.security import RateLimitMiddleware

    mw = app.middleware_stack
    while mw is not None:
        if isinstance(mw, RateLimitMiddleware):
            return mw
        mw = getattr(mw, "app", None)
    return None


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset rate limiter state between tests to prevent cross-test interference."""
    yield
    limiter = _find_rate_limiter()
    if limiter is not None:
        limiter.requests.clear()
