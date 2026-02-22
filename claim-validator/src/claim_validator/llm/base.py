"""BaseLLMClient abstract base class and Message dataclass."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """A single message in an LLM conversation."""

    role: str  # "system", "user", "assistant"
    content: str


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM provider clients.

    Subclass this to integrate a custom LLM provider.
    Implement ``send_messages()`` to transport messages
    to your provider and return the text response.
    """

    provider_name: str = ""  # Override in subclasses

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        self._model = model
        self._api_key = api_key

    @property
    def model(self) -> str:
        """The model identifier."""
        return self._model

    @abc.abstractmethod
    def send_messages(self, messages: list[Message]) -> str:
        """Send messages to the LLM and return the text response.

        Raises:
            LLMError: If the provider returns an error.
        """
