"""Tests for WorkflowOrchestrator."""

from __future__ import annotations

from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.workflow.models import StageResult, WorkflowResult
from claim_validator.workflow.orchestrator import WorkflowOrchestrator


class _FakeStage:
    """Minimal stage for orchestrator testing."""

    def __init__(
        self,
        name: str,
        is_gate: bool = False,
        *,
        skip: bool = False,
        skip_reason: str | None = None,
        passed: bool = True,
        findings: list[Finding] | None = None,
        ctx_key: str | None = None,
        ctx_value: Any = None,
    ) -> None:
        self.name = name
        self.is_gate = is_gate
        self._skip = skip
        self._skip_reason = skip_reason
        self._passed = passed
        self._findings = findings or []
        self._ctx_key = ctx_key
        self._ctx_value = ctx_value

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        return self._skip, self._skip_reason

    def run(
        self,
        input_data: Any,
        *,
        validation_context: Any = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        if workflow_context is not None and self._ctx_key:
            workflow_context[self._ctx_key] = self._ctx_value
        return StageResult(
            stage_name=self.name,
            passed=self._passed,
            findings=self._findings,
            execution_time=0.001,
        )


class TestWorkflowOrchestrator:
    """WorkflowOrchestrator tests."""

    def test_all_stages_pass(self):
        stages = [
            _FakeStage("s1", is_gate=True, passed=True),
            _FakeStage("s2", is_gate=False, passed=True),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert isinstance(result, WorkflowResult)
        assert result.stopped_at is None
        assert len(result.stage_results) == 2
        assert all(sr.passed for sr in result.stage_results)
        assert result.execution_time > 0

    def test_gate_failure_stops_execution(self):
        err = Finding(
            code="ELIG_FAIL", message="Inactive", severity=Severity.ERROR,
            field_name="coverage",
        )
        stages = [
            _FakeStage("eligibility", is_gate=True, passed=False, findings=[err]),
            _FakeStage("claim_validation", is_gate=False, passed=True),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert result.stopped_at == "eligibility"
        assert len(result.stage_results) == 1
        assert result.stage_results[0].stage_name == "eligibility"
        assert len(result.findings) == 1

    def test_non_gate_failure_continues(self):
        warn = Finding(
            code="PA_WARN", message="warn", severity=Severity.WARNING,
            field_name="pa",
        )
        stages = [
            _FakeStage("pa_determination", is_gate=False, passed=False, findings=[warn]),
            _FakeStage("claim_validation", is_gate=False, passed=True),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert result.stopped_at is None
        assert len(result.stage_results) == 2

    def test_skipped_stage_recorded(self):
        stages = [
            _FakeStage("prior_auth", is_gate=True, skip=True, skip_reason="Not required"),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert len(result.stage_results) == 1
        sr = result.stage_results[0]
        assert sr.skipped is True
        assert sr.skip_reason == "Not required"
        assert sr.passed is True

    def test_findings_sorted_errors_first(self):
        warn = Finding(
            code="W1", message="warn", severity=Severity.WARNING, field_name="x",
        )
        err = Finding(
            code="E1", message="error", severity=Severity.ERROR, field_name="y",
        )
        stages = [
            _FakeStage("s1", is_gate=False, passed=True, findings=[warn]),
            _FakeStage("s2", is_gate=False, passed=True, findings=[err]),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert result.findings[0].severity == Severity.ERROR
        assert result.findings[1].severity == Severity.WARNING

    def test_workflow_context_shared_between_stages(self):
        from claim_validator.eligibility.models.result import EligibilityResult

        elig = EligibilityResult()
        stages = [
            _FakeStage(
                "s1", ctx_key="eligibility_result", ctx_value=elig,
            ),
            _FakeStage("s2"),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        assert result.eligibility is elig

    def test_stage_times_populated(self):
        stages = [
            _FakeStage("s1", passed=True),
            _FakeStage("s2", passed=True),
        ]
        orch = WorkflowOrchestrator(stages)
        result = orch.execute({})

        times = result.stage_times
        assert "s1" in times
        assert "s2" in times

    def test_empty_stages_returns_valid_result(self):
        orch = WorkflowOrchestrator([])
        result = orch.execute({})

        assert isinstance(result, WorkflowResult)
        assert result.stopped_at is None
        assert len(result.stage_results) == 0
        assert result.passed is True
