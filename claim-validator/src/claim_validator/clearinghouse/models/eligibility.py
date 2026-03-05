"""Clearinghouse eligibility response model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ClearinghouseEligibilityResponse(BaseModel):
    """Eligibility verification response from a clearinghouse.

    Attributes:
        status: Response status string from the clearinghouse.
        eligible: Whether the patient is eligible for coverage, or None if unknown.
        reference_id: Clearinghouse-assigned reference identifier.
        plan_info: Coverage and plan details from the 271 response.
        raw_response: Full provider response for debugging.
        errors: List of error messages from the clearinghouse.
    """

    model_config = ConfigDict(frozen=True)

    status: str
    eligible: bool | None = None
    reference_id: str | None = None
    plan_info: dict[str, Any] = {}
    raw_response: dict[str, Any] = {}
    errors: list[str] = []
