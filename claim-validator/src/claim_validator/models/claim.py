"""Claim data models — ClaimData, ClaimLineData, DiagnosisCode."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DiagnosisCode(BaseModel):
    """ICD-10 diagnosis code with pointer position and type."""

    model_config = ConfigDict(frozen=True, strict=False)

    code: str
    pointer: int = 1
    type: str = "principal"


class ClaimLineData(BaseModel):
    """Single service line on a CMS-1500 claim."""

    model_config = ConfigDict(frozen=True, strict=False)

    procedure_code: str
    modifiers: list[str] = []
    diagnosis_pointers: list[int] = []
    charge_amount: float
    units: float = 1.0
    service_date_from: str | None = None
    service_date_to: str | None = None
    place_of_service: str | None = None
    rendering_provider_npi: str | None = None


class ClaimData(BaseModel):
    """CMS-1500 professional healthcare claim."""

    model_config = ConfigDict(frozen=True, strict=False)

    # Provider information
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    rendering_provider_npi: str | None = None

    # Subscriber / insurance
    subscriber_id: str | None = None
    subscriber_first_name: str | None = None
    subscriber_last_name: str | None = None
    subscriber_dob: str | None = None
    subscriber_gender: str | None = None

    # Patient demographics
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: str | None = None
    patient_gender: str | None = None
    patient_relationship: str | None = None

    # Payer
    payer_id: str | None = None
    payer_name: str | None = None

    # Claim metadata
    claim_type: str = "professional"
    place_of_service: str | None = None
    total_charge: float | None = None
    filing_date: str | None = None

    # Clinical data
    diagnosis_codes: list[DiagnosisCode] = []
    lines: list[ClaimLineData] = []
