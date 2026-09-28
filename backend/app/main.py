"""FastAPI application entrypoint."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.dependencies import bus_dependency, get_worker, store_dependency
from app.events import InMemoryEventBus
from app.logging import new_request_id, request_id_ctx, setup_logging
from app.worker import SIGNALS_CHANNEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)

    # Cross-container mode: bridge Redis -> local bus for the WS endpoint.
    bridge = None
    if settings.redis_url:
        import redis.asyncio as aioredis

        from app.redis_bus import RedisBridge

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        bridge = RedisBridge(client, bus_dependency())
        await bridge.start()

    # Only run the worker here when there is no dedicated worker container.
    worker = get_worker()
    if settings.worker_enabled:
        await worker.start()

    yield

    if settings.worker_enabled:
        await worker.stop()
    if bridge:
        await bridge.stop()


app = FastAPI(
    title="AI Trading Signal Platform",
    version="0.2.0",
    description="Technical-indicator + LLM trading signals over Binance data.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened per-env in later phases
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = new_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    request_id_ctx.set("-")
    return response


app.include_router(router)


@app.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket) -> None:
    """Live signal stream.

    On connect: one `{type: snapshot, signals: [...]}` message with the most
    recent stored signals (avoids the subscribe-vs-publish race), then one
    `{type: signal, ...}` message per live generated signal.
    """
    bus: InMemoryEventBus = bus_dependency()
    store = store_dependency()
    await websocket.accept()

    latest = await store.history(limit=10)
    await websocket.send_json(
        {
            "type": "snapshot",
            "signals": [s.model_dump(mode="json") for s in latest],
        }
    )

    subscription = bus.subscribe(SIGNALS_CHANNEL)

    async def pump() -> None:
        async for payload in subscription:
            await websocket.send_json({"type": "signal", **payload})

    receiver = asyncio.create_task(pump())
    try:
        # Keep the socket open; client messages are ignored (ping style).
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        receiver.cancel()
        subscription.close()


@app.get("/", tags=["ops"])
async def root() -> dict:
    """Service banner."""
    return {"service": "ai-trading-signal-platform", "docs": "/docs", "health": "/health"}
