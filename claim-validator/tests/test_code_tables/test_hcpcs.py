"""Tests for HCPCS code lookups."""

from __future__ import annotations

from claim_validator.code_tables.hcpcs import lookup_hcpcs


class TestLookupHcpcs:
    def test_valid_em_code(self) -> None:
        result = lookup_hcpcs("99213")
        assert result is not None
        assert "outpatient" in result.lower() or "office" in result.lower()

    def test_valid_code_case_insensitive(self) -> None:
        result = lookup_hcpcs("g0008")
        assert result is not None

    def test_valid_code_with_whitespace(self) -> None:
        result = lookup_hcpcs("  99213  ")
        assert result is not None

    def test_common_codes_exist(self) -> None:
        codes = ["99213", "99214", "36415", "85025", "80053"]
        for code in codes:
            assert lookup_hcpcs(code) is not None, f"Expected {code} to exist"

    def test_invalid_code_returns_none(self) -> None:
        assert lookup_hcpcs("00000") is None

    def test_empty_string_returns_none(self) -> None:
        assert lookup_hcpcs("") is None

    def test_hcpcs_level_ii_code(self) -> None:
        """HCPCS Level II codes start with a letter."""
        result = lookup_hcpcs("J0696")
        assert result is not None
