"""Tests for ValidationPipeline — two-phase execution orchestrator."""

from __future__ import annotations

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import (
    PhaseResult,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.pipeline import ValidationPipeline


def _valid_claim_dict() -> dict:
    """Minimal claim dict that passes all validators."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "payer_id": "BCBS001",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ],
    }


def _invalid_claim_dict() -> dict:
    """Claim dict with multiple validation issues."""
    return {
        "billing_provider_npi": "0000000000",
        "subscriber_id": "",
        "patient_first_name": "",
        "patient_last_name": "",
        "patient_dob": "",
        "patient_gender": "",
        "payer_id": "",
        "diagnosis_codes": [],
        "lines": [],
    }


class _ExplodingValidator(BaseValidator):
    """Validator that raises an exception for testing error handling."""

    name = "ExplodingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        raise RuntimeError("boom")


class _PassValidator(BaseValidator):
    """Validator that always passes."""

    name = "PassValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([])


class _WarningValidator(BaseValidator):
    """Validator that always produces a WARNING finding."""

    name = "WarningValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="TEST_WARN",
                message="Test warning",
                severity=Severity.WARNING,
                field_name="test_field",
            ),
        ])


class _ErrorValidator(BaseValidator):
    """Validator that always produces an ERROR finding."""

    name = "ErrorValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="TEST_ERR",
                message="Test error",
                severity=Severity.ERROR,
                field_name="test_field",
            ),
        ])


# --- from_settings tests ---


class TestFromSettings:
    """Test ValidationPipeline.from_settings()."""

    def test_from_default_settings_loads_8_validators(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        assert len(pipeline._rule_validators) == 8

    def test_from_custom_settings_only_npi(self) -> None:
        settings = ClaimValidatorSettings(
            rule_validators=[
                "claim_validator.validators.rule_based.npi.NPIValidator",
            ],
        )
        pipeline = ValidationPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 1
        assert pipeline._rule_validators[0].name == "NPIValidator"

    def test_from_settings_with_empty_validators(self) -> None:
        settings = ClaimValidatorSettings(rule_validators=[])
        pipeline = ValidationPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 0

    def test_from_settings_no_ai_validators_by_default(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        assert len(pipeline._ai_validators) == 0

    def test_from_settings_skip_ai_on_rule_failure_default_true(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        assert pipeline._skip_ai_on_rule_failure is True


# --- Builder tests ---


class TestPipelineBuilder:
    """Test ValidationPipeline.builder() fluent construction."""

    def test_builder_add_instance(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_PassValidator())
            .build()
        )
        assert len(pipeline._rule_validators) == 1
        assert pipeline._rule_validators[0].name == "PassValidator"

    def test_builder_add_class(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_PassValidator)
            .build()
        )
        assert len(pipeline._rule_validators) == 1
        assert pipeline._rule_validators[0].name == "PassValidator"

    def test_builder_add_multiple(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_PassValidator)
            .add(_WarningValidator)
            .add(_ErrorValidator)
            .build()
        )
        assert len(pipeline._rule_validators) == 3

    def test_builder_empty_pipeline(self) -> None:
        pipeline = ValidationPipeline.builder().build()
        assert len(pipeline._rule_validators) == 0

    def test_builder_no_ai_validators(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_PassValidator)
            .build()
        )
        assert len(pipeline._ai_validators) == 0


# --- Pipeline run tests ---


class TestPipelineRun:
    """Test ValidationPipeline.run() execution."""

    def test_valid_claim_passed_true(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.passed is True

    def test_valid_claim_no_errors(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.errors == []

    def test_invalid_claim_passed_false(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_invalid_claim_dict())
        result = pipeline.run(claim)
        assert result.passed is False

    def test_invalid_claim_has_findings(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_invalid_claim_dict())
        result = pipeline.run(claim)
        assert len(result.findings) > 0

    def test_returns_pipeline_result(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert isinstance(result, PipelineResult)

    def test_empty_pipeline_passed_true(self) -> None:
        pipeline = ValidationPipeline.builder().build()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.passed is True
        assert result.findings == []

    def test_statelessness_multiple_runs(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result1 = pipeline.run(claim)
        result2 = pipeline.run(claim)
        assert result1.passed == result2.passed
        assert len(result1.findings) == len(result2.findings)


# --- Phase result tests ---


class TestPhaseResults:
    """Test per-phase breakdown in PipelineResult."""

    def test_rule_based_phase_present(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert len(result.phase_results) >= 1
        assert result.phase_results[0].phase == "rule_based"

    def test_phase_result_is_phase_result_type(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert isinstance(result.phase_results[0], PhaseResult)

    def test_phase_result_has_validator_outputs(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        rule_phase = result.phase_results[0]
        assert len(rule_phase.validator_outputs) == 8

    def test_no_ai_phase_when_no_ai_validators(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"

    def test_phase_execution_time_positive(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.phase_results[0].execution_time > 0


# --- Execution time tests ---


class TestExecutionTime:
    """Test pipeline timing."""

    def test_execution_time_positive(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.execution_time > 0

    def test_rule_based_under_50ms(self) -> None:
        pipeline = ValidationPipeline.from_settings()
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.execution_time < 0.050


# --- Finding ordering tests ---


class TestFindingOrdering:
    """Test finding aggregation and ordering."""

    def test_errors_before_warnings(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_WarningValidator)
            .add(_ErrorValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        findings = result.findings
        assert len(findings) == 2
        assert findings[0].severity == Severity.ERROR
        assert findings[1].severity == Severity.WARNING

    def test_multiple_findings_aggregated(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_ErrorValidator)
            .add(_WarningValidator)
            .add(_ErrorValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert len(result.findings) == 3
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


# --- Exception handling tests ---


class TestValidatorExceptionHandling:
    """Test that validator exceptions become VALIDATOR_ERROR findings."""

    def test_exploding_validator_produces_error_finding(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_ExplodingValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        assert result.passed is False
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.code == "VALIDATOR_ERROR"
        assert finding.severity == Severity.ERROR

    def test_exception_context_includes_error_string(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_ExplodingValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        finding = result.findings[0]
        assert finding.context is not None
        assert "boom" in finding.context["error"]

    def test_pipeline_continues_after_exception(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_ExplodingValidator)
            .add(_PassValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        rule_phase = result.phase_results[0]
        assert len(rule_phase.validator_outputs) == 2

    def test_exception_validator_output_has_validator_name(self) -> None:
        pipeline = (
            ValidationPipeline.builder()
            .add(_ExplodingValidator)
            .build()
        )
        claim = ClaimData(**_valid_claim_dict())
        result = pipeline.run(claim)
        rule_phase = result.phase_results[0]
        assert rule_phase.validator_outputs[0].validator_name == "ExplodingValidator"


# --- AI phase gate tests ---


class TestAIPhaseGate:
    """Test two-phase AI gating logic."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_valid_claim_dict())

    def test_skip_ai_on_rule_failure_true_with_errors_skips_ai(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[_ErrorValidator()],
            ai_validators=[_PassValidator()],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(self.claim)
        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"

    def test_skip_ai_on_rule_failure_false_with_errors_runs_ai(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[_ErrorValidator()],
            ai_validators=[_PassValidator()],
            skip_ai_on_rule_failure=False,
        )
        result = pipeline.run(self.claim)
        assert len(result.phase_results) == 2
        assert result.phase_results[1].phase == "ai"

    def test_ai_runs_when_no_rule_errors(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[_PassValidator()],
            ai_validators=[_PassValidator()],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(self.claim)
        assert len(result.phase_results) == 2
        assert result.phase_results[1].phase == "ai"

    def test_no_ai_phase_when_ai_validators_empty(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[_PassValidator()],
            ai_validators=[],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(self.claim)
        assert len(result.phase_results) == 1

    def test_warnings_only_do_not_block_ai(self) -> None:
        pipeline = ValidationPipeline(
            rule_validators=[_WarningValidator()],
            ai_validators=[_PassValidator()],
            skip_ai_on_rule_failure=True,
        )
        result = pipeline.run(self.claim)
        assert len(result.phase_results) == 2
