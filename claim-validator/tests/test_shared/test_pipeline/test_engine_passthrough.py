"""Tests for BasePipeline passthrough with ValidationContext."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.pipeline import BasePipeline, PipelineConfig
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.validators.base import BaseValidator

# ---------------------------------------------------------------------------
# Mock validators with mapped category names
# ---------------------------------------------------------------------------


class MockNPIValidator(BaseValidator):
    """NPI validator (category: npi)."""

    name = "NPIValidator"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[])


class MockMemberIDValidator(BaseValidator):
    """Member ID validator (category: member_id)."""

    name = "MemberIDValidator"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(
            validator_name=self.name,
            findings=[
                Finding(
                    code="ELIG_MISSING_MEMBER_ID",
                    message="Missing member ID",
                    severity=Severity.WARNING,
                    field_name="member_id",
                ),
            ],
        )


class MockPANPIValidator(BaseValidator):
    """PA NPI validator (category: npi)."""

    name = "PANPIValidator"

    def validate(self, data: Any) -> ValidatorOutput:
        raise AssertionError("Should be skipped via passthrough")


class MockPAMemberIDValidator(BaseValidator):
    """PA Member ID validator (category: member_id)."""

    name = "PAMemberIDValidator"

    def validate(self, data: Any) -> ValidatorOutput:
        raise AssertionError("Should be skipped via passthrough")


class MockCodingValidator(BaseValidator):
    """Coding validator — no category mapping, always runs."""

    name = "CodingValidator"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[])


class TestEnginePassthrough:
    """Passthrough logic in _run_rule_phase via ValidationContext."""

    def test_without_context_all_validators_run(self):
        """When validation_context is None, all validators execute normally."""
        pipeline = BasePipeline(
            PipelineConfig(
                domain="eligibility",
                validators=(MockNPIValidator(), MockMemberIDValidator()),
            )
        )
        result = pipeline.run({})
        phase = result.phase_results[0]
        assert len(phase.validator_outputs) == 2
        assert phase.validator_outputs[0].validator_name == "NPIValidator"
        assert phase.validator_outputs[1].validator_name == "MemberIDValidator"

    def test_context_records_results(self):
        """After running with context, results are recorded."""
        ctx = ValidationContext()
        pipeline = BasePipeline(
            PipelineConfig(
                domain="eligibility",
                validators=(MockNPIValidator(), MockMemberIDValidator()),
            )
        )
        pipeline.run({}, validation_context=ctx)
        # NPI passed (no findings)
        assert ctx.has_passed("npi") is True
        # MemberID has a WARNING but no ERROR → still passed
        assert ctx.has_passed("member_id") is True

    def test_passthrough_skips_validators(self):
        """Validators with passed category in context are skipped."""
        ctx = ValidationContext()
        # Pre-populate context with passed npi and member_id
        ctx.record("NPIValidator", "npi", passed=True, findings=[])
        ctx.record(
            "MemberIDValidator",
            "member_id",
            passed=True,
            findings=[
                Finding(
                    code="ELIG_MISSING_MEMBER_ID",
                    message="Missing member ID",
                    severity=Severity.WARNING,
                    field_name="member_id",
                ),
            ],
        )

        # PA pipeline with validators that would raise if called
        pipeline = BasePipeline(
            PipelineConfig(
                domain="prior_auth",
                validators=(
                    MockPANPIValidator(),
                    MockPAMemberIDValidator(),
                    MockCodingValidator(),  # no category → runs
                ),
            )
        )
        result = pipeline.run({}, validation_context=ctx)
        phase = result.phase_results[0]

        assert len(phase.validator_outputs) == 3
        # NPI skipped with passthrough suffix
        assert phase.validator_outputs[0].validator_name == "PANPIValidator(passthrough)"
        assert phase.validator_outputs[0].findings == []
        # MemberID skipped, prior findings carried over
        assert (
            phase.validator_outputs[1].validator_name
            == "PAMemberIDValidator(passthrough)"
        )
        assert len(phase.validator_outputs[1].findings) == 1
        assert phase.validator_outputs[1].findings[0].code == "ELIG_MISSING_MEMBER_ID"
        # CodingValidator ran normally
        assert phase.validator_outputs[2].validator_name == "CodingValidator"

    def test_failed_category_not_skipped(self):
        """Validators whose category did NOT pass still execute."""
        ctx = ValidationContext()
        ctx.record("NPIValidator", "npi", passed=False)

        class NPIValidatorForPA(BaseValidator):
            name = "PANPIValidator"

            def validate(self, data: Any) -> ValidatorOutput:
                return ValidatorOutput(validator_name=self.name, findings=[])

        pipeline = BasePipeline(
            PipelineConfig(
                domain="prior_auth",
                validators=(NPIValidatorForPA(),),
            )
        )
        result = pipeline.run({}, validation_context=ctx)
        phase = result.phase_results[0]
        # Not skipped because npi didn't pass
        assert phase.validator_outputs[0].validator_name == "PANPIValidator"

    def test_unmapped_validator_always_runs(self):
        """Validators without a category mapping always run, context or not."""
        ctx = ValidationContext()
        pipeline = BasePipeline(
            PipelineConfig(
                domain="claim",
                validators=(MockCodingValidator(),),
            )
        )
        result = pipeline.run({}, validation_context=ctx)
        phase = result.phase_results[0]
        assert phase.validator_outputs[0].validator_name == "CodingValidator"

    def test_backward_compatible_no_context(self):
        """Calling run() without validation_context still works exactly as before."""
        pipeline = BasePipeline(
            PipelineConfig(
                domain="claim",
                validators=(MockNPIValidator(), MockCodingValidator()),
            )
        )
        result = pipeline.run({})
        assert result.passed is True
        assert len(result.phase_results) == 1
        assert len(result.phase_results[0].validator_outputs) == 2
