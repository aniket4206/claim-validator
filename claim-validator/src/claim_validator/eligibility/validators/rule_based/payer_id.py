"""Payer ID validator — validates payer ID against bundled payer directory."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.code_tables.payer_directory import get_payer_directory
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator


class PayerIDValidator(BaseValidator):
    """Validates payer ID exists in bundled payer directory."""

    name = "PayerIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        result = get_payer_directory(claim.payer_id)
        if result is None:
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_PAYER",
                    message="Payer ID not found in known payer directory",
                    severity=Severity.ERROR,
                    field_name="payer_id",
                    suggestion="Verify payer ID at https://www.stedi.com/app/payers",
                    context={"payer_id_length": len(claim.payer_id.strip())},
                )
            )
        return self._make_output(findings)
