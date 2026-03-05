"""PAMemberIDValidator — subscriber member ID validation for PA requests.

Thin wrapper around ``shared.validators.validate_member_id``.
"""

from __future__ import annotations

from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.validators import validate_member_id
from claim_validator.validators.base import BaseValidator


class PAMemberIDValidator(BaseValidator):
    """Validates subscriber member ID presence on PA requests."""

    name = "PAMemberIDValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        shared_findings = validate_member_id(
            request.subscriber.member_id,
            field_name="subscriber.member_id",
            code_prefix="PA_",
        )
        # PA only checks presence — filter out format findings
        findings = [f for f in shared_findings if f.code != "PA_INVALID_MEMBER_ID"]
        return self._make_output(findings)
