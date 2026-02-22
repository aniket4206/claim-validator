"""OpenAIClient — OpenAI Chat Completions API provider."""

from __future__ import annotations

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import openai
except ImportError as exc:
    raise ImportError(
        "OpenAIClient requires the openai SDK. "
        "Install it with: pip install claim-validator[openai]"
    ) from exc


class OpenAIClient(BaseLLMClient):
    """LLM client using the OpenAI Chat Completions API."""

    provider_name = "openai"

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = openai.OpenAI(api_key=api_key)

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages via OpenAI Chat Completions API."""
        api_messages: list[dict[str, str]] = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=api_messages,  # type: ignore[arg-type]
            )
            return response.choices[0].message.content or ""
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {exc}") from exc
