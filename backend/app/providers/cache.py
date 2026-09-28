"""Tiny async TTL cache so we never hammer upstream APIs."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any


class TTLCache:
    """Per-key TTL cache with single-flight coalescing.

    Concurrent calls for the same key share one upstream request. The
    in-flight future is awaited OUTSIDE the lock: holding the lock across
    that await would deadlock, because the owning coroutine needs the same
    lock to publish its result.
    """

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._inflight: dict[str, asyncio.Future[Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        hit = self._store.get(key)
        if hit and time.monotonic() - hit[0] < self._ttl:
            return hit[1]

        future: asyncio.Future[Any] | None = None
        owner = False
        async with self._lock:
            # Re-check under the lock: another coroutine may have finished.
            hit = self._store.get(key)
            if hit and time.monotonic() - hit[0] < self._ttl:
                return hit[1]
            if key in self._inflight:
                future = self._inflight[key]
            else:
                future = asyncio.get_running_loop().create_future()
                self._inflight[key] = future
                owner = True

        if not owner and future is not None:
            # Wait outside the lock; result arrives via set_result below.
            return await asyncio.shield(future)

        assert future is not None
        try:
            value = await factory()
        except BaseException:
            # Never leave a poisoned future or cache entry behind.
            async with self._lock:
                self._inflight.pop(key, None)
            future.cancel()
            raise

        self._store[key] = (time.monotonic(), value)
        async with self._lock:
            self._inflight.pop(key, None)
        future.set_result(value)
        return value

    def invalidate(self, key: str | None = None) -> None:
        """Drop one key or the entire cache."""
        if key is None:
            self._store.clear()
        else:
            self._store.pop(key, None)
