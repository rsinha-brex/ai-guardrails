"""OpenRouter-backed Pydantic AI model factories.

OpenRouter is OpenAI-compatible. Pydantic AI's OpenAI provider reaches it
through `base_url=https://openrouter.ai/api/v1` and the OpenRouter API key.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import get_settings

OPENROUTER_BASE = "https://openrouter.ai/api/v1"


@lru_cache
def _provider() -> OpenAIProvider:
    s = get_settings()
    return OpenAIProvider(api_key=s.openrouter_api_key, base_url=OPENROUTER_BASE)


def main_model() -> OpenAIChatModel:
    return OpenAIChatModel(get_settings().main_model, provider=_provider())


def main_model_for(name: str | None, *, temperature: float = 0) -> OpenAIChatModel:
    """Main-agent model factory with optional per-call overrides.

    Used by the eval lib's `agent_e2e` runner to pin a specific OpenRouter
    model and force `temperature=0` for reproducibility, without touching
    the env-driven defaults that production uses. `name=None` falls back to
    the configured MAIN_MODEL.
    """
    from pydantic_ai.settings import ModelSettings

    return OpenAIChatModel(
        name or get_settings().main_model,
        provider=_provider(),
        settings=ModelSettings(temperature=temperature),
    )


def compile_model() -> OpenAIChatModel:
    return OpenAIChatModel(get_settings().compile_model, provider=_provider())


def compile_model_for(name: str | None) -> OpenAIChatModel:
    """Compile-step model factory with optional per-call override.

    Used by the eval lib so individual cases can pin a specific OpenRouter
    model (e.g. "anthropic/claude-haiku-4.5") to compare compile fidelity
    across models without changing the env. Falls back to the configured
    COMPILE_MODEL when `name` is None.
    """
    return OpenAIChatModel(name or get_settings().compile_model, provider=_provider())


def judge_model() -> OpenAIChatModel:
    return OpenAIChatModel(get_settings().judge_model, provider=_provider())
