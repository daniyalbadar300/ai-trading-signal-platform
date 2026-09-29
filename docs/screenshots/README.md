# 📸 Screenshots

Capture these from a running `make deploy` + `make monitoring-up` stack and
save them in this folder, then drop the markdown into README at the marked
placeholder:

| File | What to show | Where |
|---|---|---|
| `dashboard.png` | `http://trading.local:8090` — candlestick chart + BUY/SELL signal cards + live WS updates | After the architecture diagram |
| `grafana.png` | `http://trading.local:8090/grafana` — "AI Trading Signals" dashboard (worker UP, signals by action) | In the Monitoring section |
| `prometheus.png` | `http://trading.local:8090/prometheus` — targets page showing `kubernetes-pods` all up | In the Monitoring section |

Suggested size: full-window at 1440×900, dark theme (matches the dashboard).
