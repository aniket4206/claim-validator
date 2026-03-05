"""Tests for PriorAuthDeidentifier — HIPAA Safe Harbor de-identification."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.deidentifier import PriorAuthDeidentifier
from claim_validator.prior_auth.models.deidentified import (
    DeidentifiedPriorAuthError,
    DeidentifiedPriorAuthResponse,
    DeidentifiedServiceLineDecision,
)
from claim_validator.prior_auth.models.response import (
    PriorAuthError,
    PriorAuthResponse,
    ServiceLineDecision,
)


def _full_phi_response() -> PriorAuthResponse:
    """PriorAuthResponse with all PHI fields populated."""
    return PriorAuthResponse(
        action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
        authorization_number="AUTH-2024-JSmith-98765",
        effective_date=datetime.date(2024, 3, 15),
        expiration_date=datetime.date(2025, 3, 14),
        decision_reason_code="01",
        decision_reason_description="Approved for patient John Smith per Dr. Jones",
        service_line_decisions=[
            ServiceLineDecision(
                cpt_code="27447",
                action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
                authorization_number="AUTH-SL-001-JSmith",
                approved_quantity=1,
                denied_reason=None,
            ),
            ServiceLineDecision(
                cpt_code="99213",
                action_code=CertificationActionCode.NOT_CERTIFIED,
                authorization_number="AUTH-SL-002-JSmith",
                approved_quantity=None,
                denied_reason="Not medically necessary for patient Jane Doe",
            ),
        ],
        errors=[
            PriorAuthError(
                rejection_code="T5",
                follow_up_code="C",
                message="Subscriber John Smith (ID: MEM-12345) not found",
                suggested_fix="Verify member ID for Smith, John DOB 1985-06-15",
            ),
            PriorAuthError(
                rejection_code="41",
                follow_up_code=None,
                message="Authorization expired for patient Jane Doe",
                suggested_fix="",
            ),
        ],
        raw_response={
            "subscriber": {
                "firstName": "John",
                "lastName": "Smith",
                "memberId": "MEM-12345",
            },
            "certificationNumber": "AUTH-2024-JSmith-98765",
        },
    )


# --- Core de-identification tests ---


class TestDeidentifyBasic:
    """Test basic de-identification behavior."""

    def test_returns_deidentified_type(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        assert isinstance(result, DeidentifiedPriorAuthResponse)

    def test_is_deidentified_true(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.is_deidentified is True

    def test_deterministic(self) -> None:
        response = _full_phi_response()
        r1 = PriorAuthDeidentifier.deidentify(response)
        r2 = PriorAuthDeidentifier.deidentify(response)
        assert r1 == r2

    def test_stateless(self) -> None:
        resp_a = _full_phi_response()
        resp_b = PriorAuthResponse()
        r_a1 = PriorAuthDeidentifier.deidentify(resp_a)
        _ = PriorAuthDeidentifier.deidentify(resp_b)
        r_a2 = PriorAuthDeidentifier.deidentify(resp_a)
        assert r_a1 == r_a2


# --- Authorization number stripping ---


class TestStripAuthNumber:
    """Test authorization_number is stripped at all levels."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_no_auth_number_field_on_response(self) -> None:
        assert not hasattr(self.result, "authorization_number")

    def test_no_auth_number_field_on_service_line(self) -> None:
        for sld in self.result.service_line_decisions:
            assert not hasattr(sld, "authorization_number")

    def test_auth_number_values_absent(self) -> None:
        dump_str = str(self.result.model_dump())
        assert "AUTH-2024-JSmith-98765" not in dump_str
        assert "AUTH-SL-001-JSmith" not in dump_str
        assert "AUTH-SL-002-JSmith" not in dump_str


# --- Date stripping ---


class TestStripDates:
    """Test full dates are reduced to year only."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_effective_year_extracted(self) -> None:
        assert self.result.effective_year == 2024

    def test_expiration_year_extracted(self) -> None:
        assert self.result.expiration_year == 2025

    def test_no_full_dates_in_output(self) -> None:
        dump_str = str(self.result.model_dump())
        assert "2024-03-15" not in dump_str
        assert "2025-03-14" not in dump_str

    def test_no_effective_date_field(self) -> None:
        assert not hasattr(self.result, "effective_date")

    def test_no_expiration_date_field(self) -> None:
        assert not hasattr(self.result, "expiration_date")


# --- Description stripping ---


class TestStripDescription:
    """Test decision_reason_description is stripped."""

    def test_no_description_field(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        assert not hasattr(result, "decision_reason_description")

    def test_description_text_absent(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        dump_str = str(result.model_dump())
        assert "Approved for patient" not in dump_str
        assert "Dr. Jones" not in dump_str


# --- Service line de-identification ---


class TestStripServiceLine:
    """Test service-line PHI is stripped."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_service_line_count_preserved(self) -> None:
        assert len(self.result.service_line_decisions) == 2

    def test_service_line_is_deidentified_type(self) -> None:
        assert isinstance(
            self.result.service_line_decisions[0], DeidentifiedServiceLineDecision
        )

    def test_denied_reason_stripped(self) -> None:
        for sld in self.result.service_line_decisions:
            assert not hasattr(sld, "denied_reason")

    def test_denied_reason_text_absent(self) -> None:
        dump_str = str(self.result.model_dump())
        assert "Not medically necessary" not in dump_str
        assert "Jane Doe" not in dump_str


