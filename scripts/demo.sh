#!/usr/bin/env bash
# Narrated end-to-end demo: tests → kustomize → kind deploy → live signals →
# monitoring → cleanup. Designed for screen-share/recording.
# Usage:  bash scripts/demo.sh          (demo mode, pauses between steps)
#         FAST=1 bash scripts/demo.sh   (no pauses, for CI-ish sanity run)
set -euo pipefail

cd "$(dirname "$0")/.."
APP_NS="ai-trading-dev"

say() { printf "\n\033[1;36m▶ %s\033[0m\n" "$1"; }
wait_step() { [ "${FAST:-0}" = "1" ] && return 0; read -rp "  ⏎ continue… " _; }

say "0/8 — Environment check (kind, kubectl, docker)"
./.tools/kind.exe get clusters 2>/dev/null || true
docker version --format 'docker: {{.Server.Version}}' 2>/dev/null || true
wait_step

say "1/8 — Quality gates: backend lint + 82 tests, frontend 8 tests"
(cd backend && .venv/Scripts/python -m ruff check app tests \
  && .venv/Scripts/python -m pytest -q 2>&1 | tail -1)
(cd frontend && npm test 2>&1 | tail -4)
wait_step

say "2/8 — Kustomize dry-render: every manifest set (base, overlays, monitoring)"
for d in infra/k8s/base infra/k8s/overlays/dev infra/k8s/overlays/staging \
         infra/k8s/overlays/prod infra/monitoring; do
  kubectl kustomize "$d" > /dev/null && echo "  ✓ $d"
done
wait_step

say "3/8 — Build images and load into kind"
docker build -q -t ai-trading/backend:latest backend
docker build -q -t ai-trading/frontend:latest frontend
./.tools/kind.exe load docker-image ai-trading/backend:latest --name ai-trading 2>&1 | tail -1
./.tools/kind.exe load docker-image ai-trading/frontend:latest --name ai-trading 2>&1 | tail -1
wait_step

say "4/8 — Deploy dev overlay (mock provider, 15s worker, 1 replica each)"
kubectl apply -k infra/k8s/overlays/dev > /dev/null
kubectl -n "$APP_NS" rollout status deploy/backend  --timeout=180s
kubectl -n "$APP_NS" rollout status deploy/frontend --timeout=180s
kubectl -n "$APP_NS" rollout status deploy/worker   --timeout=180s
kubectl -n "$APP_NS" get pods
wait_step

say "5/8 — Live signals: watch worker → Redis → API (and WS traffic on the dashboard)"
kubectl -n "$APP_NS" run smoke --image=curlimages/curl:8.10.1 --restart=Never \
  --command -- sleep 300 > /dev/null
kubectl -n "$APP_NS" wait --for=condition=Ready pod/smoke --timeout=90s
kubectl -n "$APP_NS" exec smoke -- curl -fsS http://backend:8000/health; echo
for i in 1 2 3; do
  kubectl -n "$APP_NS" exec smoke -- curl -fsS http://backend:8000/api/v1/history?limit=2 \
    | head -c 300; echo
  [ "$i" = 3 ] || sleep 5
done
echo "  → ab browser me kholen:  http://trading.local:8090   (WS live stream)"
wait_step

say "6/8 — Monitoring: Prometheus scrape targets + alerts, Grafana dashboard"
kubectl apply -k infra/monitoring > /dev/null
kubectl -n "$APP_NS" rollout status deploy/prometheus --timeout=180s
kubectl -n "$APP_NS" rollout status deploy/grafana   --timeout=180s
kubectl -n "$APP_NS" exec smoke -- curl -fsS \
  "http://prometheus:9090/prometheus/api/v1/targets" \
  | grep -o '"health":"[a-z]*"' | sort | uniq -c
echo "  → Grafana:    http://trading.local:8090/grafana"
echo "  → Prometheus: http://trading.local:8090/prometheus"
wait_step

say "7/8 — Alert pipeline: worker delete → WorkerDown pending → restore → resolved"
kubectl -n "$APP_NS" delete deploy worker --wait=false > /dev/null
echo "  worker deleted; alerts pending within ~45s (check /prometheus/alerts)"
sleep 45
kubectl -n "$APP_NS" exec smoke -- curl -fsS \
  "http://prometheus:9090/prometheus/api/v1/alerts" \
  | grep -o '"filter":\[\],"state":"[a-z]*"' | sort | uniq -c || true
kubectl apply -k infra/k8s/overlays/dev > /dev/null
kubectl -n "$APP_NS" rollout status deploy/worker --timeout=180s
echo "  worker restored — alerts resolve after their window"
wait_step

say "8/8 — Cleanup (cluster ko chalne dete hain)"
kubectl -n "$APP_NS" delete pod smoke --ignore-not-found --force --grace-period=0 2>/dev/null || true
echo "✅ Demo complete. Live URLs:"
echo "   dashboard:  http://trading.local:8090"
echo "   grafana:    http://trading.local:8090/grafana"
echo "   prometheus: http://trading.local:8090/prometheus"
echo "   Teardown:   make monitoring-down && make undeploy && make cluster-down"
