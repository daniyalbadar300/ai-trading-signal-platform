"""SignalStore and InMemoryEventBus behaviour tests."""

import asyncio
from datetime import UTC, datetime, timedelta

from app.events import InMemoryEventBus
from app.models import Signal, SignalAction
from app.store import InMemorySignalStore


def make_signal(symbol: str, minutes_ago: int = 0, action=SignalAction.BUY) -> Signal:
    from app.models import IndicatorSnapshot

    return Signal(
        symbol=symbol,
        action=action,
        confidence=0.5,
        score=0.2,
        price=100.0,
        indicators=IndicatorSnapshot(
            rsi_14=50, macd=0, macd_signal=0, macd_hist=0, ema_20=0,
            ema_50=0, bb_upper=0, bb_lower=0, bb_mid=0, volume_ratio=1,
        ),
        contributions={},
        generated_at=datetime.now(UTC) - timedelta(minutes=minutes_ago),
    )


class TestInMemorySignalStore:
    async def test_save_and_latest(self):
        store = InMemorySignalStore()
        assert await store.latest("BTCUSDT") is None
        s1 = make_signal("BTCUSDT", minutes_ago=5)
        s2 = make_signal("BTCUSDT")
        await store.save(s1)
        await store.save(s2)
        assert (await store.latest("BTCUSDT")) is s2

    async def test_history_newest_first(self):
        store = InMemorySignalStore()
        for age in (10, 5, 1):
            await store.save(make_signal("BTCUSDT", minutes_ago=age))
        history = await store.history("BTCUSDT", limit=10)
        ages = [s.generated_at for s in history]
        assert ages == sorted(ages, reverse=True)

    async def test_history_merged_across_symbols(self):
        store = InMemorySignalStore()
        await store.save(make_signal("BTCUSDT"))
        await store.save(make_signal("ETHUSDT"))
        merged = await store.history(limit=10)
        assert {s.symbol for s in merged} == {"BTCUSDT", "ETHUSDT"}

    async def test_stats_counts_actions(self):
        store = InMemorySignalStore()
        await store.save(make_signal("BTCUSDT", action=SignalAction.BUY))
        await store.save(make_signal("ETHUSDT", action=SignalAction.SELL))
        await store.save(make_signal("SOLUSDT", action=SignalAction.BUY))
        stats = await store.stats()
        assert stats["total"] == 3
        assert stats["actions"] == {"BUY": 2, "SELL": 1}

    async def test_per_symbol_trim(self):
        store = InMemorySignalStore(max_per_symbol=3)
        for _ in range(5):
            await store.save(make_signal("BTCUSDT"))
        history = await store.history("BTCUSDT", limit=10)
        assert len(history) == 3


class TestInMemoryEventBus:
    async def test_publish_without_subscribers_is_noop(self):
        bus = InMemoryEventBus()
        await bus.publish("ch", {"x": 1})  # must not raise

    async def test_subscriber_receives_payload(self):
        bus = InMemoryEventBus()
        sub = bus.subscribe("ch")
        await bus.publish("ch", {"price": 42})
        received = await asyncio.wait_for(sub.__anext__(), timeout=1)
        assert received == {"price": 42}
        sub.close()

    async def test_close_removes_subscription(self):
        bus = InMemoryEventBus()
        sub = bus.subscribe("ch")
        assert bus.subscriber_count("ch") == 1
        sub.close()
        assert bus.subscriber_count("ch") == 0

    async def test_slow_subscriber_drops_oldest(self):
        bus = InMemoryEventBus(max_queue=2)
        sub = bus.subscribe("ch")
        for i in range(4):
            await bus.publish("ch", {"i": i})
        # Drain: oldest two were dropped, latest two remain.
        first = await asyncio.wait_for(sub.__anext__(), timeout=1)
        second = await asyncio.wait_for(sub.__anext__(), timeout=1)
        assert [first["i"], second["i"]] == [2, 3]
        sub.close()
