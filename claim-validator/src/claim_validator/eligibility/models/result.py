"""Eligibility result model — pipeline output with computed ``passed`` property."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.constants import Severity
from claim_validator.eligibility.models.response import EligibilityResponse
from claim_validator.models.results import Finding


class EligibilityResult(BaseModel):
    """Complete result from the eligibility verification pipeline."""

    model_config = ConfigDict(frozen=True, strict=False)

    eligible: bool | None = None
    response: EligibilityResponse | None = None
    findings: list[Finding] = []
    ai_summary: str | None = None
    raw_response: dict[str, Any] | None = None
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only when zero ERROR-severity findings exist."""
        return not any(f.severity == Severity.ERROR for f in self.findings)
