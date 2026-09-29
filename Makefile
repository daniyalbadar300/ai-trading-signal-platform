.PHONY: dev-backend test lint fmt up down logs build tools monitoring-up monitoring-down

# Project-local kind binary (repo me commit nahi hota)
tools:
	mkdir -p .tools
	curl -Lo .tools/kind.exe https://kind.sigs.k8s.io/dl/v0.29.0/kind-windows-amd64

# Local development (no Docker needed)
dev-backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

test:
	cd backend && .venv/Scripts/python -m pytest

lint:
	cd backend && .venv/Scripts/python -m ruff check .

fmt:
	cd backend && .venv/Scripts/python -m ruff format .

# ── Docker stack (phase 4) ─────────────────────────
up:
	docker compose -f infra/docker-compose.yml up -d --build

down:
	docker compose -f infra/docker-compose.yml down

logs:
	docker compose -f infra/docker-compose.yml logs -f --tail=100

build:
	docker compose -f infra/docker-compose.yml build

# ── Monitoring (phase 7) ────────────────────────────
# Requires the app overlay first (make deploy) — shares ai-trading-dev ns
# and the trading.local ingress.
monitoring-up:
	kubectl apply -k infra/monitoring
	kubectl -n ai-trading-dev rollout status deploy/prometheus --timeout=180s
	kubectl -n ai-trading-dev rollout status deploy/grafana --timeout=180s
	@echo "Prometheus: http://trading.local:8090/prometheus - Grafana: http://trading.local:8090/grafana"

monitoring-down:
	kubectl delete -k infra/monitoring --ignore-not-found

# ── Kubernetes (phase 5) ───────────────────────────
KIND := ./.tools/kind.exe

cluster-up:
	$(KIND) create cluster --config infra/kind-config.yaml 2>/dev/null || true
	kubectl cluster-info --context kind-ai-trading

cluster-down:
	$(KIND) delete cluster --name ai-trading

load-images:
	docker build -t ai-trading/backend:latest backend
	docker build -t ai-trading/frontend:latest frontend
	$(KIND) load docker-image ai-trading/backend:latest --name ai-trading
	$(KIND) load docker-image ai-trading/frontend:latest --name ai-trading

deploy: cluster-up load-images
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	kubectl -n ingress-nginx wait --for=condition=ready pod -l app.kubernetes.io/component=controller --timeout=180s
	kubectl apply -k infra/k8s/overlays/dev
	kubectl --context kind-ai-trading -n ai-trading-dev rollout status deploy/backend --timeout=120s
	@echo "Add '127.0.0.1 trading.local' to your hosts file, then open http://trading.local:8090"

undeploy:
	kubectl delete -k infra/k8s/overlays/dev --ignore-not-found
