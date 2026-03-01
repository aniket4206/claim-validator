"""Tests for PA service type code lookups."""

from __future__ import annotations

from claim_validator.prior_auth.code_tables.service_types import get_pa_service_type

# All 22 PA-relevant service type codes in the data file.
ALL_SERVICE_TYPE_CODES = [
    "01", "02", "03", "04", "05", "06", "12", "14", "18", "42",
    "45", "48", "50", "54", "62", "73", "86", "88", "A4", "A7",
    "AL", "BB",
]


class TestGetPaServiceType:
    """Tests for get_pa_service_type() lookup function."""

    def test_medical_care_01(self) -> None:
        result = get_pa_service_type("01")
        assert result == "Medical Care"

    def test_surgical_02(self) -> None:
        result = get_pa_service_type("02")
        assert result == "Surgical"

    def test_mri_ct_62(self) -> None:
        result = get_pa_service_type("62")
        assert result == "MRI/CT Scan"

    def test_mental_health_73(self) -> None:
        result = get_pa_service_type("73")
        assert result == "Mental Health"

    def test_psychiatric_inpatient_a4(self) -> None:
        result = get_pa_service_type("A4")
        assert result is not None
        assert "Psychiatric" in result

    def test_partial_hospitalization_bb(self) -> None:
        result = get_pa_service_type("BB")
        assert result == "Partial Hospitalization"

    def test_all_codes_exist(self) -> None:
        """All 22 PA-relevant service type codes are mapped."""
        for code in ALL_SERVICE_TYPE_CODES:
            assert get_pa_service_type(code) is not None, f"Expected {code} to exist"

    def test_case_insensitive_lowercase(self) -> None:
        result = get_pa_service_type("a4")
        assert result is not None
        assert "Psychiatric" in result

    def test_case_insensitive_mixed(self) -> None:
        result = get_pa_service_type("bb")
        assert result == "Partial Hospitalization"

    def test_whitespace_handling(self) -> None:
        result = get_pa_service_type("  01  ")
        assert result == "Medical Care"

    def test_unknown_code_returns_none(self) -> None:
        assert get_pa_service_type("ZZ") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_pa_service_type("") is None

    def test_returns_string(self) -> None:
        """Service type lookups return str, not dict."""
        result = get_pa_service_type("01")
        assert isinstance(result, str)
