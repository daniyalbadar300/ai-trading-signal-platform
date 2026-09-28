# 🤖 AI Trading Signal Platform

<!-- First push ke baad YOUR_GH_OWNER apne GitHub username se replace karein -->
[![CI](https://github.com/daniyalbadar300/ai-trading-signal-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/daniyalbadar300/ai-trading-signal-platform/actions/workflows/ci.yml)
[![CD](https://github.com/daniyalbadar300/ai-trading-signal-platform/actions/workflows/cd.yml/badge.svg)](https://github.com/daniyalbadar300/ai-trading-signal-platform/actions/workflows/cd.yml)

End-to-end **AI-integrated DevOps project**: crypto trading signals (technical indicators + LLM commentary) generated from live Binance data, with a fully automated deployment pipeline — Docker, Kubernetes, GitHub Actions CI/CD, Prometheus/Grafana monitoring.

> ⚠️ Educational/portfolio project. Not financial advice.

## 🚦 Build Progress

| Phase | Description | Status |
|---|---|---|
| 1 | Backend core (data providers, indicators, signals, FastAPI, tests) | ✅ **done** |
| 2 | AI layer (LLM commentary) + Worker scheduler | ✅ **done** |
| 3 | Frontend dashboard (React + Vite) | ✅ **done** |
| 4 | Docker (multi-stage + compose stack) | ✅ **done** |
| 5 | Kubernetes (kustomize, probes, HPA) | ✅ **done** |
| 6 | CI/CD (GitHub Actions + kind e2e) | ✅ **done** |
| 7 | Monitoring (Prometheus + Grafana + alerts) | ⬜ |
| 8 | Polish (README, demo flow) | ⬜ |

## ✨ What works right now

**Signals & AI (Phase 1+2):**
- **Live signals** from Binance public API (no key needed): RSI(14) + MACD(12/26/9) + EMA 20/50 cross + Bollinger Bands + volume → weighted composite score → **BUY / SELL / HOLD** with confidence %
- **AI commentary**: LLM narrates every signal (any OpenAI-compatible API — OpenAI/Gemini/Groq/Ollama) with automatic **rule-based fallback** — works with zero API keys
- **Background worker**: generates signals every N seconds, stores history, broadcasts live
- **Pluggable data layer**: `BinanceProvider` (live) / `MockDataProvider` (deterministic, offline demo + CI)
- **TTL cache** with single-flight coalescing — never hammers upstream APIs

**APIs:**
- REST: `/health`, `/api/v1/symbols`, `/api/v1/candles/{symbol}`, `/api/v1/signals/{symbol}`, `/api/v1/signals`, `/api/v1/history`, `/api/v1/stats`, `/worker/status`
- **WebSocket** `/ws/signals`: snapshot on connect + live signal stream

**Dashboard (Phase 3):**
- **Live candlestick chart** (TradingView lightweight-charts) with dark trading theme
- **Signal cards** with action badges (🟢 BUY / 🔴 SELL / 🟡 HOLD) + confidence meters + mini indicators
- **AI commentary panel** with source badge (`llm:*` or `rule-engine`) + risk note
- **WebSocket live stream**: snapshot on load + real-time updates + auto-reconnect with backoff
- Symbol tabs, stats card, signal history table (auto-refresh)

**Docker (Phase 4):**
- **`make up`** = pura 5-service stack: backend + dedicated worker + Redis + nginx frontend
- Multi-stage, non-root images; worker → **Redis pub/sub** → API → dashboard (cross-container)
- Healthchecks, AOF-persistent Redis, `.env`-driven config (`DATA_PROVIDER=mock` = offline demo)

**Kubernetes (Phase 5):**
- Kustomize: `base` + `overlays/dev` (mock data, fast worker, 1 replica) & `overlays/prod`
- **HPA** (2→6 backend pods @70% CPU), health probes, resource limits, non-root securityContext
- Redis **PVC**, Ingress (nginx) with WebSocket routing, `trading.local` host
- Deploy to local **kind** cluster: `make deploy` (project-local kind, no system install)

**Quality:** 83 passing tests (75 backend pytest + 8 frontend vitest), ruff clean, structured JSON logging

**CI/CD (Phase 6):**
- **CI** (`.github/workflows/ci.yml`): ruff + pytest (75) / vitest + build (8) parallel,
  `kubectl kustomize` dry-render of base + dev/staging/prod, phir **kind e2e**: images build →
  load → dev overlay deploy → rollout wait → in-cluster smoke (health `mock`, frontend HTML,
  worker→store polling) → ingress smoke on :8090. CI fully offline (MockDataProvider).
- **CD** (`.github/workflows/cd.yml`): main push → GHCR publish (`sha-xxxxxxx` + `latest`,
  GHA layer cache) → staging overlay deploy to kind with exact-SHA image pinning +
  `ghcr-pull` secret → same smoke suite.
- **Staging overlay** (`infra/k8s/overlays/staging`): dev-jaisi shape lekin GHCR images;
  `__CD_OWNER__/__CD_TAG__` placeholders se kustomize render owner-agnostic rehta hai
  (CI validate kar sakta hai bina GitHub owner jaane).

## Quick start (CI/CD — first push)

```bash
git remote add origin https://github.com/daniyalbadar300/ai-trading-signal-platform.git
git push -u origin master          # CI + CD dono trigger honge
```

CI pushes: tests + kustomize validate + kind e2e (merge gate).
CD pushes: GHCR images (`ghcr.io/<owner>/ai-trading-{backend,frontend}:sha-<ref>`)
+ staging cluster deploy + smoke.

## Quick start (Docker — full stack)

```bash
make up      # build + start: backend, worker, redis, frontend
curl http://localhost:8000/api/v1/stats
# dashboard: http://localhost:5173
make down    # stop everything
```

## Quick start (Kubernetes — kind)

```bash
make deploy        # cluster up + images load + dev overlay apply + ingress
# hosts file me add karein:  127.0.0.1 trading.local
# dashboard: http://trading.local:8090
make undeploy      # remove k8s resources
make cluster-down  # delete kind cluster
```

## Quick start (dev)

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash (Linux/Mac: source .venv/bin/activate)
pip install -e ".[dev]"

DATA_PROVIDER=binance uvicorn app.main:app --reload --port 8000
# ya offline demo ke liye:
DATA_PROVIDER=mock uvicorn app.main:app --reload --port 8000
```

Docs: http://localhost:8000/docs · Health: http://localhost:8000/health

Worker auto-starts with the API (default 60s cycle; override with `WORKER_INTERVAL_SECONDS`).
Open **http://localhost:8000/docs** for the interactive API explorer.

```bash
# tests + lint
python -m pytest
python -m ruff check app tests
```

### Frontend (dev)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api + /ws to :8000)

npm test             # vitest
npm run build        # type-check + production bundle
```

Keep the backend running on :8000 — the dev server proxies API and WebSocket calls to it.

## API examples

```bash
curl http://localhost:8000/api/v1/signals/BTCUSDT
# {"symbol":"BTCUSDT","action":"BUY","confidence":0.98,"score":0.44,
#  "indicators":{"rsi_14":33.4,...},"contributions":{"rsi":0.19,"macd":0.24,...}}

curl http://localhost:8000/api/v1/history?limit=5   # worker-generated history
curl http://localhost:8000/api/v1/stats            # {"total": 12, "actions": {"BUY": 4, ...}}

# Live stream (snapshot + updates):
websocat ws://localhost:8000/ws/signals
```
