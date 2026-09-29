"""Shared fixtures."""

import os

# Never hit the real Binance API from tests.
os.environ.setdefault("DATA_PROVIDER", "mock")
# Fast worker ticks so WS/live tests do not wait a full minute.
os.environ.setdefault("WORKER_INTERVAL_SECONDS", "2")
# Metrics endpoint exercised by test_metrics.py.
os.environ.setdefault("METRICS_ENABLED", "true")

import math
from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.models import Candle
from app.providers.mock import MockDataProvider
from app.services import SignalService


def make_candles(
    n: int = 120, base: float = 100.0, wave_amp: float = 0.05, wave_len: int = 40
) -> list[Candle]:
    """Deterministic sine-wave candle factory for tests."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = []
    for i in range(n):
        price = base * (1 + wave_amp * math.sin(2 * math.pi * i / wave_len))
        prev = base * (1 + wave_amp * math.sin(2 * math.pi * (i - 1) / wave_len))
        candles.append(
            Candle(
                open_time=start + timedelta(minutes=i),
                open=prev,
                high=max(prev, price) * 1.0005,
                low=min(prev, price) * 0.9995,
                close=price,
                volume=1000 + 100 * math.sin(i / 5),
            )
        )
    return candles


@pytest.fixture
def candles() -> list[Candle]:
    return make_candles()


@pytest.fixture
def service() -> SignalService:
    settings = Settings(data_provider="mock", cache_ttl_seconds=0)
    return SignalService(provider=MockDataProvider(), settings=settings)
