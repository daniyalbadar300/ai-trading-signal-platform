"""FastAPI dependency providers."""

from functools import lru_cache

from app.ai.commentary import LLMCommentary
from app.config import Settings, get_settings
from app.events import InMemoryEventBus
from app.providers.base import MarketDataProvider
from app.providers.binance import BinanceProvider
from app.providers.mock import MockDataProvider
from app.services import SignalService
from app.store import InMemorySignalStore, SignalStore
from app.worker import SignalWorker


@lru_cache
def get_provider() -> MarketDataProvider:
    """Build the configured market data provider."""
    settings = get_settings()
    if settings.data_provider == "mock":
        return MockDataProvider()
    return BinanceProvider(base_url=settings.binance_base_url)


@lru_cache
def get_signal_service() -> SignalService:
    """Build the signal service singleton."""
    return SignalService(provider=get_provider(), settings=get_settings())


@lru_cache
def get_store() -> SignalStore:
    """Build the signal store: Redis when configured (lazy connect), else in-memory."""
    settings = get_settings()
    if settings.redis_url:
        import redis.asyncio as aioredis

        from app.redis_bus import RedisSignalStore

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        return RedisSignalStore(client)
    return InMemorySignalStore()


@lru_cache
def get_bus() -> InMemoryEventBus:
    """Build the local in-memory bus that WebSocket subscribers attach to."""
    return InMemoryEventBus()


@lru_cache
def get_worker() -> SignalWorker:
    """Build the background signal worker singleton (not auto-started)."""
    settings = get_settings()
    return SignalWorker(
        service=get_signal_service(),
        settings=settings,
        store=get_store(),
        bus=get_bus(),
        commentator=LLMCommentary(settings),
        interval_seconds=settings.worker_interval_seconds,
    )


def settings_dependency() -> Settings:
    """FastAPI dependency returning app settings."""
    return get_settings()


def signal_service_dependency() -> SignalService:
    """FastAPI dependency returning the signal service."""
    return get_signal_service()


def store_dependency() -> SignalStore:
    """FastAPI dependency returning the signal store."""
    return get_store()


def bus_dependency() -> InMemoryEventBus:
    """FastAPI dependency returning the event bus."""
    return get_bus()


def worker_dependency() -> SignalWorker:
    """FastAPI dependency returning the background worker."""
    return get_worker()
