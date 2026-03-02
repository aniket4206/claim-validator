"""Eligibility data models."""

from __future__ import annotations

from claim_validator.eligibility.models.deidentified import (
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
)
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.response import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityResponse,
)
from claim_validator.eligibility.models.result import EligibilityResult

__all__ = [
    "AAAError",
    "BenefitInfo",
    "CoverageInfo",
    "DeidentifiedAAAError",
    "DeidentifiedCoverageInfo",
    "DeidentifiedEligibilityResponse",
    "EligibilityRequest",
    "EligibilityResponse",
    "EligibilityResult",
]
