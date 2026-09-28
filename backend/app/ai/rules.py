"""Deterministic rule-based commentary: the no-key / no-network fallback."""

from datetime import UTC, datetime

from app.ai.commentary import Commentary, CommentaryProvider
from app.models import Signal, SignalAction

_ACTION_LEAD = {
    SignalAction.BUY: "Bullish confluence detected",
    SignalAction.SELL: "Bearish confluence detected",
    SignalAction.HOLD: "Mixed signals — market lacks clear direction",
}


class RuleBasedCommentary(CommentaryProvider):
    """Templates driven by the signal's own numbers — zero external calls."""

    async def generate(self, signal: Signal) -> Commentary:
        ind = signal.indicators
        parts: list[str] = [_ACTION_LEAD[signal.action]]

        # Momentum
        if ind.macd_hist > 0:
            parts.append("MACD histogram is positive, momentum currently favors buyers")
        elif ind.macd_hist < 0:
            parts.append("MACD histogram is negative, momentum leans toward sellers")

        # Mean reversion
        if ind.rsi_14 >= 70:
            parts.append(f"RSI {ind.rsi_14:.0f} is overbought, a pullback would not be surprising")
        elif ind.rsi_14 <= 30:
            parts.append(f"RSI {ind.rsi_14:.0f} is oversold, a rebound attempt is plausible")

        # Trend alignment
        if ind.ema_20 > ind.ema_50:
            parts.append("the 20-period EMA sits above the 50, consistent with an upward bias")
        else:
            parts.append("the 20-period EMA sits below the 50, consistent with a downward bias")

        # Volume context
        if ind.volume_ratio >= 1.5:
            parts.append(f"volume is elevated at {ind.volume_ratio:.1f}x its 20-period average")
        elif ind.volume_ratio <= 0.5:
            parts.append("trading activity is thin, so treat the move with extra caution")

        text = f"{parts[0]}: {', '.join(parts[1:-1])}, and {parts[-1]}."

        risk = self._risk_note(signal)
        return Commentary(
            text=text,
            risk_note=risk,
            source="rule-engine",
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _risk_note(signal: Signal) -> str:
        if signal.action == SignalAction.BUY:
            return (
                f"Signal confidence is {signal.confidence:.0%}; a stop below recent lows and "
                "sizing below 2% of capital are prudent. Educational use only."
            )
        if signal.action == SignalAction.SELL:
            return (
                f"Signal confidence is {signal.confidence:.0%}; shorts face squeeze risk, "
                "so size conservatively. Educational use only."
            )
        return (
            "Low-conviction conditions; sitting out is a valid position. "
            "Educational use only."
        )
