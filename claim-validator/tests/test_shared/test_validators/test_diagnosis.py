"""Tests for shared ICD-10 diagnosis code validation pure function."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.shared.code_tables import get_icd10_table, lookup_icd10
from claim_validator.shared.validators.diagnosis import validate_diagnosis


def _get_valid_icd10_code() -> str:
    """Get a known valid ICD-10 code from the table for testing."""
    table = get_icd10_table()
    return next(iter(table))


def _get_unknown_icd10_code() -> str:
    """Get a format-valid ICD-10 code that is NOT in the table."""
    # Try codes in an unlikely range until we find one not in the table
    for i in range(10):
        candidate = f"X{i:02d}.9"
        if lookup_icd10(candidate) is None:
            return candidate
    # Fallback — extremely unlikely to be in any table
    return "Q00.0"


class TestValidDiagnosisCodes:
    """Valid ICD-10 codes return empty findings list."""

    def test_single_valid_code(self) -> None:
        code = _get_valid_icd10_code()
        assert validate_diagnosis([code], "diagnosis_codes") == []

    def test_multiple_valid_codes(self) -> None:
        table = get_icd10_table()
        codes = list(table.keys())[:2]
        assert validate_diagnosis(codes, "diagnosis_codes") == []

    def test_dotless_variant(self) -> None:
        # lookup_icd10 handles J069 -> J06.9
        assert validate_diagnosis(["J069"], "diagnosis_codes") == []


class TestEmptyInput:
    """Empty or None input returns empty findings."""

    def test_none_codes(self) -> None:
        assert validate_diagnosis(None, "diagnosis_codes") == []

    def test_empty_list(self) -> None:
        assert validate_diagnosis([], "diagnosis_codes") == []


class TestInvalidFormat:
    """Invalid ICD-10 format returns ERROR findings."""

    def test_numeric_only(self) -> None:
        findings = validate_diagnosis(["12345"], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_too_short(self) -> None:
        findings = validate_diagnosis(["A1"], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"

    def test_too_many_decimal_digits(self) -> None:
        findings = validate_diagnosis(["A01.12345"], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"

    def test_special_characters(self) -> None:
        findings = validate_diagnosis(["A01-2"], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"

    def test_position_in_context(self) -> None:
        findings = validate_diagnosis(["12345"], "diagnosis_codes")
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1


class TestUnknownCode:
    """Valid format but unknown ICD-10 code returns ERROR."""

    def test_unknown_icd10(self) -> None:
        unknown = _get_unknown_icd10_code()
        findings = validate_diagnosis([unknown], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS"
        assert findings[0].severity == Severity.ERROR

    def test_unknown_code_position(self) -> None:
        unknown = _get_unknown_icd10_code()
        findings = validate_diagnosis([unknown], "diagnosis_codes")
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1


class TestMixedCodes:
    """Mixed valid and invalid codes return findings only for invalid ones."""

    def test_valid_then_invalid_format(self) -> None:
        valid = _get_valid_icd10_code()
        findings = validate_diagnosis([valid, "BADCODE"], "diagnosis_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"
        assert findings[0].context is not None
        assert findings[0].context["position"] == 2

    def test_invalid_format_then_unknown(self) -> None:
        unknown = _get_unknown_icd10_code()
        findings = validate_diagnosis(["12345", unknown], "diagnosis_codes")
        assert len(findings) == 2
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1
        assert findings[1].code == "INVALID_DIAGNOSIS"
        assert findings[1].context is not None
        assert findings[1].context["position"] == 2


class TestCaseInsensitivity:
    """Lookup is case insensitive."""

    def test_lowercase_code(self) -> None:
        code = _get_valid_icd10_code()
        assert validate_diagnosis([code.lower()], "diagnosis_codes") == []

    def test_mixed_case(self) -> None:
        code = _get_valid_icd10_code()
        assert validate_diagnosis([code.upper(), code.lower()], "diagnosis_codes") == []


class TestCodePrefix:
    """code_prefix is prepended to finding codes."""

    def test_prefix_on_format_error(self) -> None:
        findings = validate_diagnosis(["BADCODE"], "dx", code_prefix="CLM_")
        assert findings[0].code == "CLM_INVALID_DIAGNOSIS_FORMAT"

    def test_prefix_on_unknown_code(self) -> None:
        unknown = _get_unknown_icd10_code()
        findings = validate_diagnosis([unknown], "dx", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_DIAGNOSIS"

    def test_empty_prefix_default(self) -> None:
        findings = validate_diagnosis(["BADCODE"], "dx")
        assert findings[0].code == "INVALID_DIAGNOSIS_FORMAT"


class TestFieldName:
    """field_name is passed through to findings."""

    def test_field_name_passthrough(self) -> None:
        findings = validate_diagnosis(["BADCODE"], "primary_diagnosis")
        assert findings[0].field_name == "primary_diagnosis"

    def test_default_field_name(self) -> None:
        findings = validate_diagnosis(["BADCODE"])
        assert findings[0].field_name == "diagnosis_codes"


class TestWhitespaceTrimming:
    """Leading/trailing whitespace in codes is trimmed."""

    def test_leading_trailing_spaces(self) -> None:
        code = _get_valid_icd10_code()
        assert validate_diagnosis([f"  {code}  "], "diagnosis_codes") == []


class TestPHISafety:
    """Actual code values must not appear in finding messages or suggestions."""

    def test_no_phi_in_format_error(self) -> None:
        test_code = "BADDIAG123"
        findings = validate_diagnosis([test_code], "diagnosis_codes")
        for f in findings:
            assert test_code not in f.message
            assert test_code not in f.suggestion

    def test_no_phi_in_unknown_code_error(self) -> None:
        test_code = _get_unknown_icd10_code()
        findings = validate_diagnosis([test_code], "diagnosis_codes")
        for f in findings:
            assert test_code not in f.message
            assert test_code not in f.suggestion


class TestStatelessness:
    """Multiple calls produce independent results."""

    def test_stateless_calls(self) -> None:
        valid = _get_valid_icd10_code()
        r1 = validate_diagnosis([valid], "dx")
        r2 = validate_diagnosis(["BADCODE"], "dx")
        r3 = validate_diagnosis([valid], "dx")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []
