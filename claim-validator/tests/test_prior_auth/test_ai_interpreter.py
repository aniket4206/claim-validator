"""Tests for PriorAuthInterpreterAI and pipeline AI phase integration."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import Mock

import pytest

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient
from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.deidentifier import PriorAuthDeidentifier
from claim_validator.prior_auth.models.deidentified import (
    DeidentifiedPriorAuthError,
    DeidentifiedPriorAuthResponse,
    DeidentifiedServiceLineDecision,
)
from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)
from claim_validator.prior_auth.models.response import (
    PriorAuthError,
    PriorAuthResponse,
    ServiceLineDecision,
)
from claim_validator.prior_auth.pipeline import PriorAuthPipeline
from claim_validator.prior_auth.validators.ai.interpreter import (
    PriorAuthInterpreterAI,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_llm_client():
    """Mock BaseLLMClient returning structured JSON with PA approval summary."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Prior authorization approved for knee replacement (CPT 27447).",
        "findings": [
            {
                "code": "AI_PA_APPROVAL_SUMMARY",
                "message": "Authorization approved for 3 units",
                "suggestion": "Schedule procedure within authorization window",
            },
        ],
    })
    return client


@pytest.fixture()
def mock_llm_denial_response():
    """Mock BaseLLMClient returning denial interpretation JSON."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Prior authorization denied. Medical necessity not established.",
        "findings": [
            {
                "code": "AI_PA_DENIAL_EXPLAINED",
                "message": "Denial due to insufficient clinical documentation",
                "suggestion": "File appeal with additional clinical notes and peer-to-peer review",
            },
        ],
    })
    return client


@pytest.fixture()
def mock_llm_pended_response():
    """Mock BaseLLMClient returning pended case JSON."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Prior authorization pended pending additional clinical information.",
        "findings": [
            {
                "code": "AI_PA_PENDED_NEXT_STEPS",
                "message": "Payer requires additional clinical documentation",
                "suggestion": "Submit operative notes and imaging results within 10 business days",
            },
        ],
    })
    return client


@pytest.fixture()
def mock_llm_empty_findings():
    """Mock BaseLLMClient returning summary only, no findings."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Standard authorization approved.",
        "findings": [],
    })
    return client


@pytest.fixture()
def mock_llm_free_text():
    """Mock BaseLLMClient returning non-JSON response with denial keywords."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = (
        "The authorization was denied due to medical necessity. "
        "Consider filing an appeal with additional documentation."
    )
    return client