class TestRetainServiceLine:
    """Test service-line non-PHI data is retained."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_cpt_code_retained(self) -> None:
        assert self.result.service_line_decisions[0].cpt_code == "27447"
        assert self.result.service_line_decisions[1].cpt_code == "99213"

    def test_action_code_retained(self) -> None:
        assert (
            self.result.service_line_decisions[0].action_code
            == CertificationActionCode.CERTIFIED_IN_TOTAL
        )
        assert (
            self.result.service_line_decisions[1].action_code
            == CertificationActionCode.NOT_CERTIFIED
        )

    def test_approved_quantity_retained(self) -> None:
        assert self.result.service_line_decisions[0].approved_quantity == 1
        assert self.result.service_line_decisions[1].approved_quantity is None


# --- Error de-identification ---


class TestStripErrors:
    """Test error PHI is stripped."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_error_count_preserved(self) -> None:
        assert len(self.result.errors) == 2

    def test_error_is_deidentified_type(self) -> None:
        assert isinstance(self.result.errors[0], DeidentifiedPriorAuthError)

    def test_message_stripped(self) -> None:
        for err in self.result.errors:
            assert not hasattr(err, "message")

    def test_suggested_fix_stripped(self) -> None:
        for err in self.result.errors:
            assert not hasattr(err, "suggested_fix")

    def test_no_subscriber_info_in_errors(self) -> None:
        err_str = str([e.model_dump() for e in self.result.errors])
        assert "John" not in err_str
        assert "Smith" not in err_str
        assert "MEM-12345" not in err_str
        assert "Jane" not in err_str
        assert "Doe" not in err_str
        assert "1985-06-15" not in err_str


