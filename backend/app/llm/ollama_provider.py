import json

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.llm.provider import Message


class OllamaProvider:
    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL

    async def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
        return str(resp.json()["message"]["content"])

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
