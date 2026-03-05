"""PriorAuthDeidentifier — HIPAA Safe Harbor de-identification for prior auth responses.

Delegates year extraction to ``BaseDeidentifier``. Nested service-line and
error stripping remains domain-specific.
"""

from __future__ import annotations

from claim_validator.prior_auth.models.deidentified import (
    DeidentifiedPriorAuthError,
    DeidentifiedPriorAuthResponse,
    DeidentifiedServiceLineDecision,
)
from claim_validator.prior_auth.models.response import (
    PriorAuthError,
    PriorAuthResponse,
    ServiceLineDecision,
)
from claim_validator.shared.deidentifier import (
    PA_DEID_CONFIG,
    BaseDeidentifier,
)

_base = BaseDeidentifier(PA_DEID_CONFIG)


class PriorAuthDeidentifier:
    """Strips PHI from a PriorAuthResponse for LLM consumption.

    Stateless — safe for concurrent use, deterministic output.
    """

    @classmethod
    def deidentify(
        cls,
        response: PriorAuthResponse,
    ) -> DeidentifiedPriorAuthResponse:
        """De-identify a prior authorization response.

        Strips: authorization_number, full dates (-> year only),
        decision_reason_description, raw_response, service-line auth numbers,
        service-line denied reasons, error messages/suggested_fix.
        Retains: action_code, decision_reason_code, service-line CPT/action/quantity,
        error rejection/follow-up codes.
        """
        service_lines = [
            cls._deidentify_service_line(sld)
            for sld in response.service_line_decisions
        ]
        errors = [cls._deidentify_error(e) for e in response.errors]
        return DeidentifiedPriorAuthResponse(
            action_code=response.action_code,
            decision_reason_code=response.decision_reason_code,
            effective_year=_base.extract_year(response.effective_date),
            expiration_year=_base.extract_year(response.expiration_date),
            service_line_decisions=service_lines,
            errors=errors,
        )

    @staticmethod
    def _deidentify_service_line(
        sld: ServiceLineDecision,
    ) -> DeidentifiedServiceLineDecision:
        """Strip PHI from service-line decision — retain codes and quantity only."""
        return DeidentifiedServiceLineDecision(
            cpt_code=sld.cpt_code,
            action_code=sld.action_code,
            approved_quantity=sld.approved_quantity,
        )

    @staticmethod
    def _deidentify_error(error: PriorAuthError) -> DeidentifiedPriorAuthError:
        """Strip message/suggested_fix from error — retain codes only."""
        return DeidentifiedPriorAuthError(
            rejection_code=error.rejection_code,
            follow_up_code=error.follow_up_code,
        )
