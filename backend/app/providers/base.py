"""Abstract provider interface. Swap Binance/Mock (or future PSX) freely."""

from abc import ABC, abstractmethod

from app.models import Candle


class MarketDataProvider(ABC):
    """Anything that can deliver OHLCV candles for a symbol."""

    @abstractmethod
    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        """Return `limit` most-recent candles for `symbol`, oldest first."""
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Return True if the upstream data source is reachable."""
        raise NotImplementedError
