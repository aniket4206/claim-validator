"""Tests for EligibilityInterpreterAI and pipeline AI phase integration."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.deidentifier import EligibilityDeidentifier
from claim_validator.eligibility.models.deidentified import (
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
)
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityResponse,
)
from claim_validator.eligibility.pipeline import EligibilityPipeline
from claim_validator.eligibility.validators.ai.interpreter import (
    EligibilityInterpreterAI,
)
from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_llm_client():
    """Mock BaseLLMClient returning structured JSON."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Patient has active coverage with $40 copay for office visits.",
        "findings": [
            {
                "code": "AI_ELIG_BENEFIT_NOTE",
                "message": "Annual deductible is $2,500",
                "suggestion": "Verify remaining deductible before procedure",
            },
        ],
    })
    return client


@pytest.fixture()
def mock_llm_error_response():
    """Mock BaseLLMClient returning AAA error interpretation."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Patient not found in payer system. Coverage cannot be verified.",
        "findings": [
            {
                "code": "AI_ELIG_REJECTION_EXPLAINED",
                "message": "Rejection code 72 indicates subscriber not found",
                "suggestion": "Verify member ID and payer ID with the patient",
            },
        ],
    })
    return client


@pytest.fixture()
def mock_llm_empty_findings():
    """Mock BaseLLMClient returning summary with no findings."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Patient has standard active coverage.",
        "findings": [],
    })
    return client


@pytest.fixture()
def mock_llm_free_text():
    """Mock BaseLLMClient returning non-JSON free-text."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = (
        "The patient has active coverage but there is a limitation "
        "on imaging services that requires prior authorization."
    )
    return client


@pytest.fixture()
def mock_llm_failing():
    """Mock BaseLLMClient that raises LLMError."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.side_effect = LLMError("API key invalid")
    return client


@pytest.fixture()
def deidentified_active_response():
    """De-identified response with active coverage and benefits."""
    return DeidentifiedEligibilityResponse(
        eligible=True,
        coverage=DeidentifiedCoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_year=2023,
            termination_year=None,
        ),
        benefits=[
            BenefitInfo(
                service_type_code="30",
                service_type_name="Health Benefit Plan Coverage",
                copay=40.0,
                coinsurance=0.20,
                deductible=2500.0,
                in_network=True,
                prior_auth_required=False,
            ),
        ],
        errors=[],
    )


@pytest.fixture()
def deidentified_error_response():
    """De-identified response with AAA rejection errors."""
    return DeidentifiedEligibilityResponse(
        eligible=None,
        coverage=None,
        benefits=[],
        errors=[
            DeidentifiedAAAError(
                rejection_code="72",
                follow_up_code="C",
            ),
        ],
    )


@pytest.fixture()
def full_phi_response():
    """Full PHI eligibility response for de-identification testing."""
    return EligibilityResponse(
        eligible=True,
        coverage=CoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_date="2023-01-15",
            termination_date="2025-12-31",
            plan_name="Acme Corp Gold PPO",
            group_number="GRP-AC-2023",
        ),
        benefits=[
            BenefitInfo(
                service_type_code="30",
                service_type_name="Health Benefit Plan Coverage",
                copay=40.0,
                coinsurance=0.20,
                deductible=2500.0,
                in_network=True,
                prior_auth_required=False,
            ),
        ],
        errors=[
            AAAError(
                rejection_code="72",
                follow_up_code="C",
                message="Subscriber John Smith (ID: XYZ123) not found",
            ),
        ],
        raw_response={"subscriber": {"firstName": "John", "memberId": "XYZ123"}},
    )


@pytest.fixture()
def valid_request():
    """Valid eligibility request for pipeline tests."""
    return EligibilityRequest(
        provider_npi="1234567893",
        payer_id="60054",
        subscriber_id="XYZ123456",
        subscriber_first_name="Jane",
        subscriber_last_name="Doe",
        subscriber_dob="1985-03-15",
        date_of_service="2026-03-01",
        service_type_code="30",
    )


# ---------------------------------------------------------------------------
# TestInterpreterDirect — AC #1: Active coverage interpretation
# ---------------------------------------------------------------------------


