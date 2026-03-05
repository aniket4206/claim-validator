"""PANPIValidator — NPI validation for prior authorization requests.

Thin wrapper around ``shared.validators.validate_npi``.
"""

from __future__ import annotations

from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_npi
from claim_validator.validators.base import BaseValidator


class PANPIValidator(BaseValidator):
    """Validates requester NPI on prior authorization requests."""

    name = "PANPIValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_npi(
            request.requester_npi, field_name="requester_npi", code_prefix="PA_",
        )
        # Filter MISSING — empty/whitespace NPI is skipped (CompletenessValidator handles presence)
        findings = [f for f in shared_findings if f.code != "PA_MISSING_NPI"]
        return self._make_output(findings)
