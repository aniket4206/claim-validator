"""Tests for ValidationPipeline AI phase integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import (
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.validators.ai.base import BaseAIValidator
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.pipeline import ValidationPipeline

# --- Helpers ---


class MockLLMClient(BaseLLMClient):
    """Mock LLM client."""

    provider_name = "mock"

    def send_messages(self, messages: list[Message]) -> str:
        return "mock response"


class PassingRuleValidator(BaseValidator):
    """Rule validator that produces no findings."""

    name = "passing_rule"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([])


class WarningRuleValidator(BaseValidator):
    """Rule validator that produces a WARNING finding."""

    name = "warning_rule"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="RULE_WARNING",
                message="Minor rule issue",
                severity=Severity.WARNING,
                field_name="some_field",
            ),
        ])


class FailingRuleValidator(BaseValidator):
    """Rule validator that produces an ERROR finding."""

    name = "failing_rule"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="RULE_ERROR",
                message="Critical rule failure",
                severity=Severity.ERROR,
                field_name="npi",
            ),
        ])


class PassingAIValidator(BaseAIValidator):
    """AI validator that produces a WARNING finding."""

    name = "passing_ai"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="AI_CLINICAL_FINDING",
                message="AI detected a clinical concern",
                severity=Severity.WARNING,
                field_name="procedure_code",
            ),
        ])


class CleanAIValidator(BaseAIValidator):
    """AI validator that produces no findings."""

    name = "clean_ai"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        return self._make_output([])


class LLMErrorAIValidator(BaseAIValidator):
    """AI validator that raises LLMError."""

    name = "llm_error_ai"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        raise LLMError("Provider unreachable")


class CrashingAIValidator(BaseAIValidator):
    """AI validator that raises a generic exception."""

    name = "crashing_ai"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        raise RuntimeError("Unexpected crash")


class ClaimCapturingAIValidator(BaseAIValidator):
    """AI validator that records what claim it receives."""

    name = "capturing_ai"

    def __init__(self, llm_client: BaseLLMClient) -> None:
        super().__init__(llm_client=llm_client)
        self.received_claims: list[DeidentifiedClaim] = []

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        self.received_claims.append(claim)
        return self._make_output([])


def _make_claim() -> ClaimData:
    """Create a minimal valid claim for testing."""
    return ClaimData(
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


def _mock_client() -> MockLLMClient:
    return MockLLMClient(model="mock", api_key="sk-mock")


# --- Tests ---


class TestTwoPhaseExecution:
    """Test pipeline runs both phases and aggregates results."""

    def test_both_phases_in_result(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[PassingAIValidator(llm_client=client)],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        assert isinstance(result, PipelineResult)
        assert len(result.phase_results) == 2
        assert result.phase_results[0].phase == "rule_based"
        assert result.phase_results[1].phase == "ai"

    def test_findings_from_both_phases(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[WarningRuleValidator()],
            ai_validators=[PassingAIValidator(llm_client=client)],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        codes = [f.code for f in result.findings]
        assert "RULE_WARNING" in codes
        assert "AI_CLINICAL_FINDING" in codes

    def test_no_ai_validators_single_phase(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"


class TestSkipAIOnRuleFailure:
    """Test the skip_ai_on_rule_failure gate."""

    def test_skip_true_with_errors_skips_ai(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[FailingRuleValidator()],
            ai_validators=[PassingAIValidator(llm_client=client)],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"
        codes = [f.code for f in result.findings]
        assert "AI_CLINICAL_FINDING" not in codes

    def test_skip_true_with_warnings_runs_ai(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[WarningRuleValidator()],
            ai_validators=[PassingAIValidator(llm_client=client)],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        assert len(result.phase_results) == 2

    def test_skip_false_with_errors_still_runs_ai(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[FailingRuleValidator()],
            ai_validators=[PassingAIValidator(llm_client=client)],
            skip_ai_on_rule_failure=False,
        )
        result = pipeline.run(_make_claim())
        assert len(result.phase_results) == 2
        codes = [f.code for f in result.findings]
        assert "RULE_ERROR" in codes
        assert "AI_CLINICAL_FINDING" in codes


class TestGracefulLLMErrorHandling:
    """Test LLM errors produce AI_PROVIDER_ERROR warnings."""

    def test_llm_error_produces_warning_finding(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[
                LLMErrorAIValidator(llm_client=client),
            ],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(_make_claim())
        assert len(result.phase_results) == 2
        ai_findings = result.phase_results[1].findings
        assert len(ai_findings) == 1
        assert ai_findings[0].code == "AI_PROVIDER_ERROR"
        assert ai_findings[0].severity == Severity.WARNING

    def test_llm_error_no_exception_propagated(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[
                LLMErrorAIValidator(llm_client=client),
            ],
        )
        # Should not raise — graceful degradation
        result = pipeline.run(_make_claim())
        assert result.passed  # WARNING does not fail

    def test_llm_error_context_contains_error_message(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[
                LLMErrorAIValidator(llm_client=client),
            ],
        )
        result = pipeline.run(_make_claim())
        finding = result.phase_results[1].findings[0]
        assert finding.context is not None
        assert "Provider unreachable" in finding.context["error"]

    def test_llm_error_preserves_rule_results(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[WarningRuleValidator()],
            ai_validators=[
                LLMErrorAIValidator(llm_client=client),
            ],
        )
        result = pipeline.run(_make_claim())
        codes = [f.code for f in result.findings]
        assert "RULE_WARNING" in codes
        assert "AI_PROVIDER_ERROR" in codes

    def test_generic_exception_produces_error_finding(self) -> None:
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[
                CrashingAIValidator(llm_client=client),
            ],
        )
        result = pipeline.run(_make_claim())
        ai_findings = result.phase_results[1].findings
        assert len(ai_findings) == 1
        assert ai_findings[0].code == "VALIDATOR_ERROR"
        assert ai_findings[0].severity == Severity.ERROR


class TestDeidentificationIntegration:
    """Test de-identification happens once before AI validators."""

    @patch(
        "claim_validator.validators.pipeline.ClaimDeidentifier",
    )
    def test_deidentify_called_once(
        self, mock_deidentifier_cls: MagicMock,
    ) -> None:
        mock_deidentified = DeidentifiedClaim(
            billing_provider_npi="1234567893",
            patient_age=45,
        )
        mock_deidentifier_cls.deidentify.return_value = (
            mock_deidentified
        )
        client = _mock_client()
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[
                CleanAIValidator(llm_client=client),
                CleanAIValidator(llm_client=client),
            ],
        )
        pipeline.run(_make_claim())
        mock_deidentifier_cls.deidentify.assert_called_once()

    @patch(
        "claim_validator.validators.pipeline.ClaimDeidentifier",
    )
    def test_ai_validators_receive_deidentified_claim(
        self, mock_deidentifier_cls: MagicMock,
    ) -> None:
        mock_deidentified = DeidentifiedClaim(
            billing_provider_npi="1234567893",
            patient_age=99,
        )
        mock_deidentifier_cls.deidentify.return_value = (
            mock_deidentified
        )
        client = _mock_client()
        v1 = ClaimCapturingAIValidator(llm_client=client)
        v2 = ClaimCapturingAIValidator(llm_client=client)
        pipeline = ValidationPipeline(
            rule_validators=[PassingRuleValidator()],
            ai_validators=[v1, v2],
        )
        pipeline.run(_make_claim())
        assert len(v1.received_claims) == 1
        assert v1.received_claims[0] is mock_deidentified
        assert len(v2.received_claims) == 1
        assert v2.received_claims[0] is mock_deidentified

    def test_no_deidentify_when_ai_skipped(self) -> None:
        with patch(
            "claim_validator.validators.pipeline"
            ".ClaimDeidentifier",
        ) as mock_cls:
            client = _mock_client()
            pipeline = ValidationPipeline(
                rule_validators=[FailingRuleValidator()],
                ai_validators=[
                    CleanAIValidator(llm_client=client),
                ],
                skip_ai_on_rule_failure=True,
            )
            pipeline.run(_make_claim())
            mock_cls.deidentify.assert_not_called()

    def test_no_deidentify_when_no_ai_validators(self) -> None:
        with patch(
            "claim_validator.validators.pipeline"
            ".ClaimDeidentifier",
        ) as mock_cls:
            pipeline = ValidationPipeline(
                rule_validators=[PassingRuleValidator()],
                ai_validators=[],
            )
            pipeline.run(_make_claim())
            mock_cls.deidentify.assert_not_called()


class TestFromSettingsWithAIConfig:
    """Test pipeline construction from settings with ai_config."""

    @patch("claim_validator.llm.factory.get_llm_client")
    def test_creates_llm_client_from_ai_config(
        self, mock_factory: MagicMock,
    ) -> None:
        mock_client = _mock_client()
        mock_factory.return_value = mock_client
        settings = ClaimValidatorSettings(
            rule_validators=[],
            ai_validators=[
                "test_validators.test_pipeline_ai"
                ".CleanAIValidator",
            ],
            ai_config={
                "provider": "anthropic",
                "api_key": "sk-test",
                "model": "claude-sonnet-4-5-20241022",
            },
        )
        ValidationPipeline.from_settings(settings)
        mock_factory.assert_called_once_with(
            "anthropic",
            api_key="sk-test",
            model="claude-sonnet-4-5-20241022",
        )

    @patch("claim_validator.llm.factory.get_llm_client")
    def test_passes_extra_kwargs_to_factory(
        self, mock_factory: MagicMock,
    ) -> None:
        mock_client = _mock_client()
        mock_factory.return_value = mock_client
        settings = ClaimValidatorSettings(
            rule_validators=[],
            ai_validators=[
                "test_validators.test_pipeline_ai"
                ".CleanAIValidator",
            ],
            ai_config={
                "provider": "openai_compatible",
                "api_key": "sk-test",
                "model": "llama3",
                "base_url": "http://localhost:11434/v1",
            },
        )
        ValidationPipeline.from_settings(settings)
        mock_factory.assert_called_once_with(
            "openai_compatible",
            api_key="sk-test",
            model="llama3",
            base_url="http://localhost:11434/v1",
        )

    def test_no_ai_config_creates_empty_ai_validators(
        self,
    ) -> None:
        settings = ClaimValidatorSettings(
            rule_validators=[],
            ai_validators=[],
            ai_config=None,
        )
        pipeline = ValidationPipeline.from_settings(settings)
        assert pipeline._ai_validators == []

    def test_ai_config_without_ai_validators_no_client(
        self,
    ) -> None:
        settings = ClaimValidatorSettings(
            rule_validators=[],
            ai_validators=[],
            ai_config={
                "provider": "anthropic",
                "api_key": "sk-test",
                "model": "claude-sonnet-4-5-20241022",
            },
        )
        pipeline = ValidationPipeline.from_settings(settings)
        assert pipeline._ai_validators == []
