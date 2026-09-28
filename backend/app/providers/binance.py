"""Binance public REST provider - official API, no key required."""

import logging

import httpx

from app.models import Candle
from app.providers.base import MarketDataProvider
from app.providers.errors import ProviderError, SymbolNotFoundError

logger = logging.getLogger(__name__)

_KLINES_PATH = "/api/v3/klines"
_PING_PATH = "/api/v3/ping"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class BinanceProvider(MarketDataProvider):
    """Fetch OHLCV klines from the Binance public REST API."""

    def __init__(self, base_url: str = "https://api.binance.com") -> None:
        self._base_url = base_url.rstrip("/")

    async def get_candles(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        params = {"symbol": symbol.upper(), "interval": interval, "limit": min(limit, 1000)}
        try:
            data = await self._get(_KLINES_PATH, params)
        except SymbolNotFoundError:
            raise
        except ProviderError:
            raise
        candles: list[Candle] = []
        for row in data:
            # Binance kline row:
            # [open_time, open, high, low, close, volume, close_time, ...]
            candles.append(
                Candle(
                    open_time=row[0],  # ms epoch; pydantic coerces to datetime
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )
        return candles

    async def healthcheck(self) -> bool:
        try:
            await self._get(_PING_PATH)
            return True
        except ProviderError:
            return False

    async def _get(self, path: str, params: dict | None = None):
        """GET JSON from Binance with consistent error mapping."""
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Binance request failed: {exc}") from exc

        if resp.status_code == 400:
            # Binance returns 400 for unknown symbols / bad intervals
            detail = "bad request"
            if resp.headers.get("content-type", "").startswith("application/json"):
                detail = resp.json().get("msg", detail)
            if "Invalid symbol" in detail:
                raise SymbolNotFoundError(detail)
            raise ProviderError(f"Binance 400: {detail}")
        if resp.status_code in (418, 429):
            raise ProviderError("Binance rate limit / ban triggered")
        if resp.status_code >= 500:
            raise ProviderError(f"Binance server error: {resp.status_code}")
        if resp.status_code != 200:
            raise ProviderError(f"Unexpected Binance response: {resp.status_code}")
        return resp.json()
