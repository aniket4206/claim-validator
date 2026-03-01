"""Tests for PAProcedureValidator."""

from __future__ import annotations

from datetime import date

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.procedure import (
    PAProcedureValidator,
)


def _make_request(cpt_codes: list[str]) -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        service_lines=[ServiceLine(cpt_code=c) for c in cpt_codes],
    )


class TestPAProcedureValidatorValid:
    """AC9: Valid CPT/HCPCS codes → zero findings."""

    def test_valid_cpt(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["99213"]))
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["99213"]))
        assert result.validator_name == "PAProcedureValidator"

    def test_multiple_valid_codes(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["99213", "99214"]))
        assert len(result.findings) == 0

    def test_empty_service_lines(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request([]))
        assert len(result.findings) == 0

    def test_hcpcs_code(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["A4206"]))
        assert len(result.findings) == 0


class TestPAProcedureValidatorInvalidFormat:
    """AC10: Invalid format → PA_INVALID_PROCEDURE_FORMAT."""

    def test_too_short(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["9921"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_PROCEDURE_FORMAT"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "cpt_code"

    def test_too_long(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["992130"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_PROCEDURE_FORMAT"

    def test_special_characters(self) -> None:
        v = PAProcedureValidator()
        result = v.validate(_make_request(["9921!"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_PROCEDURE_FORMAT"

    def test_format_error_skips_lookup(self) -> None:
        """Format check fails → only format finding, no lookup finding."""
        v = PAProcedureValidator()
        result = v.validate(_make_request(["XX"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_PROCEDURE_FORMAT"

    def test_line_number_set(self) -> None:
        """Line number is 1-indexed."""
        v = PAProcedureValidator()
        result = v.validate(_make_request(["99213", "XX"]))
        format_findings = [f for f in result.findings if f.code == "PA_INVALID_PROCEDURE_FORMAT"]
        assert len(format_findings) == 1
        assert format_findings[0].line_number == 2


class TestPAProcedureValidatorUnknownCode:
    """AC10: Valid format but not in code table → PA_INVALID_PROCEDURE."""

    def test_unknown_code(self) -> None:
        """ZZ999 has valid format but is not in bundled CPT/HCPCS table."""
        v = PAProcedureValidator()
        result = v.validate(_make_request(["ZZ999"]))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_PROCEDURE"
        assert result.findings[0].line_number == 1

    def test_message_no_phi(self) -> None:
        """AC11: Message references field name, not actual procedure code."""
        v = PAProcedureValidator()
        result = v.validate(_make_request(["XX"]))
        assert len(result.findings) > 0
        for f in result.findings:
            assert "XX" not in f.message
            assert "cpt_code" in f.field_name
