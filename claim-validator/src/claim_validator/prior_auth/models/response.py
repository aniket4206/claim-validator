"""Prior authorization response models."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.prior_auth.constants import CertificationActionCode


class ServiceLineDecision(BaseModel):
    """Per-service-line authorization decision from 278 response."""

    model_config = ConfigDict(frozen=True, strict=False)

    cpt_code: str | None = None
    action_code: CertificationActionCode | None = None
    authorization_number: str | None = None
    approved_quantity: int | None = None
    denied_reason: str | None = None


class PriorAuthError(BaseModel):
    """AAA reject error from 278 response."""

    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    message: str = ""
    suggested_fix: str = ""


class PriorAuthResponse(BaseModel):
    """Parsed X12 278 prior authorization response."""

    model_config = ConfigDict(frozen=True, strict=False)

    action_code: CertificationActionCode | None = None
    authorization_number: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    decision_reason_code: str | None = None
    decision_reason_description: str | None = None
    service_line_decisions: list[ServiceLineDecision] = []
    errors: list[PriorAuthError] = []
    raw_response: dict[str, Any] | None = None

    @property
    def is_approved(self) -> bool:
        """True when action code is A1 (Certified in Total)."""
        return self.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL

    @property
    def is_denied(self) -> bool:
        """True when action code is A3 (Not Certified)."""
        return self.action_code == CertificationActionCode.NOT_CERTIFIED

    @property
    def is_pended(self) -> bool:
        """True when action code is A4 (Pended)."""
        return self.action_code == CertificationActionCode.PENDED
