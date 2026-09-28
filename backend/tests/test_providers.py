"""Provider behaviour tests (no network)."""

import pytest

from app.providers.binance import BinanceProvider
from app.providers.cache import TTLCache
from app.providers.errors import ProviderError, SymbolNotFoundError
from app.providers.mock import MockDataProvider


class TestMockProvider:
    async def test_candles_shape(self):
        provider = MockDataProvider()
        candles = await provider.get_candles("BTCUSDT", "1m", 100)
        assert len(candles) == 100
        assert candles[0].open_time < candles[-1].open_time  # oldest first

    async def test_deterministic_within_interval(self):
        provider = MockDataProvider()
        a = await provider.get_candles("BTCUSDT", "1m", 50)
        b = await provider.get_candles("BTCUSDT", "1m", 50)
        assert [c.close for c in a] == [c.close for c in b]

    async def test_healthcheck_true(self):
        assert await MockDataProvider().healthcheck() is True


class TestTTLCache:
    async def test_caches_value(self):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            return "value"

        cache = TTLCache(ttl_seconds=60)
        assert await cache.get_or_set("k", factory) == "value"
        assert await cache.get_or_set("k", factory) == "value"
        assert calls["n"] == 1

    async def test_failure_not_cached(self):
        calls = {"n": 0}

        async def failing():
            calls["n"] += 1
            raise ProviderError("boom")

        async def ok():
            return "fine"

        cache = TTLCache(ttl_seconds=60)
        with pytest.raises(ProviderError):
            await cache.get_or_set("k", failing)
        assert await cache.get_or_set("k", ok) == "fine"
        assert calls["n"] == 1

    async def test_single_flight_coalesces(self):
        calls = {"n": 0}

        async def slow():
            calls["n"] += 1
            import asyncio

            await asyncio.sleep(0.01)
            return 42

        cache = TTLCache(ttl_seconds=60)
        import asyncio

        results = await asyncio.gather(*(cache.get_or_set("k", slow) for _ in range(5)))
        assert results == [42] * 5
        assert calls["n"] == 1


class TestBinanceProvider:
    async def test_parses_klines_row(self, monkeypatch):
        provider = BinanceProvider()

        async def fake_get(self, path, params=None):
            return [
                [
                    1700000000000, "67000.0", "67500.0", "66800.0", "67250.5",
                    "123.45", 1700000059999, "0", 10, "0", "0", "0",
                ]
            ]

        monkeypatch.setattr(BinanceProvider, "_get", fake_get)
        candles = await provider.get_candles("BTCUSDT", "1m", 1)
        assert candles[0].close == 67250.5
        assert candles[0].volume == 123.45
        assert candles[0].open == 67000.0

    async def test_invalid_symbol_maps_to_404(self, monkeypatch):
        provider = BinanceProvider()

        async def fake_get(self, path, params=None):
            raise SymbolNotFoundError("Invalid symbol")

        monkeypatch.setattr(BinanceProvider, "_get", fake_get)
        with pytest.raises(SymbolNotFoundError):
            await provider.get_candles("NOPEUSDT", "1m", 10)

    async def test_network_error_maps_to_provider_error(self, monkeypatch):
        provider = BinanceProvider()

        async def fake_get(self, path, params=None):
            raise ProviderError("Binance request failed")

        monkeypatch.setattr(BinanceProvider, "_get", fake_get)
        with pytest.raises(ProviderError):
            await provider.get_candles("BTCUSDT", "1m", 10)

    async def test_healthcheck_false_on_error(self, monkeypatch):
        provider = BinanceProvider()

        async def fake_get(self, path, params=None):
            raise ProviderError("down")

        monkeypatch.setattr(BinanceProvider, "_get", fake_get)
        assert await provider.healthcheck() is False
