"""SubscriberIDValidator — subscriber/insurance ID format validation.

Thin wrapper around ``shared.validators.validate_member_id``.
"""

from __future__ import annotations

from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.shared.validators import validate_member_id
from claim_validator.validators.base import BaseValidator


class SubscriberIDValidator(BaseValidator):
    """Validates subscriber/insurance ID format."""

    name = "SubscriberIDValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        sub_id = claim.subscriber_id
        if not sub_id or not sub_id.strip():
            return self._make_output([])  # CompletenessValidator handles required

        # Claims requires only 1 alphanumeric char (shared default is 2)
        shared_findings = validate_member_id(
            sub_id, field_name="subscriber_id", min_alphanumeric=1,
        )
        findings: list[Finding] = []
        for f in shared_findings:
            if f.code == "MISSING_MEMBER_ID":
                continue  # Already filtered above
            # Remap shared code → domain code for backward compatibility
            findings.append(f.model_copy(update={
                "code": "INVALID_SUBSCRIBER_ID_FORMAT",
                "message": (
                    "Subscriber ID in 'subscriber_id' must contain"
                    " at least one alphanumeric character"
                ),
                "suggestion": (
                    "Verify the subscriber/insurance ID from the"
                    " insurance card (CMS-1500 Box 1a)"
                ),
            }))

        return self._make_output(findings)
