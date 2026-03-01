"""Member ID validator — validates subscriber ID format for eligibility requests."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_MIN_ALPHANUMERIC = 2
_ALPHANUMERIC_PATTERN = re.compile(r"[A-Za-z0-9]")


class MemberIDValidator(BaseValidator):
    """Validates subscriber/member ID format for eligibility requests."""

    name = "MemberIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        sub_id = claim.subscriber_id.strip()

        alphanumeric_count = len(_ALPHANUMERIC_PATTERN.findall(sub_id))
        if alphanumeric_count < _MIN_ALPHANUMERIC:
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_MEMBER_ID",
                    message="Subscriber ID must contain at least 2 alphanumeric characters",
                    severity=Severity.ERROR,
                    field_name="subscriber_id",
                    suggestion="Verify the member/subscriber ID from the insurance card",
                    context={
                        "alphanumeric_count": alphanumeric_count,
                        "id_length": len(sub_id),
                    },
                )
            )

        return self._make_output(findings)
