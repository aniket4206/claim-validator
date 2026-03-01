"""De-identified prior authorization models for LLM path."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.prior_auth.constants import CertificationActionCode


class DeidentifiedPriorAuthResponse(BaseModel):
    """PHI-stripped prior authorization response safe for LLM consumption.

    Full implementation in Story 4.1. This stub establishes the type
    so that type-driven enforcement can distinguish raw vs de-identified
    responses at the type level.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    action_code: CertificationActionCode | None = None
    decision_reason_code: str | None = None
    decision_reason_description: str | None = None
    service_type_codes: list[str] = []
    cpt_codes: list[str] = []
    aaa_reject_codes: list[str] = []
    raw_safe_fields: dict[str, Any] | None = None