@pytest.fixture()
def mock_llm_failing():
    """Mock BaseLLMClient that raises LLMError."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.side_effect = LLMError("API key invalid")
    return client


@pytest.fixture()
def deidentified_approved_response():
    """De-identified response: A1 action code, service lines, no errors."""
    return DeidentifiedPriorAuthResponse(
        action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
        decision_reason_code="01",
        effective_year=2024,
        expiration_year=2025,
        service_line_decisions=[
            DeidentifiedServiceLineDecision(
                cpt_code="27447",
                action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
                approved_quantity=3,
            ),
        ],
        errors=[],
    )


@pytest.fixture()
def deidentified_denied_response():
    """De-identified response: A3 action code with error codes."""
    return DeidentifiedPriorAuthResponse(
        action_code=CertificationActionCode.NOT_CERTIFIED,
        decision_reason_code="05",
        service_line_decisions=[],
        errors=[
            DeidentifiedPriorAuthError(
                rejection_code="72",
                follow_up_code="C",
            ),
        ],
    )


@pytest.fixture()
def deidentified_pended_response():
    """De-identified response: A4 action code."""
    return DeidentifiedPriorAuthResponse(
        action_code=CertificationActionCode.PENDED,
        decision_reason_code="15",
        service_line_decisions=[],
        errors=[],
    )


@pytest.fixture()
def full_phi_pa_response():
    """Full PHI PA response for de-identification gate testing."""
    return PriorAuthResponse(
        action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
        authorization_number="AUTH-2024-JD-98765",
        effective_date=date(2024, 3, 15),
        expiration_date=date(2025, 3, 15),
        decision_reason_code="01",
        decision_reason_description="Approved for patient John Smith MEM001",
        service_line_decisions=[
            ServiceLineDecision(
                cpt_code="27447",
                action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
                authorization_number="AUTH-SL-001",
                approved_quantity=3,
                denied_reason=None,
            ),
        ],
        errors=[
            PriorAuthError(
                rejection_code="72",
                follow_up_code="C",
                message="Subscriber John Smith (ID: MEM001) requires review",
                suggested_fix="Contact plan for member MEM001",
            ),
        ],
        raw_response={"subscriber": {"firstName": "John", "memberId": "MEM001"}},
    )


@pytest.fixture()
def valid_pa_request():
    """Valid PriorAuthRequest for pipeline tests."""
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=["M17.11"],
        service_lines=[
            ServiceLine(
                cpt_code="27447",
                quantity=1,
                from_date=date(2026, 4, 1),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# TestInterpreterDirect — approved case interpretation
# ---------------------------------------------------------------------------


class TestInterpreterDirect:
    """Test PriorAuthInterpreterAI.interpret() directly."""

    def test_approved_case_summary(
        self, mock_llm_client, deidentified_approved_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        summary, findings = interpreter.interpret(deidentified_approved_response)

        assert summary
        assert isinstance(summary, str)
        assert len(summary) > 10

    def test_findings_have_ai_pa_prefix(
        self, mock_llm_client, deidentified_approved_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_approved_response)

        assert len(findings) >= 1
        for f in findings:
            assert f.code.startswith("AI_PA_")

    def test_empty_response_interpretation(self, mock_llm_empty_findings):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_empty_findings)
        empty_response = DeidentifiedPriorAuthResponse()
        summary, findings = interpreter.interpret(empty_response)

        assert summary
        assert findings == []

    def test_llm_receives_messages(
        self, mock_llm_client, deidentified_approved_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        interpreter.interpret(deidentified_approved_response)

        mock_llm_client.send_messages.assert_called_once()
        messages = mock_llm_client.send_messages.call_args[0][0]
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[1].role == "user"


# ---------------------------------------------------------------------------
# TestInterpreterDenial — denial interpretation + appeal suggestions
# ---------------------------------------------------------------------------


class TestInterpreterDenial:
    """Test interpretation of denial responses."""

    def test_denial_summary(
        self, mock_llm_denial_response, deidentified_denied_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_denial_response)
        summary, findings = interpreter.interpret(deidentified_denied_response)

        assert "denied" in summary.lower()
        assert any(f.code == "AI_PA_DENIAL_EXPLAINED" for f in findings)

    def test_denial_has_appeal_suggestion(
        self, mock_llm_denial_response, deidentified_denied_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_denial_response)
        _, findings = interpreter.interpret(deidentified_denied_response)

        denial_findings = [f for f in findings if f.code == "AI_PA_DENIAL_EXPLAINED"]
        assert len(denial_findings) == 1
        assert "appeal" in denial_findings[0].suggestion.lower()


# ---------------------------------------------------------------------------
# TestInterpreterPended — pended case next-step recommendations
# ---------------------------------------------------------------------------


class TestInterpreterPended:
    """Test interpretation of pended responses."""

    def test_pended_summary(
        self, mock_llm_pended_response, deidentified_pended_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_pended_response)
        summary, findings = interpreter.interpret(deidentified_pended_response)

        assert "pended" in summary.lower()
        assert any(f.code == "AI_PA_PENDED_NEXT_STEPS" for f in findings)

    def test_pended_has_actionable_suggestion(
        self, mock_llm_pended_response, deidentified_pended_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_pended_response)
        _, findings = interpreter.interpret(deidentified_pended_response)

        pended_findings = [f for f in findings if f.code == "AI_PA_PENDED_NEXT_STEPS"]
        assert len(pended_findings) == 1
        assert pended_findings[0].suggestion


# ---------------------------------------------------------------------------
# TestPipelineAIPhase — full pipeline populates ai_summary, merges findings
# ---------------------------------------------------------------------------


class TestPipelineAIPhase:
    """Test PriorAuthPipeline with AI phase enabled."""

    def test_full_pipeline_with_ai(
        self, mock_llm_client, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        assert result.ai_summary is not None
        assert len(result.ai_summary) > 0

    def test_full_pipeline_approved_from_response(
        self, mock_llm_client, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        assert result.approved is True
        assert result.response is full_phi_pa_response

    def test_full_pipeline_ai_findings_merged(
        self, mock_llm_client, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        ai_findings = [f for f in result.findings if f.code.startswith("AI_PA_")]
        assert len(ai_findings) >= 1


# ---------------------------------------------------------------------------
# TestSkipAI — no ai_config / pa_skip_ai=True / no response → skip
# ---------------------------------------------------------------------------


class TestSkipAI:
    """Test AI phase skipping behavior."""

    def test_no_ai_config_no_summary(self, valid_pa_request):
        pipeline = PriorAuthPipeline(rule_validators=[])
        result = pipeline.run(valid_pa_request)

        assert result.ai_summary is None

    def test_no_response_no_ai(self, mock_llm_client, valid_pa_request):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request)

        assert result.ai_summary is None
        mock_llm_client.send_messages.assert_not_called()

    def test_skip_ai_true_no_ai(self, valid_pa_request, full_phi_pa_response):
        settings = ClaimValidatorSettings(
            pa_rule_validators=[],
            pa_skip_ai=True,
        )
        pipeline = PriorAuthPipeline.from_settings(settings)
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        assert result.ai_summary is None


# ---------------------------------------------------------------------------
# TestGracefulDegradation — LLMError → AI_PA_PROVIDER_ERROR WARNING
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Test graceful degradation on LLM failures."""

    def test_llm_error_produces_warning(
        self, mock_llm_failing, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_failing)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        error_findings = [
            f for f in result.findings if f.code == "AI_PA_PROVIDER_ERROR"
        ]
        assert len(error_findings) == 1
        assert error_findings[0].severity == Severity.WARNING

    def test_llm_error_no_exception_propagated(
        self, mock_llm_failing, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_failing)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)
        assert result.ai_summary is None

    def test_llm_error_context_has_error_detail(
        self, mock_llm_failing, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_failing)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        error_f = next(
            f for f in result.findings if f.code == "AI_PA_PROVIDER_ERROR"
        )
        assert "error" in error_f.context
        assert "API key invalid" in error_f.context["error"]


