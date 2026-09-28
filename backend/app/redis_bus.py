"""Redis-backed event bus and signal store for cross-container operation.

Compose/K8s topology:
- worker container: generates signals, publishes via RedisEventBus and
  mirrors history into the RedisSignalStore.
- api container: RedisBridge taps the same channel and feeds the local
  InMemoryEventBus (which the WebSocket endpoint subscribes to); history
  and stats are served from the shared RedisSignalStore.
"""

import asyncio
import contextlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.events import InMemoryEventBus
from app.models import Signal
from app.store import SignalStore
from app.worker import SIGNALS_CHANNEL

logger = logging.getLogger(__name__)

HISTORY_KEY = "signals:history"
STATS_KEY = "signals:stats"
HISTORY_MAX = 2000


class RedisEventBus:
    """Publish-only side of Redis pub/sub (worker uses this)."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(payload, default=str))

    def subscribe(self, channel: str):  # pragma: no cover - not used by worker
        raise NotImplementedError("Use RedisBridge on the consuming side")

    def subscriber_count(self, channel: str) -> int:  # pragma: no cover
        return 0


class RedisSignalStore(SignalStore):
    """History mirrored into Redis lists/hashes (shared across containers)."""

    def __init__(self, redis: aioredis.Redis, max_history: int = HISTORY_MAX) -> None:
        self._redis = redis
        self._max = max_history

    async def save(self, signal: Signal) -> None:
        payload = signal.model_dump(mode="json")
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(HISTORY_KEY, json.dumps(payload))
            pipe.ltrim(HISTORY_KEY, -self._max, -1)
            pipe.hincrby(STATS_KEY, "total", 1)
            pipe.hincrby(STATS_KEY, signal.action.value, 1)
            await pipe.execute()

    async def latest(self, symbol: str) -> Signal | None:
        history = await self.history(symbol=symbol, limit=1)
        return history[0] if history else None

    async def history(self, symbol: str | None = None, limit: int = 50) -> list[Signal]:
        raw = await self._redis.lrange(HISTORY_KEY, -limit, -1)
        signals: list[Signal] = []
        for item in reversed(raw):  # newest first
            data = json.loads(item)
            if symbol and data.get("symbol") != symbol.upper():
                continue
            signals.append(Signal.model_validate(data))
        return signals[:limit]

    async def stats(self) -> dict:
        data = await self._redis.hgetall(STATS_KEY)
        return {
            "total": int(data.get("total", 0)),
            "actions": {
                k: int(v) for k, v in data.items() if k != "total"
            },
        }


class RedisBridge:
    """API-side listener: Redis channel -> local InMemoryEventBus (for WS)."""

    def __init__(self, redis: aioredis.Redis, local_bus: InMemoryEventBus) -> None:
        self._redis = redis
        self._local = local_bus
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._listen(), name="redis-bridge")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _listen(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(SIGNALS_CHANNEL)
        logger.info("redis bridge listening on %s", SIGNALS_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except (TypeError, ValueError):
                    continue
                await self._local.publish(SIGNALS_CHANNEL, payload)
        except asyncio.CancelledError:
            raise
        finally:
            with contextlib.suppress(Exception):
                await pubsub.aclose()


async def open_redis(url: str) -> aioredis.Redis:
    """Create a Redis client and verify connectivity."""
    client = aioredis.from_url(url, decode_responses=True)
    await client.ping()
    return client
