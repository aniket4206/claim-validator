"""Eligibility response models — nested, frozen Pydantic models for 271 data."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.eligibility.constants import CoverageStatus


class CoverageInfo(BaseModel):
    """Coverage details from 271 response."""

    model_config = ConfigDict(frozen=True, strict=False)

    status: CoverageStatus = CoverageStatus.UNKNOWN
    effective_date: date | None = None
    termination_date: date | None = None
    plan_name: str | None = None
    group_number: str | None = None


class BenefitInfo(BaseModel):
    """Individual benefit from 271 EB segment."""

    model_config = ConfigDict(frozen=True, strict=False)

    service_type_code: str | None = None
    service_type_name: str | None = None
    copay: float | None = None
    coinsurance: float | None = None
    deductible: float | None = None
    in_network: bool | None = None
    prior_auth_required: bool | None = None


class AAAError(BaseModel):
    """AAA rejection from 271 response."""

    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    message: str = ""


class EligibilityResponse(BaseModel):
    """Structured 271 eligibility response."""

    model_config = ConfigDict(frozen=True, strict=False)

    eligible: bool | None = None
    coverage: CoverageInfo | None = None
    benefits: list[BenefitInfo] = []
    errors: list[AAAError] = []
    raw_response: dict[str, Any] = {}
