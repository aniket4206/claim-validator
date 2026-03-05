"""Batch eligibility request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BatchEligibilityItem(BaseModel):
    """Single eligibility check item within a batch request."""

    model_config = ConfigDict(frozen=True)

    payer_id: str
    npi: str
    subscriber_id: str
    first_name: str
    last_name: str
    dob: str
    service_types: list[str] = []
    organization_name: str | None = None
    submitter_transaction_id: str | None = None
    external_patient_id: str | None = None
    gender: str | None = None
    date_of_service: str | None = None


class BatchEligibilityRequest(BaseModel):
    """Batch eligibility request — wraps multiple items."""

    model_config = ConfigDict(frozen=True)

    name: str
    items: list[BatchEligibilityItem]


class BatchItemStatus(BaseModel):
    """Status of a single item within a batch."""

    model_config = ConfigDict(frozen=True)

    submitter_transaction_id: str
    status: str
    eligibility_response: dict[str, Any] | None = None
    errors: list[str] = []


class BatchEligibilityResponse(BaseModel):
    """Response from batch eligibility submission or status poll."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    status: str
    total_items: int = 0
    completed_items: int = 0
    items: list[BatchItemStatus] = []
    raw_response: dict[str, Any] = {}
