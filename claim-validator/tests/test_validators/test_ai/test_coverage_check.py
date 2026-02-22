"""Tests for CoverageCheckAI medical necessity validator."""

from __future__ import annotations

import json

from claim_validator.constants import Severity
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.coverage_check import (
    CoverageCheckAI,
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
        "payer_name": "BCBS",
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


class TestCoverageCheckAICleanClaim:
    """Test zero findings when no coverage concerns."""

    def test_no_concerns_returns_empty(self) -> None:
        client = MockLLMClient(
            response='{"findings": []}',
        )
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert isinstance(result, ValidatorOutput)
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        client = MockLLMClient()
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert result.validator_name == "CoverageCheckAI"


class TestCoverageCheckAICoverageConcern:
    """Test coverage concerns produce findings."""

    def test_coverage_concern_produces_finding(
        self,
    ) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "reason": (
                    "Procedure may lack medical necessity"
                    " documentation for this diagnosis"
                ),
                "documentation": (
                    "Provide clinical notes supporting"
                    " medical necessity"
                ),
            }],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "AI_COVERAGE_CONCERN"
        assert f.severity == Severity.WARNING
        assert f.field_name == "procedure_code"

    def test_severity_is_always_warning(self) -> None:
        response = json.dumps({
            "findings": [
                {
                    "field_name": "procedure_code",
                    "reason": "Coverage concern 1",
                },
                {
                    "field_name": "diagnosis_codes",
                    "reason": "Coverage concern 2",
                },
            ],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        for f in result.findings:
            assert f.severity == Severity.WARNING

    def test_multiple_coverage_concerns(self) -> None:
        response = json.dumps({
            "findings": [
                {
                    "field_name": "procedure_code",
                    "reason": "Concern A",
                },
                {
                    "field_name": "diagnosis_codes",
                    "reason": "Concern B",
                },
            ],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 2

    def test_suggestion_includes_documentation(
        self,
    ) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "reason": "Medical necessity concern",
                "documentation": (
                    "Include operative report"
                ),
            }],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1
        assert "operative report" in (
            result.findings[0].suggestion.lower()
        )


class TestCoverageCheckAIPromptConstruction:
    """Test prompt includes payer context."""

    def test_prompt_includes_payer_info(self) -> None:
        client = MockLLMClient()
        validator = CoverageCheckAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                payer_id="UHC01",
                payer_name="UnitedHealthcare",
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "UHC01" in user_msg or (
            "UnitedHealthcare" in user_msg
        )

    def test_prompt_includes_diagnosis_codes(self) -> None:
        client = MockLLMClient()
        validator = CoverageCheckAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(
                diagnosis_codes=[
                    {"code": "M54.5", "pointer": 1},
                ],
            ),
        )
        assert client.last_messages is not None
        user_msg = client.last_messages[-1].content
        assert "M54.5" in user_msg

    def test_system_message_present(self) -> None:
        client = MockLLMClient()
        validator = CoverageCheckAI(llm_client=client)
        validator.validate_deidentified(_make_claim())
        assert client.last_messages is not None
        assert client.last_messages[0].role == "system"


class TestCoverageCheckAIResponseParsing:
    """Test hybrid JSON / regex parsing."""

    def test_json_parsed(self) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "reason": "Coverage risk detected",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 1

    def test_malformed_json_falls_back(self) -> None:
        response = (
            "This procedure has a coverage concern"
            " because the diagnosis does not support"
            " medical necessity."
        )
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) >= 1
        assert (
            result.findings[0].code
            == "AI_COVERAGE_CONCERN"
        )

    def test_clean_free_text_returns_empty(self) -> None:
        response = (
            "All services appear to be covered and"
            " medically necessary. No issues found."
        )
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) == 0


class TestCoverageCheckAINoPHI:
    """Test no PHI in findings."""

    def test_no_phi_in_findings(self) -> None:
        response = json.dumps({
            "findings": [{
                "field_name": "procedure_code",
                "reason": "Coverage concern",
            }],
        })
        client = MockLLMClient(response=response)
        validator = CoverageCheckAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        for f in result.findings:
            assert "John" not in f.message
            assert "SSN" not in f.message.upper()
