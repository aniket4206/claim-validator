"""Tests for shared CPT/HCPCS procedure code validation pure function."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.shared.code_tables import get_hcpcs_table
from claim_validator.shared.validators.procedure import validate_procedure


def _get_valid_hcpcs_code() -> str:
    """Get a known valid HCPCS code from the table for testing."""
    table = get_hcpcs_table()
    return next(iter(table))


class TestValidProcedureCodes:
    """Valid CPT/HCPCS codes return empty findings list."""

    def test_single_valid_code(self) -> None:
        code = _get_valid_hcpcs_code()
        assert validate_procedure([code], "procedure_codes") == []

    def test_multiple_valid_codes(self) -> None:
        table = get_hcpcs_table()
        codes = list(table.keys())[:2]
        assert validate_procedure(codes, "procedure_codes") == []


class TestEmptyInput:
    """Empty or None input returns empty findings."""

    def test_none_codes(self) -> None:
        assert validate_procedure(None, "procedure_codes") == []

    def test_empty_list(self) -> None:
        assert validate_procedure([], "procedure_codes") == []


class TestInvalidFormat:
    """Invalid CPT/HCPCS format returns ERROR findings."""

    def test_too_short(self) -> None:
        findings = validate_procedure(["123"], "procedure_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_too_long(self) -> None:
        findings = validate_procedure(["123456"], "procedure_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"

    def test_special_characters(self) -> None:
        findings = validate_procedure(["99-13"], "procedure_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"

    def test_position_in_context(self) -> None:
        findings = validate_procedure(["123"], "procedure_codes")
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1


class TestUnknownCode:
    """Valid format but unknown HCPCS code returns WARNING."""

    def test_unknown_hcpcs(self) -> None:
        findings = validate_procedure(["ZZZZZ"], "procedure_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PROCEDURE"
        assert findings[0].severity == Severity.WARNING

    def test_unknown_code_position(self) -> None:
        findings = validate_procedure(["ZZZZZ"], "procedure_codes")
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1


class TestMixedCodes:
    """Mixed valid and invalid codes return findings only for invalid ones."""

    def test_valid_then_invalid_format(self) -> None:
        valid = _get_valid_hcpcs_code()
        findings = validate_procedure([valid, "BAD"], "procedure_codes")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"
        assert findings[0].context is not None
        assert findings[0].context["position"] == 2

    def test_invalid_format_then_unknown(self) -> None:
        findings = validate_procedure(["BAD", "ZZZZZ"], "procedure_codes")
        assert len(findings) == 2
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"
        assert findings[0].context is not None
        assert findings[0].context["position"] == 1
        assert findings[1].code == "INVALID_PROCEDURE"
        assert findings[1].context is not None
        assert findings[1].context["position"] == 2


class TestCodePrefix:
    """code_prefix is prepended to finding codes."""

    def test_prefix_on_format_error(self) -> None:
        findings = validate_procedure(["BAD"], "proc", code_prefix="CLM_")
        assert findings[0].code == "CLM_INVALID_PROCEDURE_FORMAT"

    def test_prefix_on_unknown_code(self) -> None:
        findings = validate_procedure(["ZZZZZ"], "proc", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_PROCEDURE"

    def test_empty_prefix_default(self) -> None:
        findings = validate_procedure(["BAD"], "proc")
        assert findings[0].code == "INVALID_PROCEDURE_FORMAT"


class TestFieldName:
    """field_name is passed through to findings."""

    def test_field_name_passthrough(self) -> None:
        findings = validate_procedure(["BAD"], "cpt_codes")
        assert findings[0].field_name == "cpt_codes"

    def test_default_field_name(self) -> None:
        findings = validate_procedure(["BAD"])
        assert findings[0].field_name == "procedure_codes"


class TestWhitespaceTrimming:
    """Leading/trailing whitespace in codes is trimmed."""

    def test_leading_trailing_spaces(self) -> None:
        valid = _get_valid_hcpcs_code()
        assert validate_procedure([f"  {valid}  "], "procedure_codes") == []


class TestPHISafety:
    """Actual code values must not appear in finding messages or suggestions."""

    def test_no_phi_in_format_error(self) -> None:
        test_code = "BADPROC!"
        findings = validate_procedure([test_code], "procedure_codes")
        for f in findings:
            assert test_code not in f.message
            assert test_code not in f.suggestion

    def test_no_phi_in_unknown_code_warning(self) -> None:
        test_code = "ZZZZZ"
        findings = validate_procedure([test_code], "procedure_codes")
        for f in findings:
            assert test_code not in f.message
            assert test_code not in f.suggestion


class TestStatelessness:
    """Multiple calls produce independent results."""

    def test_stateless_calls(self) -> None:
        valid = _get_valid_hcpcs_code()
        r1 = validate_procedure([valid], "proc")
        r2 = validate_procedure(["BAD"], "proc")
        r3 = validate_procedure([valid], "proc")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []
