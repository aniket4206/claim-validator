"""Tests for WorkflowResult and StageResult models."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.workflow.models import StageResult, WorkflowResult


class TestStageResult:
    """StageResult model tests."""

    def test_defaults(self):
        sr = StageResult(stage_name="eligibility", passed=True)
        assert sr.stage_name == "eligibility"
        assert sr.passed is True
        assert sr.skipped is False
        assert sr.skip_reason is None
        assert sr.findings == []
        assert sr.execution_time == 0.0
        assert sr.detail is None

    def test_skipped_stage(self):
        sr = StageResult(
            stage_name="prior_auth",
            passed=True,
            skipped=True,
            skip_reason="PA not required",
        )
        assert sr.skipped is True
        assert sr.skip_reason == "PA not required"

    def test_with_findings(self):
        f = Finding(
            code="TEST",
            message="test",
            severity=Severity.ERROR,
            field_name="x",
        )
        sr = StageResult(
            stage_name="eligibility",
            passed=False,
            findings=[f],
            execution_time=1.5,
        )
        assert len(sr.findings) == 1
        assert sr.execution_time == 1.5

    def test_frozen(self):
        sr = StageResult(stage_name="eligibility", passed=True)
        try:
            sr.passed = False  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass


class TestWorkflowResult:
    """WorkflowResult model tests."""

    def test_defaults(self):
        wr = WorkflowResult()
        assert wr.eligibility is None
        assert wr.pa_determination is None
        assert wr.prior_auth is None
        assert wr.claim_validation is None
        assert wr.stopped_at is None
        assert wr.stage_results == []
        assert wr.findings == []
        assert wr.ai_summary is None
        assert wr.execution_time == 0.0

    def test_passed_no_errors(self):
        wr = WorkflowResult(
            findings=[
                Finding(
                    code="W1",
                    message="warning",
                    severity=Severity.WARNING,
                    field_name="x",
                ),
            ],
        )
        assert wr.passed is True

    def test_not_passed_with_errors(self):
        wr = WorkflowResult(
            findings=[
                Finding(
                    code="E1",
                    message="error",
                    severity=Severity.ERROR,
                    field_name="x",
                ),
            ],
        )
        assert wr.passed is False

    def test_stage_times(self):
        wr = WorkflowResult(
            stage_results=[
                StageResult(stage_name="eligibility", passed=True, execution_time=0.5),
                StageResult(stage_name="pa_determination", passed=True, execution_time=0.1),
                StageResult(stage_name="claim_validation", passed=True, execution_time=1.2),
            ],
        )
        times = wr.stage_times
        assert times == {
            "eligibility": 0.5,
            "pa_determination": 0.1,
            "claim_validation": 1.2,
        }

    def test_stage_times_empty(self):
        wr = WorkflowResult()
        assert wr.stage_times == {}

    def test_stopped_at(self):
        wr = WorkflowResult(stopped_at="eligibility")
        assert wr.stopped_at == "eligibility"
