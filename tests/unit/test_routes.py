"""Unit tests for route helper functions (CSRF)."""

from __future__ import annotations

import time
from unittest.mock import patch

from exercise_competition.api.routes import (
    _generate_csrf_token,
    _validate_csrf_token,
)


class TestCSRF:
    """Tests for CSRF token generation and validation."""

    def test_generate_returns_string(self):
        token = _generate_csrf_token()
        assert isinstance(token, str)
        assert ":" in token

    def test_generate_format(self):
        token = _generate_csrf_token()
        parts = token.split(":")
        assert len(parts) == 2
        # First part is timestamp
        int(parts[0])

    def test_validate_valid_token(self):
        token = _generate_csrf_token()
        assert _validate_csrf_token(token) is True

    def test_validate_invalid_format(self):
        assert _validate_csrf_token("nocolon") is False

    def test_validate_invalid_signature(self):
        token = _generate_csrf_token()
        timestamp = token.split(":")[0]
        assert _validate_csrf_token(f"{timestamp}:badsig") is False

    def test_validate_expired_token(self):
        token = _generate_csrf_token()
        with patch("exercise_competition.api.routes.time") as mock_time:
            mock_time.time.return_value = time.time() + 7200  # 2 hours later
            assert _validate_csrf_token(token) is False

    def test_validate_empty_string(self):
        assert _validate_csrf_token("") is False

    def test_validate_non_numeric_timestamp(self):
        assert _validate_csrf_token("abc:def") is False
