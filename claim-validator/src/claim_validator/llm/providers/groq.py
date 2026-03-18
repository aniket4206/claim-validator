"""GroqClient — Groq Cloud API provider.

Uses the official ``groq`` SDK when available, otherwise falls back to
the OpenAI-compatible endpoint at ``https://api.groq.com/openai/v1``
via ``httpx``.
"""

from __future__ import annotations

from typing import Any

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Try the official groq SDK first; fall back to httpx.
_USE_GROQ_SDK = False
try:
    import groq as _groq_sdk

    _USE_GROQ_SDK = True
except ImportError:
    _groq_sdk = None  # type: ignore[assignment]

if not _USE_GROQ_SDK:
    try:
        import httpx as _httpx
    except ImportError as exc:
        raise ImportError(
            "GroqClient requires either the groq SDK or httpx. "
            "Install with: pip install claim-validator[groq] "
            "or pip install claim-validator[ai]"
        ) from exc


class GroqClient(BaseLLMClient):
    """LLM client for the Groq Cloud inference API.

    Automatically uses the official ``groq`` SDK when installed.
    Falls back to an httpx-based OpenAI-compatible transport otherwise.
    """

    provider_name = "groq"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = _GROQ_BASE_URL,
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._base_url = base_url.rstrip("/")

        if _USE_GROQ_SDK:
            self._groq_client: Any = _groq_sdk.Groq(api_key=api_key)
            self._http_client = None
        else:
            self._groq_client = None
            self._http_client = _httpx.Client(
                base_url=self._base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=120.0,
            )

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages to Groq and return the text response."""
        if self._groq_client is not None:
            return self._send_via_sdk(messages)
        return self._send_via_httpx(messages)

    def _send_via_sdk(self, messages: list[Message]) -> str:
        """Send using the official groq SDK."""
        api_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]
        try:
            response = self._groq_client.chat.completions.create(
                model=self._model,
                messages=api_messages,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"Groq API error: {exc}") from exc

    def _send_via_httpx(self, messages: list[Message]) -> str:
        """Send using httpx to the OpenAI-compatible endpoint."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
        }
        try:
            resp = self._http_client.post("/chat/completions", json=payload)  # type: ignore[union-attr]
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]
        except _httpx.HTTPError as exc:
            raise LLMError(f"Groq endpoint error: {exc}") from exc
