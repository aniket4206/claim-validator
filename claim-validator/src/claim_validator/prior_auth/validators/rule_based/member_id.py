"""PAMemberIDValidator — subscriber member ID validation for PA requests."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class PAMemberIDValidator(BaseValidator):
    """Validates subscriber member ID presence on PA requests."""

    name = "PAMemberIDValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []
        member_id = request.subscriber.member_id

        if not member_id or not member_id.strip():
            findings.append(
                self._make_finding(
                    code="PA_MISSING_MEMBER_ID",
                    message=(
                        "Subscriber member ID in 'subscriber.member_id' "
                        "is required and must not be empty"
                    ),
                    severity=Severity.ERROR,
                    field_name="subscriber.member_id",
                    suggestion="Provide the subscriber's member ID from their insurance card",
                )
            )

        return self._make_output(findings)