# ---------------------------------------------------------------------------
# TestDeidentificationGate — no PHI in user messages sent to LLM
# ---------------------------------------------------------------------------


class TestDeidentificationGate:
    """Test that only de-identified data reaches the LLM."""

    def test_deidentified_data_sent_to_llm(
        self, mock_llm_client, valid_pa_request, full_phi_pa_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        pipeline.run(valid_pa_request, response=full_phi_pa_response)

        messages = mock_llm_client.send_messages.call_args[0][0]
        user_msg = messages[1].content
        # PHI values that must NOT appear
        assert "John" not in user_msg
        assert "Smith" not in user_msg
        assert "MEM001" not in user_msg
        assert "AUTH-2024" not in user_msg
        assert "AUTH-SL" not in user_msg
        assert "2024-03-15" not in user_msg

    def test_deidentification_runs_before_llm(
        self, mock_llm_client, valid_pa_request, full_phi_pa_response,
    ):
        deidentified = PriorAuthDeidentifier.deidentify(full_phi_pa_response)
        assert deidentified.is_deidentified is True

        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        pipeline.run(valid_pa_request, response=full_phi_pa_response)

        mock_llm_client.send_messages.assert_called_once()


# ---------------------------------------------------------------------------
# TestProviderAgnostic — different providers produce identical behavior
# ---------------------------------------------------------------------------


class TestProviderAgnostic:
    """Test that AI works identically across providers."""

    def test_different_mock_providers_same_behavior(
        self, deidentified_approved_response,
    ):
        response_json = json.dumps({
            "summary": "Authorization approved.",
            "findings": [],
        })

        for provider_name in ("anthropic", "openai", "openai_compatible"):
            client = Mock(spec=BaseLLMClient)
            client.send_messages.return_value = response_json
            client.provider_name = provider_name

            interpreter = PriorAuthInterpreterAI(llm_client=client)
            summary, findings = interpreter.interpret(
                deidentified_approved_response,
            )
            assert summary == "Authorization approved."
            assert findings == []


# ---------------------------------------------------------------------------
# TestFindingConventions — AI_PA_ prefix, WARNING severity, invalid code sanitization
# ---------------------------------------------------------------------------


class TestFindingConventions:
    """Test finding code and severity conventions."""

    def test_all_findings_ai_pa_prefix(
        self, mock_llm_client, deidentified_approved_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_approved_response)

        for f in findings:
            assert f.code.startswith("AI_PA_"), f"Finding {f.code} missing prefix"

    def test_all_findings_warning_severity(
        self, mock_llm_client, deidentified_approved_response,
    ):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_client)
        _, findings = interpreter.interpret(deidentified_approved_response)

        for f in findings:
            assert f.severity == Severity.WARNING

    def test_invalid_code_sanitized(self):
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = json.dumps({
            "summary": "Test",
            "findings": [
                {"code": "INVALID_CODE", "message": "Test", "suggestion": ""},
            ],
        })
        interpreter = PriorAuthInterpreterAI(llm_client=client)
        _, findings = interpreter.interpret(DeidentifiedPriorAuthResponse())

        assert len(findings) == 1
        assert findings[0].code == "AI_PA_GENERAL_NOTE"


