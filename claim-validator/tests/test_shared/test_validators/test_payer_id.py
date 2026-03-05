"""Tests for shared payer ID validation pure function."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.shared.code_tables import get_payer_directory_table
from claim_validator.shared.validators.payer_id import validate_payer_id


def _get_valid_payer_id() -> str:
    """Get a known valid payer ID from the table for testing."""
    table = get_payer_directory_table()
    return next(iter(table))


class TestValidPayerId:
    """Valid payer ID returns empty findings list."""

    def test_known_payer(self) -> None:
        payer = _get_valid_payer_id()
        assert validate_payer_id(payer, "payer_id") == []


class TestMissingPayerId:
    """Missing or empty payer ID returns ERROR."""

    def test_none_payer(self) -> None:
        findings = validate_payer_id(None, "payer_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PAYER_ID"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "payer_id"

    def test_empty_string(self) -> None:
        findings = validate_payer_id("", "payer_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PAYER_ID"
        assert findings[0].severity == Severity.ERROR

    def test_whitespace_only(self) -> None:
        findings = validate_payer_id("   ", "payer_id")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_PAYER_ID"
        assert findings[0].severity == Severity.ERROR


class TestUnknownPayer:
    """Unknown payer ID returns WARNING."""

    def test_unknown_payer(self) -> None:
        findings = validate_payer_id("NONEXISTENT_PAYER_99999", "payer_id")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_PAYER"
        assert findings[0].severity == Severity.WARNING


class TestCodePrefix:
    """code_prefix is prepended to finding codes."""

    def test_prefix_on_missing(self) -> None:
        findings = validate_payer_id(None, "payer_id", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_MISSING_PAYER_ID"

    def test_prefix_on_unknown(self) -> None:
        findings = validate_payer_id("FAKE_PAYER", "payer_id", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_INVALID_PAYER"

    def test_empty_prefix_default(self) -> None:
        findings = validate_payer_id(None, "payer_id")
        assert findings[0].code == "MISSING_PAYER_ID"


class TestFieldName:
    """field_name is passed through to findings."""

    def test_field_name_passthrough(self) -> None:
        findings = validate_payer_id(None, "insurance_payer")
        assert findings[0].field_name == "insurance_payer"

    def test_default_field_name(self) -> None:
        findings = validate_payer_id(None)
        assert findings[0].field_name == "payer_id"


class TestCaseInsensitivity:
    """Payer ID lookup is case insensitive (via lookup_payer)."""

    def test_lowercase_payer(self) -> None:
        payer = _get_valid_payer_id()
        assert validate_payer_id(payer.lower(), "payer_id") == []

    def test_uppercase_payer(self) -> None:
        payer = _get_valid_payer_id()
        assert validate_payer_id(payer.upper(), "payer_id") == []


class TestWhitespaceTrimming:
    """Leading/trailing whitespace is trimmed."""

    def test_leading_trailing_spaces(self) -> None:
        payer = _get_valid_payer_id()
        assert validate_payer_id(f"  {payer}  ", "payer_id") == []


class TestPHISafety:
    """Actual payer ID values must not appear in finding messages or suggestions."""

    def test_no_phi_in_missing_error(self) -> None:
        findings = validate_payer_id(None, "payer_id")
        for f in findings:
            assert "None" not in f.message

    def test_no_phi_in_unknown_warning(self) -> None:
        test_payer = "FAKE_PAYER_XYZ"
        findings = validate_payer_id(test_payer, "payer_id")
        for f in findings:
            assert test_payer not in f.message
            assert test_payer not in f.suggestion


class TestStatelessness:
    """Multiple calls produce independent results."""

    def test_stateless_calls(self) -> None:
        payer = _get_valid_payer_id()
        r1 = validate_payer_id(payer, "payer_id")
        r2 = validate_payer_id(None, "payer_id")
        r3 = validate_payer_id(payer, "payer_id")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []
