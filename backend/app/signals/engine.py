"""Composite signal engine: turn indicator values into a scored signal."""

from datetime import UTC, datetime

from app.indicators import engine
from app.models import Candle, IndicatorSnapshot, Signal, SignalAction, candles_to_frame

# Each voter: (name, raw score in [-1, 1], weight).
# +1 = bullish, -1 = bearish. Weights sum to 1.0.
WEIGHTS: dict[str, float] = {
    "rsi": 0.25,
    "macd": 0.30,
    "ema_cross": 0.25,
    "bollinger": 0.15,
    "volume": 0.05,
}

# RSI extremes: below OVERSOLD -> bullish (rebound), above OVERBOUGHT -> bearish.
OVERSOLD = 30.0
OVERBOUGHT = 70.0
RSI_NEUTRAL_BAND = (45.0, 55.0)


def _rsi_score(rsi_value: float) -> float:
    if rsi_value <= OVERSOLD:
        return 1.0
    if rsi_value >= OVERBOUGHT:
        return -1.0
    lo, hi = RSI_NEUTRAL_BAND
    if lo <= rsi_value <= hi:
        return 0.0
    # Linear lean between neutral band and the extremes.
    if rsi_value < lo:
        return (lo - rsi_value) / (lo - OVERSOLD)
    return -(rsi_value - hi) / (OVERBOUGHT - hi)


def _macd_score(hist: float, prev_hist: float) -> float:
    """Histogram sign plus momentum direction (rising/falling histogram)."""
    magnitude = min(abs(hist) / (abs(hist) + abs(prev_hist) + 1e-9), 1.0)
    direction = 1.0 if hist > 0 else -1.0
    accelerating = (hist - prev_hist) >= 0
    boost = 1.15 if accelerating else 0.85
    return max(-1.0, min(1.0, direction * magnitude * boost))


def _ema_cross_score(close: float, ema20: float, ema50: float) -> float:
    distance = (ema20 - ema50) / close if close else 0.0
    # 1% EMA gap => full conviction.
    return max(-1.0, min(1.0, distance / 0.01))


def _bollinger_score(close: float, upper: float, lower: float, mid: float) -> float:
    if upper <= lower:
        return 0.0
    position = (close - mid) / (upper - mid) if upper != mid else 0.0  # [-1, 1]
    # Mean-reversion: near lower band -> bullish, near upper band -> bearish.
    return max(-1.0, min(1.0, -position))


def _volume_score(volume_ratio: float) -> float:
    """Volume only amplifies conviction; direction comes from the others."""
    if volume_ratio >= 1.5:
        return 0.5
    if volume_ratio <= 0.5:
        return -0.5
    return 0.0


def _prev_hist(frame) -> float:
    """MACD histogram one bar back (0.0 if not computable)."""
    close = frame["close"].astype(float)
    if len(close) < 2:
        return 0.0
    _, _, hist = engine.macd(close.iloc[:-1])
    return float(hist.iloc[-1]) if len(hist) else 0.0


def generate_signal(symbol: str, candles: list[Candle], threshold: float = 0.15) -> Signal:
    """Score the candle series and produce a composite signal."""
    frame = candles_to_frame(candles)
    snap: IndicatorSnapshot = engine.snapshot(frame)

    raw_scores = {
        "rsi": _rsi_score(snap.rsi_14),
        "macd": _macd_score(snap.macd_hist, _prev_hist(frame)),
        "ema_cross": _ema_cross_score(snap.bb_mid, snap.ema_20, snap.ema_50),
        "bollinger": _bollinger_score(
            candles[-1].close, snap.bb_upper, snap.bb_lower, snap.bb_mid
        ),
        "volume": _volume_score(snap.volume_ratio),
    }
    contributions = {name: raw_scores[name] * WEIGHTS[name] for name in WEIGHTS}
    score = sum(contributions.values())

    if score >= threshold:
        action = SignalAction.BUY
    elif score <= -threshold:
        action = SignalAction.SELL
    else:
        action = SignalAction.HOLD

    # Confidence: conviction relative to threshold, capped at 1.0.
    if action == SignalAction.HOLD:
        confidence = max(0.0, 0.5 - abs(score))
    else:
        confidence = min(1.0, abs(score) / (abs(threshold) * 3.0))

    return Signal(
        symbol=symbol,
        action=action,
        confidence=round(confidence, 4),
        score=round(score, 4),
        price=candles[-1].close,
        indicators=snap,
        contributions={k: round(v, 4) for k, v in contributions.items()},
        generated_at=datetime.now(UTC),
    )
