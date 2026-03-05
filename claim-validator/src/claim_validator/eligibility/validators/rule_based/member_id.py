"""Member ID validator — validates subscriber ID format for eligibility requests.

Thin wrapper around ``shared.validators.validate_member_id``.
"""

from __future__ import annotations

from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_member_id
from claim_validator.validators.base import BaseValidator


class MemberIDValidator(BaseValidator):
    """Validates subscriber/member ID format for eligibility requests."""

    name = "MemberIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_member_id(
            claim.subscriber_id, field_name="subscriber_id", code_prefix="ELIG_",
        )
        # Remap MISSING → INVALID (eligibility treats empty the same as invalid format)
        findings = []
        for f in shared_findings:
            if f.code == "ELIG_MISSING_MEMBER_ID":
                findings.append(f.model_copy(update={"code": "ELIG_INVALID_MEMBER_ID"}))
            else:
                findings.append(f)
        return self._make_output(findings)
