"""Eligibility verification module for claim-validator."""

from __future__ import annotations

from claim_validator.eligibility._api import check_eligibility
from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.models import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResult,
)
from claim_validator.eligibility.pipeline import EligibilityPipeline

__all__ = [
    "AAAError",
    "BenefitInfo",
    "check_eligibility",
    "CoverageInfo",
    "CoverageStatus",
    "EligibilityPipeline",
    "EligibilityRequest",
    "EligibilityResponse",
    "EligibilityResult",
]
