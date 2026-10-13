"""In-memory sliding-window rate limiter (per client IP).

Swap for Redis in multi-process deployments — interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict

from ..config import settings


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                oldest = bucket[0] if bucket else now
                retry_after = max(1, int(oldest + self.window_seconds - now))
                return RateLimitDecision(
                    allowed=False, remaining=0, retry_after_seconds=retry_after
                )
            bucket.append(now)
            return RateLimitDecision(
                allowed=True,
                remaining=self.max_requests - len(bucket),
                retry_after_seconds=0,
            )

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
