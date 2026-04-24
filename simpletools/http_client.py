"""Central HTTP calls with timeouts and bounded retries (python-resilience skill)."""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

# Transient transport failures only — do not retry logical HTTP errors.
_RETRYABLE: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
    OSError,
)


@retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=0.4, max=10.0),
    reraise=True,
)
def request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Single entry point for outbound HTTP (timeouts + exponential backoff + jitter)."""
    timeout = kwargs.pop("timeout", 60.0)
    follow_redirects = kwargs.pop("follow_redirects", True)
    with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
        return client.request(method, url, **kwargs)


def get(url: str, **kwargs: Any) -> httpx.Response:
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any) -> httpx.Response:
    return request("POST", url, **kwargs)