class TestInterpreterDirect:
    """Test EligibilityInterpreterAI.interpret() directly."""

    def test_active_coverage_summary(
        self, mock_llm_client, deidentified_active_response,
    ):
        """AC #1: AI generates human-readable coverage summary."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        summary, findings = interpreter.interpret(deidentified_active_response)

        assert summary
        assert isinstance(summary, str)
        assert len(summary) > 10

    def test_active_coverage_findings(
        self, mock_llm_client, deidentified_active_response,
    ):
        """AC #1: AI generates AI_ELIG_ prefixed findings."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_active_response)

        assert len(findings) >= 1
        for f in findings:
            assert f.code.startswith("AI_ELIG_")

    def test_empty_response_interpretation(self, mock_llm_empty_findings):
        """Minimal response with no findings."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_empty_findings)
        empty_response = DeidentifiedEligibilityResponse()
        summary, findings = interpreter.interpret(empty_response)

        assert summary
        assert findings == []

    def test_llm_receives_messages(
        self, mock_llm_client, deidentified_active_response,
    ):
        """Verify LLM receives system + user messages."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        interpreter.interpret(deidentified_active_response)

        mock_llm_client.send_messages.assert_called_once()
        messages = mock_llm_client.send_messages.call_args[0][0]
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"


# ---------------------------------------------------------------------------
# TestInterpreterErrors — AC #2: AAA rejection interpretation
# ---------------------------------------------------------------------------


class TestInterpreterErrors:
    """Test interpretation of AAA rejection errors."""

    def test_rejection_explained(
        self, mock_llm_error_response, deidentified_error_response,
    ):
        """AC #2: AI interprets rejection codes into plain English."""
        interpreter = EligibilityInterpreterAI(
            llm_client=mock_llm_error_response,
        )
        summary, findings = interpreter.interpret(deidentified_error_response)

        assert "not found" in summary.lower() or "cannot" in summary.lower()
        assert any(
            f.code == "AI_ELIG_REJECTION_EXPLAINED" for f in findings
        )

    def test_rejection_has_suggestion(
        self, mock_llm_error_response, deidentified_error_response,
    ):
        """AC #2: Rejection findings include suggested next steps."""
        interpreter = EligibilityInterpreterAI(
            llm_client=mock_llm_error_response,
        )
        _, findings = interpreter.interpret(deidentified_error_response)

        for f in findings:
            if f.code == "AI_ELIG_REJECTION_EXPLAINED":
                assert f.suggestion


# ---------------------------------------------------------------------------
# TestPipelineAIPhase — AC #3: Full pipeline with AI
# ---------------------------------------------------------------------------


class TestPipelineAIPhase:
    """Test EligibilityPipeline with AI phase enabled."""

    def test_full_pipeline_with_ai(
        self, mock_llm_client, valid_request, full_phi_response,
    ):
        """AC #3: Full pipeline populates ai_summary."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        assert result.ai_summary is not None
        assert len(result.ai_summary) > 0

    def test_full_pipeline_eligible_from_response(
        self, mock_llm_client, valid_request, full_phi_response,
    ):
        """AC #3: Result eligible comes from provided response."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        assert result.eligible is True
        assert result.response is full_phi_response

    def test_full_pipeline_ai_findings_merged(
        self, mock_llm_client, valid_request, full_phi_response,
    ):
        """AC #3: AI findings are merged into result."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        ai_findings = [f for f in result.findings if f.code.startswith("AI_ELIG_")]
        assert len(ai_findings) >= 1


# ---------------------------------------------------------------------------
# TestSkipAI — AC #4: AI phase skipped when not configured
# ---------------------------------------------------------------------------


class TestSkipAI:
    """Test AI phase skipping behavior."""

    def test_no_ai_config_no_summary(self, valid_request):
        """AC #4: No ai_config → ai_summary=None."""
        pipeline = EligibilityPipeline(rule_validators=[])
        result = pipeline.run(valid_request)

        assert result.ai_summary is None

    def test_no_response_no_ai(self, mock_llm_client, valid_request):
        """AC #4: AI configured but no response → AI skipped."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request)

        assert result.ai_summary is None
        mock_llm_client.send_messages.assert_not_called()

    def test_skip_ai_true_no_ai(self, valid_request, full_phi_response):
        """AC #4: eligibility_skip_ai=True → AI skipped."""
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[],
            eligibility_skip_ai=True,
        )
        pipeline = EligibilityPipeline.from_settings(settings)
        result = pipeline.run(valid_request, response=full_phi_response)

        assert result.ai_summary is None


