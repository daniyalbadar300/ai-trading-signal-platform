"""API endpoint tests using FastAPI TestClient with mocked providers."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.providers.errors import SymbolNotFoundError

client = TestClient(app)


class TestOps:
    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "ai-trading-signal-platform"

    def test_health_ok_with_mock_provider(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["upstream_ok"] is True


class TestMarketEndpoints:
    def test_list_symbols(self):
        resp = client.get("/api/v1/symbols")
        assert resp.status_code == 200
        assert "BTCUSDT" in resp.json()["symbols"]

    def test_candles_endpoint(self):
        resp = client.get("/api/v1/candles/BTCUSDT?limit=50")
        assert resp.status_code == 200
        candles = resp.json()
        assert len(candles) == 50
        assert set(candles[0]) >= {"open_time", "open", "high", "low", "close", "volume"}

    def test_candles_validates_limit(self):
        resp = client.get("/api/v1/candles/BTCUSDT?limit=5")
        assert resp.status_code == 422  # below ge=10

    def test_candles_unknown_symbol_404(self):
        with patch(
            "app.services.SignalService.get_candles",
            side_effect=SymbolNotFoundError("Invalid symbol"),
        ):
            resp = client.get("/api/v1/candles/NOPEUSDT")
        assert resp.status_code == 404


class TestSignalEndpoints:
    def test_signal_for_symbol(self):
        resp = client.get("/api/v1/signals/BTCUSDT")
        assert resp.status_code == 200
        body = resp.json()
        assert body["symbol"] == "BTCUSDT"
        assert body["action"] in {"BUY", "SELL", "HOLD"}
        assert 0.0 <= body["confidence"] <= 1.0
        assert "indicators" in body and "rsi_14" in body["indicators"]

    def test_signals_for_watchlist(self):
        resp = client.get("/api/v1/signals")
        assert resp.status_code == 200
        signals = resp.json()
        assert len(signals) >= 3
        assert {s["action"] for s in signals} <= {"BUY", "SELL", "HOLD"}

    def test_signal_response_contains_contributions(self):
        resp = client.get("/api/v1/signals/ETHUSDT")
        body = resp.json()
        assert set(body["contributions"]) == {"rsi", "macd", "ema_cross", "bollinger", "volume"}
