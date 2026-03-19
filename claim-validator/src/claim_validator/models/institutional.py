"""Institutional (UB-04 / 837I) claim data models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OccurrenceCode(BaseModel):
    """UB-04 occurrence code with associated date."""

    model_config = ConfigDict(frozen=True, strict=False)

    code: str
    date: str | None = None


class ValueCode(BaseModel):
    """UB-04 value code with associated amount."""

    model_config = ConfigDict(frozen=True, strict=False)

    code: str
    amount: float | None = None


class InstitutionalServiceLine(BaseModel):
    """Single service line on a UB-04 institutional claim."""

    model_config = ConfigDict(frozen=True, strict=False)

    revenue_code: str
    hcpcs_code: str | None = None
    modifiers: list[str] = []
    rate: float | None = None
    units: float = 1.0
    service_date_from: str | None = None
    service_date_to: str | None = None


class InstitutionalClaimData(BaseModel):
    """UB-04 institutional (hospital / facility) healthcare claim.

    Represents 837I claims for inpatient, outpatient, SNF, and other
    institutional billing.  Includes all UB-04 specific fields alongside
    shared demographics and payer fields.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    # Claim type identifier
    claim_type: str = "institutional"

    # Facility / billing info
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    facility_name: str | None = None

    # Attending / operating physicians
    attending_physician_npi: str | None = None
    operating_physician_npi: str | None = None

    # UB-04 specific fields
    bill_type_code: str | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    admission_type_code: str | None = None
    admission_source_code: str | None = None
    patient_status_code: str | None = None
    drg_code: str | None = None

    # UB-04 code lists
    condition_codes: list[str] = []
    occurrence_codes: list[OccurrenceCode] = []
    value_codes: list[ValueCode] = []

    # Service lines
    service_lines: list[InstitutionalServiceLine] = []

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

    # Monetary
    total_charge_amount: float | None = None

    # Dates
    statement_from_date: str | None = None
    statement_to_date: str | None = None