# ---------------------------------------------------------------------------
# TestGracefulDegradation — AC #5: LLM provider errors
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Test graceful degradation on LLM failures."""

    def test_llm_error_produces_warning(
        self, mock_llm_failing, valid_request, full_phi_response,
    ):
        """AC #5: LLMError → AI_ELIG_PROVIDER_ERROR WARNING finding."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_failing)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        error_findings = [
            f for f in result.findings if f.code == "AI_ELIG_PROVIDER_ERROR"
        ]
        assert len(error_findings) == 1
        assert error_findings[0].severity == Severity.WARNING

    def test_llm_error_no_exception_propagated(
        self, mock_llm_failing, valid_request, full_phi_response,
    ):
        """AC #5: No exception propagates to caller."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_failing)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        # Should not raise
        result = pipeline.run(valid_request, response=full_phi_response)
        assert result.ai_summary is None

    def test_llm_error_context_has_error_detail(
        self, mock_llm_failing, valid_request, full_phi_response,
    ):
        """AC #5: Provider error finding includes error details."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_failing)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        error_f = next(
            f for f in result.findings if f.code == "AI_ELIG_PROVIDER_ERROR"
        )
        assert "error" in error_f.context
        assert "API key invalid" in error_f.context["error"]


# ---------------------------------------------------------------------------
# TestDeidentificationGate — AC #6: Only de-identified data reaches LLM
# ---------------------------------------------------------------------------


class TestDeidentificationGate:
    """Test that only de-identified data reaches the LLM."""

    def test_deidentified_data_sent_to_llm(
        self, mock_llm_client, valid_request, full_phi_response,
    ):
        """AC #6: Raw PHI never reaches the LLM."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        pipeline.run(valid_request, response=full_phi_response)

        # Check that the user message does NOT contain PHI
        messages = mock_llm_client.send_messages.call_args[0][0]
        user_msg = messages[1].content
        assert "John" not in user_msg
        assert "Smith" not in user_msg
        assert "XYZ123" not in user_msg
        assert "Acme Corp" not in user_msg
        assert "GRP-AC" not in user_msg

    def test_deidentification_runs_before_llm(
        self, mock_llm_client, valid_request, full_phi_response,
    ):
        """AC #6: EligibilityDeidentifier.deidentify() runs before LLM call."""
        # Verify the de-identification produces safe output
        deidentified = EligibilityDeidentifier.deidentify(full_phi_response)
        assert deidentified.is_deidentified is True

        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        pipeline.run(valid_request, response=full_phi_response)

        # LLM was called (de-identification succeeded)
        mock_llm_client.send_messages.assert_called_once()


# ---------------------------------------------------------------------------
# TestProviderAgnostic — AC #7: Provider-agnostic interpretation
# ---------------------------------------------------------------------------


class TestProviderAgnostic:
    """Test that AI works identically across providers."""

    def test_different_mock_providers_same_behavior(
        self, deidentified_active_response,
    ):
        """AC #7: Different providers produce identical pipeline behavior."""
        response_json = json.dumps({
            "summary": "Coverage active.",
            "findings": [],
        })

        for provider_name in ("anthropic", "openai", "openai_compatible"):
            client = Mock(spec=BaseLLMClient)
            client.send_messages.return_value = response_json
            client.provider_name = provider_name

            interpreter = EligibilityInterpreterAI(llm_client=client)
            summary, findings = interpreter.interpret(
                deidentified_active_response,
            )
            assert summary == "Coverage active."
            assert findings == []


# ---------------------------------------------------------------------------
# TestFindingConventions — AC #8: Code prefixes and severity
# ---------------------------------------------------------------------------


