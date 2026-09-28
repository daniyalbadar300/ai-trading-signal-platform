"""AI commentary tests: rules, LLM parsing and fallback behaviour."""

from unittest.mock import patch

from app.ai.commentary import LLMCommentary, _extract_json
from app.ai.rules import RuleBasedCommentary
from app.config import Settings
from app.models import SignalAction
from app.signals.engine import generate_signal
from tests.conftest import make_candles


def make_signal(action: SignalAction = SignalAction.BUY):
    candles = make_candles()
    signal = generate_signal("TESTUSDT", candles)
    # Force a specific action variant when a test needs it.
    return signal


class TestExtractJson:
    def test_plain_json(self):
        assert _extract_json('{"commentary": "hi", "risk_note": "lo"}') == {
            "commentary": "hi",
            "risk_note": "lo",
        }

    def test_json_in_markdown_fence(self):
        content = '```json\n{"commentary": "a", "risk_note": "b"}\n```'
        assert _extract_json(content) == {"commentary": "a", "risk_note": "b"}

    def test_json_with_leading_prose(self):
        content = 'Sure! {"commentary": "a", "risk_note": "b"} hope that helps'
        assert _extract_json(content) == {"commentary": "a", "risk_note": "b"}

    def test_garbage_returns_empty(self):
        assert _extract_json("not json at all") == {}


class TestRuleBasedCommentary:
    async def test_buy_signal_commentary(self):
        signal = make_signal()
        out = await RuleBasedCommentary().generate(signal)
        assert out.source == "rule-engine"
        assert out.text
        assert "Educational use only" in out.risk_note
        assert "Educational use only" in out.risk_note

    async def test_mentions_confidence(self):
        out = await RuleBasedCommentary().generate(make_signal())
        assert "%" in out.risk_note


class _FakeResponse:
    def __init__(self, status_code: int, content: dict):
        self.status_code = status_code
        self._content = content

    def json(self) -> dict:
        return self._content


class _FakeAsyncClient:
    """Replaces httpx.AsyncClient in LLM tests (no network)."""

    def __init__(self, status_code: int, content: dict):
        self._status = status_code
        self._content = content
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(self._status, self._content)


class TestLLMCommentary:
    async def test_no_key_falls_back_to_rules(self):
        settings = Settings(openai_api_key="")
        out = await LLMCommentary(settings).generate(make_signal())
        assert out.source == "rule-engine"

    async def test_successful_llm_call_parses_fields(self):
        settings = Settings(openai_api_key="sk-test", openai_model="test-model")
        content = '{"commentary": "Bulls in control", "risk_note": "Tight stop."}'
        fake = _FakeAsyncClient(200, {"choices": [{"message": {"content": content}}]})
        with patch("app.ai.commentary.httpx.AsyncClient", return_value=fake):
            out = await LLMCommentary(settings).generate(make_signal())
        assert out.source == "llm:test-model"
        assert out.text == "Bulls in control"
        assert out.risk_note == "Tight stop."
        assert fake.calls[0]["headers"]["Authorization"] == "Bearer sk-test"

    async def test_api_error_falls_back_to_rules(self):
        settings = Settings(openai_api_key="sk-test")
        fake = _FakeAsyncClient(500, {})
        with patch("app.ai.commentary.httpx.AsyncClient", return_value=fake):
            out = await LLMCommentary(settings).generate(make_signal())
        assert out.source == "rule-engine"

    async def test_malformed_llm_json_falls_back(self):
        settings = Settings(openai_api_key="sk-test")
        fake = _FakeAsyncClient(200, {"choices": [{"message": {"content": "blah"}}]})
        with patch("app.ai.commentary.httpx.AsyncClient", return_value=fake):
            out = await LLMCommentary(settings).generate(make_signal())
        assert out.source == "rule-engine"
