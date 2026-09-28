"""Publish/subscribe event bus for live signal distribution."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class EventBus(Protocol):
    """Minimal pub/sub surface; Phase 4 swaps in Redis-backed impl."""

    async def publish(self, channel: str, payload: dict[str, Any]) -> None: ...

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]: ...


class _Subscription:
    """Async iterator over one subscriber queue; closes cleanly on exit."""

    def __init__(self, queue: asyncio.Queue[dict[str, Any]], on_close) -> None:
        self._queue = queue
        self._on_close = on_close

    def __aiter__(self):
        return self

    async def __anext__(self) -> dict[str, Any]:
        return await self._queue.get()

    def close(self) -> None:
        self._on_close()


class InMemoryEventBus:
    """Per-subscriber bounded queues; slow subscribers drop oldest events."""

    def __init__(self, max_queue: int = 256) -> None:
        self._max_queue = max_queue
        self._subs: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        for queue in list(self._subs.get(channel, set())):
            if queue.qsize() >= self._max_queue:
                try:
                    queue.get_nowait()  # drop oldest for slow subscribers
                except asyncio.QueueEmpty:
                    pass
            await queue.put(payload)

    def subscribe(self, channel: str) -> _Subscription:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue)
        self._subs.setdefault(channel, set()).add(queue)
        return _Subscription(queue, lambda: self._subs[channel].discard(queue))

    def subscriber_count(self, channel: str) -> int:
        return len(self._subs.get(channel, set()))
