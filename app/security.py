from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict


class ApiKeyAuth:
    def __init__(self) -> None:
        self.enabled = _bool_env("API_AUTH_ENABLED", False)
        keys_raw = os.getenv("API_KEYS", "")
        self.api_keys = {k.strip() for k in keys_raw.split(",") if k.strip()}
        exempt_raw = os.getenv(
            "API_AUTH_EXEMPT_PATHS",
            "/health,/openapi.json,/docs,/docs/oauth2-redirect,/redoc",
        )
        self.exempt_paths = {p.strip() for p in exempt_raw.split(",") if p.strip()}

    def is_authorized(self, path: str, method: str, api_key: str | None) -> bool:
        if method.upper() == "OPTIONS":
            return True
        if not self.enabled:
            return True
        if path in self.exempt_paths:
            return True
        if not self.api_keys:
            # Misconfigured secure mode: fail closed.
            return False
        return bool(api_key and api_key in self.api_keys)


class SlidingWindowRateLimiter:
    def __init__(self, enabled: bool, requests_per_minute: int) -> None:
        self.enabled = enabled
        self.requests_per_minute = max(1, requests_per_minute)
        self._lock = Lock()
        self._windows: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        if not self.enabled:
            return True

        now = time.time()
        cutoff = now - 60.0
        with self._lock:
            window = self._windows[key]
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= self.requests_per_minute:
                return False
            window.append(now)
            return True


def build_rate_limiter() -> SlidingWindowRateLimiter:
    enabled = _bool_env("RATE_LIMIT_ENABLED", False)
    requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
    return SlidingWindowRateLimiter(enabled=enabled, requests_per_minute=requests_per_minute)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
