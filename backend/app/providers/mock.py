"""Deterministic mock provider for tests, CI and offline demos."""

import math
from datetime import UTC, datetime, timedelta

from app.models import Candle
from app.providers.base import MarketDataProvider

_BASE_PRICES = {
    "BTCUSDT": 67000.0,
    "ETHUSDT": 3500.0,
    "SOLUSDT": 150.0,
}
_DEFAULT_BASE = 100.0


class MockDataProvider(MarketDataProvider):
    """Generates a smooth synthetic price series.

    Same symbol + params always yields the same series, so tests are
    deterministic. Prices ride a slow sine wave plus mild harmonics so that
    RSI/MACD/EMA produce a believable spread of BUY/SELL/HOLD outcomes.
    """

    def __init__(self, interval_seconds: int = 60) -> None:
        self._interval_seconds = interval_seconds

    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        symbol = symbol.upper()
        base = _BASE_PRICES.get(symbol, _DEFAULT_BASE)
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        candles: list[Candle] = []
        # Anchor to a fixed grid so results are stable within the interval.
        start = now - timedelta(minutes=self._interval_seconds * (limit - 1))
        for i in range(limit):
            t = start + timedelta(minutes=self._interval_seconds * i)
            price = self._price_at(base, t)
            prev = self._price_at(base, t - timedelta(minutes=self._interval_seconds))
            candles.append(
                Candle(
                    open_time=t,
                    open=prev,
                    high=max(prev, price) * 1.001,
                    low=min(prev, price) * 0.999,
                    close=price,
                    volume=1000 + 400 * math.sin(t.minute / 3.0),
                )
            )
        return candles

    async def healthcheck(self) -> bool:
        return True

    @staticmethod
    def _price_at(base: float, t: datetime) -> float:
        minutes = int(t.timestamp() // 60)
        wave = math.sin(minutes / 90.0) * 0.06 + math.sin(minutes / 17.0) * 0.02
        return round(base * (1 + wave), 2)
