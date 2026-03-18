"""Tests for get_llm_client() factory function."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.exceptions import ConfigurationError
from claim_validator.llm.base import BaseLLMClient
from claim_validator.llm.factory import get_llm_client


def _make_mock_httpx() -> MagicMock:
    """Create a mock httpx module."""
    mock_mod = MagicMock()
    mock_mod.HTTPError = type("HTTPError", (Exception,), {})
    return mock_mod


class TestFactoryDispatch:
    """Test get_llm_client dispatches to correct provider."""

    def test_anthropic_provider(self) -> None:
        mock_sdk = MagicMock()
        mock_sdk.APIError = type("APIError", (Exception,), {})
        mod_key = "claim_validator.llm.providers.anthropic"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch.dict("sys.modules", {"anthropic": mock_sdk}):
                result = get_llm_client(
                    "anthropic",
                    api_key="sk-test",
                    model="claude-sonnet-4-5-20241022",
                )
            assert isinstance(result, BaseLLMClient)
            assert result.provider_name == "anthropic"
            assert result.model == "claude-sonnet-4-5-20241022"
        finally:
            if saved is not None:
                sys.modules[mod_key] = saved

    def test_openai_provider(self) -> None:
        mock_sdk = MagicMock()
        mock_sdk.APIError = type("APIError", (Exception,), {})
        mod_key = "claim_validator.llm.providers.openai"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch.dict("sys.modules", {"openai": mock_sdk}):
                result = get_llm_client(
                    "openai", api_key="sk-test", model="gpt-4o"
                )
            assert isinstance(result, BaseLLMClient)
            assert result.provider_name == "openai"
            assert result.model == "gpt-4o"
        finally:
            if saved is not None:
                sys.modules[mod_key] = saved

    def test_openai_compatible_provider(self) -> None:
        mock_httpx = _make_mock_httpx()
        mod_key = "claim_validator.llm.providers.openai_compatible"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch.dict("sys.modules", {"httpx": mock_httpx}):
                result = get_llm_client(
                    "openai_compatible",
                    api_key="sk-test",
                    model="llama3",
                    base_url="http://localhost:11434/v1",
                )
            assert isinstance(result, BaseLLMClient)
            assert result.provider_name == "openai_compatible"
            assert result.model == "llama3"
        finally:
            if saved is not None:
                sys.modules[mod_key] = saved


    def test_groq_provider(self) -> None:
        mock_httpx = _make_mock_httpx()
        mod_key = "claim_validator.llm.providers.groq"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch.dict(
                "sys.modules", {"groq": None, "httpx": mock_httpx}
            ):
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
                sys.modules[mod_key] = saved


class TestFactoryErrors:
    """Test error handling in get_llm_client."""

    def test_unknown_provider_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Unknown LLM provider"):
            get_llm_client(
                "not_a_provider", api_key="k", model="m"
            )

    def test_error_message_lists_supported_providers(self) -> None:
        with pytest.raises(
            ConfigurationError, match="anthropic"
        ):
            get_llm_client("bad", api_key="k", model="m")

    def test_error_message_lists_groq(self) -> None:
        with pytest.raises(
            ConfigurationError, match="groq"
        ):
            get_llm_client("bad", api_key="k", model="m")

    def test_anthropic_missing_sdk_raises_import_error(self) -> None:
        provider_mod = "claim_validator.llm.providers.anthropic"
        saved = sys.modules.pop(provider_mod, None)
        try:
            with patch.dict("sys.modules", {"anthropic": None}):
                with pytest.raises(
                    ImportError, match="claim-validator\\[anthropic\\]"
                ):
                    get_llm_client("anthropic", api_key="k", model="m")
        finally:
            if saved is not None:
                sys.modules[provider_mod] = saved

    def test_openai_missing_sdk_raises_import_error(self) -> None:
        provider_mod = "claim_validator.llm.providers.openai"
        saved = sys.modules.pop(provider_mod, None)
        try:
            with patch.dict("sys.modules", {"openai": None}):
                with pytest.raises(
                    ImportError, match="claim-validator\\[openai\\]"
                ):
                    get_llm_client("openai", api_key="k", model="m")
        finally:
            if saved is not None:
                sys.modules[provider_mod] = saved

    def test_httpx_missing_raises_import_error(self) -> None:
        provider_mod = "claim_validator.llm.providers.openai_compatible"
        saved = sys.modules.pop(provider_mod, None)
        try:
            with patch.dict("sys.modules", {"httpx": None}):
                with pytest.raises(
                    ImportError, match="claim-validator\\[ai\\]"
                ):
                    get_llm_client(
                        "openai_compatible", api_key="k", model="m"
                    )
        finally:
            if saved is not None:
                sys.modules[provider_mod] = saved


class TestFactoryKwargs:
    """Test that kwargs are passed through to providers."""

    def test_base_url_passed_to_openai_compatible(self) -> None:
        mock_httpx = _make_mock_httpx()
        mod_key = "claim_validator.llm.providers.openai_compatible"
        saved = sys.modules.pop(mod_key, None)
        try:
            with patch.dict("sys.modules", {"httpx": mock_httpx}):
                result = get_llm_client(
                    "openai_compatible",
                    api_key="k",
                    model="m",
                    base_url="http://custom:8080/v1",
                )
                assert result._base_url == "http://custom:8080/v1"
        finally:
            if saved is not None:
                sys.modules[mod_key] = saved


class TestFactoryImports:
    """Test that the factory can be imported correctly."""

    def test_import_from_llm_package(self) -> None:
        from claim_validator.llm import get_llm_client as fn
        assert callable(fn)

    def test_import_from_top_level(self) -> None:
        from claim_validator import get_llm_client as fn
        assert callable(fn)
