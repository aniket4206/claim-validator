"""Tests for AAA reject reason code lookups."""

from __future__ import annotations

from claim_validator.prior_auth.code_tables.aaa_reject_codes import get_aaa_reject_code

# All 23 AAA reject codes in the data file.
ALL_AAA_CODES = [
    "04", "15", "33", "35", "41", "42", "43", "44", "45", "46",
    "47", "48", "49", "51", "56", "57", "58", "60", "71", "72",
    "73", "79", "T4",
]


class TestGetAaaRejectCode:
    """Tests for get_aaa_reject_code() lookup function."""

    def test_quantity_exceeded_04(self) -> None:
        result = get_aaa_reject_code("04")
        assert result is not None
        assert result["meaning"] == "Authorized Quantity Exceeded"
        assert "suggested_fix" in result

    def test_missing_data_15(self) -> None:
        result = get_aaa_reject_code("15")
        assert result is not None
        assert result["meaning"] == "Required Application Data Missing"

    def test_invalid_npi_43(self) -> None:
        result = get_aaa_reject_code("43")
        assert result is not None
        assert result["meaning"] == "Invalid/Missing Provider Identification"

    def test_patient_not_eligible_57(self) -> None:
        result = get_aaa_reject_code("57")
        assert result is not None
        assert result["meaning"] == "Patient Not Eligible"

    def test_subscriber_id_72(self) -> None:
        result = get_aaa_reject_code("72")
        assert result is not None
        assert result["meaning"] == "Invalid/Missing Subscriber ID"

    def test_payer_missing_t4(self) -> None:
        result = get_aaa_reject_code("T4")
        assert result is not None
        assert result["meaning"] == "Payer Name/ID Missing"

    def test_all_codes_exist(self) -> None:
        """All 23 AAA reject codes are mapped."""
        for code in ALL_AAA_CODES:
            assert get_aaa_reject_code(code) is not None, f"Expected {code} to exist"

    def test_case_insensitive(self) -> None:
        result = get_aaa_reject_code("t4")
        assert result is not None
        assert result["meaning"] == "Payer Name/ID Missing"

    def test_whitespace_handling(self) -> None:
        result = get_aaa_reject_code("  04  ")
        assert result is not None
        assert result["meaning"] == "Authorized Quantity Exceeded"

    def test_unknown_code_returns_none(self) -> None:
        assert get_aaa_reject_code("99") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_aaa_reject_code("") is None

    def test_result_has_all_fields(self) -> None:
        """Every AAA entry has meaning, description, and suggested_fix."""
        for code in ALL_AAA_CODES:
            result = get_aaa_reject_code(code)
            assert result is not None
            assert "meaning" in result, f"{code} missing meaning"
            assert "description" in result, f"{code} missing description"
            assert "suggested_fix" in result, f"{code} missing suggested_fix"
