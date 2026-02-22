"""AnthropicClient — Anthropic Messages API provider."""

from __future__ import annotations

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import anthropic
except ImportError as exc:
    raise ImportError(
        "AnthropicClient requires the anthropic SDK. "
        "Install it with: pip install claim-validator[anthropic]"
    ) from exc


class AnthropicClient(BaseLLMClient):
    """LLM client using the Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = anthropic.Anthropic(api_key=api_key)

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages via Anthropic Messages API."""
        system_msg = ""
        api_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                api_messages.append(
                    {"role": msg.role, "content": msg.content}
                )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system_msg,
                messages=api_messages,  # type: ignore[arg-type]
            )
            return response.content[0].text  # type: ignore[union-attr]
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
