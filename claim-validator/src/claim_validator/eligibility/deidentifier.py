"""EligibilityDeidentifier — HIPAA Safe Harbor de-identification for eligibility responses.

Delegates year extraction to ``BaseDeidentifier``. Nested AAA error
stripping remains domain-specific.
"""

from __future__ import annotations

from claim_validator.eligibility.models.deidentified import (
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
)
from claim_validator.eligibility.models.response import (
    AAAError,
    CoverageInfo,
    EligibilityResponse,
)
from claim_validator.shared.deidentifier import (
    ELIGIBILITY_DEID_CONFIG,
    BaseDeidentifier,
)

_base = BaseDeidentifier(ELIGIBILITY_DEID_CONFIG)


class EligibilityDeidentifier:
    """Strips PHI from an EligibilityResponse for LLM consumption.

    Stateless — safe for concurrent use, deterministic output.
    """

    @classmethod
    def deidentify(
        cls,
        response: EligibilityResponse,
    ) -> DeidentifiedEligibilityResponse:
        """De-identify an eligibility response.

        Strips: plan_name, group_number, full dates (→ year only),
        AAA error messages, raw_response.
        Retains: eligible, coverage status, benefit amounts/codes/flags,
        rejection codes, follow-up codes.
        """
        coverage = cls._deidentify_coverage(response.coverage)
        errors = [cls._deidentify_error(e) for e in response.errors]
        return DeidentifiedEligibilityResponse(
            eligible=response.eligible,
            coverage=coverage,
            benefits=list(response.benefits),
            errors=errors,
        )

    @classmethod
    def _deidentify_coverage(
        cls,
        cov: CoverageInfo | None,
    ) -> DeidentifiedCoverageInfo | None:
        """Strip PHI from coverage info — dates to year only."""
        if cov is None:
            return None
        return DeidentifiedCoverageInfo(
            status=cov.status,
            effective_year=_base.extract_year(cov.effective_date),
            termination_year=_base.extract_year(cov.termination_date),
        )

    @staticmethod
    def _deidentify_error(error: AAAError) -> DeidentifiedAAAError:
        """Strip message from AAA error — retain codes only."""
        return DeidentifiedAAAError(
            rejection_code=error.rejection_code,
            follow_up_code=error.follow_up_code,
        )
