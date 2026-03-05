"""Tests for shared demographics validation pure function."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.shared.validators.demographics import validate_demographics


class TestValidateDemographics:
    """Tests for validate_demographics() pure function."""

    # --- All valid ---

    def test_all_valid(self) -> None:
        assert validate_demographics("John Doe", "M", "1990-01-15") == []

    def test_all_valid_female(self) -> None:
        assert validate_demographics("Jane Doe", "F", "1985-06-30") == []

    def test_all_valid_unknown_gender(self) -> None:
        assert validate_demographics("Pat Smith", "U", "2000-12-01") == []

    def test_gender_case_insensitive(self) -> None:
        assert validate_demographics("Test", "m", "1990-01-01") == []
        assert validate_demographics("Test", "f", "1990-01-01") == []

    # --- Missing name ---

    def test_missing_name_none(self) -> None:
        findings = validate_demographics(None, "M", "1990-01-15")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PATIENT_NAME"
        assert findings[0].severity == Severity.ERROR

    def test_missing_name_empty(self) -> None:
        findings = validate_demographics("", "M", "1990-01-15")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PATIENT_NAME"

    def test_missing_name_whitespace(self) -> None:
        findings = validate_demographics("   ", "M", "1990-01-15")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PATIENT_NAME"

    # --- Invalid gender ---

    def test_invalid_gender(self) -> None:
        findings = validate_demographics("Test", "X", "1990-01-15")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_GENDER"
        assert findings[0].severity == Severity.ERROR

    def test_invalid_gender_numeric(self) -> None:
        findings = validate_demographics("Test", "1", "1990-01-15")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_GENDER"

    def test_none_gender_no_finding(self) -> None:
        # None gender is not an error in shared function — domain decides if required
        findings = validate_demographics("Test", None, "1990-01-15")
        assert all(f.code != "INVALID_GENDER" for f in findings)

    def test_empty_gender_no_finding(self) -> None:
        findings = validate_demographics("Test", "", "1990-01-15")
        assert all(f.code != "INVALID_GENDER" for f in findings)

    # --- Invalid DOB format ---

    def test_invalid_dob_format(self) -> None:
        findings = validate_demographics("Test", "M", "not-a-date")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DOB_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_invalid_dob_slashes(self) -> None:
        findings = validate_demographics("Test", "M", "01/15/1990")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DOB_FORMAT"

    def test_invalid_dob_month_13(self) -> None:
        findings = validate_demographics("Test", "M", "1990-13-01")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DOB_FORMAT"

    def test_none_dob_no_finding(self) -> None:
        # None DOB is not an error in shared function — domain decides if required
        findings = validate_demographics("Test", "M", None)
        assert all(f.code not in ("INVALID_DOB_FORMAT", "FUTURE_DOB") for f in findings)

    def test_empty_dob_no_finding(self) -> None:
        findings = validate_demographics("Test", "M", "")
        assert all(f.code not in ("INVALID_DOB_FORMAT", "FUTURE_DOB") for f in findings)

    # --- Future DOB ---

    def test_future_dob(self) -> None:
        future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        findings = validate_demographics("Test", "M", future)
        assert len(findings) == 1
        assert findings[0].code == "FUTURE_DOB"
        assert findings[0].severity == Severity.ERROR

    # --- Multiple errors ---

    def test_multiple_errors(self) -> None:
        findings = validate_demographics(None, "X", "not-a-date")
        codes = {f.code for f in findings}
        assert "MISSING_PATIENT_NAME" in codes
        assert "INVALID_GENDER" in codes
        assert "INVALID_DOB_FORMAT" in codes
        assert len(findings) == 3

    # --- field_prefix ---

    def test_field_prefix_in_field_name(self) -> None:
        findings = validate_demographics(None, "M", "1990-01-15", field_prefix="patient_")
        assert findings[0].field_name == "patient_name"

    def test_field_prefix_gender(self) -> None:
        findings = validate_demographics("Test", "X", "1990-01-15", field_prefix="subscriber_")
        assert findings[0].field_name == "subscriber_gender"

    def test_field_prefix_dob(self) -> None:
        findings = validate_demographics("Test", "M", "bad-date", field_prefix="patient_")
        assert findings[0].field_name == "patient_dob"

    # --- code_prefix ---

    def test_code_prefix_name(self) -> None:
        findings = validate_demographics(None, "M", "1990-01-15", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_MISSING_PATIENT_NAME"

    def test_code_prefix_gender(self) -> None:
        findings = validate_demographics("Test", "X", "1990-01-15", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_GENDER"

    def test_code_prefix_dob(self) -> None:
        findings = validate_demographics("Test", "M", "bad", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_INVALID_DOB_FORMAT"

    # --- PHI safety ---

    def test_no_phi_in_message(self) -> None:
        test_name = "John Doe"
        test_dob = "1990-13-01"
        findings = validate_demographics(test_name, "X", test_dob)
        assert len(findings) >= 2  # INVALID_GENDER + INVALID_DOB_FORMAT at minimum
        for f in findings:
            assert test_name not in f.message
            assert test_dob not in f.message

    def test_no_phi_in_future_dob(self) -> None:
        future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        findings = validate_demographics("Test", "M", future)
        for f in findings:
            assert future not in f.message

    # --- Statelessness ---

    def test_stateless_multiple_calls(self) -> None:
        r1 = validate_demographics("Test", "M", "1990-01-15")
        r2 = validate_demographics(None, "X", "bad")
        r3 = validate_demographics("Test", "M", "1990-01-15")
        assert r1 == []
        assert len(r2) == 3
        assert r3 == []
