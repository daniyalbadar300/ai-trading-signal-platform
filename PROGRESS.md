# 📋 Project Progress

## Phase 7: Monitoring — ✅ COMPLETE (Sep 29)

**Verified live:** Prometheus pod-SD scraping worker + backend ×2 (all `up`, `namespace`/`pod`
labels), `worker_cycles_total=36` flowing, 4 alerts loaded (health ok), Grafana datasource
+ "AI Trading Signals" dashboard provisioned, `/prometheus` + `/grafana` 200 via shared
trading.local ingress. **Alert state machine live-tested:** worker deployment deleted →
WorkerDown + WorkerNoSuccessfulCycles went pending (for-window) → worker restored →
0 active alerts. 82/82 pytest + ruff clean.

### What exists (new in phase 7)
- `app/metrics.py` — shared collectors: http_requests (method/path-template/status),
  request-duration histogram, worker_running gauge, worker_cycles / cycle_errors counters,
  worker_last_success_timestamp, signals_generated{symbol,action}, commentary_source{source}
- API: `/metrics` endpoint gated by `METRICS_ENABLED` (default false) + middleware
  instrumentation (skips /metrics itself; route-template paths for low cardinality)
- Worker: same registry + `prometheus_client.start_http_server(8000)` in both
  lifespan (in-process) and worker_main (standalone) when metrics enabled
- `infra/monitoring/` kustomize stack: prometheus (RBAC Role/RoleBinding, pod-SD
  `own_namespace: true`, route-prefix /prometheus, 3d retention) + grafana (provisioned
  datasource `http://prometheus:9090/prometheus`, dashboard JSON, anonymous viewer,
  GF_SERVER_SERVE_FROM_SUB_PATH) + monitoring ingress (/prometheus, /grafana)
- Alert rules: WorkerDown (`absent(worker_running) == 1 or max(worker_running) < 1`),
  WorkerNoSuccessfulCycles, WorkerCycleErrors, ApiHighErrorRate (5xx > 5%)
