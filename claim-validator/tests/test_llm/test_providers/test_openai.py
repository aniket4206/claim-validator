"""Tests for OpenAIClient LLM provider."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message


def _make_mock_openai() -> MagicMock:
    """Create a mock openai module with proper structure."""
    mock_mod = MagicMock()
    mock_mod.APIError = type("APIError", (Exception,), {})
    return mock_mod


def _get_openai_client_class(mock_mod: MagicMock) -> type:
    """Import OpenAIClient with mocked openai SDK."""
    mod_key = "claim_validator.llm.providers.openai"
    if mod_key in sys.modules:
        del sys.modules[mod_key]
    with patch.dict("sys.modules", {"openai": mock_mod}):
        mod = importlib.import_module(mod_key)
        return mod.OpenAIClient  # type: ignore[no-any-return]


class TestOpenAIClientBasics:
    """Test OpenAIClient basic behavior."""

    def test_is_base_llm_client_subclass(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        assert issubclass(cls, BaseLLMClient)

    def test_provider_name(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        assert cls.provider_name == "openai"

    def test_model_property(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="gpt-4o", api_key="sk-test")
        assert client.model == "gpt-4o"

    def test_creates_openai_sdk_client(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        cls(model="m", api_key="sk-test")
        mock_mod.OpenAI.assert_called_once_with(api_key="sk-test")


class TestOpenAISendMessages:
    """Test OpenAIClient.send_messages()."""

    def test_send_user_message(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="gpt-4o", api_key="sk-test")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="AI response"))
        ]
        mock_mod.OpenAI.return_value.chat.completions.create.return_value = (
            mock_response
        )

        result = client.send_messages(
            [Message(role="user", content="Hello")]
        )
        assert result == "AI response"

    def test_system_message_passed_directly(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="ok"))
        ]
        mock_client = mock_mod.OpenAI.return_value
        mock_client.chat.completions.create.return_value = mock_response

        client.send_messages([
            Message(role="system", content="Be helpful"),
            Message(role="user", content="Hi"),
        ])

        call_kwargs = mock_client.chat.completions.create.call_args
        msgs = call_kwargs.kwargs["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "Be helpful"

    def test_handles_none_content(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=None))
        ]
        mock_mod.OpenAI.return_value.chat.completions.create.return_value = (
            mock_response
        )

        result = client.send_messages(
            [Message(role="user", content="x")]
        )
        assert result == ""

    def test_returns_string(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="text"))
        ]
        mock_mod.OpenAI.return_value.chat.completions.create.return_value = (
            mock_response
        )

        result = client.send_messages(
            [Message(role="user", content="x")]
        )
        assert isinstance(result, str)


class TestOpenAIErrors:
    """Test OpenAIClient error handling."""

    def test_api_error_wrapped_in_llm_error(self) -> None:
        mock_mod = _make_mock_openai()
        cls = _get_openai_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_mod.OpenAI.return_value.chat.completions.create.side_effect = (
            mock_mod.APIError("quota exceeded")
        )

        with pytest.raises(LLMError, match="OpenAI API error"):
            client.send_messages(
                [Message(role="user", content="x")]
            )

    def test_import_error_without_sdk(self) -> None:
        mod_key = "claim_validator.llm.providers.openai"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(
                ImportError,
                match="claim-validator\\[openai\\]",
            ):
                importlib.import_module(mod_key)
