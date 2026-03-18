"""LLM client factory — get_llm_client()."""

from __future__ import annotations

from typing import Any

from claim_validator.exceptions import ConfigurationError
from claim_validator.llm.base import BaseLLMClient


def get_llm_client(
    provider: str,
    *,
    api_key: str,
    model: str,
    **kwargs: Any,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: Provider name ("anthropic", "openai", "openai_compatible").
        api_key: API key for the provider.
        model: Model identifier (e.g., "claude-sonnet-4-5-20241022", "gpt-4o").
        **kwargs: Provider-specific options (e.g., base_url for openai_compatible).

    Returns:
        A configured BaseLLMClient instance.

    Raises:
        ConfigurationError: If provider name is unknown.
        ImportError: If required SDK is not installed.
    """
    if provider == "anthropic":
        from claim_validator.llm.providers.anthropic import AnthropicClient

        return AnthropicClient(model=model, api_key=api_key, **kwargs)
    if provider == "openai":
        from claim_validator.llm.providers.openai import OpenAIClient

        return OpenAIClient(model=model, api_key=api_key, **kwargs)
    if provider == "openai_compatible":
        from claim_validator.llm.providers.openai_compatible import (
            OpenAICompatibleClient,
        )

        return OpenAICompatibleClient(model=model, api_key=api_key, **kwargs)
    if provider == "groq":
        from claim_validator.llm.providers.groq import GroqClient

        return GroqClient(model=model, api_key=api_key, **kwargs)
    raise ConfigurationError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported: 'anthropic', 'openai', 'openai_compatible', 'groq'."
    )
