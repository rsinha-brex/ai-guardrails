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


def compile_model() -> OpenAIChatModel:
    return OpenAIChatModel(get_settings().compile_model, provider=_provider())


def judge_model() -> OpenAIChatModel:
    return OpenAIChatModel(get_settings().judge_model, provider=_provider())
