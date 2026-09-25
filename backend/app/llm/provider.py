from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(
        self,
        system: str,
        messages: list[Message],
        *,
        max_tokens: int = 1024,
    ) -> str: ...

    async def structured(
        self,
        system: str,
        messages: list[Message],
        schema: type[BaseModel],
        *,
        max_tokens: int = 1024,
    ) -> BaseModel: ...
