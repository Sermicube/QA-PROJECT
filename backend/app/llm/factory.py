"""Selección del proveedor LLM.

Orden de prioridad:
1. Config del usuario en BD (user_api_keys) si se pasa user_id.
2. Variables de entorno del servidor (LLM_PROVIDER, ANTHROPIC_API_KEY, etc.).
3. FakeProvider como último recurso.
"""
from __future__ import annotations

import uuid

from app.core.config import settings
from app.llm.provider import LLMProvider


def get_provider() -> LLMProvider:
    """Proveedor global basado en variables de entorno."""
    match settings.LLM_PROVIDER:
        case "anthropic":
            from app.llm.anthropic_provider import AnthropicProvider
            return AnthropicProvider()  # type: ignore[return-value]
        case "ollama":
            from app.llm.ollama_provider import OllamaProvider
            return OllamaProvider()  # type: ignore[return-value]
        case _:
            from app.llm.fake_provider import FakeProvider
            return FakeProvider()  # type: ignore[return-value]


async def get_provider_for_user(user_id: uuid.UUID | str) -> LLMProvider:
    """Proveedor usando la API key configurada por el usuario, si existe.

    Si el usuario no tiene key configurada, cae al proveedor global.
    """
    from sqlalchemy import select
    from app.core.db import async_session_factory
    from app.core.crypto import decrypt
    from app.users.models import UserApiKey

    uid = uuid.UUID(str(user_id))
    async with async_session_factory() as session:
        result = await session.execute(
            select(UserApiKey).where(UserApiKey.user_id == uid)
        )
        key_row = result.scalar_one_or_none()

    if key_row is None:
        return get_provider()

    try:
        raw_key = decrypt(key_row.encrypted_key)
    except Exception:
        return get_provider()

    match key_row.provider:
        case "anthropic":
            from app.llm.anthropic_provider import AnthropicProvider
            return AnthropicProvider(api_key=raw_key, model=key_row.model)  # type: ignore[return-value]
        case "ollama":
            from app.llm.ollama_provider import OllamaProvider
            return OllamaProvider(base_url=key_row.base_url, model=key_row.model)  # type: ignore[return-value]
        case _:
            from app.llm.fake_provider import FakeProvider
            return FakeProvider()  # type: ignore[return-value]
