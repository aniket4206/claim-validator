"""Pre-claim orchestrator result model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from claim_validator.constants import Severity
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import Finding
from claim_validator.prior_auth.models.result import PADeterminationResult, PriorAuthResult


class PreClaimResult(BaseModel):
    """Unified result from the pre-claim orchestrator."""

    model_config = ConfigDict(frozen=True, strict=False)

    ready_to_submit: bool = False
    eligibility: EligibilityResult | None = None
    pa_determination: PADeterminationResult | None = None
    pa_result: PriorAuthResult | None = None
    findings: list[Finding] = []
    ai_summary: str | None = None
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only when zero ERROR-severity findings exist."""
        return not any(f.severity == Severity.ERROR for f in self.findings)
