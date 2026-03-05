"""De-identified prior authorization models for LLM path."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from claim_validator.prior_auth.constants import CertificationActionCode


class DeidentifiedServiceLineDecision(BaseModel):
    """De-identified service-line decision — auth number and denied reason stripped."""

    model_config = ConfigDict(frozen=True, strict=False)

    cpt_code: str | None = None
    action_code: CertificationActionCode | None = None
    approved_quantity: int | None = None
    # authorization_number STRIPPED — patient-specific identifier
    # denied_reason STRIPPED — freetext may embed names


class DeidentifiedPriorAuthError(BaseModel):
    """De-identified AAA error — codes retained, message/suggested_fix stripped."""

    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    # message STRIPPED — may contain subscriber-identifying info
    # suggested_fix STRIPPED — may reference patient details


class DeidentifiedPriorAuthResponse(BaseModel):
    """PHI-stripped prior authorization response safe for LLM consumption.

    Created exclusively by ``PriorAuthDeidentifier.deidentify()``.
    Contains only clinically relevant, non-PHI data.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    action_code: CertificationActionCode | None = None
    decision_reason_code: str | None = None
    effective_year: int | None = None
    expiration_year: int | None = None
    service_line_decisions: list[DeidentifiedServiceLineDecision] = []
    errors: list[DeidentifiedPriorAuthError] = []
    # authorization_number STRIPPED — patient-specific identifier
    # decision_reason_description STRIPPED — freetext may embed names
    # raw_response STRIPPED — unknown PHI risk

    @property
    def is_deidentified(self) -> Literal[True]:
        """Type-level marker that this response is de-identified."""
        return True
