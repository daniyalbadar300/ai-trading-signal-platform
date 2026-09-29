"""Central application configuration loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings; every value overridable via env vars."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "ai-trading-signal-platform"
    env: str = "dev"
    log_level: str = "INFO"

    # Market data
    data_provider: str = "binance"  # "binance" | "mock"
    binance_base_url: str = "https://api.binance.com"
    symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT"
    default_interval: str = "1m"
    candle_limit: int = 300

    # Signal engine
    signal_threshold: float = 0.15

    # Worker + history
    worker_interval_seconds: int = 60
    signals_history_limit: int = 50
    worker_enabled: bool = True  # false when a dedicated worker container runs

    # Caching (phase 2+)
    cache_ttl_seconds: int = 30

    # Event bus: empty = in-process; set REDIS_URL for cross-container pub/sub
    redis_url: str = ""

    # Metrics (phase 7): /metrics endpoint + HTTP/worker Prometheus counters.
    # Off by default; k8s deployments enable it via configmap. Port 0 =
    # ephemeral (tests), 8000 in k8s (scrape annotations target it).
    metrics_enabled: bool = False
    metrics_port: int = 8000

    # AI layer (phase 2, optional)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    @property
    def symbol_list(self) -> list[str]:
        """Parsed watchlist symbols."""
        return [s.strip().upper() for s in self.symbols.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (dependency-injectable)."""
    return Settings()
