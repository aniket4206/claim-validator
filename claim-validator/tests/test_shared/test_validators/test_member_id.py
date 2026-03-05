"""Tests for shared member ID validation pure function."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.shared.validators.member_id import validate_member_id


class TestValidateMemberID:
    """Tests for validate_member_id() pure function."""

    # --- Valid member IDs ---

    def test_valid_alphanumeric(self) -> None:
        assert validate_member_id("ABC12345", "subscriber_id") == []

    def test_valid_just_two_chars(self) -> None:
        assert validate_member_id("AB", "subscriber_id") == []

    def test_valid_mixed_special(self) -> None:
        assert validate_member_id("AB-123-XY", "subscriber_id") == []

    # --- Missing member ID ---

    def test_none_member_id(self) -> None:
        findings = validate_member_id(None, "subscriber_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_MEMBER_ID"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "subscriber_id"

    def test_empty_member_id(self) -> None:
        findings = validate_member_id("", "subscriber_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_MEMBER_ID"

    def test_whitespace_member_id(self) -> None:
        findings = validate_member_id("   ", "subscriber_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_MEMBER_ID"

    # --- Insufficient alphanumeric ---

    def test_single_char_fails_default(self) -> None:
        findings = validate_member_id("A", "subscriber_id")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_MEMBER_ID"
        assert findings[0].severity == Severity.ERROR

    def test_only_special_chars(self) -> None:
        findings = validate_member_id("---", "subscriber_id")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_MEMBER_ID"
        assert findings[0].context is not None
        assert findings[0].context["alphanumeric_count"] == 0

    def test_context_includes_metadata(self) -> None:
        findings = validate_member_id("A", "subscriber_id")
        assert findings[0].context is not None
        assert findings[0].context["alphanumeric_count"] == 1
        assert findings[0].context["id_length"] == 1

    # --- Custom min_alphanumeric ---

    def test_custom_min_one(self) -> None:
        assert validate_member_id("A", "subscriber_id", min_alphanumeric=1) == []

    def test_custom_min_three(self) -> None:
        findings = validate_member_id("AB", "subscriber_id", min_alphanumeric=3)
        assert len(findings) == 1
        assert findings[0].code == "INVALID_MEMBER_ID"

    # --- Whitespace trimming ---

    def test_whitespace_trimmed_valid(self) -> None:
        assert validate_member_id(" ABC123 ", "subscriber_id") == []

    # --- code_prefix ---

    def test_code_prefix_missing(self) -> None:
        findings = validate_member_id(None, "member_id", code_prefix="PA_")
        assert findings[0].code == "PA_MISSING_MEMBER_ID"

    def test_code_prefix_invalid(self) -> None:
        findings = validate_member_id("A", "member_id", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_INVALID_MEMBER_ID"

    # --- field_name passthrough ---

    def test_field_name_in_finding(self) -> None:
        findings = validate_member_id(None, "subscriber.member_id")
        assert findings[0].field_name == "subscriber.member_id"

    # --- PHI safety ---

    def test_no_phi_in_message(self) -> None:
        test_id = "XYZ789"
        findings = validate_member_id("A", "subscriber_id")
        for f in findings:
            assert test_id not in f.message

    def test_no_phi_value_in_message(self) -> None:
        test_id = "A"
        findings = validate_member_id(test_id, "subscriber_id")
        for f in findings:
            # Message should reference field name, not the actual ID value
            assert "subscriber_id" in f.field_name

    # --- Statelessness ---

    def test_stateless_multiple_calls(self) -> None:
        r1 = validate_member_id("ABC123", "id")
        r2 = validate_member_id(None, "id")
        r3 = validate_member_id("ABC123", "id")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []
