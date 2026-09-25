from app.core.config import settings
from app.llm.provider import LLMProvider


def get_llm_provider() -> LLMProvider:
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
