"""Workflow orchestrator — sequential stage execution with gate logic."""

from __future__ import annotations

import logging
import time
from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.workflow.models import StageResult, WorkflowResult
from claim_validator.workflow.stages import Stage

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Execute workflow stages sequentially with gate and skip logic.

    Each stage is checked for skip conditions, then executed.  Gate stages
    that fail cause early termination (``stopped_at`` is set).
    """

    def __init__(self, stages: list[Stage]) -> None:
        self._stages = stages

    def execute(
        self,
        input_data: dict[str, Any],
        *,
        workflow_context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """Run all stages in order, collecting results.

        Args:
            input_data: Dict with keys consumed by individual stages
                (e.g. ``eligibility_request``, ``claim_data``).
            workflow_context: Shared mutable dict for inter-stage state.

        Returns:
            WorkflowResult with per-stage results and aggregate findings.
        """
        start = time.perf_counter()
        wf_ctx = workflow_context if workflow_context is not None else {}
        val_ctx = ValidationContext()
        stage_results: list[StageResult] = []
        all_findings: list[Finding] = []
        stopped_at: str | None = None

        for stage in self._stages:
            skip, skip_reason = stage.should_skip(wf_ctx)
            if skip:
                logger.info("Stage %s skipped: %s", stage.name, skip_reason)
                stage_results.append(
                    StageResult(
                        stage_name=stage.name,
                        passed=True,
                        skipped=True,
                        skip_reason=skip_reason,
                    ),
                )
                continue

            logger.info("Stage %s starting", stage.name)
            try:
                result = stage.run(
                    input_data,
                    validation_context=val_ctx,
                    workflow_context=wf_ctx,
                )
            except Exception:
                logger.exception("Stage %s raised an exception", stage.name)
                elapsed_stage = time.perf_counter() - start
                result = StageResult(
                    stage_name=stage.name,
                    passed=False,
                    findings=[
                        Finding(
                            code="STAGE_ERROR",
                            message=f"Stage '{stage.name}' raised an unexpected error",
                            severity=Severity.ERROR,
                            field_name="",
                        ),
                    ],
                    execution_time=elapsed_stage,
                )

            stage_results.append(result)
            all_findings.extend(result.findings)
            logger.info(
                "Stage %s completed: passed=%s findings=%d",
                stage.name, result.passed, len(result.findings),
            )

            if stage.is_gate and not result.passed:
                stopped_at = stage.name
                logger.warning("Gate stage %s failed — stopping workflow", stage.name)
                break

        # Sort findings: ERRORs first, then WARNINGs.
        # Note: only ERROR and WARNING are defined in Severity enum.
        severity_order = {Severity.ERROR: 0, Severity.WARNING: 1}
        all_findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        elapsed = time.perf_counter() - start
        logger.info("Workflow completed in %.3fs — %d stages, stopped_at=%s",
                     elapsed, len(stage_results), stopped_at)

        # Extract typed domain results from workflow_context
        return WorkflowResult(
            eligibility=wf_ctx.get("eligibility_result"),
            pa_determination=wf_ctx.get("pa_determination"),
            prior_auth=wf_ctx.get("prior_auth_result"),
            claim_validation=wf_ctx.get("claim_validation_result"),
            stopped_at=stopped_at,
            stage_results=stage_results,
            findings=all_findings,
            ai_summary=None,
            execution_time=elapsed,
        )
