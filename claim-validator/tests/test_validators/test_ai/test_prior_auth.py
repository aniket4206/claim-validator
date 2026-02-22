"""Tests for PriorAuthAI prior authorization validator."""

from __future__ import annotations

import json

from claim_validator.constants import Severity
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.prior_auth import (
    PriorAuthAI,
)

# --- Helpers ---


class MockLLMClient(BaseLLMClient):
    """Mock LLM client returning controlled responses."""

    provider_name = "mock"

    def __init__(
        self,
        *,
        model: str = "mock",
        api_key: str = "sk-mock",
        response: str = '{"findings": []}',
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._response = response
        self.last_messages: list[Message] | None = None

    def send_messages(
        self, messages: list[Message],
    ) -> str:
        self.last_messages = messages
        return self._response


def _make_claim(
    **overrides: object,
) -> DeidentifiedClaim:
    """Create a de-identified claim for testing."""
    defaults: dict = {
        "billing_provider_npi": "1234567893",
        "patient_age": 45,
        "patient_gender": "M",
        "payer_id": "BCBS01",
        "diagnosis_codes": [
            {"code": "M54.5", "pointer": 1},
        ],
        "lines": [
            DeidentifiedLineData(
                procedure_code="72148",
                diagnosis_pointers=[1],
                charge_amount=800.0,
            ),
        ],
    }
    defaults.update(overrides)
    return DeidentifiedClaim(**defaults)


# --- Tests ---


class TestPriorAuthAICleanClaim:
    """Test zero findings when no prior auth needed."""

    def test_no_auth_returns_empty(self) -> None:
        client = MockLLMClient(
            response='{"findings": []}',
        )
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert isinstance(result, ValidatorOutput)
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        client = MockLLMClient()
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert result.validator_name == "PriorAuthAI"


class TestPriorAuthAIPriorAuthLikely:
    """Test prior auth concerns produce findings."""

    def test_prior_auth_produces_finding(self) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "line_number": 1,
                "reason": (
                    "MRI typically requires prior"
                    " authorization"
                ),
            }],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "AI_PRIOR_AUTH_LIKELY"
        assert f.severity == Severity.WARNING
        assert f.field_name == "procedure_code"
        assert f.line_number == 1

    def test_severity_is_always_warning(self) -> None:
        response = json.dumps({
            "findings": [
                {
                    "field_name": "procedure_code",
                    "line_number": 1,
                    "reason": "Needs prior auth",
                },
                {
                    "field_name": "procedure_code",
                    "line_number": 2,
                    "reason": "Also needs prior auth",
                },
            ],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        claim = _make_claim(
            lines=[
                DeidentifiedLineData(
                    procedure_code="72148",
                    diagnosis_pointers=[1],
                    charge_amount=800.0,
                ),
                DeidentifiedLineData(
                    procedure_code="70553",
                    diagnosis_pointers=[1],
                    charge_amount=1200.0,
                ),
            ],
        )
        result = validator.validate_deidentified(claim)
        for f in result.findings:
            assert f.severity == Severity.WARNING

    def test_multiple_prior_auth_findings(self) -> None:
        response = json.dumps({
            "findings": [
                {
                    "field_name": "procedure_code",
                    "line_number": 1,
                    "reason": "Auth A",
                },
                {
                    "field_name": "procedure_code",
                    "line_number": 2,
                    "reason": "Auth B",
                },
            ],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        claim = _make_claim(
            lines=[
                DeidentifiedLineData(
                    procedure_code="72148",
                    diagnosis_pointers=[1],
                    charge_amount=800.0,
                ),
                DeidentifiedLineData(
                    procedure_code="70553",
                    diagnosis_pointers=[1],
                    charge_amount=1200.0,
                ),
            ],
        )
        result = validator.validate_deidentified(claim)
        assert len(result.findings) == 2

    def test_suggestion_recommends_checking_auth(
        self,
    ) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "line_number": 1,
                "reason": "MRI requires prior auth",
            }],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        suggestion = result.findings[0].suggestion.lower()
        assert (
            "prior auth" in suggestion
            or "authorization" in suggestion
        )


class TestPriorAuthAIPromptConstruction:
    """Test prompt includes relevant claim data."""

    def test_prompt_includes_procedure_codes(
        self,
    ) -> None:
        client = MockLLMClient()
        validator = PriorAuthAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                lines=[
                    DeidentifiedLineData(
                        procedure_code="72148",
                        diagnosis_pointers=[1],
                        charge_amount=800.0,
                    ),
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "72148" in user_msg

    def test_prompt_includes_charge_amount(
        self,
    ) -> None:
        client = MockLLMClient()
        validator = PriorAuthAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                lines=[
                    DeidentifiedLineData(
                        procedure_code="72148",
                        diagnosis_pointers=[1],
                        charge_amount=800.0,
                    ),
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "800.00" in user_msg

    def test_system_message_present(self) -> None:
        client = MockLLMClient()
        validator = PriorAuthAI(llm_client=client)
        validator.validate_deidentified(_make_claim())
        assert client.last_messages is not None
        assert client.last_messages[0].role == "system"


class TestPriorAuthAIResponseParsing:
    """Test hybrid JSON / regex parsing."""

    def test_json_parsed(self) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "line_number": 1,
                "reason": "Requires prior authorization",
            }],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1

    def test_malformed_json_falls_back(self) -> None:
        response = (
            "This MRI procedure likely requires"
            " prior authorization from the payer."
        )
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) >= 1
        assert (
            result.findings[0].code
            == "AI_PRIOR_AUTH_LIKELY"
        )

    def test_clean_free_text_returns_empty(self) -> None:
        response = (
            "No services in this claim typically"
            " require prior authorization."
        )
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 0


class TestPriorAuthAINoPHI:
    """Test no PHI in findings."""

    def test_no_phi_in_findings(self) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "line_number": 1,
                "reason": "Prior auth required",
            }],
        })
        client = MockLLMClient(response=response)
        validator = PriorAuthAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        for f in result.findings:
            assert "John" not in f.message
            assert "SSN" not in f.message.upper()
