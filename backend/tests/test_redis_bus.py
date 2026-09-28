"""Redis bus/store tests with an in-memory fake Redis (no live redis needed)."""

import json
from datetime import UTC, datetime

from app.models import IndicatorSnapshot, Signal, SignalAction
from app.redis_bus import RedisEventBus, RedisSignalStore


class FakePipeline:
    """Collects rpush/ltrim/hincrby and applies them on execute()."""

    def __init__(self, parent: "FakeRedis"):
        self._parent = parent
        self._ops: list[tuple] = []

    def rpush(self, key, value):
        self._ops.append(("rpush", key, value))
        return self

    def ltrim(self, key, start, end):
        self._ops.append(("ltrim", key, start, end))
        return self

    def hincrby(self, key, field, amount):
        self._ops.append(("hincrby", key, field, amount))
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self):
        for op in self._ops:
            if op[0] == "rpush":
                self._parent.lists.setdefault(op[1], []).append(op[2])
            elif op[0] == "ltrim":
                _, key, start, end = op
                lst = self._parent.lists[key]
                self._parent.lists[key] = lst[start:] if end == -1 else lst[start:end]
            elif op[0] == "hincrby":
                _, key, field, amount = op
                hashes = self._parent.hashes.setdefault(key, {})
                hashes[field] = hashes.get(field, 0) + amount
        self._ops.clear()


class FakeRedis:
    def __init__(self):
        self.lists: dict[str, list] = {}
        self.hashes: dict[str, dict] = {}
        self.published: list[tuple[str, str]] = []

    def pipeline(self, transaction: bool = True):
        return FakePipeline(self)

    async def aclose(self):  # parity with real client
        return None

    async def lrange(self, key, start, end):
        lst = self.lists.get(key, [])
        # Redis lrange is end-inclusive; negative indices count from the tail.
        n = len(lst)
        s = start if start >= 0 else max(n + start, 0)
        e = end + 1 if end >= 0 else n + end + 1
        return lst[s:e]

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def ping(self):
        return True


def make_signal(symbol: str, minutes_ago: int = 0, action=SignalAction.BUY) -> Signal:
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
        generated_at=datetime.now(UTC),
    )


class TestRedisSignalStore:
    async def test_save_and_history_newest_first(self):
        fake = FakeRedis()
        store = RedisSignalStore(fake)
        await store.save(make_signal("BTCUSDT", action=SignalAction.BUY))
        await store.save(make_signal("ETHUSDT", action=SignalAction.SELL))
        history = await store.history(limit=10)
        assert [s.action for s in history] == [SignalAction.SELL, SignalAction.BUY]

    async def test_history_symbol_filter(self):
        fake = FakeRedis()
        store = RedisSignalStore(fake)
        await store.save(make_signal("BTCUSDT"))
        await store.save(make_signal("ETHUSDT"))
        await store.save(make_signal("BTCUSDT"))
        history = await store.history(symbol="BTCUSDT", limit=10)
        assert {s.symbol for s in history} == {"BTCUSDT"}

    async def test_stats_accumulate(self):
        fake = FakeRedis()
        store = RedisSignalStore(fake)
        await store.save(make_signal("BTCUSDT", action=SignalAction.BUY))
        await store.save(make_signal("ETHUSDT", action=SignalAction.SELL))
        await store.save(make_signal("SOLUSDT", action=SignalAction.BUY))
        stats = await store.stats()
        assert stats["total"] == 3
        assert stats["actions"] == {"BUY": 2, "SELL": 1}

    async def test_history_trimmed_to_max(self):
        fake = FakeRedis()
        store = RedisSignalStore(fake, max_history=5)
        for _ in range(8):
            await store.save(make_signal("BTCUSDT"))
        assert len(fake.lists["signals:history"]) == 5


class TestRedisEventBus:
    async def test_publish_sends_json(self):
        fake = FakeRedis()
        bus = RedisEventBus(fake)
        await bus.publish("signals", {"symbol": "BTCUSDT", "price": 1.5})
        channel, raw = fake.published[0]
        assert channel == "signals"
        assert json.loads(raw)["symbol"] == "BTCUSDT"
