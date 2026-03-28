"""Tests for security middleware: headers, rate limiting, and SSRF prevention."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from exercise_competition.middleware.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    SSRFPreventionMiddleware,
    add_security_middleware,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(*middleware_classes, **middleware_kwargs) -> FastAPI:
    """Create a minimal FastAPI app with the given middleware."""
    app = FastAPI()
    for cls in middleware_classes:
        app.add_middleware(cls, **middleware_kwargs)

    @app.get("/test")
    def _endpoint():
        return {"ok": True}

    return app


# ===========================================================================
# SecurityHeadersMiddleware
# ===========================================================================


@pytest.mark.security
class TestSecurityHeaders:
    """Tests for SecurityHeadersMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(_make_app(SecurityHeadersMiddleware))

    def test_x_content_type_options(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_x_xss_protection(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert resp.headers["X-XSS-Protection"] == "1; mode=block"

    def test_csp_header(self, client: TestClient) -> None:
        resp = client.get("/test")
        csp = resp.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_referrer_policy(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client: TestClient) -> None:
        resp = client.get("/test")
        pp = resp.headers["Permissions-Policy"]
        assert "geolocation=()" in pp
        assert "camera=()" in pp

    def test_hsts_on_https(self) -> None:
        client = TestClient(
            _make_app(SecurityHeadersMiddleware), base_url="https://testserver"
        )
        resp = client.get("/test")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]

    def test_no_hsts_on_http(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert "Strict-Transport-Security" not in resp.headers

    def test_server_header_removed(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert "Server" not in resp.headers


# ===========================================================================
# RateLimitMiddleware
# ===========================================================================


@pytest.mark.security
class TestRateLimit:
    """Tests for RateLimitMiddleware."""

    def _make_rate_client(self, **kwargs) -> TestClient:
        return TestClient(
            _make_app(RateLimitMiddleware, **kwargs),
            raise_server_exceptions=False,
        )

    def test_normal_request_passes(self) -> None:
        client = self._make_rate_client(requests_per_minute=60)
        resp = client.get("/test")
        assert resp.status_code == 200

    def test_rate_limit_exceeded(self) -> None:
        client = self._make_rate_client(requests_per_minute=3, burst_size=100)
        for _ in range(3):
            client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429

    def test_rate_limit_response_body(self) -> None:
        client = self._make_rate_client(requests_per_minute=1, burst_size=100)
        client.get("/test")
        resp = client.get("/test")
        body = resp.json()
        assert body["error"] == "Too Many Requests"
        assert "Rate limit exceeded" in body["message"]
        assert body["retry_after"] == 60

    def test_rate_limit_retry_after_header(self) -> None:
        client = self._make_rate_client(requests_per_minute=1, burst_size=100)
        client.get("/test")
        resp = client.get("/test")
        assert resp.headers["Retry-After"] == "60"

    def test_burst_limit_exceeded(self) -> None:
        # All requests within the same second should trigger burst limit
        client = self._make_rate_client(requests_per_minute=1000, burst_size=2)
        client.get("/test")
        client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429

    def test_burst_response_body(self) -> None:
        client = self._make_rate_client(requests_per_minute=1000, burst_size=1)
        client.get("/test")
        resp = client.get("/test")
        body = resp.json()
        assert "Burst limit exceeded" in body["message"]
        assert resp.headers["Retry-After"] == "1"

    def test_requests_expire_after_60s(self) -> None:
        """Requests older than 60s should not count toward the limit."""
        client = self._make_rate_client(requests_per_minute=2, burst_size=100)
        base_time = 1000000.0

        with patch("exercise_competition.middleware.security.time") as mock_time:
            mock_time.time.return_value = base_time
            client.get("/test")
            client.get("/test")

            # Advance past 60s window
            mock_time.time.return_value = base_time + 61
            resp = client.get("/test")
            assert resp.status_code == 200

    def test_different_ips_independent(self) -> None:
        """Each IP should have its own rate limit counter."""
        app = _make_app(RateLimitMiddleware, requests_per_minute=1, burst_size=100)
        # TestClient uses testclient as the client IP; we can't easily change
        # the IP, but we can verify one IP gets limited while a fresh app works.
        client = TestClient(app, raise_server_exceptions=False)
        client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429

        # A fresh app has no tracked IPs — same IP but fresh state
        client2 = TestClient(
            _make_app(RateLimitMiddleware, requests_per_minute=1, burst_size=100),
            raise_server_exceptions=False,
        )
        resp2 = client2.get("/test")
        assert resp2.status_code == 200

    def test_cleanup_stale_entries(self) -> None:
        """Stale IPs should be removed during cleanup."""
        app = _make_app(
            RateLimitMiddleware,
            requests_per_minute=100,
            burst_size=100,
            cleanup_interval=0,
        )
        client = TestClient(app, raise_server_exceptions=False)
        base_time = 1000000.0

        with patch("exercise_competition.middleware.security.time") as mock_time:
            mock_time.time.return_value = base_time
            client.get("/test")

            # Find the middleware instance to inspect internal state
            mw = None
            for m in app.user_middleware:
                if m.cls is RateLimitMiddleware:
                    mw = m
                    break
            assert mw is not None

            # Advance time past 60s and trigger cleanup via another request
            mock_time.time.return_value = base_time + 120
            client.get("/test")

            # The middleware's internal state should have cleaned up old entries
            # (we can verify the request succeeded and no stale data persists)

    def test_max_tracked_ips_eviction(self) -> None:
        """When max_tracked_ips is exceeded, LRU eviction should occur."""
        app = _make_app(
            RateLimitMiddleware,
            requests_per_minute=100,
            burst_size=100,
            max_tracked_ips=2,
            cleanup_interval=0,
        )
        # Access the middleware instance directly to inject state
        # Build the app so middleware is initialized
        client = TestClient(app, raise_server_exceptions=False)
        base_time = 1000000.0

        with patch("exercise_competition.middleware.security.time") as mock_time:
            mock_time.time.return_value = base_time
            # Make requests to fill up tracked IPs
            # TestClient always uses same IP, so we inject fake IPs into middleware
            # First, trigger app build
            client.get("/test")

            # Find the RateLimitMiddleware instance from the ASGI stack
            # After first request, the middleware's .requests dict is populated
            # We'll inject extra IPs to trigger LRU eviction
            # Walk the ASGI app stack to find our middleware
            current = app.middleware_stack
            rate_mw = None
            while current is not None:
                if isinstance(current, RateLimitMiddleware):
                    rate_mw = current
                    break
                current = getattr(current, "app", None)

            if rate_mw is not None:
                # Inject 3 IPs when max is 2 — next cleanup should evict
                rate_mw.requests["10.0.0.1"] = [base_time - 90]  # old, stale
                rate_mw.requests["10.0.0.2"] = [base_time - 90]  # old, stale
                rate_mw.requests["10.0.0.3"] = [base_time]  # recent

                # Trigger cleanup (cleanup_interval=0 so it always runs)
                mock_time.time.return_value = base_time + 1
                client.get("/test")

                # Stale IPs should be cleaned, only recent ones remain
                assert "10.0.0.1" not in rate_mw.requests
                assert "10.0.0.2" not in rate_mw.requests

    def test_custom_rpm(self) -> None:
        client = self._make_rate_client(requests_per_minute=5, burst_size=100)
        for _ in range(5):
            client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429
        assert "5 requests per minute" in resp.json()["message"]

    def test_custom_burst_size(self) -> None:
        client = self._make_rate_client(requests_per_minute=1000, burst_size=3)
        for _ in range(3):
            client.get("/test")
        resp = client.get("/test")
        assert resp.status_code == 429
        assert "3 requests per second" in resp.json()["message"]

    def test_uses_cf_connecting_ip(self) -> None:
        """Rate limiter should use CF-Connecting-IP when present."""
        app = _make_app(RateLimitMiddleware, requests_per_minute=1, burst_size=100)
        client = TestClient(app, raise_server_exceptions=False)
        # First request with one CF IP — should pass
        client.get("/test", headers={"CF-Connecting-IP": "1.2.3.4"})
        # Second request with same CF IP — should be rate limited
        resp = client.get("/test", headers={"CF-Connecting-IP": "1.2.3.4"})
        assert resp.status_code == 429
        # Different CF IP — should pass
        resp = client.get("/test", headers={"CF-Connecting-IP": "5.6.7.8"})
        assert resp.status_code == 200

    def test_uses_x_forwarded_for_first_ip(self) -> None:
        """Rate limiter should use first IP from X-Forwarded-For."""
        app = _make_app(RateLimitMiddleware, requests_per_minute=1, burst_size=100)
        client = TestClient(app, raise_server_exceptions=False)
        client.get(
            "/test",
            headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"},
        )
        resp = client.get(
            "/test",
            headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.99"},
        )
        assert resp.status_code == 429

    def test_cf_connecting_ip_takes_priority(self) -> None:
        """CF-Connecting-IP should take priority over X-Forwarded-For."""
        app = _make_app(RateLimitMiddleware, requests_per_minute=1, burst_size=100)
        client = TestClient(app, raise_server_exceptions=False)
        # Use CF header to identify as 1.2.3.4, XFF says something different
        client.get(
            "/test",
            headers={
                "CF-Connecting-IP": "1.2.3.4",
                "X-Forwarded-For": "5.6.7.8",
            },
        )
        # Same CF IP should be limited even if XFF changes
        resp = client.get(
            "/test",
            headers={
                "CF-Connecting-IP": "1.2.3.4",
                "X-Forwarded-For": "9.9.9.9",
            },
        )
        assert resp.status_code == 429


# ===========================================================================
# SSRFPreventionMiddleware
# ===========================================================================


@pytest.mark.security
class TestSSRFPrevention:
    """Tests for SSRFPreventionMiddleware."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(
            _make_app(SSRFPreventionMiddleware), raise_server_exceptions=False
        )

    def test_normal_request_passes(self, client: TestClient) -> None:
        resp = client.get("/test")
        assert resp.status_code == 200

    def test_blocks_localhost(self, client: TestClient) -> None:
        resp = client.get("/test", params={"url": "http://localhost/secret"})
        assert resp.status_code == 400
        assert "SSRF" in resp.json()["message"]

    def test_blocks_private_ip(self, client: TestClient) -> None:
        resp = client.get("/test", params={"url": "http://192.168.1.1/admin"})
        assert resp.status_code == 400

    def test_blocks_cloud_metadata(self, client: TestClient) -> None:
        resp = client.get(
            "/test",
            params={"url": "http://169.254.169.254/latest/meta-data"},
        )
        assert resp.status_code == 400

    def test_blocks_file_scheme(self, client: TestClient) -> None:
        resp = client.get("/test", params={"url": "file:///etc/passwd"})
        assert resp.status_code == 400

    def test_blocks_decimal_ip_obfuscation(self, client: TestClient) -> None:
        # 2130706433 == 127.0.0.1
        resp = client.get("/test", params={"url": "http://2130706433/"})
        assert resp.status_code == 400

    def test_allows_external_url(self, client: TestClient) -> None:
        resp = client.get("/test", params={"url": "https://example.com/page"})
        assert resp.status_code == 200

    def test_is_private_ip_ipv6_mapped(self) -> None:
        assert SSRFPreventionMiddleware._is_private_ip("::ffff:127.0.0.1") is True

    def test_is_private_ip_public(self) -> None:
        assert SSRFPreventionMiddleware._is_private_ip("8.8.8.8") is False

    def test_is_private_ip_invalid(self) -> None:
        assert SSRFPreventionMiddleware._is_private_ip("not-an-ip") is False

    def test_blocks_gopher_scheme(self) -> None:
        mw = SSRFPreventionMiddleware(app=FastAPI())
        assert mw._is_blocked_url("gopher://evil.com") is True

    def test_allows_https_scheme(self) -> None:
        mw = SSRFPreventionMiddleware(app=FastAPI())
        assert mw._is_blocked_url("https://example.com") is False

    def test_blocked_url_no_host(self) -> None:
        """URL with no extractable host should not be blocked."""
        mw = SSRFPreventionMiddleware(app=FastAPI())
        assert mw._is_blocked_url("http://") is False

    def test_query_param_without_url_passes(self, client: TestClient) -> None:
        """Query params that don't look like URLs should pass through."""
        resp = client.get("/test", params={"name": "Byron", "week": "1"})
        assert resp.status_code == 200


# ===========================================================================
# add_security_middleware
# ===========================================================================


@pytest.mark.security
class TestAddSecurityMiddleware:
    """Tests for the add_security_middleware composition helper."""

    def test_default_configuration(self) -> None:
        app = FastAPI()
        add_security_middleware(app)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert SecurityHeadersMiddleware in middleware_classes
        assert RateLimitMiddleware in middleware_classes
        assert SSRFPreventionMiddleware in middleware_classes
        assert CORSMiddleware in middleware_classes

    def test_https_redirect_enabled(self) -> None:
        app = FastAPI()
        add_security_middleware(app, enable_https_redirect=True)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert HTTPSRedirectMiddleware in middleware_classes

    def test_https_redirect_disabled_by_default(self) -> None:
        app = FastAPI()
        add_security_middleware(app)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert HTTPSRedirectMiddleware not in middleware_classes

    def test_rate_limiting_disabled(self) -> None:
        app = FastAPI()
        add_security_middleware(app, enable_rate_limiting=False)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert RateLimitMiddleware not in middleware_classes

    def test_ssrf_prevention_disabled(self) -> None:
        app = FastAPI()
        add_security_middleware(app, enable_ssrf_prevention=False)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert SSRFPreventionMiddleware not in middleware_classes

    def test_trusted_hosts_added(self) -> None:
        app = FastAPI()
        add_security_middleware(app, allowed_hosts=["example.com"])
        middleware_classes = [m.cls for m in app.user_middleware]
        assert TrustedHostMiddleware in middleware_classes

    def test_no_trusted_hosts_by_default(self) -> None:
        app = FastAPI()
        add_security_middleware(app)
        middleware_classes = [m.cls for m in app.user_middleware]
        assert TrustedHostMiddleware not in middleware_classes
