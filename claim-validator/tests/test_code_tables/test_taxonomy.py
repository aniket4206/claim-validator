"""Tests for provider taxonomy code lookups."""

from __future__ import annotations

from claim_validator.code_tables.taxonomy import lookup_taxonomy


class TestLookupTaxonomy:
    def test_valid_family_medicine(self) -> None:
        result = lookup_taxonomy("207Q00000X")
        assert result is not None
        assert "family" in result.lower()

    def test_valid_code_case_insensitive(self) -> None:
        result = lookup_taxonomy("207q00000x")
        assert result is not None

    def test_valid_code_with_whitespace(self) -> None:
        result = lookup_taxonomy("  207Q00000X  ")
        assert result is not None

    def test_common_codes_exist(self) -> None:
        codes = ["207Q00000X", "207R00000X", "363LF0000X", "208D00000X"]
        for code in codes:
            assert lookup_taxonomy(code) is not None, f"Expected {code} to exist"

    def test_invalid_code_returns_none(self) -> None:
        assert lookup_taxonomy("000000000X") is None

    def test_empty_string_returns_none(self) -> None:
        assert lookup_taxonomy("") is None

    def test_nurse_practitioner_exists(self) -> None:
        result = lookup_taxonomy("363L00000X")
        assert result is not None
        assert "nurse" in result.lower()
