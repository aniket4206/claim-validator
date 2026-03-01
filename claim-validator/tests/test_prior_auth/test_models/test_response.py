"""Tests for prior authorization response models."""

from __future__ import annotations

from datetime import date

import pydantic
import pytest

from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.models.response import (
    PriorAuthError,
    PriorAuthResponse,
    ServiceLineDecision,
)

# ---------------------------------------------------------------------------
# ServiceLineDecision
# ---------------------------------------------------------------------------


class TestServiceLineDecision:
    def test_create_with_defaults(self) -> None:
        decision = ServiceLineDecision()
        assert decision.cpt_code is None
        assert decision.action_code is None
        assert decision.authorization_number is None
        assert decision.approved_quantity is None
        assert decision.denied_reason is None

    def test_create_approved(self) -> None:
        decision = ServiceLineDecision(
            cpt_code="27447",
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            authorization_number="AUTH123",
            approved_quantity=1,
        )
        assert decision.cpt_code == "27447"
        assert decision.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert decision.authorization_number == "AUTH123"
        assert decision.approved_quantity == 1

    def test_create_denied(self) -> None:
        decision = ServiceLineDecision(
            cpt_code="27447",
            action_code=CertificationActionCode.NOT_CERTIFIED,
            denied_reason="Medical necessity not met",
        )
        assert decision.action_code == CertificationActionCode.NOT_CERTIFIED
        assert decision.denied_reason == "Medical necessity not met"

    def test_frozen(self) -> None:
        decision = ServiceLineDecision(cpt_code="99213")
        with pytest.raises(pydantic.ValidationError):
            decision.cpt_code = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PriorAuthError
# ---------------------------------------------------------------------------


class TestPriorAuthError:
    def test_create_with_required_fields(self) -> None:
        error = PriorAuthError(rejection_code="72")
        assert error.rejection_code == "72"
        assert error.follow_up_code is None
        assert error.message == ""
        assert error.suggested_fix == ""

    def test_create_with_all_fields(self) -> None:
        error = PriorAuthError(
            rejection_code="72",
            follow_up_code="C",
            message="Invalid/Missing Subscriber/Insured ID",
            suggested_fix="Verify member ID with payer",
        )
        assert error.follow_up_code == "C"
        assert "Subscriber" in error.message
        assert "Verify" in error.suggested_fix

    def test_frozen(self) -> None:
        error = PriorAuthError(rejection_code="72")
        with pytest.raises(pydantic.ValidationError):
            error.rejection_code = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PriorAuthResponse
# ---------------------------------------------------------------------------


class TestPriorAuthResponse:
    def test_create_empty(self) -> None:
        resp = PriorAuthResponse()
        assert resp.action_code is None
        assert resp.authorization_number is None
        assert resp.effective_date is None
        assert resp.expiration_date is None
        assert resp.decision_reason_code is None
        assert resp.decision_reason_description is None
        assert resp.service_line_decisions == []
        assert resp.errors == []
        assert resp.raw_response is None

    def test_create_approved(self) -> None:
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            authorization_number="AUTH456",
            effective_date=date(2026, 3, 1),
            expiration_date=date(2026, 6, 1),
        )
        assert resp.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert resp.authorization_number == "AUTH456"
        assert resp.effective_date == date(2026, 3, 1)
        assert resp.expiration_date == date(2026, 6, 1)

    def test_create_with_line_decisions(self) -> None:
        decision = ServiceLineDecision(
            cpt_code="27447",
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
        )
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            service_line_decisions=[decision],
        )
        assert len(resp.service_line_decisions) == 1
        assert resp.service_line_decisions[0].cpt_code == "27447"

    def test_create_with_errors(self) -> None:
        error = PriorAuthError(rejection_code="72", message="Invalid member ID")
        resp = PriorAuthResponse(errors=[error])
        assert len(resp.errors) == 1
        assert resp.errors[0].rejection_code == "72"

    def test_frozen(self) -> None:
        resp = PriorAuthResponse()
        with pytest.raises(pydantic.ValidationError):
            resp.action_code = CertificationActionCode.CERTIFIED_IN_TOTAL  # type: ignore[misc]


class TestPriorAuthResponseConvenienceProperties:
    def test_is_approved_true(self) -> None:
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
        )
        assert resp.is_approved is True
        assert resp.is_denied is False
        assert resp.is_pended is False

    def test_is_denied_true(self) -> None:
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.NOT_CERTIFIED,
        )
        assert resp.is_approved is False
        assert resp.is_denied is True
        assert resp.is_pended is False

    def test_is_pended_true(self) -> None:
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.PENDED,
        )
        assert resp.is_approved is False
        assert resp.is_denied is False
        assert resp.is_pended is True

    def test_partial_approval_not_approved(self) -> None:
        """A2 (Certified Partial) should NOT be is_approved."""
        resp = PriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_PARTIAL,
        )
        assert resp.is_approved is False
        assert resp.is_denied is False
        assert resp.is_pended is False

    def test_none_action_code(self) -> None:
        resp = PriorAuthResponse()
        assert resp.is_approved is False
        assert resp.is_denied is False
        assert resp.is_pended is False

    def test_enum_coercion_action_code(self) -> None:
        """strict=False allows string -> CertificationActionCode coercion."""
        resp = PriorAuthResponse(
            action_code="A1",  # type: ignore[arg-type]
        )
        assert resp.is_approved is True

    def test_model_validate_from_dict(self) -> None:
        """PriorAuthResponse.model_validate(dict) works with nested models."""
        data = {
            "action_code": "A1",
            "authorization_number": "AUTH123",
            "effective_date": "2026-03-01",
            "service_line_decisions": [
                {"cpt_code": "27447", "action_code": "A1", "approved_quantity": 1}
            ],
            "errors": [{"rejection_code": "72", "message": "test"}],
        }
        resp = PriorAuthResponse.model_validate(data)
        assert resp.is_approved is True
        assert resp.authorization_number == "AUTH123"
        assert resp.effective_date == date(2026, 3, 1)
        assert len(resp.service_line_decisions) == 1
        assert len(resp.errors) == 1
