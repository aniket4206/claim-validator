"""Payer ID validator — validates payer ID against bundled payer directory.

Thin wrapper around ``shared.validators.validate_payer_id``.
"""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_payer_id
from claim_validator.validators.base import BaseValidator


class PayerIDValidator(BaseValidator):
    """Validates payer ID exists in bundled payer directory."""

    name = "PayerIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_payer_id(
            claim.payer_id, field_name="payer_id", code_prefix="ELIG_",
        )
        findings = []
        for f in shared_findings:
            if f.code == "ELIG_MISSING_PAYER_ID":
                continue  # payer_id is required on the model
            update: dict = {}
            # Eligibility treats unknown payer as ERROR (shared uses WARNING)
            if f.severity == Severity.WARNING:
                update["severity"] = Severity.ERROR
            # Add payer_id_length context for backward compatibility
            update["context"] = {"payer_id_length": len(claim.payer_id.strip())}
            findings.append(f.model_copy(update=update))
        return self._make_output(findings)
