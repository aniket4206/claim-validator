"""Tests for BaseAIValidator ABC."""

from __future__ import annotations

import abc

import pytest

from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator

# --- Helpers ---


class MockLLMClient(BaseLLMClient):
    """Fake LLM client for testing."""

    provider_name = "mock"

    def __init__(
        self, *, model: str = "mock-model", api_key: str = "sk-mock",
        response: str = "mock response", **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._response = response
        self.last_messages: list[Message] | None = None

    def send_messages(self, messages: list[Message]) -> str:
        self.last_messages = messages
        return self._response


class FailingLLMClient(BaseLLMClient):
    """LLM client that always raises LLMError."""

    provider_name = "failing"

    def send_messages(self, messages: list[Message]) -> str:
        raise LLMError("Connection refused")


class ConcreteAIValidator(BaseAIValidator):
    """Concrete subclass for testing."""

    name = "test_ai_validator"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        response = self._send_to_llm([
            Message(role="system", content="You are a validator."),
            Message(role="user", content="Validate this claim."),
        ])
        if "issue" in response.lower():
            return self._make_output([
                self._make_finding(
                    code="AI_TEST_ISSUE",
                    message="Test AI issue found",
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                ),
            ])
        return self._make_output([])


def _make_deidentified_claim() -> DeidentifiedClaim:
    """Create a minimal DeidentifiedClaim for testing."""
    return DeidentifiedClaim(
        billing_provider_npi="1234567893",
        patient_age=45,
        patient_gender="M",
        payer_id="BCBS01",
        total_charge=150.0,
    )


# --- Tests ---


class TestBaseAIValidatorABC:
    """Test BaseAIValidator is a proper ABC."""

    def test_cannot_instantiate_directly(self) -> None:
        client = MockLLMClient()
        with pytest.raises(TypeError, match="abstract"):
            BaseAIValidator(llm_client=client)  # type: ignore[abstract]

    def test_is_abstract_class(self) -> None:
        assert abc.ABC in BaseAIValidator.__mro__

    def test_validate_deidentified_is_abstract(self) -> None:
        assert getattr(
            BaseAIValidator.validate_deidentified,
            "__isabstractmethod__",
            False,
        )

    def test_extends_base_validator(self) -> None:
        from claim_validator.validators.base import BaseValidator
        assert issubclass(BaseAIValidator, BaseValidator)


class TestBaseAIValidatorConstruction:
    """Test LLM client injection."""

    def test_llm_client_injection(self) -> None:
        client = MockLLMClient()
        validator = ConcreteAIValidator(llm_client=client)
        assert validator._llm_client is client

    def test_concrete_subclass_instantiates(self) -> None:
        client = MockLLMClient()
        validator = ConcreteAIValidator(llm_client=client)
        assert validator.name == "test_ai_validator"

    def test_name_attribute_required(self) -> None:
        """Subclass without name should fail when _make_output is used."""

        class NoNameValidator(BaseAIValidator):
            def validate_deidentified(
                self, claim: DeidentifiedClaim,
            ) -> ValidatorOutput:
                return self._make_output([])

        client = MockLLMClient()
        validator = NoNameValidator(llm_client=client)
        claim = _make_deidentified_claim()
        with pytest.raises(AttributeError):
            validator.validate_deidentified(claim)


class TestValidateRaisesNotImplemented:
    """Test that validate() raises NotImplementedError."""

    def test_validate_raises_not_implemented(self) -> None:
        from claim_validator.models.claim import ClaimData
        client = MockLLMClient()
        validator = ConcreteAIValidator(llm_client=client)
        claim = ClaimData(
            billing_provider_npi="1234567893",
            patient_first_name="Test",
            patient_last_name="Patient",
            patient_dob="1980-01-01",
            patient_gender="M",
            subscriber_id="SUB123",
            payer_id="BCBS01",
            payer_name="BCBS",
            total_charge=150.0,
            lines=[],
            diagnosis_codes=[],
        )
        with pytest.raises(NotImplementedError, match="validate_deidentified"):
            validator.validate(claim)


class TestSendToLLM:
    """Test _send_to_llm helper."""

    def test_delegates_to_llm_client(self) -> None:
        client = MockLLMClient(response="LLM says hello")
        validator = ConcreteAIValidator(llm_client=client)
        messages = [Message(role="user", content="Hello")]
        result = validator._send_to_llm(messages)
        assert result == "LLM says hello"
        assert client.last_messages == messages

    def test_propagates_llm_error(self) -> None:
        client = FailingLLMClient(model="m", api_key="k")
        validator = ConcreteAIValidator(llm_client=client)
        with pytest.raises(LLMError, match="Connection refused"):
            validator._send_to_llm([
                Message(role="user", content="test"),
            ])


class TestValidateDeidentified:
    """Test validate_deidentified with concrete subclass."""

    def setup_method(self) -> None:
        self.client = MockLLMClient(response="All checks passed")
        self.validator = ConcreteAIValidator(llm_client=self.client)
        self.claim = _make_deidentified_claim()

    def test_returns_validator_output(self) -> None:
        result = self.validator.validate_deidentified(self.claim)
        assert isinstance(result, ValidatorOutput)

    def test_no_findings_when_clean(self) -> None:
        result = self.validator.validate_deidentified(self.claim)
        assert result.validator_name == "test_ai_validator"
        assert len(result.findings) == 0

    def test_findings_when_issue_detected(self) -> None:
        self.client._response = "Found an issue with coding"
        result = self.validator.validate_deidentified(self.claim)
        assert len(result.findings) == 1
        assert result.findings[0].code == "AI_TEST_ISSUE"
        assert result.findings[0].severity == Severity.WARNING

    def test_sends_messages_to_llm(self) -> None:
        self.validator.validate_deidentified(self.claim)
        assert self.client.last_messages is not None
        assert len(self.client.last_messages) == 2
        assert self.client.last_messages[0].role == "system"

    def test_uses_make_output_helper(self) -> None:
        result = self.validator.validate_deidentified(self.claim)
        assert result.validator_name == "test_ai_validator"

    def test_uses_make_finding_helper(self) -> None:
        self.client._response = "Found an issue"
        result = self.validator.validate_deidentified(self.claim)
        finding = result.findings[0]
        assert finding.field_name == "procedure_code"
        assert finding.suggestion == ""
