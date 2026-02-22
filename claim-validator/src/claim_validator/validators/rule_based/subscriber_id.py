"""SubscriberIDValidator — subscriber/insurance ID format validation."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# At least one alphanumeric character
_SUBSCRIBER_ID_PATTERN = re.compile(r"[A-Za-z0-9]")


class SubscriberIDValidator(BaseValidator):
    """Validates subscriber/insurance ID format."""

    name = "SubscriberIDValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        sub_id = claim.subscriber_id
        if not sub_id or not sub_id.strip():
            return self._make_output(findings)  # CompletenessValidator handles required

        if not _SUBSCRIBER_ID_PATTERN.search(sub_id.strip()):
            findings.append(
                self._make_finding(
                    code="INVALID_SUBSCRIBER_ID_FORMAT",
                    message=(
                        "Subscriber ID in 'subscriber_id' must contain"
                        " at least one alphanumeric character"
                    ),
                    severity=Severity.ERROR,
                    field_name="subscriber_id",
                    suggestion=(
                        "Verify the subscriber/insurance ID from the"
                        " insurance card (CMS-1500 Box 1a)"
                    ),
                )
            )

        return self._make_output(findings)