class TestRetainErrorCodes:
    """Test error codes are retained."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = PriorAuthDeidentifier.deidentify(self.response)

    def test_rejection_code_retained(self) -> None:
        assert self.result.errors[0].rejection_code == "T5"
        assert self.result.errors[1].rejection_code == "41"

    def test_follow_up_code_retained(self) -> None:
        assert self.result.errors[0].follow_up_code == "C"
        assert self.result.errors[1].follow_up_code is None


# --- Raw response stripping ---


class TestStripRawResponse:
    """Test raw_response is completely removed."""

    def test_no_raw_response_field(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        assert not hasattr(result, "raw_response")

    def test_no_raw_phi_in_output(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        result_str = str(result.model_dump())
        assert "firstName" not in result_str
        assert "lastName" not in result_str
        assert "memberId" not in result_str
        assert "certificationNumber" not in result_str


# --- Edge cases ---


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_response(self) -> None:
        response = PriorAuthResponse()
        result = PriorAuthDeidentifier.deidentify(response)
        assert isinstance(result, DeidentifiedPriorAuthResponse)
        assert result.action_code is None
        assert result.decision_reason_code is None
        assert result.effective_year is None
        assert result.expiration_year is None
        assert result.service_line_decisions == []
        assert result.errors == []

    def test_none_dates(self) -> None:
        response = PriorAuthResponse(
            effective_date=None,
            expiration_date=None,
        )
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.effective_year is None
        assert result.expiration_year is None

    def test_empty_service_lines_list(self) -> None:
        response = PriorAuthResponse(service_line_decisions=[])
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.service_line_decisions == []

    def test_empty_errors_list(self) -> None:
        response = PriorAuthResponse(errors=[])
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.errors == []

    def test_error_with_empty_message(self) -> None:
        response = PriorAuthResponse(
            errors=[PriorAuthError(rejection_code="42", message="")],
        )
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.errors[0].rejection_code == "42"
        assert result.errors[0].follow_up_code is None

    def test_service_line_with_all_none(self) -> None:
        response = PriorAuthResponse(
            service_line_decisions=[ServiceLineDecision()],
        )
        result = PriorAuthDeidentifier.deidentify(response)
        sld = result.service_line_decisions[0]
        assert sld.cpt_code is None
        assert sld.action_code is None
        assert sld.approved_quantity is None

    def test_only_effective_date_set(self) -> None:
        response = PriorAuthResponse(
            effective_date=datetime.date(2024, 6, 1),
            expiration_date=None,
        )
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.effective_year == 2024
        assert result.expiration_year is None

    def test_only_expiration_date_set(self) -> None:
        response = PriorAuthResponse(
            effective_date=None,
            expiration_date=datetime.date(2025, 12, 31),
        )
        result = PriorAuthDeidentifier.deidentify(response)
        assert result.effective_year is None
        assert result.expiration_year == 2025


# --- PHI leak sweep ---


class TestPHILeakSweep:
    """Comprehensive sweep: no PHI values appear anywhere in output."""

    def test_no_phi_in_full_dump(self) -> None:
        response = _full_phi_response()
        result = PriorAuthDeidentifier.deidentify(response)
        dump_str = str(result.model_dump())

        # Names
        assert "John" not in dump_str
        assert "Smith" not in dump_str
        assert "Jane" not in dump_str
        assert "Doe" not in dump_str
        assert "Jones" not in dump_str

        # Member/auth IDs
        assert "MEM-12345" not in dump_str
        assert "AUTH-2024" not in dump_str
        assert "AUTH-SL-001" not in dump_str
        assert "AUTH-SL-002" not in dump_str
        assert "JSmith" not in dump_str

        # Full dates
        assert "2024-03-15" not in dump_str
        assert "2025-03-14" not in dump_str
        assert "1985-06-15" not in dump_str

        # Freetext descriptions
        assert "Approved for patient" not in dump_str
        assert "Not medically necessary" not in dump_str
        assert "Verify member ID" not in dump_str

        # Raw response fields
        assert "firstName" not in dump_str
        assert "lastName" not in dump_str
        assert "memberId" not in dump_str
        assert "certificationNumber" not in dump_str


# --- Type distinction tests ---


class TestTypeDistinction:
    """Verify raw PriorAuthResponse is distinguishable from de-identified."""

    def test_raw_response_lacks_is_deidentified(self) -> None:
        raw = PriorAuthResponse()
        assert not hasattr(raw, "is_deidentified")

    def test_deidentified_has_is_deidentified(self) -> None:
        result = PriorAuthDeidentifier.deidentify(PriorAuthResponse())
        assert result.is_deidentified is True

    def test_different_types(self) -> None:
        raw = PriorAuthResponse()
        result = PriorAuthDeidentifier.deidentify(raw)
        assert type(raw) is not type(result)


# --- Frozen enforcement tests ---


class TestFrozenEnforcement:
    """Verify de-identified models reject mutation (HIPAA immutability)."""

    def test_deidentified_response_frozen(self) -> None:
        result = PriorAuthDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.action_code = CertificationActionCode.NOT_CERTIFIED  # type: ignore[misc]

    def test_deidentified_service_line_frozen(self) -> None:
        result = PriorAuthDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.service_line_decisions[0].cpt_code = "99999"  # type: ignore[misc]

    def test_deidentified_error_frozen(self) -> None:
        result = PriorAuthDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.errors[0].rejection_code = "99"  # type: ignore[misc]


# --- Import tests ---


class TestImports:
    """Test de-identification types importable from expected locations."""

    def test_deidentifier_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import PriorAuthDeidentifier

        assert PriorAuthDeidentifier is not None

    def test_deidentified_response_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import DeidentifiedPriorAuthResponse

        assert DeidentifiedPriorAuthResponse is not None

    def test_deidentified_service_line_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import DeidentifiedServiceLineDecision

        assert DeidentifiedServiceLineDecision is not None

    def test_deidentified_error_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import DeidentifiedPriorAuthError

        assert DeidentifiedPriorAuthError is not None

    def test_deidentifier_from_top_level(self) -> None:
        from claim_validator import PriorAuthDeidentifier

        assert PriorAuthDeidentifier is not None

    def test_deidentified_response_from_top_level(self) -> None:
        from claim_validator import DeidentifiedPriorAuthResponse

        assert DeidentifiedPriorAuthResponse is not None

    def test_deidentified_service_line_from_top_level(self) -> None:
        from claim_validator import DeidentifiedServiceLineDecision

        assert DeidentifiedServiceLineDecision is not None

    def test_deidentified_error_from_top_level(self) -> None:
        from claim_validator import DeidentifiedPriorAuthError

        assert DeidentifiedPriorAuthError is not None
