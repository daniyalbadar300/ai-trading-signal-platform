"""Standalone worker entrypoint: `python -m app.worker_main`.

Runs the SignalWorker outside the API process — the container command used
by Docker/K8s. With REDIS_URL set, signals are published through Redis
pub/sub and history/stats are mirrored into the shared Redis store.
"""

import asyncio

from app.ai.commentary import LLMCommentary
from app.config import get_settings
from app.dependencies import get_provider
from app.events import InMemoryEventBus
from app.logging import setup_logging
from app.services import SignalService
from app.store import InMemorySignalStore, SignalStore
from app.worker import SignalWorker


async def build_worker() -> SignalWorker:
    """Wire a worker; Redis-backed bus/store when REDIS_URL is configured."""
    settings = get_settings()
    service = SignalService(provider=get_provider(), settings=settings)

    if settings.redis_url:
        import redis.asyncio as aioredis

        from app.redis_bus import RedisEventBus, RedisSignalStore

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        bus = RedisEventBus(client)
        store: SignalStore = RedisSignalStore(client)
    else:
        bus = InMemoryEventBus()
        store = InMemorySignalStore()

    return SignalWorker(
        service=service,
        settings=settings,
        store=store,
        bus=bus,
        commentator=LLMCommentary(settings),
        interval_seconds=max(15, settings.worker_interval_seconds),
    )


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    if settings.metrics_enabled:
        from prometheus_client import start_http_server

        start_http_server(8000)  # worker-side metrics (:8000, path /)
    worker = await build_worker()
    await worker.start()
    print(  # noqa: T201
        f"worker running (provider={settings.data_provider}, "
        f"redis={'yes' if settings.redis_url else 'no'}, interval={worker._interval}s)"
    )
    try:
        await asyncio.Event().wait()  # run forever
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
