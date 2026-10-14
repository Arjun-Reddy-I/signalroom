"""Simple in-memory rate limiter for authentication endpoints.

Uses a sliding window per (IP, endpoint) key. Suitable for a single-process
deployment. For multi-process production, replace with Redis-backed storage.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi import status as http_status

from app.core.config import settings
from app.core.exceptions import AppException


class RateLimitError(AppException):
    def __init__(self, retry_after: int = settings.AUTH_LOCKOUT_SECONDS) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message=(
                f"Too many failed attempts. Please wait {retry_after // 60} minutes before trying again."
            ),
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after},
        )


# {key: deque of timestamps}
_attempt_log: dict[str, deque[float]] = defaultdict(deque)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def record_failed_attempt(request: Request, endpoint: str = "auth") -> None:
    """Record a failed attempt and raise RateLimitError if limit exceeded."""
    ip = _get_client_ip(request)
    key = f"{ip}:{endpoint}"
    now = time.monotonic()
    window = settings.AUTH_LOCKOUT_SECONDS
    max_attempts = settings.AUTH_MAX_ATTEMPTS

    dq = _attempt_log[key]

    # Remove stale entries outside the window
    while dq and now - dq[0] > window:
        dq.popleft()

    dq.append(now)

    if len(dq) > max_attempts:
        raise RateLimitError(retry_after=window)


def check_rate_limit(request: Request, endpoint: str = "auth") -> None:
    """Check if the IP is currently rate-limited (call before processing)."""
    ip = _get_client_ip(request)
    key = f"{ip}:{endpoint}"
    now = time.monotonic()
    window = settings.AUTH_LOCKOUT_SECONDS
    max_attempts = settings.AUTH_MAX_ATTEMPTS

    dq = _attempt_log[key]
    while dq and now - dq[0] > window:
        dq.popleft()

    if len(dq) >= max_attempts:
        raise RateLimitError(retry_after=window)


def clear_attempts(request: Request, endpoint: str = "auth") -> None:
    """Clear attempts for a successful login."""
    ip = _get_client_ip(request)
    key = f"{ip}:{endpoint}"
    _attempt_log.pop(key, None)
