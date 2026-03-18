"""Tests for GroqClient LLM provider."""

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


def _make_mock_groq_sdk() -> MagicMock:
    """Create a mock groq SDK module."""
    mock_mod = MagicMock()
    return mock_mod


def _get_groq_client_class_httpx(mock_httpx: MagicMock) -> type:
    """Import GroqClient with mocked httpx and no groq SDK."""
    mod_key = "claim_validator.llm.providers.groq"
    if mod_key in sys.modules:
        del sys.modules[mod_key]
    with patch.dict("sys.modules", {"groq": None, "httpx": mock_httpx}):
        mod = importlib.import_module(mod_key)
        return mod.GroqClient  # type: ignore[no-any-return]


def _get_groq_client_class_sdk(mock_sdk: MagicMock) -> type:
    """Import GroqClient with mocked groq SDK."""
    mod_key = "claim_validator.llm.providers.groq"
    if mod_key in sys.modules:
        del sys.modules[mod_key]
    with patch.dict("sys.modules", {"groq": mock_sdk}):
        mod = importlib.import_module(mod_key)
        return mod.GroqClient  # type: ignore[no-any-return]


class TestGroqClientBasics:
    """Test GroqClient basic behavior."""

    def test_is_base_llm_client_subclass(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        assert issubclass(cls, BaseLLMClient)

    def test_provider_name(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        assert cls.provider_name == "groq"

    def test_model_property(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="llama-3.3-70b-versatile", api_key="gsk-test")
        assert client.model == "llama-3.3-70b-versatile"

    def test_default_base_url(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="m", api_key="k")
        assert client._base_url == "https://api.groq.com/openai/v1"

    def test_custom_base_url(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="m", api_key="k", base_url="http://custom:8080/v1")
        assert client._base_url == "http://custom:8080/v1"

    def test_trailing_slash_stripped(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(
            model="m", api_key="k",
            base_url="https://api.groq.com/openai/v1/",
        )
        assert client._base_url == "https://api.groq.com/openai/v1"


class TestGroqClientHttpxFallback:
    """Test GroqClient httpx fallback mode (no groq SDK)."""

    def test_creates_httpx_client(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        cls(model="m", api_key="test-key")
        mock_httpx.Client.assert_called_once()
        call_kwargs = mock_httpx.Client.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"

    def test_send_messages_via_httpx(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="llama-3.3-70b-versatile", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Groq response"}}]
        }
        mock_httpx.Client.return_value.post.return_value = mock_resp

        result = client.send_messages(
            [Message(role="user", content="Hello")]
        )
        assert result == "Groq response"

    def test_posts_to_chat_completions(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="m", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_httpx.Client.return_value.post.return_value = mock_resp

        client.send_messages([Message(role="user", content="x")])

        mock_httpx.Client.return_value.post.assert_called_once()
        call_args = mock_httpx.Client.return_value.post.call_args
        assert call_args.args[0] == "/chat/completions"

    def test_sends_correct_payload(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="mixtral-8x7b-32768", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_httpx.Client.return_value.post.return_value = mock_resp

        client.send_messages([
            Message(role="system", content="System prompt"),
            Message(role="user", content="User msg"),
        ])

        call_kwargs = mock_httpx.Client.return_value.post.call_args.kwargs
        payload = call_kwargs["json"]
        assert payload["model"] == "mixtral-8x7b-32768"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"

    def test_http_error_wrapped_in_llm_error(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="m", api_key="k")

        mock_httpx.Client.return_value.post.side_effect = (
            mock_httpx.HTTPError("connection failed")
        )

        with pytest.raises(LLMError, match="Groq endpoint error"):
            client.send_messages([Message(role="user", content="x")])

    def test_calls_raise_for_status(self) -> None:
        mock_httpx = _make_mock_httpx()
        cls = _get_groq_client_class_httpx(mock_httpx)
        client = cls(model="m", api_key="k")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "ok"}}]
        }
        mock_httpx.Client.return_value.post.return_value = mock_resp

        client.send_messages([Message(role="user", content="x")])
        mock_resp.raise_for_status.assert_called_once()


class TestGroqClientSDKMode:
    """Test GroqClient with groq SDK installed."""

    def test_uses_groq_sdk_when_available(self) -> None:
        mock_sdk = _make_mock_groq_sdk()
        cls = _get_groq_client_class_sdk(mock_sdk)
        client = cls(model="llama-3.3-70b-versatile", api_key="gsk-test")

        assert client._groq_client is not None
        assert client._http_client is None

    def test_send_messages_via_sdk(self) -> None:
        mock_sdk = _make_mock_groq_sdk()
        cls = _get_groq_client_class_sdk(mock_sdk)
        client = cls(model="llama-3.3-70b-versatile", api_key="gsk-test")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "SDK response"
        client._groq_client.chat.completions.create.return_value = mock_response

        result = client.send_messages(
            [Message(role="user", content="Hello")]
        )
        assert result == "SDK response"

    def test_sdk_sends_correct_model(self) -> None:
        mock_sdk = _make_mock_groq_sdk()
        cls = _get_groq_client_class_sdk(mock_sdk)
        client = cls(model="mixtral-8x7b-32768", api_key="gsk-test")

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "ok"
        client._groq_client.chat.completions.create.return_value = mock_response

        client.send_messages([Message(role="user", content="x")])

        call_kwargs = client._groq_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "mixtral-8x7b-32768"

    def test_sdk_error_wrapped_in_llm_error(self) -> None:
        mock_sdk = _make_mock_groq_sdk()
        cls = _get_groq_client_class_sdk(mock_sdk)
        client = cls(model="m", api_key="k")

        client._groq_client.chat.completions.create.side_effect = (
            RuntimeError("Groq API rate limit")
        )

        with pytest.raises(LLMError, match="Groq API error"):
            client.send_messages([Message(role="user", content="x")])


class TestGroqClientImportErrors:
    """Test import error handling."""

    def test_import_error_without_groq_or_httpx(self) -> None:
        mod_key = "claim_validator.llm.providers.groq"
        if mod_key in sys.modules:
            del sys.modules[mod_key]
        with patch.dict("sys.modules", {"groq": None, "httpx": None}):
            with pytest.raises(ImportError, match="groq SDK or httpx"):
                importlib.import_module(mod_key)


class TestGroqFactoryIntegration:
    """Test that get_llm_client dispatches to GroqClient."""

    def test_factory_creates_groq_client(self) -> None:
        mock_httpx = _make_mock_httpx()
        groq_mod_key = "claim_validator.llm.providers.groq"
        saved = sys.modules.pop(groq_mod_key, None)
        try:
            with patch.dict(
                "sys.modules", {"groq": None, "httpx": mock_httpx}
            ):
                from claim_validator.llm.factory import get_llm_client

                result = get_llm_client(
                    "groq",
                    api_key="gsk-test",
                    model="llama-3.3-70b-versatile",
                )
            assert isinstance(result, BaseLLMClient)
            assert result.provider_name == "groq"
            assert result.model == "llama-3.3-70b-versatile"
        finally:
            if saved is not None:
                sys.modules[groq_mod_key] = saved
