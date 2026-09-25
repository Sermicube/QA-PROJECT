import json

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.core.config import settings
from app.llm.provider import Message


class AnthropicProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self._model = model or settings.ANTHROPIC_MODEL

    async def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
    ) -> str:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        block = resp.content[0]
        return block.text if hasattr(block, "text") else ""

    async def structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[BaseModel],
        *,
        max_tokens: int = 1024,
    ) -> BaseModel:
        schema_desc = json.dumps(schema.model_json_schema(), indent=2)
        json_system = f"{system}\n\nResponde SOLO con JSON válido que siga este esquema:\n{schema_desc}"
        current = list(messages)
        last_exc: Exception = RuntimeError("structured() no pudo parsear la respuesta")
        for _ in range(3):
            raw = await self.complete(json_system, current, max_tokens=max_tokens)
            try:
                return schema.model_validate_json(raw)
            except Exception as exc:
                last_exc = exc
                current = current + [
                    Message(role="assistant", content=raw),
                    Message(role="user", content=f"JSON inválido: {exc}. Intenta de nuevo."),
                ]
        raise last_exc
