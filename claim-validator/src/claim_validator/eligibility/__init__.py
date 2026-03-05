"""Eligibility verification module for claim-validator."""

from __future__ import annotations

from claim_validator.eligibility._api import check_eligibility
from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.deidentifier import EligibilityDeidentifier
from claim_validator.eligibility.models import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResult,
)
from claim_validator.eligibility.pipeline import EligibilityPipeline
from claim_validator.eligibility.validators.ai.interpreter import (
    EligibilityInterpreterAI,
)

__all__ = [
    "AAAError",
    "BenefitInfo",
    "check_eligibility",
    "CoverageInfo",
    "CoverageStatus",
    "DeidentifiedAAAError",
    "DeidentifiedCoverageInfo",
    "DeidentifiedEligibilityResponse",
    "EligibilityDeidentifier",
    "EligibilityInterpreterAI",
    "EligibilityPipeline",
    "EligibilityRequest",
    "EligibilityResponse",
    "EligibilityResult",
]
