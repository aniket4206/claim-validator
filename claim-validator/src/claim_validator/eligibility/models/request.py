"""Eligibility request model — flat, frozen Pydantic model for 270 transactions."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EligibilityRequest(BaseModel):
    """Eligibility verification request.

    Flat structure for the X12 270 eligibility inquiry.  All fields map
    directly to 270 transaction segments.  ``strict=False`` allows string
    coercion (e.g. ``"1985-03-15"`` → ``date``).
    """

    model_config = ConfigDict(frozen=True, strict=False)

    # Provider
    provider_npi: str
    provider_taxonomy: str | None = None

    # Payer
    payer_id: str

    # Subscriber (required)
    subscriber_id: str
    subscriber_first_name: str
    subscriber_last_name: str
    subscriber_dob: date

    # Service
    service_type_code: str = "30"  # Default: health benefit plan coverage
    date_of_service: date | None = None

    # Dependent / Patient (optional — when patient differs from subscriber)
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: date | None = None
    relationship_code: str | None = None
