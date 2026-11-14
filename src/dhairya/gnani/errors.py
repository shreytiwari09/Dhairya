"""Typed Gnani errors and the retry rule. Never put the API key in a message."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from dhairya.config import RETRY_FIRST_DELAY_S, RETRY_TRIES

log = logging.getLogger(__name__)
T = TypeVar("T")


class GnaniError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"Gnani API returned {status}: {body[:300]}")
        self.status = status
        self.body = body


class GnaniAuthError(GnaniError): ...  # 401, 403


class GnaniCreditError(GnaniError): ...  # 402


class GnaniRateLimitError(GnaniError): ...  # 429


class GnaniBadRequestError(GnaniError): ...  # 400, 422


class GnaniServerError(GnaniError): ...  # 5xx


class GnaniStreamClosed(Exception): ...


def error_for(status: int, body: str) -> GnaniError:
    if status in (401, 403):
        return GnaniAuthError(status, body)
    if status == 402:
        return GnaniCreditError(status, body)
    if status == 429:
        return GnaniRateLimitError(status, body)
    if status in (400, 422):
        return GnaniBadRequestError(status, body)
    if status >= 500:
        return GnaniServerError(status, body)
    return GnaniError(status, body)


def with_retry(call: Callable[[], T]) -> T:
    """Retry only rate limits and server errors; everything else fails at once."""
    delay = RETRY_FIRST_DELAY_S
    for attempt in range(1, RETRY_TRIES + 1):
        try:
            return call()
        except (GnaniRateLimitError, GnaniServerError) as exc:
            if attempt == RETRY_TRIES:
                raise
            log.warning(
                "Gnani %s, retry %d of %d in %.0fs", exc.status, attempt, RETRY_TRIES, delay
            )
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")
