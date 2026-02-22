"""Tests for Place of Service code lookups."""

from __future__ import annotations

from claim_validator.code_tables.pos import lookup_pos


class TestLookupPos:
    def test_office(self) -> None:
        result = lookup_pos("11")
        assert result is not None
        assert result == "Office"

    def test_inpatient_hospital(self) -> None:
        result = lookup_pos("21")
        assert result is not None
        assert "inpatient" in result.lower()

    def test_emergency_room(self) -> None:
        result = lookup_pos("23")
        assert result is not None
        assert "emergency" in result.lower()

    def test_valid_code_with_whitespace(self) -> None:
        result = lookup_pos("  11  ")
        assert result is not None

    def test_common_codes_exist(self) -> None:
        codes = ["11", "12", "21", "22", "23", "24", "31", "81"]
        for code in codes:
            assert lookup_pos(code) is not None, f"Expected POS {code} to exist"

    def test_invalid_code_returns_none(self) -> None:
        assert lookup_pos("98") is None

    def test_empty_string_returns_none(self) -> None:
        assert lookup_pos("") is None
