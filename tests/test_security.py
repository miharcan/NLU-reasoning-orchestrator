import pytest

from app.security import ApiKeyAuth, SlidingWindowRateLimiter


def test_api_key_auth_disabled_allows_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)

    auth = ApiKeyAuth()

    assert auth.is_authorized(path="/analyze", method="POST", api_key=None) is True


def test_api_key_auth_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "key-1,key-2")

    auth = ApiKeyAuth()

    assert auth.is_authorized(path="/analyze", method="POST", api_key=None) is False
    assert auth.is_authorized(path="/analyze", method="POST", api_key="bad") is False
    assert auth.is_authorized(path="/analyze", method="POST", api_key="key-1") is True


def test_rate_limiter_blocks_over_limit() -> None:
    limiter = SlidingWindowRateLimiter(enabled=True, requests_per_minute=2)

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
