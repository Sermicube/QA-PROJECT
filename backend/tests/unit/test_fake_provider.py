import pytest
from pydantic import BaseModel

from app.llm.fake_provider import FakeProvider
from app.llm.provider import Message


class _Schema(BaseModel):
    value: str
    count: int = 0


# ── complete ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_complete_returns_configured_response() -> None:
    provider = FakeProvider(response="respuesta fija")
    result = await provider.complete("sistema", [Message(role="user", content="hola")], max_tokens=50)
    assert result == "respuesta fija"


@pytest.mark.asyncio
async def test_complete_records_call() -> None:
    provider = FakeProvider()
    await provider.complete("sys", [Message(role="user", content="q1")], max_tokens=100)
    await provider.complete("sys", [Message(role="user", content="q2")], max_tokens=100)
    assert len(provider.calls) == 2


@pytest.mark.asyncio
async def test_complete_records_system_and_messages() -> None:
    provider = FakeProvider()
    await provider.complete("el sistema", [Message(role="user", content="pregunta")], max_tokens=50)
    call = provider.calls[0]
    assert call.system == "el sistema"
    assert call.messages[0].content == "pregunta"
    assert call.schema_name is None


# ── structured ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_structured_parses_json_response() -> None:
    provider = FakeProvider(response='{"value": "ok", "count": 3}')
    result = await provider.structured("sys", [Message(role="user", content="q")], _Schema)
    assert isinstance(result, _Schema)
    assert result.value == "ok"
    assert result.count == 3


@pytest.mark.asyncio
async def test_structured_records_schema_name() -> None:
    provider = FakeProvider(response='{"value": "x"}')
    await provider.structured("sys", [Message(role="user", content="q")], _Schema)
    assert provider.calls[0].schema_name == "_Schema"


@pytest.mark.asyncio
async def test_structured_raises_on_invalid_json() -> None:
    provider = FakeProvider(response="no es json")
    with pytest.raises(Exception):
        await provider.structured("sys", [Message(role="user", content="q")], _Schema)


# ── spy helpers ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_sent_text_aggregates_calls() -> None:
    provider = FakeProvider(response="x")
    await provider.complete("sistema A", [Message(role="user", content="mensaje 1")], max_tokens=10)
    await provider.complete("sistema B", [Message(role="user", content="mensaje 2")], max_tokens=10)
    aggregated = provider.all_sent_text
    assert "sistema A" in aggregated
    assert "mensaje 1" in aggregated
    assert "sistema B" in aggregated
    assert "mensaje 2" in aggregated


@pytest.mark.asyncio
async def test_reset_clears_calls() -> None:
    provider = FakeProvider()
    await provider.complete("sys", [Message(role="user", content="q")], max_tokens=10)
    assert len(provider.calls) == 1
    provider.reset()
    assert len(provider.calls) == 0
