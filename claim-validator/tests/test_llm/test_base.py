"""Tests for BaseLLMClient ABC and Message dataclass."""

from __future__ import annotations

import abc

import pytest

from claim_validator.llm.base import BaseLLMClient, Message

# --- Message dataclass tests ---


class TestMessage:
    """Test the Message dataclass."""

    def test_create_message(self) -> None:
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self) -> None:
        msg = Message(role="system", content="You are a validator.")
        assert msg.role == "system"

    def test_assistant_message(self) -> None:
        msg = Message(role="assistant", content="I'll help.")
        assert msg.role == "assistant"

    def test_frozen(self) -> None:
        msg = Message(role="user", content="Hello")
        with pytest.raises(AttributeError):
            msg.role = "assistant"  # type: ignore[misc]

    def test_equality(self) -> None:
        m1 = Message(role="user", content="Hi")
        m2 = Message(role="user", content="Hi")
        assert m1 == m2

    def test_inequality(self) -> None:
        m1 = Message(role="user", content="Hi")
        m2 = Message(role="user", content="Bye")
        assert m1 != m2


# --- BaseLLMClient ABC tests ---


class TestBaseLLMClient:
    """Test BaseLLMClient is a proper ABC."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            BaseLLMClient(model="test", api_key="key")  # type: ignore[abstract]

    def test_is_abstract_class(self) -> None:
        assert abc.ABC in BaseLLMClient.__mro__

    def test_send_messages_is_abstract(self) -> None:
        assert getattr(
            BaseLLMClient.send_messages, "__isabstractmethod__", False
        )

    def test_subclass_with_implementation(self) -> None:
        class FakeClient(BaseLLMClient):
            provider_name = "fake"

            def send_messages(self, messages: list[Message]) -> str:
                return "fake response"

        client = FakeClient(model="test-model", api_key="sk-test")
        assert client.model == "test-model"
        assert client.provider_name == "fake"

    def test_model_property(self) -> None:
        class FakeClient(BaseLLMClient):
            provider_name = "fake"

            def send_messages(self, messages: list[Message]) -> str:
                return ""

        client = FakeClient(model="gpt-4o", api_key="sk-test")
        assert client.model == "gpt-4o"

    def test_send_messages_returns_string(self) -> None:
        class FakeClient(BaseLLMClient):
            provider_name = "fake"

            def send_messages(self, messages: list[Message]) -> str:
                return messages[0].content

        client = FakeClient(model="m", api_key="k")
        result = client.send_messages([Message(role="user", content="hi")])
        assert isinstance(result, str)
        assert result == "hi"

    def test_provider_name_default_empty(self) -> None:
        assert BaseLLMClient.provider_name == ""

    def test_kwargs_accepted(self) -> None:
        class FakeClient(BaseLLMClient):
            provider_name = "fake"

            def __init__(
                self, *, model: str, api_key: str, **kwargs: object
            ) -> None:
                super().__init__(model=model, api_key=api_key, **kwargs)
                self.extra = kwargs.get("extra_param")

            def send_messages(self, messages: list[Message]) -> str:
                return ""

        client = FakeClient(
            model="m", api_key="k", extra_param="value"
        )
        assert client.extra == "value"
