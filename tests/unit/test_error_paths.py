"""Tests for error/failure paths to close remaining branch coverage gaps.

Covers:
- database.py L85-87: session rollback on exception
- health.py L99-101, L137: DB check failure and readiness 503
- routes.py L129: week range validation in POST handler
- logging.py L89, L116-118: noop processor and ImportError fallback
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import structlog

from exercise_competition.api.health import ReadinessCheck, check_database
from exercise_competition.utils.logging import setup_logging

# ===========================================================================
# database.py — session rollback on exception (L85-87)
# ===========================================================================


def _run_session_with_error(error_cls: type[Exception], msg: str) -> MagicMock:
    """Run get_session() with an injected error, returning the mock session."""
    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)

    with patch(
        "exercise_competition.core.database.get_session_factory",
        return_value=mock_factory,
    ):
        from exercise_competition.core.database import get_session

        with pytest.raises(error_cls, match=msg), get_session():
            raise error_cls(msg)

    return mock_session


class TestSessionRollback:
    """Tests for get_session() exception handling."""

    def test_rollback_on_exception(self) -> None:
        """Session.rollback() should be called when an exception occurs."""
        mock_session = _run_session_with_error(ValueError, "boom")
        mock_session.rollback.assert_called_once()

    def test_close_always_called(self) -> None:
        """Session.close() should be called even after an exception."""
        mock_session = _run_session_with_error(RuntimeError, "fail")
        mock_session.close.assert_called_once()

    def test_exception_propagates(self) -> None:
        """The original exception should propagate after rollback."""
        _run_session_with_error(TypeError, "specific error")


# ===========================================================================
# health.py — DB check failure paths (L99-101, L137)
# ===========================================================================


class TestHealthCheckFailure:
    """Tests for check_database and readiness failure paths."""

    def test_check_database_returns_error_on_failure(self) -> None:
        """check_database should return a failed ReadinessCheck on exception."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("connection refused")

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        with patch(
            "exercise_competition.core.database.get_session",
            return_value=mock_ctx,
        ):
            result = check_database()
            assert isinstance(result, ReadinessCheck)
            assert result.status is False
            assert result.error == "Database connectivity check failed"
            assert result.latency_ms is not None

    def test_readiness_503_when_db_down(self) -> None:
        """Readiness endpoint should return 503 when database check fails."""
        from fastapi.testclient import TestClient

        from exercise_competition.main import app

        failed_check = ReadinessCheck(
            name="database", status=False, latency_ms=1.0, error="db down"
        )
        with patch(
            "exercise_competition.api.health.check_database",
            return_value=failed_check,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health/ready")
            assert resp.status_code == 503

    def test_readiness_503_response_detail(self) -> None:
        """503 response should include check details."""
        from fastapi.testclient import TestClient

        from exercise_competition.main import app

        failed_check = ReadinessCheck(
            name="database", status=False, latency_ms=2.5, error="timeout"
        )
        with patch(
            "exercise_competition.api.health.check_database",
            return_value=failed_check,
        ):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/health/ready")
            body = resp.json()
            assert body["detail"]["status"] == "unavailable"
            assert "database" in body["detail"]["checks"]
            assert body["detail"]["checks"]["database"]["error"] == "timeout"


# ===========================================================================
# routes.py — week range validation (L129)
# ===========================================================================


class TestWeekRangeValidation:
    """Tests for week number out-of-range in POST /submit."""

    @pytest.fixture(autouse=True)
    def _setup_test_db(self, tmp_path):
        """Configure a fresh temp SQLite DB for each test."""
        import exercise_competition.core.database as db_module
        from exercise_competition.core.config import Settings

        db_path = tmp_path / "test.db"
        original_settings = db_module.settings
        db_module.settings = Settings(database_url=f"sqlite:///{db_path}")
        db_module.reset_engine()
        db_module.init_db()
        yield
        db_module.reset_engine()
        db_module.settings = original_settings

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from exercise_competition.main import app

        return TestClient(app, raise_server_exceptions=False)

    def _get_csrf_token(self, client) -> str:
        """Extract a valid CSRF token from the submit form."""
        resp = client.get("/submit")
        # Parse the CSRF token from the hidden input
        html = resp.text
        marker = 'name="csrf_token" value="'
        start = html.index(marker) + len(marker)
        end = html.index('"', start)
        return html[start:end]

    def test_submit_week_zero_shows_error(self, client) -> None:
        csrf = self._get_csrf_token(client)
        resp = client.post(
            "/submit",
            data={
                "csrf_token": csrf,
                "participant_name": "Byron Williams",
                "week_number": "0",
            },
        )
        assert resp.status_code == 200
        assert "Week number must be between 1 and 20" in resp.text

    def test_submit_week_21_shows_error(self, client) -> None:
        csrf = self._get_csrf_token(client)
        resp = client.post(
            "/submit",
            data={
                "csrf_token": csrf,
                "participant_name": "Byron Williams",
                "week_number": "21",
            },
        )
        assert resp.status_code == 200
        assert "Week number must be between 1 and 20" in resp.text


# ===========================================================================
# logging.py — untested branches (L89, L116-118)
# ===========================================================================


class TestLoggingBranches:
    """Tests for logging.py uncovered branches."""

    def test_noop_processor_used_when_no_timestamp(self) -> None:
        """When include_timestamp=False, noop processor should replace TimeStamper."""
        setup_logging(level="DEBUG", json_logs=False, include_timestamp=False)
        config = structlog.get_config()
        processors = config["processors"]
        # TimeStamper should not be in the processor list
        processor_types = [type(p).__name__ for p in processors]
        assert "TimeStamper" not in processor_types

    def test_json_mode_uses_json_renderer(self) -> None:
        """When json_logs=True, JSONRenderer should be the final processor."""
        setup_logging(level="INFO", json_logs=True)
        config = structlog.get_config()
        processors = config["processors"]
        last_processor = processors[-1]
        assert type(last_processor).__name__ == "JSONRenderer"

    def test_correlation_import_error_fallback(self) -> None:
        """setup_logging should succeed even if correlation module import fails."""
        with patch(
            "exercise_competition.utils.logging.structlog.stdlib.filter_by_level",
        ):
            # Patch the import inside setup_logging to fail
            import builtins

            original_import = builtins.__import__

            def _failing_import(name, *args, **kwargs):
                if "correlation" in name:
                    msg = "no correlation module"
                    raise ImportError(msg)
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", side_effect=_failing_import):
                # Should not raise
                setup_logging(
                    level="INFO",
                    json_logs=False,
                    include_correlation=True,
                )

    def test_no_correlation_processor_when_disabled(self) -> None:
        """When include_correlation=False, no correlation processor should be added."""
        setup_logging(level="INFO", json_logs=False, include_correlation=False)
        config = structlog.get_config()
        processors = config["processors"]
        processor_names = [getattr(p, "__name__", type(p).__name__) for p in processors]
        assert "correlation_context_processor" not in processor_names
