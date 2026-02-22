"""Tests for AnthropicClient LLM provider."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message


def _make_mock_anthropic() -> MagicMock:
    """Create a mock anthropic module with proper structure."""
    mock_mod = MagicMock()
    mock_mod.APIError = type("APIError", (Exception,), {})
    return mock_mod


def _get_anthropic_client_class(mock_mod: MagicMock) -> type:
    """Import AnthropicClient with mocked anthropic SDK."""
    mod_key = "claim_validator.llm.providers.anthropic"
    # Remove cached module so guard re-runs
    if mod_key in sys.modules:
        del sys.modules[mod_key]
    with patch.dict("sys.modules", {"anthropic": mock_mod}):
        mod = importlib.import_module(mod_key)
        return mod.AnthropicClient  # type: ignore[no-any-return]


class TestAnthropicClientBasics:
    """Test AnthropicClient basic behavior."""

    def test_is_base_llm_client_subclass(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        assert issubclass(cls, BaseLLMClient)

    def test_provider_name(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        assert cls.provider_name == "anthropic"

    def test_model_property(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="claude-sonnet-4-5-20241022", api_key="sk-test")
        assert client.model == "claude-sonnet-4-5-20241022"

    def test_creates_anthropic_sdk_client(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        cls(model="m", api_key="sk-test")
        mock_mod.Anthropic.assert_called_once_with(api_key="sk-test")


class TestAnthropicSendMessages:
    """Test AnthropicClient.send_messages()."""

    def test_send_user_message(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="claude-sonnet-4-5-20241022", api_key="sk-test")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="AI response")]
        mock_mod.Anthropic.return_value.messages.create.return_value = (
            mock_response
        )

        result = client.send_messages(
            [Message(role="user", content="Hello")]
        )
        assert result == "AI response"

    def test_system_message_extracted(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]
        mock_client = mock_mod.Anthropic.return_value
        mock_client.messages.create.return_value = mock_response

        client.send_messages([
            Message(role="system", content="Be helpful"),
            Message(role="user", content="Hi"),
        ])

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["system"] == "Be helpful"
        # System message should NOT be in messages list
        for msg in call_kwargs.kwargs["messages"]:
            assert msg["role"] != "system"

    def test_multiple_messages(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="response")]
        mock_mod.Anthropic.return_value.messages.create.return_value = (
            mock_response
        )

        client.send_messages([
            Message(role="user", content="First"),
            Message(role="assistant", content="Reply"),
            Message(role="user", content="Second"),
        ])

        call_kwargs = (
            mock_mod.Anthropic.return_value.messages.create.call_args
        )
        assert len(call_kwargs.kwargs["messages"]) == 3

    def test_returns_string(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="text")]
        mock_mod.Anthropic.return_value.messages.create.return_value = (
            mock_response
        )

        result = client.send_messages(
            [Message(role="user", content="x")]
        )
        assert isinstance(result, str)


class TestAnthropicErrors:
    """Test AnthropicClient error handling."""

    def test_api_error_wrapped_in_llm_error(self) -> None:
        mock_mod = _make_mock_anthropic()
        cls = _get_anthropic_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_mod.Anthropic.return_value.messages.create.side_effect = (
            mock_mod.APIError("rate limit")
        )

        with pytest.raises(LLMError, match="Anthropic API error"):
            client.send_messages(
                [Message(role="user", content="x")]
            )

    def test_import_error_without_sdk(self) -> None:
        mod_key = "claim_validator.llm.providers.anthropic"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(
                ImportError,
                match="claim-validator\\[anthropic\\]",
            ):
                importlib.import_module(mod_key)
