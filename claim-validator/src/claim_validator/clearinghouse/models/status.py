"""Clearinghouse claim status response model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ClaimStatusResponse(BaseModel):
    """Claim status response from a clearinghouse (276/277).

    Attributes:
        status: Response status string from the clearinghouse.
        claim_status: Claim adjudication status, or None if not available.
        adjudication_date: Date of adjudication, or None if not available.
        reference_id: Clearinghouse-assigned reference identifier.
        raw_response: Full provider response for debugging.
        errors: List of error messages from the clearinghouse.
    """

    model_config = ConfigDict(frozen=True)

    status: str
    claim_status: str | None = None
    adjudication_date: str | None = None
    reference_id: str | None = None
    raw_response: dict[str, Any] = {}
    errors: list[str] = []
