import os
from .base import AIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider

_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider is None:
        provider_name = os.environ.get("AI_PROVIDER", "anthropic").lower()
        if provider_name == "gemini":
            _provider = GeminiProvider()
        else:
            _provider = AnthropicProvider()
    return _provider
