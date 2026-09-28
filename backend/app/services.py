"""Service layer: cached market data + signal generation orchestration."""

from datetime import UTC, datetime

from app.config import Settings
from app.models import Candle, IndicatorSnapshot, Signal, SignalAction
from app.providers.base import MarketDataProvider
from app.providers.cache import TTLCache
from app.providers.errors import ProviderError
from app.signals.engine import generate_signal


class SignalService:
    """Coordinates provider calls, caching and the scoring engine."""

    def __init__(self, provider: MarketDataProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._cache = TTLCache(ttl_seconds=settings.cache_ttl_seconds)

    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        """Provider call with TTL caching (single-flight per key)."""
        symbol = symbol.upper()
        key = f"candles:{symbol}:{interval}:{limit}"
        return await self._cache.get_or_set(
            key, lambda: self._provider.get_candles(symbol, interval, limit)
        )

    async def get_signal(self, symbol: str, interval: str, limit: int) -> Signal:
        """Generate a signal for one symbol (uses the cached candles)."""
        candles = await self.get_candles(symbol, interval, limit)
        return generate_signal(symbol, candles, threshold=self._settings.signal_threshold)

    async def get_all_signals(self) -> list[Signal]:
        """Signals for every configured watchlist symbol."""
        results: list[Signal] = []
        for symbol in self._settings.symbol_list:
            try:
                results.append(
                    await self.get_signal(
                        symbol, self._settings.default_interval, self._settings.candle_limit
                    )
                )
            except ProviderError:
                results.append(self._error_signal(symbol))
        return results

    def _error_signal(self, symbol: str) -> Signal:
        """Placeholder HOLD signal so one bad symbol can't break the batch."""
        neutral = IndicatorSnapshot(
            rsi_14=50.0,
            macd=0.0,
            macd_signal=0.0,
            macd_hist=0.0,
            ema_20=0.0,
            ema_50=0.0,
            bb_upper=0.0,
            bb_lower=0.0,
            bb_mid=0.0,
            volume_ratio=1.0,
        )
        return Signal(
            symbol=symbol,
            action=SignalAction.HOLD,
            confidence=0.0,
            score=0.0,
            price=0.0,
            indicators=neutral,
            contributions={},
            generated_at=datetime.now(UTC),
        )
