"""Tests for de-identified prior authorization models."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.models.deidentified import (
    DeidentifiedPriorAuthError,
    DeidentifiedPriorAuthResponse,
    DeidentifiedServiceLineDecision,
)


class TestDeidentifiedServiceLineDecision:
    def test_create_empty(self) -> None:
        sld = DeidentifiedServiceLineDecision()
        assert sld.cpt_code is None
        assert sld.action_code is None
        assert sld.approved_quantity is None

    def test_create_with_fields(self) -> None:
        sld = DeidentifiedServiceLineDecision(
            cpt_code="27447",
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            approved_quantity=3,
        )
        assert sld.cpt_code == "27447"
        assert sld.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert sld.approved_quantity == 3

    def test_frozen(self) -> None:
        sld = DeidentifiedServiceLineDecision(cpt_code="27447")
        with pytest.raises(pydantic.ValidationError):
            sld.cpt_code = "99999"  # type: ignore[misc]

    def test_no_phi_fields(self) -> None:
        phi_fields = {"authorization_number", "denied_reason"}
        model_fields = set(DeidentifiedServiceLineDecision.model_fields.keys())
        overlap = phi_fields & model_fields
        assert overlap == set(), f"PHI fields found: {overlap}"


class TestDeidentifiedPriorAuthError:
    def test_create_minimal(self) -> None:
        err = DeidentifiedPriorAuthError(rejection_code="72")
        assert err.rejection_code == "72"
        assert err.follow_up_code is None

    def test_create_full(self) -> None:
        err = DeidentifiedPriorAuthError(rejection_code="72", follow_up_code="C")
        assert err.rejection_code == "72"
        assert err.follow_up_code == "C"

    def test_frozen(self) -> None:
        err = DeidentifiedPriorAuthError(rejection_code="72")
        with pytest.raises(pydantic.ValidationError):
            err.rejection_code = "99"  # type: ignore[misc]

    def test_no_phi_fields(self) -> None:
        phi_fields = {"message", "suggested_fix"}
        model_fields = set(DeidentifiedPriorAuthError.model_fields.keys())
        overlap = phi_fields & model_fields
        assert overlap == set(), f"PHI fields found: {overlap}"


class TestDeidentifiedPriorAuthResponse:
    def test_create_empty(self) -> None:
        resp = DeidentifiedPriorAuthResponse()
        assert resp.action_code is None
        assert resp.decision_reason_code is None
        assert resp.effective_year is None
        assert resp.expiration_year is None
        assert resp.service_line_decisions == []
        assert resp.errors == []

    def test_create_with_all_fields(self) -> None:
        resp = DeidentifiedPriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            decision_reason_code="01",
            effective_year=2024,
            expiration_year=2025,
            service_line_decisions=[
                DeidentifiedServiceLineDecision(cpt_code="27447"),
            ],
            errors=[
                DeidentifiedPriorAuthError(rejection_code="72"),
            ],
        )
        assert resp.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert resp.decision_reason_code == "01"
        assert resp.effective_year == 2024
        assert resp.expiration_year == 2025
        assert len(resp.service_line_decisions) == 1
        assert len(resp.errors) == 1

    def test_is_deidentified_property(self) -> None:
        resp = DeidentifiedPriorAuthResponse()
        assert resp.is_deidentified is True

    def test_frozen(self) -> None:
        resp = DeidentifiedPriorAuthResponse()
        with pytest.raises(pydantic.ValidationError):
            resp.action_code = CertificationActionCode.NOT_CERTIFIED  # type: ignore[misc]

    def test_no_phi_fields(self) -> None:
        phi_field_names = {
            "member_id",
            "subscriber_id",
            "first_name",
            "last_name",
            "dob",
            "date_of_birth",
            "ssn",
            "address",
            "phone",
            "authorization_number",
            "patient_name",
            "decision_reason_description",
            "raw_response",
            "effective_date",
            "expiration_date",
        }
        model_fields = set(DeidentifiedPriorAuthResponse.model_fields.keys())
        overlap = phi_field_names & model_fields
        assert overlap == set(), f"PHI fields found in deidentified model: {overlap}"
