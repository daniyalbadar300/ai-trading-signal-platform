"""Indicator math correctness against hand-computed references."""

import pandas as pd

from app.indicators.engine import bollinger, ema, macd, rsi


def test_ema_converges_to_constant_series():
    s = pd.Series([100.0] * 50)
    result = ema(s, span=10)
    assert abs(result.iloc[-1] - 100.0) < 1e-9


def test_ema_matches_manual_recursive_definition():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    span = 3
    alpha = 2 / (span + 1)
    expected = [s.iloc[0]]
    for value in s.iloc[1:]:
        expected.append(alpha * value + (1 - alpha) * expected[-1])
    result = ema(s, span=span)
    for got, want in zip(result, expected, strict=True):
        assert abs(got - want) < 1e-9


def test_rsi_all_gains_is_100():
    up = pd.Series([float(i) for i in range(1, 30)])
    assert rsi(up).iloc[-1] == 100.0


def test_rsi_all_losses_is_0():
    down = pd.Series([float(i) for i in range(30, 1, -1)])
    assert rsi(down).iloc[-1] == 0.0


def test_rsi_flat_series_is_neutral_50():
    flat = pd.Series([50.0] * 30)
    assert rsi(flat).iloc[-1] == 50.0


def test_rsi_range_bounds():
    import math

    s = pd.Series([100 + 10 * math.sin(i / 3.0) for i in range(200)])
    out = rsi(s)
    assert ((out >= 0) & (out <= 100)).all()


def test_macd_line_is_ema_difference():
    s = pd.Series([100.0, 101.5, 99.0, 102.0, 100.5, 103.0] * 10)
    macd_line, signal_line, hist = macd(s)
    expected_line = ema(s, 12) - ema(s, 26)
    pd.testing.assert_series_equal(macd_line, expected_line)
    assert (hist == macd_line - signal_line).all()


def test_bollinger_contains_recent_prices_mostly():
    """With realistic noise, ~95% of prices stay inside the bands."""
    import math

    import numpy as np

    rng = np.random.RandomState(42)  # deterministic noise
    noise = rng.normal(0, 2.0, 120)
    s = pd.Series([100 + 5 * math.sin(i / 7.0) for i in range(120)]) + noise
    upper, mid, lower = bollinger(s)
    inside = ((s <= upper) & (s >= lower)).iloc[20:]
    assert inside.mean() > 0.85
