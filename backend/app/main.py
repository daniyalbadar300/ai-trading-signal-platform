"""FastAPI application entrypoint."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.config import get_settings
from app.dependencies import bus_dependency, get_worker, store_dependency
from app.events import InMemoryEventBus
from app.logging import new_request_id, request_id_ctx, setup_logging
from app.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS
from app.worker import SIGNALS_CHANNEL

logger = logging.getLogger(__name__)


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
        if settings.metrics_enabled:
            from prometheus_client import start_http_server

            try:
                start_http_server(settings.metrics_port)  # worker-side metrics
            except OSError as exc:
                logger.warning("metrics server not started: %s", exc)

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
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)  # templates keep cardinality low
    if path != "/metrics":  # self-scrapes must not appear in their own output
        HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        HTTP_REQUEST_DURATION.labels(request.method, path).observe(duration)
    response.headers["X-Request-ID"] = rid
    request_id_ctx.set("-")
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus scrape endpoint (enabled via METRICS_ENABLED)."""
    settings = get_settings()
    if not settings.metrics_enabled:
        return Response(status_code=404)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
