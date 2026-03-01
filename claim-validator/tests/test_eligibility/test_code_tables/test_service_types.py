"""Tests for service type code lookups."""

from __future__ import annotations

import json
from importlib.resources import files

from claim_validator.eligibility.code_tables.service_types import get_service_type


class TestGetServiceType:
    """Tests for get_service_type() lookup."""

    def test_valid_code_returns_description(self) -> None:
        result = get_service_type("30")
        assert result == "Health Benefit Plan Coverage"

    def test_medical_care_code(self) -> None:
        assert get_service_type("1") == "Medical Care"

    def test_hospital_code(self) -> None:
        assert get_service_type("47") == "Hospital"

    def test_prescription_drug_code(self) -> None:
        assert get_service_type("71") == "Prescription Drug"

    def test_emergency_services_code(self) -> None:
        assert get_service_type("86") == "Emergency Services"

    def test_urgent_care_code(self) -> None:
        assert get_service_type("UC") == "Urgent Care"

    def test_surgical_code(self) -> None:
        assert get_service_type("2") == "Surgical"

    def test_diagnostic_lab_code(self) -> None:
        assert get_service_type("5") == "Diagnostic Lab"

    def test_case_insensitive_alpha_code(self) -> None:
        assert get_service_type("uc") == "Urgent Care"

    def test_case_insensitive_mixed(self) -> None:
        assert get_service_type("Uc") == "Urgent Care"

    def test_whitespace_handling(self) -> None:
        assert get_service_type("  30  ") == "Health Benefit Plan Coverage"

    def test_whitespace_with_alpha_code(self) -> None:
        assert get_service_type("  uc  ") == "Urgent Care"

    def test_unknown_code_returns_none(self) -> None:
        assert get_service_type("ZZZ") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_service_type("") is None

    def test_numeric_string_not_in_table(self) -> None:
        assert get_service_type("999") is None

    def test_all_entries_are_nonempty_strings(self) -> None:
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(data_pkg.joinpath("service_types.json").read_text(encoding="utf-8"))
        for code, desc in raw.items():
            assert isinstance(code, str) and len(code) > 0, "Empty key found"
            assert isinstance(desc, str) and len(desc) > 0, f"Empty value for {code}"

    def test_all_known_codes_round_trip(self) -> None:
        """Every code in the JSON can be looked up successfully."""
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(data_pkg.joinpath("service_types.json").read_text(encoding="utf-8"))
        for code, desc in raw.items():
            assert get_service_type(code) == desc, f"Failed for code {code}"

    def test_default_eligibility_request_service_type_exists(self) -> None:
        """The default service_type_code '30' in EligibilityRequest must exist."""
        assert get_service_type("30") is not None

    def test_returns_string_type(self) -> None:
        result = get_service_type("1")
        assert isinstance(result, str)
