"""REST API endpoints."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings
from app.dependencies import (
    settings_dependency,
    signal_service_dependency,
    store_dependency,
    worker_dependency,
)
from app.models import Candle, Signal
from app.providers.errors import ProviderError, SymbolNotFoundError
from app.services import SignalService
from app.store import InMemorySignalStore
from app.worker import SignalWorker

router = APIRouter()

ServiceDep = Annotated[SignalService, Depends(signal_service_dependency)]
SettingsDep = Annotated[Settings, Depends(settings_dependency)]
StoreDep = Annotated[InMemorySignalStore, Depends(store_dependency)]
WorkerDep = Annotated[SignalWorker, Depends(worker_dependency)]

STARTED_AT = datetime.now(UTC)


@router.get("/health", tags=["ops"])
async def health(service: ServiceDep, settings: SettingsDep) -> dict:
    """Liveness + upstream reachability probe."""
    upstream = await service._provider.healthcheck()
    return {
        "status": "ok" if upstream else "degraded",
        "env": settings.env,
        "provider": settings.data_provider,
        "upstream_ok": upstream,
        "uptime_s": (datetime.now(UTC) - STARTED_AT).total_seconds(),
    }


@router.get("/api/v1/symbols", tags=["market"])
async def list_symbols(settings: SettingsDep) -> dict:
    """Configured watchlist."""
    return {"symbols": settings.symbol_list, "interval": settings.default_interval}


@router.get("/api/v1/candles/{symbol}", response_model=list[Candle], tags=["market"])
async def get_candles(
    symbol: str,
    service: ServiceDep,
    settings: SettingsDep,
    interval: str | None = Query(None, description="e.g. 1m, 5m, 1h, 1d"),
    limit: int = Query(120, ge=10, le=1000),
) -> list[Candle]:
    """OHLCV candles for a symbol (cached upstream calls)."""
    try:
        return await service.get_candles(symbol, interval or settings.default_interval, limit)
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/v1/signals/{symbol}", response_model=Signal, tags=["signals"])
async def get_signal(
    symbol: str,
    service: ServiceDep,
    settings: SettingsDep,
    interval: str | None = Query(None),
) -> Signal:
    """Composite AI/technical signal for one symbol (computed on demand)."""
    try:
        return await service.get_signal(
            symbol, interval or settings.default_interval, settings.candle_limit
        )
    except SymbolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/v1/signals", response_model=list[Signal], tags=["signals"])
async def get_signals(service: ServiceDep) -> list[Signal]:
    """Signals for the whole watchlist (computed on demand)."""
    return await service.get_all_signals()


@router.get("/api/v1/history", response_model=list[Signal], tags=["signals"])
async def get_history(
    store: StoreDep,
    settings: SettingsDep,
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> list[Signal]:
    """Worker-generated signal history (newest first, optionally per symbol)."""
    return await store.history(symbol, limit=limit or settings.signals_history_limit)


@router.get("/api/v1/stats", tags=["signals"])
async def get_stats(store: StoreDep) -> dict:
    """Aggregate counters over stored signals."""
    return await store.stats()


@router.get("/worker/status", tags=["ops"])
async def worker_status(worker: WorkerDep) -> dict:
    """Background signal-worker health snapshot."""
    return worker.status()
