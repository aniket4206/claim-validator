"""Tests for Finding, ValidatorOutput, PhaseResult, PipelineResult."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator import Finding, PipelineResult, Severity, ValidatorOutput
from claim_validator.models.results import PhaseResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error_finding(code: str = "ERR", field: str = "field_a") -> Finding:
    return Finding(code=code, message="error msg", severity=Severity.ERROR, field_name=field)


def _warning_finding(code: str = "WARN", field: str = "field_b") -> Finding:
    return Finding(code=code, message="warning msg", severity=Severity.WARNING, field_name=field)


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


class TestFinding:
    def test_create_with_all_fields(self) -> None:
        f = Finding(
            code="INVALID_NPI",
            message="NPI fails Luhn check-digit validation",
            severity=Severity.ERROR,
            field_name="billing_provider_npi",
            line_number=None,
            suggestion="Verify NPI at https://npiregistry.cms.hhs.gov",
            context={"expected_check_digit": 3},
        )
        assert f.code == "INVALID_NPI"
        assert f.severity == Severity.ERROR
        assert f.field_name == "billing_provider_npi"
        assert f.line_number is None
        assert f.suggestion.startswith("Verify")
        assert f.context == {"expected_check_digit": 3}

    def test_create_with_defaults(self) -> None:
        f = Finding(
            code="MISSING_FIELD",
            message="Required field is missing",
            severity=Severity.ERROR,
            field_name="subscriber_id",
        )
        assert f.line_number is None
        assert f.suggestion == ""
        assert f.context is None

    def test_line_level_finding(self) -> None:
        f = Finding(
            code="INVALID_CHARGE_AMOUNT",
            message="Charge amount must be positive",
            severity=Severity.ERROR,
            field_name="charge_amount",
            line_number=2,
        )
        assert f.line_number == 2

    def test_frozen_raises_on_modification(self) -> None:
        f = _error_finding()
        with pytest.raises(pydantic.ValidationError):
            f.code = "CHANGED"  # type: ignore[misc]

    def test_severity_accepts_enum(self) -> None:
        f = Finding(code="TEST", message="msg", severity=Severity.WARNING, field_name="f")
        assert f.severity == Severity.WARNING

    def test_severity_coerces_string(self) -> None:
        """strict=False allows string -> Severity coercion."""
        f = Finding(
            code="TEST",
            message="msg",
            severity="error",
            field_name="f",  # type: ignore[arg-type]
        )
        assert f.severity == Severity.ERROR


# ---------------------------------------------------------------------------
# ValidatorOutput
# ---------------------------------------------------------------------------


class TestValidatorOutput:
    def test_create_with_findings(self) -> None:
        findings = [_error_finding(), _warning_finding()]
        output = ValidatorOutput(validator_name="NPIValidator", findings=findings)
        assert output.validator_name == "NPIValidator"
        assert len(output.findings) == 2

    def test_create_empty(self) -> None:
        output = ValidatorOutput(validator_name="CompletenessValidator")
        assert output.findings == []

    def test_frozen(self) -> None:
        output = ValidatorOutput(validator_name="Test")
        with pytest.raises(pydantic.ValidationError):
            output.validator_name = "Changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhaseResult
# ---------------------------------------------------------------------------


class TestPhaseResult:
    def test_findings_flattens_outputs(self) -> None:
        out1 = ValidatorOutput(validator_name="V1", findings=[_error_finding("A")])
        out2 = ValidatorOutput(
            validator_name="V2", findings=[_warning_finding("B"), _error_finding("C")]
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out1, out2], execution_time=0.05)
        assert len(phase.findings) == 3
        assert [f.code for f in phase.findings] == ["A", "B", "C"]

    def test_empty_phase(self) -> None:
        phase = PhaseResult(phase="ai")
        assert phase.findings == []
        assert phase.execution_time == 0.0


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_passed_with_no_findings(self) -> None:
        result = PipelineResult()
        assert result.passed is True
        assert result.findings == []

    def test_passed_with_warnings_only(self) -> None:
        """WARNINGs do NOT cause passed to be False."""
        out = ValidatorOutput(validator_name="V1", findings=[_warning_finding()])
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        assert result.passed is True
        assert len(result.warnings) == 1

    def test_failed_with_errors(self) -> None:
        out = ValidatorOutput(validator_name="V1", findings=[_error_finding()])
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        assert result.passed is False
        assert len(result.errors) == 1

    def test_failed_with_mixed_findings(self) -> None:
        out = ValidatorOutput(
            validator_name="V1",
            findings=[_warning_finding(), _error_finding()],
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        assert result.passed is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_findings_ordered_errors_first(self) -> None:
        """Findings ordered: ERROR before WARNING within same phase."""
        out = ValidatorOutput(
            validator_name="V1",
            findings=[_warning_finding("W1"), _error_finding("E1"), _warning_finding("W2")],
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        codes = [f.code for f in result.findings]
        assert codes == ["E1", "W1", "W2"]

    def test_findings_ordered_across_phases(self) -> None:
        """Phase order preserved: rule-based before AI. Errors first within that."""
        rule_out = ValidatorOutput(validator_name="RuleV", findings=[_warning_finding("RW")])
        ai_out = ValidatorOutput(validator_name="AIV", findings=[_error_finding("AE")])
        rule_phase = PhaseResult(phase="rule_based", validator_outputs=[rule_out])
        ai_phase = PhaseResult(phase="ai", validator_outputs=[ai_out])
        result = PipelineResult(phase_results=[rule_phase, ai_phase])
        codes = [f.code for f in result.findings]
        # ERROR from AI comes before WARNING from rule_based (severity first)
        assert codes == ["AE", "RW"]

    def test_findings_across_validators_in_same_phase(self) -> None:
        """Multiple validators in same phase — errors sorted first, stable within severity."""
        out1 = ValidatorOutput(
            validator_name="V1", findings=[_warning_finding("V1W"), _error_finding("V1E")]
        )
        out2 = ValidatorOutput(
            validator_name="V2", findings=[_error_finding("V2E"), _warning_finding("V2W")]
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out1, out2])
        result = PipelineResult(phase_results=[phase])
        codes = [f.code for f in result.findings]
        # All ERRORs first (V1E, V2E), then WARNINGs (V1W, V2W) — stable order within severity
        assert codes == ["V1E", "V2E", "V1W", "V2W"]

    def test_execution_time(self) -> None:
        result = PipelineResult(execution_time=0.123)
        assert result.execution_time == 0.123

    def test_phase_results_accessible(self) -> None:
        phase = PhaseResult(phase="rule_based", execution_time=0.05)
        result = PipelineResult(phase_results=[phase], execution_time=0.05)
        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"

    def test_errors_property(self) -> None:
        out = ValidatorOutput(
            validator_name="V1",
            findings=[_error_finding("E1"), _warning_finding("W1"), _error_finding("E2")],
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        assert len(result.errors) == 2
        assert all(f.severity == Severity.ERROR for f in result.errors)

    def test_warnings_property(self) -> None:
        out = ValidatorOutput(
            validator_name="V1",
            findings=[_error_finding("E1"), _warning_finding("W1"), _warning_finding("W2")],
        )
        phase = PhaseResult(phase="rule_based", validator_outputs=[out])
        result = PipelineResult(phase_results=[phase])
        assert len(result.warnings) == 2
        assert all(f.severity == Severity.WARNING for f in result.warnings)


# ---------------------------------------------------------------------------
# PHI Convention
# ---------------------------------------------------------------------------


class TestPHIConvention:
    def test_finding_messages_should_not_contain_phi(self) -> None:
        """Convention: findings reference field names, never PHI values."""
        f = Finding(
            code="INVALID_NPI",
            message="NPI fails Luhn check-digit validation",
            severity=Severity.ERROR,
            field_name="billing_provider_npi",
            suggestion="Verify NPI at https://npiregistry.cms.hhs.gov",
        )
        # No actual NPI or patient data in message/suggestion
        assert "1234567890" not in f.message
        assert "John" not in f.message
        assert "1234567890" not in f.suggestion
