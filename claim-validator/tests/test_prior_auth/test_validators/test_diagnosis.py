"""Tests for PADiagnosisValidator."""

from __future__ import annotations

from datetime import date

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.diagnosis import (
    PADiagnosisValidator,
)


def _make_request(codes: list[str]) -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=codes,
    )


class TestPADiagnosisValidatorValid:
    """AC7: Valid ICD-10 codes → zero findings."""

    def test_valid_code_with_dot(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J06.9"]))
        assert len(result.findings) == 0

    def test_valid_three_char_code(self) -> None:
        """3-char code (letter + 2 digits) passes format check."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["E11"]))
        format_findings = [f for f in result.findings if f.code == "PA_INVALID_DIAGNOSIS_FORMAT"]
        assert len(format_findings) == 0

    def test_valid_dotless_code(self) -> None:
        """Dotless ICD-10 codes (common in X12 EDI) pass format check."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J069"]))
        format_findings = [f for f in result.findings if f.code == "PA_INVALID_DIAGNOSIS_FORMAT"]
        assert len(format_findings) == 0

    def test_validator_name(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J06.9"]))
        assert result.validator_name == "PADiagnosisValidator"

    def test_multiple_valid_codes(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J06.9", "E11.9"]))
        assert len(result.findings) == 0

    def test_empty_list(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request([]))
        assert len(result.findings) == 0


class TestPADiagnosisValidatorInvalidFormat:
    """AC8: Invalid format → PA_INVALID_DIAGNOSIS_FORMAT."""

    def test_no_letter_prefix(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["123.4"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DIAGNOSIS_FORMAT"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "diagnosis_codes"

    def test_too_short(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J0"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DIAGNOSIS_FORMAT"

    def test_special_characters(self) -> None:
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J06!9"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DIAGNOSIS_FORMAT"

    def test_format_error_skips_lookup(self) -> None:
        """Format check fails → only format finding, no lookup finding."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["INVALID"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DIAGNOSIS_FORMAT"


class TestPADiagnosisValidatorUnknownCode:
    """AC8: Valid format but not in code table → PA_INVALID_DIAGNOSIS."""

    def test_unknown_code(self) -> None:
        """X99.9 has valid format but is not in bundled ICD-10-CM table."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["X99.9"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DIAGNOSIS"

    def test_position_in_message(self) -> None:
        """Message includes position number."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["X99.9"]))
        assert len(result.findings) == 1
        assert "position 1" in result.findings[0].message

    def test_multiple_codes_mixed(self) -> None:
        """Multiple codes: valid + invalid format + unknown."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["J06.9", "INVALID", "X99.9"]))
        codes = [f.code for f in result.findings]
        # At minimum, "INVALID" should produce format error
        assert "PA_INVALID_DIAGNOSIS_FORMAT" in codes

    def test_message_no_phi(self) -> None:
        """AC11: Message references field name, not actual diagnosis code."""
        v = PADiagnosisValidator()
        result = v.validate(_make_request(["INVALID"]))
        assert len(result.findings) > 0
        for f in result.findings:
            assert "INVALID" not in f.message
            assert "diagnosis_codes" in f.field_name
