"""Tests for BasePipeline — phase execution, gating, timing, error handling."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import DeidentificationConfig
from claim_validator.shared.pipeline import BasePipeline, PipelineConfig
from claim_validator.validators.base import BaseValidator

# ---------------------------------------------------------------------------
# Mock validators
# ---------------------------------------------------------------------------


class PassingValidator(BaseValidator):
    """Validator that produces zero findings."""

    name = "passing"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[])


class FailingValidator(BaseValidator):
    """Validator that produces an ERROR finding."""

    name = "failing"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(
            validator_name=self.name,
            findings=[
                Finding(
                    code="TEST_ERROR",
                    message="Test failure",
                    severity=Severity.ERROR,
                    field_name="test_field",
                )
            ],
        )


class WarningValidator(BaseValidator):
    """Validator that produces a WARNING finding."""

    name = "warning"

    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(
            validator_name=self.name,
            findings=[
                Finding(
                    code="TEST_WARNING",
                    message="Test warning",
                    severity=Severity.WARNING,
                    field_name="test_field",
                )
            ],
        )


class ExplodingValidator(BaseValidator):
    """Validator that raises an exception."""

    name = "exploding"

    def validate(self, data: Any) -> ValidatorOutput:
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# Mock clearinghouse client
# ---------------------------------------------------------------------------


class MockClearinghouseClient:
    """Duck-typed clearinghouse client for testing."""

    def __init__(self, *, should_fail: bool = False) -> None:
        self.called = False
        self._should_fail = should_fail

    def submit(self, data: Any) -> dict[str, str]:
        self.called = True
        if self._should_fail:
            raise RuntimeError("Clearinghouse error")
        return {"status": "ok"}


# ---------------------------------------------------------------------------
# Mock AI interpreter
# ---------------------------------------------------------------------------


class MockAIInterpreter:
    """Duck-typed AI interpreter for testing."""

    name = "mock_ai"

    def __init__(
        self,
        *,
        should_fail: bool = False,
        fail_with_llm_error: bool = False,
    ) -> None:
        self.called = False
        self.received_data: Any = None
        self._should_fail = should_fail
        self._fail_with_llm_error = fail_with_llm_error

    def validate_deidentified(self, data: Any) -> ValidatorOutput:
        self.called = True
        self.received_data = data
        if self._fail_with_llm_error:
            raise LLMError("LLM unavailable")
        if self._should_fail:
            raise RuntimeError("AI error")
        return ValidatorOutput(validator_name=self.name, findings=[])


class MockAIInterpreterWithFindings:
    """AI interpreter that returns actual findings."""

    name = "mock_ai_findings"

    def validate_deidentified(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(
            validator_name=self.name,
            findings=[
                Finding(
                    code="AI_ISSUE",
                    message="AI found a problem",
                    severity=Severity.WARNING,
                    field_name="diagnosis_code",
                )
            ],
        )


class MockExplodingDeidentifier:
    """Deidentifier that raises an exception."""

    def deidentify(self, data: Any) -> dict[str, Any]:
        raise TypeError("Expected dict, got something else")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_INPUT = {"patient_name": "John Doe", "diagnosis_code": "J06.9"}


_DEFAULT_DEID = BaseDeidentifier(DeidentificationConfig())


def _make_config(**overrides: Any) -> PipelineConfig:
    """Create a PipelineConfig with sensible test defaults.

    Auto-provides a no-op deidentifier when ai_interpreter is set
    (required by __post_init__ validation per FR40).
    """
    defaults: dict[str, Any] = {"domain": "test", "code_prefix": "TST_"}
    defaults.update(overrides)
    if defaults.get("ai_interpreter") is not None and "deidentifier" not in overrides:
        defaults["deidentifier"] = _DEFAULT_DEID
    return PipelineConfig(**defaults)


# ===========================================================================
# Test classes
# ===========================================================================


class TestBasePipelineRulePhase:
    """Phase 1: rule-based validators execute and produce PhaseResult."""

    def test_single_passing_validator(self) -> None:
        cfg = _make_config(validators=(PassingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"
        assert result.phase_results[0].findings == []
        assert result.passed is True

    def test_single_failing_validator(self) -> None:
        cfg = _make_config(validators=(FailingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "TEST_ERROR"

    def test_mixed_validators(self) -> None:
        cfg = _make_config(
            validators=(PassingValidator(), FailingValidator(), WarningValidator())
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_warning_only_passes(self) -> None:
        cfg = _make_config(validators=(WarningValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is True
        assert len(result.warnings) == 1

    def test_multiple_outputs_in_phase(self) -> None:
        cfg = _make_config(validators=(PassingValidator(), PassingValidator()))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.phase_results[0].validator_outputs) == 2

    def test_exception_produces_error_finding(self) -> None:
        cfg = _make_config(validators=(ExplodingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is False
        assert len(result.errors) == 1
        finding = result.errors[0]
        assert finding.code == "TST_VALIDATOR_ERROR"
        assert finding.severity == Severity.ERROR
        assert "boom" in finding.context["error"]

    def test_exception_uses_validator_name(self) -> None:
        cfg = _make_config(validators=(ExplodingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        output = result.phase_results[0].validator_outputs[0]
        assert output.validator_name == "exploding"

    def test_empty_validators_produces_empty_rule_phase(self) -> None:
        cfg = _make_config(validators=())
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.phase_results) == 1
        assert result.phase_results[0].phase == "rule_based"
        assert result.phase_results[0].validator_outputs == []
        assert result.passed is True


class TestBasePipelineClearinghousePhase:
    """Phase 2: clearinghouse submission."""

    def test_clearinghouse_called_when_configured(self) -> None:
        ch = MockClearinghouseClient()
        cfg = _make_config(
            validators=(PassingValidator(),), clearinghouse_client=ch
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is True
        phases = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" in phases

    def test_clearinghouse_skipped_when_none(self) -> None:
        cfg = _make_config(
            validators=(PassingValidator(),), clearinghouse_client=None
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        phases = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" not in phases

    def test_clearinghouse_success_no_findings(self) -> None:
        ch = MockClearinghouseClient()
        cfg = _make_config(
            validators=(PassingValidator(),), clearinghouse_client=ch
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        ch_phase = [pr for pr in result.phase_results if pr.phase == "clearinghouse"][0]
        assert ch_phase.findings == []

    def test_clearinghouse_error_produces_error_finding(self) -> None:
        ch = MockClearinghouseClient(should_fail=True)
        cfg = _make_config(
            validators=(PassingValidator(),), clearinghouse_client=ch
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is False
        ch_phase = [pr for pr in result.phase_results if pr.phase == "clearinghouse"][0]
        assert len(ch_phase.findings) == 1
        assert ch_phase.findings[0].code == "TST_CLEARINGHOUSE_ERROR"


class TestBasePipelineAIPhase:
    """Phase 3: AI interpretation."""

    def test_ai_called_when_configured(self) -> None:
        ai = MockAIInterpreter()
        cfg = _make_config(validators=(PassingValidator(),), ai_interpreter=ai)
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ai.called is True
        phases = [pr.phase for pr in result.phase_results]
        assert "ai" in phases

    def test_ai_skipped_when_none(self) -> None:
        cfg = _make_config(
            validators=(PassingValidator(),), ai_interpreter=None
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        phases = [pr.phase for pr in result.phase_results]
        assert "ai" not in phases

    def test_ai_deidentifies_before_calling(self) -> None:
        ai = MockAIInterpreter()
        deid = BaseDeidentifier(
            DeidentificationConfig(name_fields=("patient_name",))
        )
        cfg = _make_config(
            validators=(PassingValidator(),),
            ai_interpreter=ai,
            deidentifier=deid,
        )
        BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ai.called is True
        assert ai.received_data["patient_name"] is None
        assert ai.received_data["diagnosis_code"] == "J06.9"

    def test_ai_with_noop_deidentifier_passes_data_unchanged(self) -> None:
        ai = MockAIInterpreter()
        deid = BaseDeidentifier(DeidentificationConfig())  # no PHI fields configured
        cfg = _make_config(
            validators=(PassingValidator(),),
            ai_interpreter=ai,
            deidentifier=deid,
        )
        BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ai.received_data == _SAMPLE_INPUT

    def test_llm_error_produces_warning(self) -> None:
        ai = MockAIInterpreter(fail_with_llm_error=True)
        cfg = _make_config(validators=(PassingValidator(),), ai_interpreter=ai)
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is True  # WARNING, not ERROR
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "TST_AI_PROVIDER_ERROR"
        assert result.warnings[0].severity == Severity.WARNING

    def test_generic_error_produces_error(self) -> None:
        ai = MockAIInterpreter(should_fail=True)
        cfg = _make_config(validators=(PassingValidator(),), ai_interpreter=ai)
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.passed is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "TST_VALIDATOR_ERROR"
        assert result.errors[0].severity == Severity.ERROR

    def test_ai_error_uses_interpreter_name(self) -> None:
        ai = MockAIInterpreter(should_fail=True)
        cfg = _make_config(validators=(PassingValidator(),), ai_interpreter=ai)
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        ai_phase = [pr for pr in result.phase_results if pr.phase == "ai"][0]
        assert ai_phase.validator_outputs[0].validator_name == "mock_ai"

    def test_ai_findings_propagate_to_result(self) -> None:
        deid = BaseDeidentifier(DeidentificationConfig())
        cfg = _make_config(
            validators=(PassingValidator(),),
            ai_interpreter=MockAIInterpreterWithFindings(),
            deidentifier=deid,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.warnings) == 1
        assert result.warnings[0].code == "AI_ISSUE"
        assert result.warnings[0].field_name == "diagnosis_code"
        ai_phase = [pr for pr in result.phase_results if pr.phase == "ai"][0]
        assert ai_phase.validator_outputs[0].validator_name == "mock_ai_findings"

    def test_deidentifier_error_produces_distinct_finding(self) -> None:
        deid = MockExplodingDeidentifier()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(PassingValidator(),),
            ai_interpreter=ai,
            deidentifier=deid,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ai.called is False  # AI never reached
        assert result.passed is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "TST_DEIDENTIFIER_ERROR"
        assert "Expected dict" in result.errors[0].context["error"]
        ai_phase = [pr for pr in result.phase_results if pr.phase == "ai"][0]
        assert ai_phase.validator_outputs[0].validator_name == "deidentifier"


class TestBasePipelineGating:
    """Phase gating — skipping phases based on rule-phase errors."""

    def test_skip_clearinghouse_on_rule_failure(self) -> None:
        ch = MockClearinghouseClient()
        cfg = _make_config(
            validators=(FailingValidator(),),
            clearinghouse_client=ch,
            skip_clearinghouse_on_rule_failure=True,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is False
        phases = [pr.phase for pr in result.phase_results]
        assert "clearinghouse" not in phases

    def test_skip_ai_on_rule_failure(self) -> None:
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(FailingValidator(),),
            ai_interpreter=ai,
            skip_ai_on_rule_failure=True,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ai.called is False
        phases = [pr.phase for pr in result.phase_results]
        assert "ai" not in phases

    def test_cascade_clearinghouse_skipped_also_skips_ai(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(FailingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
            skip_clearinghouse_on_rule_failure=True,
            skip_ai_on_rule_failure=False,  # AI gating disabled
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is False
        assert ai.called is False  # cascade: clearinghouse skip -> AI skip
        phases = [pr.phase for pr in result.phase_results]
        assert phases == ["rule_based"]

    def test_no_gating_when_rules_pass(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(PassingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
            skip_clearinghouse_on_rule_failure=True,
            skip_ai_on_rule_failure=True,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is True
        assert ai.called is True
        phases = [pr.phase for pr in result.phase_results]
        assert phases == ["rule_based", "clearinghouse", "ai"]

    def test_no_gating_when_warnings_only(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(WarningValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
            skip_clearinghouse_on_rule_failure=True,
            skip_ai_on_rule_failure=True,
        )
        BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is True
        assert ai.called is True

    def test_no_gating_when_gating_disabled(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(FailingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
            skip_clearinghouse_on_rule_failure=False,
            skip_ai_on_rule_failure=False,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is True
        assert ai.called is True
        phases = [pr.phase for pr in result.phase_results]
        assert phases == ["rule_based", "clearinghouse", "ai"]

    def test_skip_ai_but_not_clearinghouse(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(FailingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
            skip_clearinghouse_on_rule_failure=False,
            skip_ai_on_rule_failure=True,
        )
        BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert ch.called is True
        assert ai.called is False


class TestBasePipelineTiming:
    """Per-phase and total timing (AC-5)."""

    def test_total_execution_time_positive(self) -> None:
        cfg = _make_config(validators=(PassingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.execution_time > 0

    def test_per_phase_execution_time_positive(self) -> None:
        cfg = _make_config(validators=(PassingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        for phase_result in result.phase_results:
            assert phase_result.execution_time >= 0

    def test_total_gte_sum_of_phases(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(PassingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        phase_sum = sum(pr.execution_time for pr in result.phase_results)
        assert result.execution_time >= phase_sum

    def test_three_phases_have_individual_times(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(PassingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.phase_results) == 3
        for pr in result.phase_results:
            assert isinstance(pr.execution_time, float)


class TestBasePipelineResultStructure:
    """PipelineResult has correct structure and properties."""

    def test_phase_names_correct(self) -> None:
        ch = MockClearinghouseClient()
        ai = MockAIInterpreter()
        cfg = _make_config(
            validators=(PassingValidator(),),
            clearinghouse_client=ch,
            ai_interpreter=ai,
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        phases = [pr.phase for pr in result.phase_results]
        assert phases == ["rule_based", "clearinghouse", "ai"]

    def test_passed_true_when_no_errors(self) -> None:
        cfg = _make_config(validators=(PassingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)
        assert result.passed is True

    def test_passed_false_when_errors(self) -> None:
        cfg = _make_config(validators=(FailingValidator(),))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)
        assert result.passed is False

    def test_findings_flat_list(self) -> None:
        cfg = _make_config(
            validators=(FailingValidator(), WarningValidator())
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.findings) == 2
        assert result.findings[0].severity == Severity.ERROR  # errors first
        assert result.findings[1].severity == Severity.WARNING

    def test_errors_property(self) -> None:
        cfg = _make_config(validators=(FailingValidator(), WarningValidator()))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.errors) == 1
        assert all(f.severity == Severity.ERROR for f in result.errors)

    def test_warnings_property(self) -> None:
        cfg = _make_config(validators=(FailingValidator(), WarningValidator()))
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.warnings) == 1
        assert all(f.severity == Severity.WARNING for f in result.warnings)


class TestBasePipelineEdgeCases:
    """Edge cases and boundary conditions."""

    def test_no_validators_no_clearinghouse_no_ai(self) -> None:
        cfg = _make_config()
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert len(result.phase_results) == 1  # empty rule phase
        assert result.passed is True

    def test_input_data_not_mutated(self) -> None:
        original = {"patient_name": "John Doe", "code": "J06.9"}
        input_copy = {**original}
        cfg = _make_config(validators=(PassingValidator(),))
        BasePipeline(cfg).run(input_copy)

        assert input_copy == original

    def test_config_accessible_via_property(self) -> None:
        cfg = _make_config(domain="claim")
        pipeline = BasePipeline(cfg)
        assert pipeline.config is cfg
        assert pipeline.config.domain == "claim"

    def test_code_prefix_in_error_codes(self) -> None:
        cfg = _make_config(
            validators=(ExplodingValidator(),), code_prefix="MY_PREFIX_"
        )
        result = BasePipeline(cfg).run(_SAMPLE_INPUT)

        assert result.errors[0].code == "MY_PREFIX_VALIDATOR_ERROR"

    def test_ai_with_deidentifier_does_not_mutate_input(self) -> None:
        original = {"patient_name": "John Doe", "diagnosis_code": "J06.9"}
        input_copy = {**original}
        ai = MockAIInterpreter()
        deid = BaseDeidentifier(
            DeidentificationConfig(name_fields=("patient_name",))
        )
        cfg = _make_config(
            validators=(PassingValidator(),),
            ai_interpreter=ai,
            deidentifier=deid,
        )
        BasePipeline(cfg).run(input_copy)

        assert input_copy == original  # input not mutated
        assert ai.received_data["patient_name"] is None  # AI got de-identified data
