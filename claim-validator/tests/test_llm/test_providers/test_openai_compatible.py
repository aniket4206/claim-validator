"""Tests for OpenAICompatibleClient LLM provider."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message


def _make_mock_httpx() -> MagicMock:
    """Create a mock httpx module with proper structure."""
    mock_mod = MagicMock()
    mock_mod.HTTPError = type("HTTPError", (Exception,), {})
    return mock_mod


def _get_compatible_client_class(mock_mod: MagicMock) -> type:
    """Import OpenAICompatibleClient with mocked httpx."""
    mod_key = "claim_validator.llm.providers.openai_compatible"
    if mod_key in sys.modules:
        del sys.modules[mod_key]
    with patch.dict("sys.modules", {"httpx": mock_mod}):
        mod = importlib.import_module(mod_key)
        return mod.OpenAICompatibleClient  # type: ignore[no-any-return]


class TestOpenAICompatibleClientBasics:
    """Test OpenAICompatibleClient basic behavior."""

    def test_is_base_llm_client_subclass(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        assert issubclass(cls, BaseLLMClient)

    def test_provider_name(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        assert cls.provider_name == "openai_compatible"

    def test_model_property(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(
            model="llama3",
            api_key="k",
            base_url="http://localhost:11434/v1",
        )
        assert client.model == "llama3"

    def test_default_base_url(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="m", api_key="k")
        assert client._base_url == "http://localhost:11434/v1"

    def test_custom_base_url(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(
            model="m",
            api_key="k",
            base_url="http://custom:8080/v1",
        )
        assert client._base_url == "http://custom:8080/v1"

    def test_trailing_slash_stripped(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(
            model="m",
            api_key="k",
            base_url="http://localhost:11434/v1/",
        )
        assert client._base_url == "http://localhost:11434/v1"

    def test_creates_httpx_client(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        cls(model="m", api_key="test-key")
        mock_mod.Client.assert_called_once()
        call_kwargs = mock_mod.Client.call_args.kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"


class TestOpenAICompatibleSendMessages:
    """Test OpenAICompatibleClient.send_messages()."""

    def test_send_user_message(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="llama3", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [
                {"message": {"content": "AI response"}}
            ]
        }
        mock_mod.Client.return_value.post.return_value = mock_resp

        result = client.send_messages(
            [Message(role="user", content="Hello")]
        )
        assert result == "AI response"

    def test_posts_to_chat_completions(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_mod.Client.return_value.post.return_value = mock_resp

        client.send_messages(
            [Message(role="user", content="x")]
        )

        mock_mod.Client.return_value.post.assert_called_once()
        call_args = mock_mod.Client.return_value.post.call_args
        assert call_args.args[0] == "/chat/completions"

    def test_sends_correct_payload(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="llama3", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_mod.Client.return_value.post.return_value = mock_resp

        client.send_messages([
            Message(role="system", content="System prompt"),
            Message(role="user", content="User msg"),
        ])

        call_kwargs = mock_mod.Client.return_value.post.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["model"] == "llama3"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"

    def test_calls_raise_for_status(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_mod.Client.return_value.post.return_value = mock_resp

        client.send_messages(
            [Message(role="user", content="x")]
        )
        mock_resp.raise_for_status.assert_called_once()

    def test_returns_string(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "text"}}]
        }
        mock_mod.Client.return_value.post.return_value = mock_resp

        result = client.send_messages(
            [Message(role="user", content="x")]
        )
        assert isinstance(result, str)


class TestOpenAICompatibleErrors:
    """Test OpenAICompatibleClient error handling."""

    def test_http_error_wrapped_in_llm_error(self) -> None:
        mock_mod = _make_mock_httpx()
        cls = _get_compatible_client_class(mock_mod)
        client = cls(model="m", api_key="k")

        mock_mod.Client.return_value.post.side_effect = (
            mock_mod.HTTPError("connection failed")
        )

        with pytest.raises(
            LLMError, match="OpenAI-compatible endpoint error"
        ):
            client.send_messages(
                [Message(role="user", content="x")]
            )

    def test_import_error_without_httpx(self) -> None:
        mod_key = "claim_validator.llm.providers.openai_compatible"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        with patch.dict("sys.modules", {"httpx": None}):
            with pytest.raises(
                ImportError, match="claim-validator\\[ai\\]"
            ):
                importlib.import_module(mod_key)
