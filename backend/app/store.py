"""Signal storage abstraction plus an in-memory implementation.

Phase 4+ can add a Postgres-backed store behind the same interface without
touching callers.
"""

from abc import ABC, abstractmethod

from app.models import Signal


class SignalStore(ABC):
    """Persistence boundary for generated signals."""

    @abstractmethod
    async def save(self, signal: Signal) -> None:
        """Append a signal to the store."""
        raise NotImplementedError

    @abstractmethod
    async def latest(self, symbol: str) -> Signal | None:
        """Most recent signal for a symbol, or None."""
        raise NotImplementedError

    @abstractmethod
    async def history(self, symbol: str | None = None, limit: int = 50) -> list[Signal]:
        """Most recent `limit` signals, newest first, optionally per symbol."""
        raise NotImplementedError

    @abstractmethod
    async def stats(self) -> dict:
        """Aggregate counters (total, per-action)."""
        raise NotImplementedError


class InMemorySignalStore(SignalStore):
    """Thread-safe-enough list-backed store (single event loop)."""

    def __init__(self, max_per_symbol: int = 1000) -> None:
        self._max = max_per_symbol
        self._by_symbol: dict[str, list[Signal]] = {}

    async def save(self, signal: Signal) -> None:
        bucket = self._by_symbol.setdefault(signal.symbol, [])
        bucket.append(signal)
        if len(bucket) > self._max:
            del bucket[: len(bucket) - self._max]

    async def latest(self, symbol: str) -> Signal | None:
        bucket = self._by_symbol.get(symbol.upper())
        return bucket[-1] if bucket else None

    async def history(self, symbol: str | None = None, limit: int = 50) -> list[Signal]:
        if symbol:
            bucket = self._by_symbol.get(symbol.upper(), [])
            return list(reversed(bucket[-limit:]))
        merged: list[Signal] = []
        for bucket in self._by_symbol.values():
            merged.extend(bucket)
        merged.sort(key=lambda s: s.generated_at, reverse=True)
        return merged[:limit]

    async def stats(self) -> dict:
        total = 0
        actions: dict[str, int] = {}
        for bucket in self._by_symbol.values():
            for s in bucket:
                total += 1
                actions[s.action.value] = actions.get(s.action.value, 0) + 1
        return {"total": total, "actions": actions}
