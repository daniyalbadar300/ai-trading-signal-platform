"""Signal engine scoring and classification tests."""

from datetime import UTC, datetime, timedelta

from app.models import Candle, SignalAction
from app.signals.engine import (
    _bollinger_score,
    _ema_cross_score,
    _macd_score,
    _rsi_score,
    _volume_score,
    generate_signal,
)

START = datetime(2026, 1, 1, tzinfo=UTC)


def staircase_candles(direction: str, n: int = 120) -> list[Candle]:
    """Deterministic staircase trend series."""
    step = 1.0 if direction == "up" else -1.0
    return [
        Candle(
            open_time=START + timedelta(minutes=i),
            open=300.0 + step * i,
            high=300.5 + step * i,
            low=299.5 + step * i,
            close=300.4 + step * i,
            volume=1000.0,
        )
        for i in range(n)
    ]


class TestComponentScores:
    def test_rsi_oversold_is_bullish(self):
        assert _rsi_score(20.0) == 1.0

    def test_rsi_overbought_is_bearish(self):
        assert _rsi_score(80.0) == -1.0

    def test_rsi_neutral_band_is_zero(self):
        assert _rsi_score(50.0) == 0.0

    def test_rsi_between_band_and_extreme_scales(self):
        score = _rsi_score(37.5)  # halfway between 30 and 45
        assert 0.0 < score < 1.0
        assert abs(score - 0.5) < 1e-9

    def test_macd_positive_hist_bullish(self):
        assert _macd_score(hist=0.5, prev_hist=0.4) > 0

    def test_macd_negative_hist_bearish(self):
        assert _macd_score(hist=-0.5, prev_hist=-0.4) < 0

    def test_macd_accelerating_gets_boost(self):
        accelerating = _macd_score(hist=0.5, prev_hist=0.4)
        decelerating = _macd_score(hist=0.5, prev_hist=0.7)
        assert accelerating > decelerating

    def test_ema_cross_bullish_alignment(self):
        assert _ema_cross_score(100.0, 101.0, 99.0) > 0

    def test_ema_cross_clamped_at_one_percent(self):
        assert _ema_cross_score(100.0, 102.0, 98.0) == 1.0

    def test_bollinger_mean_reversion(self):
        upper, mid, lower = 110.0, 100.0, 90.0
        assert _bollinger_score(90.5, upper, lower, mid) > 0  # near lower -> bullish
        assert _bollinger_score(109.5, upper, lower, mid) < 0  # near upper -> bearish

    def test_volume_amplifies(self):
        assert _volume_score(1.8) > 0
        assert _volume_score(1.0) == 0.0
        assert _volume_score(0.4) < 0


class TestCompositeSignal:
    def test_signal_shape(self, candles):
        signal = generate_signal("BTCUSDT", candles)
        assert signal.symbol == "BTCUSDT"
        assert signal.action in list(SignalAction)
        assert 0.0 <= signal.confidence <= 1.0
        assert -1.0 <= signal.score <= 1.0
        assert signal.price == candles[-1].close
        assert set(signal.contributions) == {"rsi", "macd", "ema_cross", "bollinger", "volume"}

    def test_deterministic(self, candles):
        a = generate_signal("BTCUSDT", candles)
        b = generate_signal("BTCUSDT", candles)
        assert a.score == b.score
        assert a.action == b.action

    def test_strong_uptrend_shows_bullish_momentum(self):
        """Momentum voters confirm the trend; mean-reversion voters fade it."""
        signal = generate_signal("BTCUSDT", staircase_candles("up"))
        assert signal.contributions["macd"] > 0  # momentum confirms uptrend
        assert signal.contributions["ema_cross"] > 0  # trend alignment
        assert signal.contributions["rsi"] < 0  # overbought -> fade signal

    def test_strong_downtrend_shows_bearish_momentum(self):
        signal = generate_signal("BTCUSDT", staircase_candles("down"))
        assert signal.contributions["macd"] < 0  # momentum confirms downtrend
        assert signal.contributions["ema_cross"] < 0  # trend alignment
        assert signal.contributions["rsi"] > 0  # oversold -> fade signal

    def test_weights_sum_to_one(self):
        from app.signals.engine import WEIGHTS

        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
