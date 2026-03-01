"""Prior authorization result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.prior_auth.models.response import PriorAuthResponse


class PADeterminationResult(BaseModel):
    """Result of determining whether prior authorization is required."""

    model_config = ConfigDict(frozen=True, strict=False)

    required: bool
    confidence: str
    reason: str
    auth_or_cert_indicator: str | None = None
    free_text_indicators: list[str] = []


class PriorAuthResult(BaseModel):
    """Aggregated result from the prior authorization pipeline."""

    model_config = ConfigDict(frozen=True, strict=False)

    approved: bool | None = None
    response: PriorAuthResponse | None = None
    findings: list[Finding] = []
    ai_summary: str | None = None
    authorization_number: str | None = None
    raw_response: dict[str, Any] | None = None
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True when zero ERROR-severity findings exist."""
        return not any(f.severity == Severity.ERROR for f in self.findings)