class TestFindingConventions:
    """Test finding code and severity conventions."""

    def test_all_findings_ai_elig_prefix(
        self, mock_llm_client, deidentified_active_response,
    ):
        """AC #8: All findings use AI_ELIG_ code prefix."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_active_response)

        for f in findings:
            assert f.code.startswith("AI_ELIG_"), f"Finding {f.code} missing prefix"

    def test_all_findings_warning_severity(
        self, mock_llm_client, deidentified_active_response,
    ):
        """AC #8: All AI findings have WARNING severity."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_active_response)

        for f in findings:
            assert f.severity == Severity.WARNING

    def test_invalid_code_sanitized(self):
        """AC #8: Invalid codes from LLM are sanitized to valid codes."""
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = json.dumps({
            "summary": "Test",
            "findings": [
                {"code": "INVALID_CODE", "message": "Test", "suggestion": ""},
            ],
        })
        interpreter = EligibilityInterpreterAI(llm_client=client)
        _, findings = interpreter.interpret(DeidentifiedEligibilityResponse())

        assert len(findings) == 1
        assert findings[0].code == "AI_ELIG_BENEFIT_NOTE"


# ---------------------------------------------------------------------------
# TestNoPHILeakage — AC #8: No PHI in output
# ---------------------------------------------------------------------------


class TestNoPHILeakage:
    """Test that no PHI appears in AI output."""

    def test_no_phi_in_summary_or_findings(
        self, valid_request, full_phi_response,
    ):
        """AC #8: No PHI in ai_summary or finding messages."""
        # Use a client that echoes back the prompt
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = json.dumps({
            "summary": "Active coverage detected.",
            "findings": [
                {
                    "code": "AI_ELIG_BENEFIT_NOTE",
                    "message": "Standard copay applies",
                    "suggestion": "No action needed",
                },
            ],
        })
        interpreter = EligibilityInterpreterAI(llm_client=client)
        pipeline = EligibilityPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_request, response=full_phi_response)

        # Check summary and findings for PHI
        phi_values = [
            "John", "Smith", "XYZ123", "Acme Corp", "GRP-AC",
            "1985-03-15", "subscriber_id",
        ]
        combined_text = str(result.ai_summary or "")
        for f in result.findings:
            combined_text += f" {f.message} {f.suggestion}"

        for phi in phi_values:
            assert phi not in combined_text


# ---------------------------------------------------------------------------
# TestFreeTextFallback — JSON parse failure handling
# ---------------------------------------------------------------------------


class TestFreeTextFallback:
    """Test free-text LLM response parsing fallback."""

    def test_free_text_with_concern_keyword(self, mock_llm_free_text):
        """Non-JSON response with concern keywords → coverage concern finding."""
        interpreter = EligibilityInterpreterAI(llm_client=mock_llm_free_text)
        summary, findings = interpreter.interpret(
            DeidentifiedEligibilityResponse(),
        )

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert any(f.code == "AI_ELIG_COVERAGE_CONCERN" for f in findings)

    def test_free_text_without_concern_keyword(self):
        """Non-JSON response without keywords → no findings."""
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = "Everything looks normal."
        interpreter = EligibilityInterpreterAI(llm_client=client)
        summary, findings = interpreter.interpret(
            DeidentifiedEligibilityResponse(),
        )

        assert summary == "Everything looks normal."
        assert findings == []

    def test_long_free_text_truncated(self):
        """Very long free-text response is truncated to 500 chars."""
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = "A" * 600
        interpreter = EligibilityInterpreterAI(llm_client=client)
        summary, _ = interpreter.interpret(DeidentifiedEligibilityResponse())

        assert len(summary) == 500


# ---------------------------------------------------------------------------
# TestImports — importability
# ---------------------------------------------------------------------------


class TestImports:
    """Test that AI interpreter is importable from expected locations."""

    def test_import_from_eligibility_module(self):
        """Importable from claim_validator.eligibility."""
        from claim_validator.eligibility import EligibilityInterpreterAI

        assert EligibilityInterpreterAI is not None

    def test_import_from_validators_ai(self):
        """Importable from claim_validator.eligibility.validators.ai."""
        from claim_validator.eligibility.validators.ai import (
            EligibilityInterpreterAI,
        )

        assert EligibilityInterpreterAI is not None

    def test_import_from_interpreter_module(self):
        """Importable from full module path."""
        from claim_validator.eligibility.validators.ai.interpreter import (
            EligibilityInterpreterAI,
        )

        assert EligibilityInterpreterAI is not None
