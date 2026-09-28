"""Worker cycle tests and WebSocket endpoint tests."""

import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.config import Settings
from app.events import InMemoryEventBus
from app.main import app
from app.providers.mock import MockDataProvider
from app.services import SignalService
from app.store import InMemorySignalStore
from app.worker import SIGNALS_CHANNEL, SignalWorker


def build_worker(interval: int = 3600, bus: InMemoryEventBus | None = None):
    """Worker wired with mock provider and fake commentator (no LLM calls)."""
    settings = Settings(data_provider="mock", cache_ttl_seconds=0)
    bus = bus or InMemoryEventBus()
    store = InMemorySignalStore()

    class FakeCommentator:
        async def generate(self, signal):
            from app.ai.commentary import Commentary

            return Commentary(
                text=f"fake commentary for {signal.symbol}",
                risk_note="fake risk",
                source="rule-engine",
                generated_at=datetime.now(UTC),
            )

    worker = SignalWorker(
        service=SignalService(provider=MockDataProvider(), settings=settings),
        settings=settings,
        store=store,
        bus=bus,
        commentator=FakeCommentator(),
        interval_seconds=interval,
    )
    return worker, store, bus


class TestSignalWorker:
    async def test_run_cycle_generates_stores_and_publishes(self):
        worker, store, bus = build_worker()
        sub = bus.subscribe(SIGNALS_CHANNEL)
        signals = await worker.run_cycle()
        assert len(signals) == 3  # default watchlist
        assert worker.cycles == 1
        assert worker.signals_generated == 3
        assert worker.last_error is None
        # stored
        history = await store.history(limit=10)
        assert len(history) == 3
        # published with commentary attached
        payload = await asyncio.wait_for(sub.__anext__(), timeout=2)
        assert payload["symbol"] in {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
        assert payload["commentary"]["text"] == f"fake commentary for {payload['symbol']}"
        sub.close()

    async def test_loop_survives_cycle_errors(self):
        worker, store, bus = build_worker(interval=0.05)

        async def boom():
            raise RuntimeError("upstream down")

        worker._service.get_all_signals = boom  # force failure
        await worker.start()
        await asyncio.sleep(0.2)
        await worker.stop()
        assert worker.cycles == 0  # every cycle failed...
        assert "upstream down" in worker.last_error  # ...but error captured
        assert worker._running is False

    async def test_start_is_idempotent(self):
        worker, _, _ = build_worker()
        await worker.start()
        task1 = worker._task
        await worker.start()
        assert worker._task is task1
        await worker.stop()

    def test_status_shape(self):
        worker, _, _ = build_worker()
        status = worker.status()
        expected = {
            "running", "interval_s", "cycles", "signals_generated", "last_cycle_at", "last_error"
        }
        assert expected <= set(status)


class TestHistoryEndpoint:
    def test_history_empty_initially(self):
        client = TestClient(app)
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_stats_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        assert "total" in resp.json()

    def test_worker_status_endpoint(self):
        with TestClient(app) as client:  # lifespan starts the worker
            resp = client.get("/worker/status")
        assert resp.status_code == 200
        assert resp.json()["running"] is True


class TestWebSocket:
    def test_ws_snapshot_then_live_signal(self):
        with TestClient(app) as client:  # context manager runs lifespan
            with client.websocket_connect("/ws/signals") as ws:
                # 1) Immediate snapshot (latest stored signals).
                snapshot = ws.receive_json()
                assert snapshot["type"] == "snapshot"
                assert isinstance(snapshot["signals"], list)
                # 2) First live worker signal arrives within one fast interval.
                live = ws.receive_json()
                assert live["type"] == "signal"
                assert live["symbol"] in {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
                assert "commentary" in live
                assert "action" in live
