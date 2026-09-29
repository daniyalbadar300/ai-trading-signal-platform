# 💻 Laptop Setup Guide (Roman Urdu)

Ye project kisi bhi laptop par chalane ke liye poora guide. VSCode ki
**zaroorat nahi** — sirf Docker + Git. (AI help chahiye to laptop par
[Codebuff](https://codebuff.com) install karein, ya VSCode + Copilot extension.)

## Step 0 — Install (ek dafa)

1. **Docker Desktop** → <https://www.docker.com/products/docker-desktop/>
   - Install ke baad START karein aur chalu rakhein (system tray whale icon green ho)
2. **Git** → <https://git-scm.com/download>
3. Check:
   ```bash
   docker --version && git --version
   ```

## Step 1 — Code laptop par le aayein

```bash
git clone https://github.com/daniyalbadar300/ai-trading-signal-platform.git
cd ai-trading-signal-platform
```

## Step 2 — Chalayein (sab se asaan tareeqa)

```bash
make up
```

Pehli dafa images build hongi (~3-5 min). Uske baad:

| Kya | Kahan |
|---|---|
| **Dashboard (live candles + signals)** | <http://localhost:5173> |
| API docs (interactive) | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |

Default mein **real Binance data** use hota hai (koi API key nahi chahiye).
Offline demo chahiye to `infra/docker-compose.yml` mein `DATA_PROVIDER=binance`
ko `mock` kar dein.

Band karne ke liye:

```bash
make down
```

## Step 3 (optional) — Kubernetes + Monitoring mode

```bash
make tools           # sirf pehli dafa: kind binary download
make deploy          # kind cluster + app + ingress
make monitoring-up   # Prometheus + Grafana
```

Phir Windows hosts file (`C:\Windows\System32\drivers\etc\hosts`, admin notepad
se) mein add karein:

```
127.0.0.1 trading.local
```

Ab:

| Kya | Kahan |
|---|---|
| Dashboard (K8s) | <http://trading.local:8090> |
| Grafana dashboard | <http://trading.local:8090/grafana> |
| Prometheus | <http://trading.local:8090/prometheus> |

Cleanup:

```bash
make monitoring-down && make undeploy && make cluster-down
```

## Step 4 (optional) — Tests

```bash
# Backend (82 tests)
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
pip install -e ".[dev]"
python -m pytest
python -m ruff check app tests

# Frontend (8 tests)
cd ../frontend
npm install
npm test
```

## Guided demo (interview/screen-share ke liye)

```bash
make demo
```

## Masail aur hal (troubleshooting)

| Masla | Hal |
|---|---|
| `docker: command not found` | Docker Desktop install/start nahi hua |
| `make` not found (Windows) | Git Bash use karein (Git ke saath aata hai) ya `choco install make` |
| Port 5173/8000 busy | Docker Desktop restart karein, ya `docker ps` se purane container band karein |
| Dashboard khali | 5-10s wait karein (worker ka pehla signal aa raha hoga); `docker compose -f infra/docker-compose.yml logs -f` se logs dekhein |
| `trading.local` nahi khulta | hosts file entry check karein (Step 3) |
| `make deploy` image pull fail | `make tools` chala kar kind binary download karein |

## Rozana chalane ka routine

```bash
# Subah (Docker Desktop chalu hone ke baad):
make up          # ya k8s ke liye: make deploy (+ make monitoring-up)

# Kaam khatam:
make down        # ya: make monitoring-down && make undeploy
```
