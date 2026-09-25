from dataclasses import dataclass, field

from pydantic import BaseModel

from app.llm.provider import Message


@dataclass
class LLMCall:
    system: str
    messages: list[Message]
    schema_name: str | None = None

    def all_text(self) -> str:
        parts = [self.system, *(m.content for m in self.messages)]
        return "\n".join(parts)


class FakeProvider:
    """Proveedor de LLM falso para tests. Actúa como espía."""

    def __init__(self, response: str = "{}") -> None:
        self._response = response
        self.calls: list[LLMCall] = []

    @property
    def all_sent_text(self) -> str:
        return "\n".join(c.all_text() for c in self.calls)

    def reset(self) -> None:
        self.calls.clear()

    async def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
    ) -> str:
        self.calls.append(LLMCall(system=system, messages=messages))
        return self._response

    async def structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[BaseModel],
        *,
        max_tokens: int = 1024,
    ) -> BaseModel:
        self.calls.append(LLMCall(system=system, messages=messages, schema_name=schema.__name__))
        return schema.model_validate_json(self._response)
