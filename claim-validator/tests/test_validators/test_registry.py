"""Tests for ValidatorRegistry dotted-path loading."""

from __future__ import annotations

import pytest

from claim_validator.exceptions import ConfigurationError
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.registry import ValidatorRegistry

# --- Stub validators for testing ---


class StubValidator(BaseValidator):
    """Valid validator used as a known dotted-path target."""

    name = "StubValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([])


class AnotherStubValidator(BaseValidator):
    """Second valid validator for multi-load tests."""

    name = "AnotherStubValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([])


class NotAValidator:
    """A class that is NOT a BaseValidator subclass."""

    pass


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for AI validator tests."""

    provider_name = "mock"

    def send_messages(self, messages: list[Message]) -> str:
        return "mock"


class StubAIValidator(BaseAIValidator):
    """Valid AI validator used as a known dotted-path target."""

    name = "StubAIValidator"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        return self._make_output([])


# --- Tests ---


class TestRegistryLoad:
    """Tests for ValidatorRegistry.load() method."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()

    def test_load_valid_path(self) -> None:
        cls = self.registry.load(
            "test_validators.test_registry.StubValidator"
        )
        assert cls is StubValidator

    def test_load_returns_class_not_instance(self) -> None:
        cls = self.registry.load(
            "test_validators.test_registry.StubValidator"
        )
        assert isinstance(cls, type)
        assert issubclass(cls, BaseValidator)

    def test_cache_hit_on_repeated_load(self) -> None:
        path = "test_validators.test_registry.StubValidator"
        cls1 = self.registry.load(path)
        cls2 = self.registry.load(path)
        assert cls1 is cls2

    def test_different_paths_loaded_independently(self) -> None:
        cls1 = self.registry.load(
            "test_validators.test_registry.StubValidator"
        )
        cls2 = self.registry.load(
            "test_validators.test_registry.AnotherStubValidator"
        )
        assert cls1 is not cls2
        assert cls1 is StubValidator
        assert cls2 is AnotherStubValidator

    def test_invalid_path_no_dot_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Invalid validator path"):
            self.registry.load("NoDotPath")

    def test_nonexistent_module_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Cannot import module"):
            self.registry.load("nonexistent.module.FakeValidator")

    def test_nonexistent_class_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="has no class"):
            self.registry.load(
                "test_validators.test_registry.DoesNotExist"
            )

    def test_non_validator_class_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="not a BaseValidator subclass"):
            self.registry.load(
                "test_validators.test_registry.NotAValidator"
            )

    def test_error_message_contains_offending_path(self) -> None:
        bad_path = "bad.module.path.Validator"
        with pytest.raises(ConfigurationError, match="bad.module.path"):
            self.registry.load(bad_path)


class TestRegistryCreateValidators:
    """Tests for ValidatorRegistry.create_validators() method."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()

    def test_create_returns_instances(self) -> None:
        validators = self.registry.create_validators(
            ["test_validators.test_registry.StubValidator"]
        )
        assert len(validators) == 1
        assert isinstance(validators[0], StubValidator)

    def test_create_multiple_validators(self) -> None:
        validators = self.registry.create_validators([
            "test_validators.test_registry.StubValidator",
            "test_validators.test_registry.AnotherStubValidator",
        ])
        assert len(validators) == 2
        assert isinstance(validators[0], StubValidator)
        assert isinstance(validators[1], AnotherStubValidator)

    def test_create_empty_list_returns_empty(self) -> None:
        validators = self.registry.create_validators([])
        assert validators == []

    def test_create_with_invalid_path_raises(self) -> None:
        with pytest.raises(ConfigurationError):
            self.registry.create_validators([
                "test_validators.test_registry.StubValidator",
                "nonexistent.module.FakeValidator",
            ])

    def test_instances_are_functional(self) -> None:
        validators = self.registry.create_validators(
            ["test_validators.test_registry.StubValidator"]
        )
        result = validators[0].validate(ClaimData())
        assert isinstance(result, ValidatorOutput)
        assert result.findings == []


class TestRegistryCreateAIValidators:
    """Tests for ValidatorRegistry.create_ai_validators() method."""

    def setup_method(self) -> None:
        self.registry = ValidatorRegistry()
        self.llm_client = MockLLMClient(
            model="mock-model", api_key="sk-mock",
        )

    def test_create_returns_ai_validator_instances(self) -> None:
        validators = self.registry.create_ai_validators(
            ["test_validators.test_registry.StubAIValidator"],
            llm_client=self.llm_client,
        )
        assert len(validators) == 1
        assert isinstance(validators[0], StubAIValidator)
        assert isinstance(validators[0], BaseAIValidator)

    def test_llm_client_injected(self) -> None:
        validators = self.registry.create_ai_validators(
            ["test_validators.test_registry.StubAIValidator"],
            llm_client=self.llm_client,
        )
        assert validators[0]._llm_client is self.llm_client

    def test_empty_list_returns_empty(self) -> None:
        validators = self.registry.create_ai_validators(
            [], llm_client=self.llm_client,
        )
        assert validators == []

    def test_non_ai_validator_raises_configuration_error(
        self,
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match="not a BaseAIValidator subclass",
        ):
            self.registry.create_ai_validators(
                [
                    "test_validators.test_registry"
                    ".StubValidator"
                ],
                llm_client=self.llm_client,
            )

    def test_invalid_path_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError):
            self.registry.create_ai_validators(
                ["nonexistent.module.FakeAIValidator"],
                llm_client=self.llm_client,
            )

    def test_instances_are_functional(self) -> None:
        validators = self.registry.create_ai_validators(
            ["test_validators.test_registry.StubAIValidator"],
            llm_client=self.llm_client,
        )
        claim = DeidentifiedClaim(
            billing_provider_npi="1234567893",
            patient_age=45,
        )
        result = validators[0].validate_deidentified(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.findings == []
