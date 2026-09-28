"""AI market commentary: LLM-backed with deterministic rule-based fallback.

Uses any OpenAI-compatible chat-completions API (OpenAI, Gemini, Groq,
Ollama...). Configure via OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL.
Without a key the rule-based fallback keeps the whole system functional.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx
from pydantic import BaseModel

from app.config import Settings
from app.models import Signal

logger = logging.getLogger(__name__)


class Commentary(BaseModel):
    """AI-generated commentary attached to a signal."""

    text: str
    risk_note: str
    source: str  # "llm:<model>" | "rule-engine"
    generated_at: datetime


class CommentaryProvider(ABC):
    """Anything that can narrate a signal."""

    @abstractmethod
    async def generate(self, signal: Signal) -> Commentary:
        """Return commentary for the given signal."""
        raise NotImplementedError


class LLMCommentary(CommentaryProvider):
    """OpenAI-compatible chat-completions client."""

    SYSTEM_PROMPT = (
        "You are a concise crypto market analyst for an educational trading-signal app. "
        "Given a JSON signal summary, write: (1) a 2-3 sentence market commentary, "
        "(2) a one-sentence risk note. Never give financial advice; use hedged language. "
        'Respond ONLY with JSON: {"commentary": "...", "risk_note": "..."}'
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._timeout = httpx.Timeout(15.0, connect=5.0)

    async def generate(self, signal: Signal) -> Commentary:
        if not self._settings.openai_api_key:
            return await self.generate_fallback(signal)
        try:
            return await self._call_llm(signal)
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
            logger.warning("LLM commentary failed (%s); using rule-based fallback", exc)
            return await self.generate_fallback(signal)

    async def generate_fallback(self, signal: Signal) -> Commentary:
        """Deterministic commentary when no key or the API fails."""
        from app.ai.rules import RuleBasedCommentary

        return await RuleBasedCommentary().generate(signal)

    async def _call_llm(self, signal: Signal) -> Commentary:
        payload = {
            "model": self._settings.openai_model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": self._user_prompt(signal)},
            ],
            "temperature": 0.4,
            "max_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._settings.openai_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
        if resp.status_code != 200:
            raise ValueError(f"LLM API status {resp.status_code}")
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        text = str(parsed.get("commentary", "")).strip()
        if not text:
            raise ValueError("LLM returned empty commentary")
        return Commentary(
            text=text,
            risk_note=str(parsed.get("risk_note", "")).strip(),
            source=f"llm:{self._settings.openai_model}",
            generated_at=datetime.now(UTC),
        )

    def _user_prompt(self, signal: Signal) -> str:
        ema_side = "above" if signal.indicators.ema_20 >= signal.indicators.ema_50 else "below"
        bb_side = "above" if signal.price >= signal.indicators.bb_mid else "below"
        return (
            f"Signal: {signal.action} {signal.symbol} at {signal.price:.2f} USDT, "
            f"confidence {signal.confidence:.0%}, composite score {signal.score:+.2f}. "
            f"Indicators: RSI14={signal.indicators.rsi_14:.1f}, "
            f"MACD hist={signal.indicators.macd_hist:.4g}, "
            f"EMA20={ema_side} EMA50, "
            f"close {bb_side} BB mid, "
            f"volume x{signal.indicators.volume_ratio:.2f} of 20-period avg. "
            "Comment on momentum, trend and volatility balance."
        )


def _extract_json(content: str) -> dict:
    """Tolerant JSON extraction from an LLM response string."""
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except ValueError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(content[start : end + 1])
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}