# ---------------------------------------------------------------------------
# TestNoPHILeakage — no PHI in output summary/findings
# ---------------------------------------------------------------------------


class TestNoPHILeakage:
    """Test that no PHI appears in AI output."""

    def test_no_phi_in_summary_or_findings(
        self, valid_pa_request, full_phi_pa_response,
    ):
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = json.dumps({
            "summary": "Authorization approved for knee replacement.",
            "findings": [
                {
                    "code": "AI_PA_APPROVAL_SUMMARY",
                    "message": "Standard approval with 3 units",
                    "suggestion": "No action needed",
                },
            ],
        })
        interpreter = PriorAuthInterpreterAI(llm_client=client)
        pipeline = PriorAuthPipeline(
            rule_validators=[],
            ai_interpreter=interpreter,
        )
        result = pipeline.run(valid_pa_request, response=full_phi_pa_response)

        phi_values = [
            "John", "Smith", "MEM001", "AUTH-2024", "AUTH-SL",
            "1985-03-15", "subscriber_id",
        ]
        combined_text = str(result.ai_summary or "")
        for f in result.findings:
            combined_text += f" {f.message} {f.suggestion}"

        for phi in phi_values:
            assert phi not in combined_text


# ---------------------------------------------------------------------------
# TestFreeTextFallback — non-JSON handling with keyword detection
# ---------------------------------------------------------------------------


class TestFreeTextFallback:
    """Test free-text LLM response parsing fallback."""

    def test_free_text_with_denial_keyword(self, mock_llm_free_text):
        interpreter = PriorAuthInterpreterAI(llm_client=mock_llm_free_text)
        summary, findings = interpreter.interpret(
            DeidentifiedPriorAuthResponse(),
        )

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert any(f.code == "AI_PA_CLINICAL_CONCERN" for f in findings)

    def test_free_text_without_concern_keyword(self):
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = "Everything looks normal."
        interpreter = PriorAuthInterpreterAI(llm_client=client)
        summary, findings = interpreter.interpret(
            DeidentifiedPriorAuthResponse(),
        )

        assert summary == "Everything looks normal."
        assert findings == []

    def test_long_free_text_truncated(self):
        client = Mock(spec=BaseLLMClient)
        client.send_messages.return_value = "A" * 600
        interpreter = PriorAuthInterpreterAI(llm_client=client)
        summary, _ = interpreter.interpret(DeidentifiedPriorAuthResponse())

        assert len(summary) == 500


# ---------------------------------------------------------------------------
# TestImports — importable from prior_auth, validators.ai, top-level
# ---------------------------------------------------------------------------


class TestImports:
    """Test that AI interpreter is importable from expected locations."""

    def test_import_from_prior_auth_module(self):
        from claim_validator.prior_auth import PriorAuthInterpreterAI

        assert PriorAuthInterpreterAI is not None

    def test_import_from_validators_ai(self):
        from claim_validator.prior_auth.validators.ai import (
            PriorAuthInterpreterAI,
        )

        assert PriorAuthInterpreterAI is not None

    def test_import_from_interpreter_module(self):
        from claim_validator.prior_auth.validators.ai.interpreter import (
            PriorAuthInterpreterAI,
        )

        assert PriorAuthInterpreterAI is not None

    def test_import_from_top_level(self):
        from claim_validator import PriorAuthInterpreterAI

        assert PriorAuthInterpreterAI is not None
