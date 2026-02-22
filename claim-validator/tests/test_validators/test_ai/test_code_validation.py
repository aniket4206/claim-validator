"""Tests for CodeValidationAI clinical plausibility validator."""

from __future__ import annotations

import json

from claim_validator.constants import Severity
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.code_validation import (
    CodeValidationAI,
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
            {"code": "J06.9", "pointer": 1},
        ],
        "lines": [
            DeidentifiedLineData(
                procedure_code="99213",
                diagnosis_pointers=[1],
                charge_amount=150.0,
            ),
        ],
    }
    defaults.update(overrides)
    return DeidentifiedClaim(**defaults)


# --- Tests ---


class TestCodeValidationAICleanClaim:
    """Test zero findings for valid clinical coding."""

    def test_valid_coding_returns_empty(self) -> None:
        client = MockLLMClient(
            response='{"findings": []}',
        )
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert isinstance(result, ValidatorOutput)
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert result.validator_name == "CodeValidationAI"


class TestCodeValidationAIImplausibleClaim:
    """Test implausible combination produces findings."""

    def test_implausible_produces_finding(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
                "reason": (
                    "Obstetric procedure for male patient"
                ),
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        claim = _make_claim(
            patient_gender="M",
            lines=[
                DeidentifiedLineData(
                    procedure_code="59400",
                    diagnosis_pointers=[1],
                    charge_amount=3500.0,
                ),
            ],
        )
        result = validator.validate_deidentified(claim)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "AI_CLINICAL_IMPLAUSIBILITY"
        assert f.severity == Severity.WARNING
        assert f.line_number == 1
        assert f.field_name == "procedure_code"

    def test_multiple_findings(self) -> None:
        response = json.dumps({
            "findings": [
                {
                    "line_number": 1,
                    "field_name": "procedure_code",
                    "reason": "Issue one",
                },
                {
                    "line_number": 2,
                    "field_name": "procedure_code",
                    "reason": "Issue two",
                },
            ],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        claim = _make_claim(
            lines=[
                DeidentifiedLineData(
                    procedure_code="59400",
                    diagnosis_pointers=[1],
                    charge_amount=3500.0,
                ),
                DeidentifiedLineData(
                    procedure_code="59510",
                    diagnosis_pointers=[1],
                    charge_amount=4000.0,
                ),
            ],
        )
        result = validator.validate_deidentified(claim)
        assert len(result.findings) == 2

    def test_severity_is_always_warning(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
                "reason": "Some issue",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        for f in result.findings:
            assert f.severity == Severity.WARNING


class TestCodeValidationAIPromptConstruction:
    """Test prompt includes correct de-identified fields."""

    def test_prompt_includes_age_gender(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(patient_age=72, patient_gender="F"),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "72" in user_msg
        assert "F" in user_msg

    def test_prompt_includes_diagnosis_codes(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                diagnosis_codes=[
                    {"code": "J06.9", "pointer": 1},
                    {"code": "M54.5", "pointer": 2},
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "J06.9" in user_msg
        assert "M54.5" in user_msg

    def test_prompt_includes_procedure_codes(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                lines=[
                    DeidentifiedLineData(
                        procedure_code="99213",
                        diagnosis_pointers=[1],
                        charge_amount=150.0,
                    ),
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "99213" in user_msg

    def test_prompt_includes_modifiers(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                lines=[
                    DeidentifiedLineData(
                        procedure_code="99213",
                        modifiers=["25"],
                        diagnosis_pointers=[1],
                        charge_amount=150.0,
                    ),
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "25" in user_msg

    def test_system_message_present(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(_make_claim())
        assert client.last_messages is not None
        assert client.last_messages[0].role == "system"

    def test_two_messages_sent(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(_make_claim())
        assert client.last_messages is not None
        assert len(client.last_messages) == 2
        assert client.last_messages[0].role == "system"
        assert client.last_messages[1].role == "user"


class TestCodeValidationAIResponseParsing:
    """Test hybrid JSON / regex parsing."""

    def test_json_response_parsed(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
                "reason": "Age mismatch for procedure",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        assert result.findings[0].message == (
            "Age mismatch for procedure"
        )

    def test_empty_json_findings_returns_empty(self) -> None:
        response = json.dumps({"findings": []})
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 0

    def test_malformed_json_falls_back_to_regex(
        self,
    ) -> None:
        response = (
            "Line 1: Obstetric procedure billed for"
            " male patient — implausible"
        )
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) >= 1
        assert (
            result.findings[0].code
            == "AI_CLINICAL_IMPLAUSIBILITY"
        )
        assert result.findings[0].line_number == 1

    def test_free_text_with_issue_keywords(self) -> None:
        response = (
            "The combination is implausible because the"
            " procedure does not match the diagnosis."
        )
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) >= 1
        assert (
            result.findings[0].code
            == "AI_CLINICAL_IMPLAUSIBILITY"
        )

    def test_clean_free_text_returns_empty(self) -> None:
        response = (
            "All diagnosis-procedure combinations appear"
            " clinically appropriate."
        )
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 0

    def test_json_missing_reason_uses_default(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        assert result.findings[0].message != ""


class TestCodeValidationAINoPHI:
    """Test no PHI in any findings."""

    def test_no_phi_in_system_prompt(self) -> None:
        assert hasattr(CodeValidationAI, "SYSTEM_PROMPT")
        prompt = CodeValidationAI.SYSTEM_PROMPT
        phi_terms = [
            "patient name",
            "social security",
            "date of birth",
            "address",
            "phone",
            "email",
        ]
        lower = prompt.lower()
        for term in phi_terms:
            assert term not in lower or "strip" in lower

    def test_no_phi_in_findings(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
                "reason": "Clinical concern detected",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        for f in result.findings:
            assert "John" not in f.message
            assert "1980" not in f.message
            assert "SSN" not in f.message.upper()
