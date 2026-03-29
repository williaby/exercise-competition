"""Tests for main.py lifespan and app configuration.

Covers:
- main.py L32-37: lifespan startup/shutdown (setup_logging, init_db, log messages)
- main.py: static files mount at /static
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestLifespan:
    """Tests for the FastAPI app lifespan events."""

    def test_lifespan_calls_init_db(self) -> None:
        """init_db should be called during app startup."""
        with patch("exercise_competition.main.init_db") as mock_init:
            with patch("exercise_competition.main.setup_logging"):
                from exercise_competition.main import app

                with TestClient(app):
                    pass  # NOSONAR — entering/exiting context triggers lifespan events
            mock_init.assert_called_once()

    def test_lifespan_calls_setup_logging(self) -> None:
        """setup_logging should be called during app startup."""
        with patch("exercise_competition.main.setup_logging") as mock_setup:
            with patch("exercise_competition.main.init_db"):
                from exercise_competition.main import app

                with TestClient(app):
                    pass  # NOSONAR — entering/exiting context triggers lifespan events
            mock_setup.assert_called_once()

    def test_lifespan_logs_startup(self) -> None:
        """Startup log message should be emitted."""
        with (
            patch("exercise_competition.main.init_db"),
            patch("exercise_competition.main.setup_logging"),
            patch("exercise_competition.main.logger") as mock_logger,
        ):
            from exercise_competition.main import app

            with TestClient(app):
                pass

        # Check that startup message was logged
        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("Starting" in c for c in info_calls)

    def test_lifespan_logs_shutdown(self) -> None:
        """Shutdown log message should be emitted."""
        with (
            patch("exercise_competition.main.init_db"),
            patch("exercise_competition.main.setup_logging"),
            patch("exercise_competition.main.logger") as mock_logger,
        ):
            from exercise_competition.main import app

            with TestClient(app):
                pass

        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("Shutting down" in c for c in info_calls)


class TestStaticFiles:
    """Tests for static file mounting."""

    def test_static_route_exists(self) -> None:
        """/static should always be mounted."""
        from exercise_competition.main import app

        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/static" in route_paths
