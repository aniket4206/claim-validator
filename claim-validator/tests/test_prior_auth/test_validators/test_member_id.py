"""Tests for PAMemberIDValidator."""

from __future__ import annotations

from datetime import date

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.member_id import (
    PAMemberIDValidator,
)


def _make_request(member_id: str) -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id=member_id,
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
    )


class TestPAMemberIDValidatorValid:
    """AC3: Non-empty member ID → zero findings."""

    def test_valid_member_id(self) -> None:
        v = PAMemberIDValidator()
        result = v.validate(_make_request("MEM001"))
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PAMemberIDValidator()
        result = v.validate(_make_request("MEM001"))
        assert result.validator_name == "PAMemberIDValidator"

    def test_numeric_member_id(self) -> None:
        v = PAMemberIDValidator()
        result = v.validate(_make_request("123456789"))
        assert len(result.findings) == 0


class TestPAMemberIDValidatorInvalid:
    """AC4: Empty/whitespace member ID → PA_MISSING_MEMBER_ID."""

    def test_empty_string(self) -> None:
        v = PAMemberIDValidator()
        result = v.validate(_make_request(""))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_MISSING_MEMBER_ID"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "subscriber.member_id"

    def test_whitespace_only(self) -> None:
        v = PAMemberIDValidator()
        result = v.validate(_make_request("   "))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_MISSING_MEMBER_ID"

    def test_message_no_phi(self) -> None:
        """AC11: Message references field name, not actual value."""
        v = PAMemberIDValidator()
        result = v.validate(_make_request(""))
        assert "subscriber.member_id" in result.findings[0].message
