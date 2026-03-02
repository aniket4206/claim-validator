"""De-identified eligibility response models for LLM path."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.models.response import BenefitInfo


class DeidentifiedCoverageInfo(BaseModel):
    """De-identified coverage — dates reduced to year only, identifiers stripped."""

    model_config = ConfigDict(frozen=True, strict=False)

    status: CoverageStatus = CoverageStatus.UNKNOWN
    effective_year: int | None = None
    termination_year: int | None = None
    # plan_name STRIPPED — may embed group/employer identifiers
    # group_number STRIPPED — group-specific identifier


class DeidentifiedAAAError(BaseModel):
    """De-identified AAA error — codes retained, message stripped."""

    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    # message STRIPPED — may contain subscriber-identifying info


class DeidentifiedEligibilityResponse(BaseModel):
    """PHI-stripped eligibility response safe for LLM consumption.

    Created exclusively by ``EligibilityDeidentifier.deidentify()``.
    Contains only clinically relevant, non-PHI data.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    eligible: bool | None = None
    coverage: DeidentifiedCoverageInfo | None = None
    benefits: list[BenefitInfo] = []
    errors: list[DeidentifiedAAAError] = []
    # raw_response STRIPPED — unknown PHI risk

    @property
    def is_deidentified(self) -> Literal[True]:
        """Type-level marker that this response is de-identified."""
        return True
