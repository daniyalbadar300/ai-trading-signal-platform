"""Background signal-generation loop.

Every cycle: fetch/score signals for the watchlist -> attach AI commentary
-> persist to the store -> publish on the event bus. Designed to run inside
the API process; `app.worker_main` runs it standalone for Docker/K8s.
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime

from app.ai.commentary import CommentaryProvider, LLMCommentary
from app.config import Settings
from app.events import EventBus
from app.services import SignalService
from app.store import SignalStore

logger = logging.getLogger(__name__)

SIGNALS_CHANNEL = "signals"


class SignalWorker:
    """Interval loop producing enriched, stored and broadcast signals."""

    def __init__(
        self,
        service: SignalService,
        settings: Settings,
        store: SignalStore,
        bus: EventBus,
        commentator: CommentaryProvider,
        interval_seconds: int = 60,
    ) -> None:
        self._service = service
        self._settings = settings
        self._store = store
        self._bus = bus
        self._commentator = commentator
        self._interval = interval_seconds
        self._task: asyncio.Task | None = None
        self._running = False
        # Observability counters (exposed via /worker/status)
        self.cycles = 0
        self.signals_generated = 0
        self.last_cycle_at: datetime | None = None
        self.last_error: str | None = None

    async def run_cycle(self) -> list:
        """One generation pass over the whole watchlist."""
        signals = await self._service.get_all_signals()
        for signal in signals:
            commentary = await self._commentator.generate(signal)
            await self._store.save(signal)
            await self._bus.publish(
                SIGNALS_CHANNEL,
                {
                    **signal.model_dump(mode="json"),
                    "commentary": commentary.model_dump(mode="json"),
                },
            )
            self.signals_generated += 1
        self.cycles += 1
        self.last_cycle_at = datetime.now(UTC)
        self.last_error = None
        return signals

    async def start(self) -> None:
        """Start the loop as a background task (idempotent)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="signal-worker")
        logger.info(
            "worker started (interval=%ss, symbols=%s)", self._interval, self._settings.symbol_list
        )

    async def stop(self) -> None:
        """Cancel the loop and wait for a clean exit."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.run_cycle()
            except Exception as exc:  # noqa: BLE001 - loop must survive anything
                logger.exception("worker cycle failed")
                self.last_error = str(exc)
            await asyncio.sleep(self._interval)

    def status(self) -> dict:
        """Worker health snapshot for the ops endpoints."""
        return {
            "running": self._running,
            "interval_s": self._interval,
            "cycles": self.cycles,
            "signals_generated": self.signals_generated,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
            "last_error": self.last_error,
        }


def build_commentator(settings: Settings) -> CommentaryProvider:
    """LLM-backed commentary (falls back to rules internally when key missing)."""
    return LLMCommentary(settings)
