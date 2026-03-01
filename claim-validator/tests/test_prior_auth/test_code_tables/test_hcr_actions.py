"""Tests for HCR action code lookups."""

from __future__ import annotations

from claim_validator.prior_auth.code_tables.hcr_actions import get_hcr_action_code


class TestGetHcrActionCode:
    """Tests for get_hcr_action_code() lookup function."""

    def test_approved_a1(self) -> None:
        result = get_hcr_action_code("A1")
        assert result is not None
        assert result["description"] == "Certified in Total"
        assert result["category"] == "approved"
        assert "suggested_action" in result

    def test_partial_a2(self) -> None:
        result = get_hcr_action_code("A2")
        assert result is not None
        assert result["description"] == "Certified Partial"
        assert result["category"] == "partial"

    def test_denied_a3(self) -> None:
        result = get_hcr_action_code("A3")
        assert result is not None
        assert result["description"] == "Not Certified"
        assert result["category"] == "denied"

    def test_pended_a4(self) -> None:
        result = get_hcr_action_code("A4")
        assert result is not None
        assert result["description"] == "Pended"
        assert result["category"] == "pended"

    def test_modified_a6(self) -> None:
        result = get_hcr_action_code("A6")
        assert result is not None
        assert result["description"] == "Modified"
        assert result["category"] == "modified"

    def test_contact_ct(self) -> None:
        result = get_hcr_action_code("CT")
        assert result is not None
        assert result["description"] == "Contact Payer"
        assert result["category"] == "contact"

    def test_no_action_na(self) -> None:
        result = get_hcr_action_code("NA")
        assert result is not None
        assert result["description"] == "No Action Required"
        assert result["category"] == "no_action"

    def test_all_seven_codes_exist(self) -> None:
        """All 7 HCR action codes are mapped."""
        codes = ["A1", "A2", "A3", "A4", "A6", "CT", "NA"]
        for code in codes:
            assert get_hcr_action_code(code) is not None, f"Expected {code} to exist"

    def test_case_insensitive_lowercase(self) -> None:
        result = get_hcr_action_code("a1")
        assert result is not None
        assert result["description"] == "Certified in Total"

    def test_case_insensitive_mixed(self) -> None:
        result = get_hcr_action_code("ct")
        assert result is not None
        assert result["description"] == "Contact Payer"

    def test_whitespace_handling(self) -> None:
        result = get_hcr_action_code("  A1  ")
        assert result is not None
        assert result["description"] == "Certified in Total"

    def test_unknown_code_returns_none(self) -> None:
        assert get_hcr_action_code("XX") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_hcr_action_code("") is None

    def test_result_has_all_fields(self) -> None:
        """Every HCR entry has description, category, and suggested_action."""
        codes = ["A1", "A2", "A3", "A4", "A6", "CT", "NA"]
        for code in codes:
            result = get_hcr_action_code(code)
            assert result is not None
            assert "description" in result, f"{code} missing description"
            assert "category" in result, f"{code} missing category"
            assert "suggested_action" in result, f"{code} missing suggested_action"