- `make monitoring-up/monitoring-down`; CI k8s-validate covers infra/monitoring
- base deployments carry prometheus.io/* annotations (inert without the stack);
  dev overlay sets METRICS_ENABLED=true

### Gotchas learned (do not regress)
1. **kustomize namespace transformer does NOT rewrite ClusterRoleBinding subject
   namespaces** — binding pointed SA `ai-trading-dev:prometheus` at `ai-trading` (403).
   Fix: namespaced Role + RoleBinding, subject WITHOUT namespace (binding's ns is used).
2. **kubernetes_sd role:pod does a CLUSTER-WIDE pod LIST** — forbidden with a namespaced
   Role even when permissions are correct (`can-i` in-ns = yes). Fix:
   `namespaces: own_namespace: true` in kubernetes_sd_configs.
3. **`--web.route-prefix=/prometheus` moves health endpoints too** — probes must hit
   `/prometheus/-/ready` etc. Self-scrape needs `metrics_path: /prometheus/metrics`.
4. **Grafana behind a sub-path needs BOTH** `GF_SERVER_ROOT_URL` and
   `GF_SERVER_SERVE_FROM_SUB_PATH=true` — otherwise ingress /grafana 404s.
5. **`absent()` branch in WorkerDown** — plain `max()<1` stays silent when the worker
   pod (and its series) disappears entirely; `absent(worker_running) == 1 or ...` covers
   both. Live-tested via pod deletion.
6. **Git Bash /tmp vs Windows python paths don't mix** — pipe JSON through stdin instead
   of temp files in verification one-liners.
7. Test counters are process-global: capture `before` values; never assert absolute
   numbers. Gauge reads via `._value.get()` (no `.get()` on the Gauge object).

## Phase 6: CI/CD — ✅ COMPLETE (Sep 27)

**Verified:** ruff clean + 75/75 pytest + 8/8 vitest + vite build green; kustomize render OK
for base + dev/staging/prod; workflow YAML syntax validated.

**Live dry-run (Sep 28, Docker unpaused) — CI e2e + CD staging dono simulated green:**
- CI e2e sim: images rebuild → kind load → dev overlay re-apply → rollout waits →
  in-cluster smoke (health `mock`, frontend HTML, stats poll total=228) → ingress :8090 OK
- CD sim: sed pin (`sha-localsim`) → SHA-tagged images kind load → ghcr-pull secret →
  staging apply → rollouts (HPA ne backend 2 replicas tak scale kiya) → smoke total=15 →
  worker JSON logs OK → full cleanup, dev ingress wapas restored (total=306)
- Dry-run ne 1 **asli bug** pakra: staging kustomization mein `namespace:` field missing
  tha (rewrite ke dauran drop hua) — kustomize sab resources nonexistent `ai-trading` ns
  mein bhej raha tha (`namespaces "ai-trading" not found` ×12). Fixed + verified (render
  grep 12× `ai-trading-staging`). Yehi CD par pehli push mein fail hota.

First push par CI green hona expected; agar e2e fail ho to PROGRESS phase-5/6 gotchas dekhein.

**First push live runs (Sep 28) — CI + CD dono GREEN on `453af2b`:**
Repo: `github.com/daniyalbadar300/ai-trading-signal-platform` (public, rename ke baad).
CD verified: GHCR publish (sha+latest, single-manifest) → kind staging deploy with REAL
GHCR pulls → rollouts + smoke. CI verified: 4 jobs incl. kind e2e.

### First-push ke live-run gotchas (do not regress)
10. **PEP 621: `homepage` [project] ke under invalid hai** — setuptools build par reject
    karta hai (`project must not contain {'homepage'}`) → pip install + docker build dono
    fat-te hain. Sahi jagah: `[project.urls] Homepage = ...`.
11. **buildx default provenance attestations = OCI image index (2 manifests)** — kind ka
    containerd aisa index registry se pull nahi kar pata (imagePullBackOff → rollout
    timeout). Fix: `provenance: false` in build-push-action. Verify: token endpoint se
    GHCR manifest check (`mediaType=oci.image.manifest` = plain, `refs=0`).
12. **Staging overlay mein worker deployment ka image patch zaroori** — worker backend
    image reuse karta hai (different command); patch miss → `ai-trading/backend:latest`
    Docker Hub se (nonexistent) → ImagePullBackOff. **Local sim ye pakad nahi sakta**
    kyunki wahan image node-loaded hoti hai; sirf real GHCR pull path par dikhta hai.
13. **Fresh repo ka first push with workflows kabhi kabhi trigger nahi hota** (rename ke
    baad aur bhi). Fix: ek chhota non-md commit push karo; `paths-ignore: **.md` md-only
    pushes skip karta hai (design intent).
14. **GHCR anonymous check**: pehle `ghcr.io/token?scope=...:pull` se token lo, phir
    manifests API — direct 401 normal hai (auth-free ≠ invalid).
15. Public repo: job logs API/sign-in ke baghair nahi khulte; job page HTML annotations
    ("STEP FAILED: ...") se failing step identify hota hai, timings se error class
    (fast crash vs timeout) ka pata chalta hai.

### What exists (new in phase 6)
- `.github/workflows/ci.yml` — 4 jobs: backend (ruff+pytest), frontend (vitest+build),
  k8s-validate (kubectl kustomize base+dev+staging+prod), e2e-kind (build→kind→load→
  apply dev overlay→rollout wait→in-cluster smoke→ingress :8090 smoke). concurrency
  cancel + paths-ignore md. CI 100% offline (MockDataProvider, conftest-pinned).
- `.github/workflows/cd.yml` — publish job (GHCR `sha-<short>` + `latest`, buildx +
  GHA cache) → deploy-staging job (sed __CD_OWNER__/__CD_TAG__ pin → kind → ghcr-pull
  secret → apply staging overlay → rollout + smoke suite same as CI).
- `infra/k8s/overlays/staging/` — kustomization (base + namespace `ai-trading-staging`,
  mock provider, 15s worker, replicas 1) + replica-patch + images-patch (GHCR images
  with `__CD_OWNER__/__CD_TAG__` placeholders + `imagePullSecrets: ghcr-pull`).
- `frontend/package.json` — missing `"test": "vitest run"` script added (README claimed
  `npm test` but package.json me script tha hi nahi — CI would have failed).

### Gotchas learned (do not regress)
1. **frontend/package-lock.json glob miss**: glob `frontend/package-lock.json` returned 0
   matches (root-level glob quirk?) — `list_directory` ne confirm kiya file hai. `npm ci`
   safe hai.
2. **Base deployments use container names `backend`/`frontend`** matching service names —
   staging images-patch strategic-merge container-name se match karta hai.
3. **`kind create secret` does not exist** (workflow bug caught in review): docker-registry
   credentials must use `kubectl create secret docker-registry --dry-run=client -o yaml |
   kubectl apply`.
4. **imagePullSecrets must be in pod spec** — sirf secret banana kaafi nahi for private
   GHCR pulls; staging patch adds it explicitly.
5. **Staging overlay uses placeholder tokens** (`__CD_OWNER__/__CD_TAG__`) instead of a
   guessed GHCR owner — kustomize render stays valid pre-push, CD seds them.
6. **Docker Desktop paused = kubectl hang** (server unreachable) — cluster checks se
   pehle `docker ps` karein; `taskkill //PID ... //F` only for port conflicts.
7. **Kustomization edit ke baad render+grep zaroori**: staging rewrite se `namespace:`
   field drop ho gaya tha aur kustomize silently base ns (`ai-trading`) target karne laga —
   kubectl apply par 12 NotFound errors. Rule: kustomization.yaml touch karo →
   `kubectl kustomize <overlay> | grep namespace:` before apply.
8. **`kubectl apply -k` copy-outside-repo par toot-ta hai** — `/tmp` copy se `../../base`
   relative path resolve nahi hota (Windows par AppData mein gaya). Local sims repo ke
   andar sibling overlay dir use karein (e.g. `overlays/staging-sim`). CD unaffected
   (checkout ke andar chalta hai).
9. **ingress-nginx admission duplicate host+path reject karta hai namespaces ke beech** —
   shared local cluster par dev+staging dono `trading.local` nahi rakh sakte. Local sim:
   dev ingress temp-delete → staging apply → staging delete → dev restore. CI/CD fresh
   clusters par N/A.

### Local pre-flight transcript (Sep 27)
```bash
backend: ruff All checks passed! · 75 passed, 1 warning in 3.12s
frontend: 4 files / 8 tests passed · tsc -b && vite build ✓ built in 412ms
kubectl kustomize base/dev/staging/prod → OK ×4
staging render contains ghcr.io/__CD_OWNER__/ai-trading-{backend,frontend}:__CD_TAG__
workflow YAML: yaml.safe_load OK for ci.yml + cd.yml

Live dry-run transcript (Sep 28):
```bash
# CI e2e sim
dev smoke: {"provider":"mock","upstream_ok":true} · frontend <!doctype html> · total=228
ingress: INGRESS SMOKE OK (attempt 1)

# CD staging sim (sed pin → sha-localsim images, ghcr-pull secret)
staging pods: 5 Running (backend 2/2 after HPA) · smoke total=15 → STAGING SMOKE OK
worker log: {"msg": "worker started (interval=15s, symbols=['BTCUSDT','ETHUSDT','SOLUSDT'])"}
cleanup: ai-trading-staging deleted → dev ingress restored → trading.local total=306
```

## Phase 5: Kubernetes — ✅ COMPLETE (Sep 27)

**Verified:** kind cluster `ai-trading` running · dev overlay deployed (5 pods Running) ·
in-cluster smoke tests via service DNS (health OK, worker→redis→api history/stats OK,
frontend 200) · ingress-nginx installed; `trading.local:8090` → dashboard 200, API JSON,
WS 101 upgrade. 83 tests still green.

### What exists (new in phase 5)
- `infra/k8s/base/` — configmap, secret, redis (deployment+svc+PVC), backend
  (deployment+svc+HPA), worker deployment, frontend (deployment+svc), ingress (nginx class,
  /api /health /worker /ws → backend, / → frontend, WS timeout annotations)
- `infra/k8s/overlays/dev|prod/` — namespace resource + configMapGenerator merge;
  dev: DATA_PROVIDER=mock, WORKER_INTERVAL_SECONDS=15, replicas 1
- `infra/kind-config.yaml` — cluster `ai-trading`, hostPort 8090→80 (ingress), 8443→443
- Makefile: `cluster-up / cluster-down / load-images / deploy / undeploy`
- kind binary is project-local at `.tools/kind.exe` (no system install)

### Gotchas learned (do not regress)
1. **kustomize `namespace:` transformer** renames but does NOT create the Namespace —
   overlays must ship their own Namespace resource (base must NOT include one, or
   dev/prod builds collide on it).
2. **`imagePullPolicy: IfNotPresent` must be explicit** — with `:latest` the default is
   `Always` and kind-loaded images get ignored (ErrImagePull from Docker Hub).
3. **kubectl apply -k is NOT atomic**: partial apply on first failure left old
   ErrImagePull ReplicaSet pods — always `get pods` after apply and clean stale RS pods.
4. **Multiple strategic-merge patches in one `patches:` entry** with a `target:` are
   rejected; use one entry per file (or no target + multi-doc patch file).
5. **HPA shows `<unknown>` targets** without metrics-server — expected on plain kind;
   CI/e2e assertions must not depend on HPA metrics.
6. kind extraPortMappings bind at create-time — changing them needs cluster recreation.

### Verification transcript
```bash
kubectl -n ai-trading-dev get pods            # 5/5 Running (redis, backend x2, worker, frontend)
kubectl exec curlpod -- curl http://backend:8000/health   # ok (mock provider via overlay)
curl -H "Host: trading.local" http://localhost:8090/api/v1/stats
# → {"total":45,"actions":{"BUY":45}}   (worker actively generating)
curl WS upgrade via :8090 → 101 Switching Protocols
```

## Phase 4: Docker + Compose — ✅ COMPLETE (Sep 26/27)

**Verified:** images built · 5-service stack up (backend/frontend/redis healthy) ·
cross-container flow live-verified in browser (worker→Redis→API→nginx→dashboard + WS
through nginx, 101 upgrade). 75/75 pytest + ruff clean.

### What exists (new in phase 4)
- `backend/Dockerfile` — multi-stage (deps → runtime), non-root `appuser`, healthcheck
- `frontend/Dockerfile` — node build → nginx:1.27-alpine; `nginx.conf`: SPA fallback,
  /api /health /worker proxy → backend:8000, /ws with Upgrade headers
- `app/redis_bus.py` — `RedisEventBus` (publish), `RedisSignalStore` (history+stats in
  Redis lists/hashes), `RedisBridge` (API-side: Redis → local bus for WS)
- `WORKER_ENABLED` config: compose API container runs worker=false; dedicated worker
  container (`python -m app.worker_main`) publishes via Redis
- `infra/docker-compose.yml` — backend, worker, redis (AOF volume), frontend;
  worker healthcheck disabled (serves no HTTP)
- Makefile: `make up / down / logs / build`

### Gotchas learned (do not regress)
1. **Dockerfile deps stage**: `pip install .` needs `app/` copied too (setuptools needs
   the packages), not just pyproject.toml.
2. **Worker container healthcheck**: image has a port-8000 healthcheck; worker serves no
   HTTP → disable per-service (`healthcheck: disable: true`) or it goes unhealthy.
3. **Lazy Redis client**: never call `asyncio.run_until_complete` inside dependency
   getters (running loop crash). `aioredis.from_url` connects lazily on first command.
4. **In-process worker + dedicated worker container = double signals**: gate the
   lifespan worker behind `WORKER_ENABLED`.
5. nginx `location /ws/` needs `proxy_http_version 1.1` + Upgrade/Connection headers.
6. Fake redis in tests: pipeline must support async context-manager protocol.

### Demo commands
```bash
make up          # build + start 5-service stack
curl localhost:8000/api/v1/stats
open http://localhost:5173
make down
```

## Phase 3: Frontend Dashboard — ✅ COMPLETE (Sep 26/27)

**Verified:** build green · 8/8 vitest · 70/70 pytest · dashboard live-verified in browser
(chart rendering, signal cards updating over WS, history refreshing every 3s, commentary panel)

### What exists (new in phase 3)
- Vite + React 19 + TS + Tailwind v4 scaffold (`frontend/`), dev proxy: `/api` `/health`
  `/worker` → :8000, `/ws` → ws://:8000
- `src/api.ts` typed client; `src/types.ts` mirrors backend Pydantic models
- `hooks/useWebSocket.ts` — snapshot + live messages, exponential-backoff reconnect,
  **stale-socket guard** (StrictMode double-mount fix)
- `hooks/usePolling.ts` — interval + deps-aware refresh (symbol switching)
- Components: `Header` (live dot + worker stats), `PriceChart` (lightweight-charts v5),
  `SignalCard` (badge + confidence meter + mini indicators), `CommentaryPanel`,
  `HistoryTable`, symbol tabs in `App.tsx`
- Tests: SignalCard / CommentaryPanel / HistoryTable / useWebSocket (MockWebSocket)

### Gotchas learned (do not regress)
1. **lightweight-charts v5**: `chart.addCandlestickSeries(...)` removed →
   `chart.addSeries(CandlestickSeries, {...})` (import `CandlestickSeries`).
2. **TS `erasableSyntaxOnly`** (new Vite templates): constructor parameter properties
   (`constructor(public url)`) are a compile error — assign fields manually.
3. **vitest `globals: true`** required for @testing-library auto-cleanup — otherwise
   duplicate-DOM false failures across tests in a file.
4. **WS reconnect race**: socket replaced by newer connect → its onclose must not
   schedule another reconnect (`socketRef.current !== ws` guard).
5. Long-running `nohup ... &` inside SYNC terminal commands can hold the shell past the
   timeout even after servers are up — verify with a separate short curl command.

### Live-demo commands
```bash
# terminal 1 (backend + worker)
cd backend && DATA_PROVIDER=mock WORKER_INTERVAL_SECONDS=3 .venv/Scripts/python -m uvicorn app.main:app --port 8000
# terminal 2 (frontend)
cd frontend && npm run dev
# open http://localhost:5173
```

## Phase 2: AI Layer + Worker — ✅ COMPLETE (Sep 26)

**Verified:** 70/70 tests passing (3.8s) · ruff clean · live smoke-test with real Binance
(worker 3 cycles → 9 signals: 3 BUY / 6 HOLD, zero errors)

### What exists (new in phase 2)
- `app/ai/commentary.py` — `LLMCommentary` (OpenAI-compatible chat completions; works with
  OpenAI/Gemini/Groq/Ollama via env) with automatic rule-based fallback on missing key,
  non-200, or malformed JSON. `_extract_json` tolerates markdown fences + prose.
- `app/ai/rules.py` — `RuleBasedCommentary`: deterministic templates from signal numbers
  (momentum/RSI/EMA/volume) + risk note. Keeps system fully functional without API key.
- `app/store.py` — `SignalStore` ABC + `InMemorySignalStore` (per-symbol trim, history
  newest-first, merged history, stats). Postgres impl can slot in later.
- `app/events.py` — `EventBus` Protocol + `InMemoryEventBus` (bounded per-subscriber
  queues, slow-subscriber drops oldest). Redis impl can slot in later.
- `app/worker.py` — `SignalWorker`: interval loop → signals → commentary → store → publish;
  idempotent start/stop, error-surviving loop, observability counters (`status()`).
  `app/worker_main.py` = standalone entry for Docker/K8s.
- `app/main.py` — lifespan auto-starts worker; `WS /ws/signals` sends
  `{type: "snapshot", signals: [...]}` on connect then `{type: "signal", ...}` per event.
- New REST: `/api/v1/history`, `/api/v1/stats`, `/worker/status`.

### Gotchas learned (do not regress)
1. **WS subscribe-vs-publish race**: a client subscribing right after a worker cycle would
   wait a full interval. Fixed by sending a store snapshot immediately on connect.
2. **Test speed**: lifespan worker with 60s interval made WS tests wait 61s. conftest sets
   `WORKER_INTERVAL_SECONDS=2` for the whole suite → 3.8s runtime.
3. **Class ordering in Python**: `_Subscription` referenced in a method signature *before*
   its definition = import-time NameError (annotations evaluate eagerly). Define first.
4. **pytest-asyncio 1.x**: bare `@pytest.mark.asyncio` not needed (asyncio_mode=auto);
   async tests without any marker run fine.
5. Phase 1 gotchas (pandas 3.0 RSI masks, TTLCache await-outside-lock, Bollinger noise,
   Annotated DI ordering) still apply.

## Phase 1: Backend Core — ✅ COMPLETE (Sep 26)

**Verified:** 43/43 tests · ruff clean · live server smoke-tested with real Binance API

- Providers: `BinanceProvider` / `MockDataProvider` / `TTLCache` (single-flight, deadlock-free)
- Indicators: pure pandas RSI(14, Wilder), MACD(12/26/9), EMA(20/50), Bollinger(20, 2σ), volume ratio
- Signals: weighted composite (rsi .25 / macd .30 / ema_cross .25 / bollinger .15 / volume .05)
- REST: `/health`, `/api/v1/symbols`, `/api/v1/candles/{symbol}`, `/api/v1/signals/{symbol}`, `/api/v1/signals`

## Next: Phase 3 — Frontend dashboard (React + Vite)
1. Vite + React + TS scaffold, Tailwind
2. lightweight-charts candlestick view (candles API)
3. Signal cards with confidence meter + AI commentary panel
4. WebSocket client (snapshot + live), history table, worker status badge
