"""OpenAICompatibleClient — Generic OpenAI-compatible endpoint."""

from __future__ import annotations

from typing import Any

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import httpx
except ImportError as exc:
    raise ImportError(
        "OpenAICompatibleClient requires httpx. "
        "Install it with: pip install claim-validator[ai]"
    ) from exc


class OpenAICompatibleClient(BaseLLMClient):
    """LLM client for any OpenAI-compatible endpoint."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "http://localhost:11434/v1",
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._base_url = base_url.rstrip("/")
        self._http_client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages to an OpenAI-compatible endpoint."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
        }
        try:
            resp = self._http_client.post(
                "/chat/completions", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]
        except httpx.HTTPError as exc:
            raise LLMError(
                f"OpenAI-compatible endpoint error: {exc}"
            ) from exc
