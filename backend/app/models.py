"""Domain models shared across data providers, indicators and the API layer."""

from datetime import datetime
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel, Field


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Candle(BaseModel):
    """One OHLCV candle."""

    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorSnapshot(BaseModel):
    """Latest indicator values for one symbol."""

    rsi_14: float
    macd: float
    macd_signal: float
    macd_hist: float
    ema_20: float
    ema_50: float
    bb_upper: float
    bb_lower: float
    bb_mid: float
    volume_ratio: float  # last volume vs 20-period average


class Signal(BaseModel):
    """A composite trading signal with per-indicator breakdown."""

    symbol: str
    action: SignalAction
    confidence: float = Field(ge=0.0, le=1.0)
    score: float  # raw composite score in [-1, 1]
    price: float
    indicators: IndicatorSnapshot
    contributions: dict[str, float]  # per-indicator weighted contributions
    generated_at: datetime


def candles_to_frame(candles: list[Candle]) -> pd.DataFrame:
    """Convert candle models to an OHLCV DataFrame indexed by open_time."""
    frame = pd.DataFrame([c.model_dump() for c in candles])
    if frame.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    frame["open_time"] = pd.to_datetime(frame["open_time"])
    return frame.set_index("open_time").sort_index()
