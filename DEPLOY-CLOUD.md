# ☁️ Cloud Deploy — Vercel (frontend) + Render (backend)

Localhost duniya ke liye nahi hota — ye guide project ko **public URLs** par
lati hai. Sab **free tier** par.

## Architecture (kyun 2 jagah?)

| Hissa | Kahan | Wajah |
|---|---|---|
| Frontend (React dashboard) | **Vercel** | Static site + CDN — Vercel ka perfect use-case |
| Backend + Worker (FastAPI + WS) | **Render** (Docker) | WebSocket + background worker serverless (Vercel) par nahi chalte — container chahiye |

```
Browser → Vercel (React, static) → fetch/wss → Render (FastAPI + worker + in-memory bus)
```

> Backend Render par single-service mode mein chalta hai: in-process worker +
> in-memory store (Redis ki zaroorat nahi — free tier par sab se simple).
> WS Render free par kaam karta hai, lekin 15 min idleness ke baad service
> sleep ho sakti hai (pehla request thanda aayega — normal hai).

## Step 1 — Backend: Render

1. <https://dashboard.render.com> → GitHub se login (repo authorize karein)
2. **New + → Web Service** → repo select karein
3. Settings (agar `render.yaml` blueprint use karein to ye auto ho jata hai —
   **New + → Blueprint** chunein aur repo select karein):
   - Runtime: **Docker** · Dockerfile path: `backend/Dockerfile` · Context: `backend`
   - Instance Type: **Free**
   - Health Check Path: `/health`
   - Environment variables:
     | Key | Value |
     |---|---|
     | `WORKER_ENABLED` | `true` |
     | `DATA_PROVIDER` | `binance` (live) ya `mock` (offline demo) |
     | `REDIS_URL` | *(khali — in-memory mode)* |
     | `METRICS_ENABLED` | `false` (Prometheus yahan nahi chal raha) |
4. **Create** → ~3-5 min build/deploy
5. URL milega, e.g. `https://ai-trading-api.onrender.com`
   - Verify: `https://<service>.onrender.com/health` → `{"status":"ok",...}`

## Step 2 — Frontend: Vercel

1. <https://vercel.com/new> → GitHub se login → repo **Import** karein
2. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`  ← zaroori (repo root nahi)
   - **Build Command:** `npm run build` (auto detect ho jata hai)
   - **Environment Variables:** `VITE_API_BASE` = `https://<service>.onrender.com`
     (Step 1 ka URL, **bina** trailing slash)
3. **Deploy** → URL milega: `https://<project>.vercel.app`

## Step 3 — Verify

- Vercel URL kholen → candles load hon, `UP` badge dikhe, 15-20s mein signal cards
- Backend URL kholen → `/docs` interactive API bhi public hai
- WS: dashboard par live updates aani chahiye (har worker cycle ke baad)

## Free-tier notes

| Baat | Detail |
|---|---|
| Render sleep | 15 min traffic na hone par spin-down; pehla request ~30-50s cold |
| WS reconnect | Dashboard ka auto-reconnect (backoff) ise khud handle karta hai |
| Bandwidth | Vercel/Render free limits demo ke liye kaafi hain |
| Upgrades | Paid tier par sleep off + Redis (Upstash free) add kar sakte hain |

## Local vs Cloud kahan farq parta hai

| | Local | Cloud |
|---|---|---|
| Frontend | localhost:5173 (vite) / :8090 (k8s) | `*.vercel.app` |
| Backend | localhost:8000 / trading.local | `*.onrender.com` |
| WS | same-origin proxy | direct `wss://` to Render |
| CORS | same-origin (issue nahi) | backend already `allow_origins=["*"]` |
