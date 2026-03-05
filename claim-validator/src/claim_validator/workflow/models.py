"""Workflow result models — StageResult and WorkflowResult."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from claim_validator.constants import Severity
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import Finding, PipelineResult
from claim_validator.prior_auth.models.result import (
    PADeterminationResult,
    PriorAuthResult,
)


class StageResult(BaseModel):
    """Outcome of a single workflow stage."""

    model_config = ConfigDict(frozen=True, strict=False)

    stage_name: str
    passed: bool
    skipped: bool = False
    skip_reason: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    execution_time: float = 0.0
    detail: Any = None


class WorkflowResult(BaseModel):
    """Aggregated result from the full workflow pipeline."""

    model_config = ConfigDict(frozen=True, strict=False)

    eligibility: EligibilityResult | None = None
    pa_determination: PADeterminationResult | None = None
    prior_auth: PriorAuthResult | None = None
    claim_validation: PipelineResult | None = None
    stopped_at: str | None = None
    stage_results: list[StageResult] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    ai_summary: str | None = None
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only if zero ERROR-severity findings."""
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def stage_times(self) -> dict[str, float]:
        """Map of stage_name → execution_time for each stage."""
        return {sr.stage_name: sr.execution_time for sr in self.stage_results}
