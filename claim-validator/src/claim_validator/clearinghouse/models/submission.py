"""Clearinghouse claim submission result model."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SubmissionResult(BaseModel):
    """Result of a claim submission to a clearinghouse.

    Attributes:
        status: Submission status string from the clearinghouse.
        accepted: Whether the claim was accepted for processing.
        reference_id: Clearinghouse-assigned reference identifier.
        raw_response: Full provider response for debugging.
        errors: List of error messages from the clearinghouse.
    """

    model_config = ConfigDict(frozen=True)

    status: str
    accepted: bool
    reference_id: str | None = None
    raw_response: dict[str, Any] = {}
    errors: list[str] = []
