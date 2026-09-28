# ── Stage 1: deps ─────────────────────────────────────────────
FROM python:3.13-slim AS deps
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: runtime ──────────────────────────────────────────
FROM python:3.13-slim AS runtime
WORKDIR /app

# Unprivileged user
RUN useradd --create-home --uid 1000 appuser

COPY --from=deps /install /usr/local
COPY app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
