"""Prior authorization request models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from claim_validator.prior_auth.constants import (
    CertificationTypeCode,
    RequestCategoryCode,
)


class SubscriberInfo(BaseModel):
    """Subscriber (insured person) information for PA request."""

    model_config = ConfigDict(frozen=True, strict=False)

    member_id: str
    first_name: str
    last_name: str
    dob: date


class PatientInfo(BaseModel):
    """Patient information when patient differs from subscriber (dependent)."""

    model_config = ConfigDict(frozen=True, strict=False)

    first_name: str
    last_name: str
    dob: date
    gender: str | None = None
    relationship: str | None = None


class ServiceLine(BaseModel):
    """Single service line within a prior authorization request."""

    model_config = ConfigDict(frozen=True, strict=False)

    cpt_code: str
    quantity: int = 1
    from_date: date | None = None
    to_date: date | None = None
    place_of_service_code: str | None = None


class PriorAuthRequest(BaseModel):
    """X12 278 prior authorization request data."""

    model_config = ConfigDict(frozen=True, strict=False)

    requester_npi: str
    requester_taxonomy: str | None = None
    payer_id: str | None = None
    subscriber: SubscriberInfo
    patient: PatientInfo | None = None
    diagnosis_codes: list[str] = []
    service_lines: list[ServiceLine] = []
    request_category_code: RequestCategoryCode = RequestCategoryCode.HEALTH_SERVICES_REVIEW
    certification_type_code: CertificationTypeCode = CertificationTypeCode.INITIAL
    clinical_info: str | None = None
