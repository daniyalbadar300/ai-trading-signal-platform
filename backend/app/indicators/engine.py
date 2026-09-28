"""Technical indicators implemented in pure pandas.

No third-party TA library: fewer dependencies, fully deterministic and easy
to unit-test against hand-computed values.
"""

import pandas as pd

from app.models import IndicatorSnapshot


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder smoothing == EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    rs = avg_gain / avg_loss
    out = (100 - (100 / (1 + rs))).astype(float)

    # Explicit edge cases (0-division produces inf/NaN otherwise):
    #   pure gains            -> RSI 100
    #   pure losses           -> RSI 0
    #   no movement at all    -> neutral 50
    out[(avg_loss == 0) & (avg_gain > 0)] = 100.0
    out[(avg_gain == 0) & (avg_loss > 0)] = 0.0
    out[(avg_gain == 0) & (avg_loss == 0)] = 50.0
    return out.fillna(50.0)


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line and histogram."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Upper, middle (SMA) and lower Bollinger bands."""
    mid = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    return mid + num_std * std, mid, mid - num_std * std


def snapshot(frame: pd.DataFrame) -> IndicatorSnapshot:
    """Compute the latest indicator values for an OHLCV DataFrame.

    Expects columns: open, high, low, close, volume (indexed by open_time).
    """
    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float)

    rsi_series = rsi(close)
    macd_line, signal_line, hist = macd(close)
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)
    bb_upper, bb_mid, bb_lower = bollinger(close)
    vol_avg = volume.rolling(20).mean()

    def last(s: pd.Series) -> float:
        return float(s.iloc[-1])

    return IndicatorSnapshot(
        rsi_14=last(rsi_series),
        macd=last(macd_line),
        macd_signal=last(signal_line),
        macd_hist=last(hist),
        ema_20=last(ema20),
        ema_50=last(ema50),
        bb_upper=last(bb_upper),
        bb_lower=last(bb_lower),
        bb_mid=last(bb_mid),
        volume_ratio=last(volume) / last(vol_avg) if last(vol_avg) > 0 else 1.0,
    )
