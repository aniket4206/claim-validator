"""PAProcedureValidator — CPT/HCPCS procedure code validation for PA requests.

Thin wrapper around ``shared.validators.validate_procedure``.
"""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_procedure
from claim_validator.validators.base import BaseValidator


class PAProcedureValidator(BaseValidator):
    """Validates CPT/HCPCS procedure codes on PA requests."""

    name = "PAProcedureValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings = []

        if not request.service_lines:
            return self._make_output(findings)

        for idx, line in enumerate(request.service_lines, start=1):
            code = line.cpt_code.strip() if line.cpt_code else ""
            if not code:
                continue
            shared_findings = validate_procedure(
                [code], field_name="cpt_code", code_prefix="PA_",
            )
            for f in shared_findings:
                update: dict = {"line_number": idx}
                # PA treats unknown procedures as ERROR (shared uses WARNING)
                if f.severity == Severity.WARNING:
                    update["severity"] = Severity.ERROR
                findings.append(f.model_copy(update=update))

        return self._make_output(findings)
