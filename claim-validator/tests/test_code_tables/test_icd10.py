"""Tests for ICD-10-CM code lookups."""

from __future__ import annotations

from claim_validator.code_tables.icd10 import lookup_icd10


class TestLookupIcd10:
    def test_valid_code_returns_description(self) -> None:
        result = lookup_icd10("J06.9")
        assert result is not None
        assert "upper respiratory" in result.lower()

    def test_valid_code_case_insensitive(self) -> None:
        result = lookup_icd10("j06.9")
        assert result is not None

    def test_valid_code_with_whitespace(self) -> None:
        result = lookup_icd10("  J06.9  ")
        assert result is not None

    def test_common_codes_exist(self) -> None:
        codes = ["I10", "E11.9", "M54.5", "Z00.00", "R05.9"]
        for code in codes:
            assert lookup_icd10(code) is not None, f"Expected {code} to exist"

    def test_invalid_code_returns_none(self) -> None:
        assert lookup_icd10("Z99.99") is None

    def test_empty_string_returns_none(self) -> None:
        assert lookup_icd10("") is None

    def test_nonsense_code_returns_none(self) -> None:
        assert lookup_icd10("NOTACODE") is None

    def test_code_without_dot(self) -> None:
        """Lookup should work with or without the dot separator."""
        with_dot = lookup_icd10("J06.9")
        without_dot = lookup_icd10("J069")
        assert with_dot is not None
        assert with_dot == without_dot
