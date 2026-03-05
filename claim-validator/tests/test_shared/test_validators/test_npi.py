"""Tests for shared NPI validation pure function."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.shared.validators.npi import validate_npi


class TestValidateNPI:
    """Tests for validate_npi() pure function."""

    # --- Valid NPIs ---

    def test_valid_npi_returns_empty(self) -> None:
        assert validate_npi("1234567893", "billing_provider_npi") == []

    def test_valid_npi_second(self) -> None:
        assert validate_npi("1245319599", "billing_provider_npi") == []

    def test_valid_npi_third(self) -> None:
        assert validate_npi("1306849450", "billing_provider_npi") == []

    # --- Missing NPI ---

    def test_none_npi(self) -> None:
        findings = validate_npi(None, "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_NPI"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "billing_provider_npi"

    def test_empty_npi(self) -> None:
        findings = validate_npi("", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_NPI"

    def test_whitespace_npi(self) -> None:
        findings = validate_npi("   ", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_NPI"

    # --- Invalid format ---

    def test_too_short(self) -> None:
        findings = validate_npi("12345", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_non_numeric(self) -> None:
        findings = validate_npi("12345678AB", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"

    def test_too_long(self) -> None:
        findings = validate_npi("12345678901", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI_FORMAT"

    # --- Luhn failure ---

    def test_invalid_luhn(self) -> None:
        findings = validate_npi("1234567890", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"
        assert findings[0].severity == Severity.ERROR

    def test_invalid_luhn_second(self) -> None:
        findings = validate_npi("1234567891", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"

    def test_invalid_luhn_nines(self) -> None:
        findings = validate_npi("9999999999", "billing_provider_npi")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_NPI"

    # --- code_prefix ---

    def test_code_prefix_missing(self) -> None:
        findings = validate_npi(None, "requester_npi", code_prefix="PA_")
        assert findings[0].code == "PA_MISSING_NPI"

    def test_code_prefix_format(self) -> None:
        findings = validate_npi("short", "requester_npi", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_NPI_FORMAT"

    def test_code_prefix_luhn(self) -> None:
        findings = validate_npi("1234567890", "requester_npi", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_NPI"

    def test_elig_prefix(self) -> None:
        findings = validate_npi("1234567890", "npi", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_INVALID_NPI"

    # --- field_name passthrough ---

    def test_field_name_in_finding(self) -> None:
        findings = validate_npi("1234567890", "rendering_provider_npi")
        assert findings[0].field_name == "rendering_provider_npi"

    # --- PHI safety ---

    def test_no_phi_in_message(self) -> None:
        test_npi = "1234567890"
        findings = validate_npi(test_npi, "billing_provider_npi")
        for f in findings:
            assert test_npi not in f.message
            assert test_npi not in f.suggestion

    def test_no_phi_in_format_error(self) -> None:
        test_npi = "12345678AB"
        findings = validate_npi(test_npi, "billing_provider_npi")
        for f in findings:
            assert test_npi not in f.message
            assert test_npi not in f.suggestion

    # --- Statelessness ---

    def test_stateless_multiple_calls(self) -> None:
        r1 = validate_npi("1234567893", "npi")
        r2 = validate_npi("1234567890", "npi")
        r3 = validate_npi("1234567893", "npi")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []

    # --- Whitespace trimming ---

    def test_leading_trailing_whitespace(self) -> None:
        assert validate_npi(" 1234567893 ", "npi") == []
