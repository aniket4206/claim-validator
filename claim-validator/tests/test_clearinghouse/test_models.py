"""Tests for clearinghouse response models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)


class TestSubmissionResult:
    """Tests for SubmissionResult model."""

    def test_create_minimal(self) -> None:
        result = SubmissionResult(status="accepted", accepted=True)
        assert result.status == "accepted"
        assert result.accepted is True
        assert result.reference_id is None
        assert result.raw_response == {}
        assert result.errors == []

    def test_create_full(self) -> None:
        result = SubmissionResult(
            status="accepted",
            accepted=True,
            reference_id="REF-123",
            raw_response={"id": "abc"},
            errors=[],
        )
        assert result.reference_id == "REF-123"
        assert result.raw_response == {"id": "abc"}

    def test_create_rejected(self) -> None:
        result = SubmissionResult(
            status="rejected",
            accepted=False,
            errors=["Invalid NPI"],
        )
        assert result.accepted is False
        assert result.errors == ["Invalid NPI"]

    def test_frozen(self) -> None:
        result = SubmissionResult(status="accepted", accepted=True)
        with pytest.raises(ValidationError):
            result.status = "changed"  # type: ignore[misc]

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            SubmissionResult(status="accepted")  # type: ignore[call-arg]


class TestClearinghouseEligibilityResponse:
    """Tests for ClearinghouseEligibilityResponse model."""

    def test_create_minimal(self) -> None:
        resp = ClearinghouseEligibilityResponse(status="active")
        assert resp.status == "active"
        assert resp.eligible is None
        assert resp.reference_id is None
        assert resp.plan_info == {}
        assert resp.raw_response == {}
        assert resp.errors == []

    def test_create_eligible(self) -> None:
        resp = ClearinghouseEligibilityResponse(
            status="active",
            eligible=True,
            plan_info={"plan_name": "BCBS PPO"},
        )
        assert resp.eligible is True
        assert resp.plan_info["plan_name"] == "BCBS PPO"

    def test_create_ineligible(self) -> None:
        resp = ClearinghouseEligibilityResponse(
            status="inactive",
            eligible=False,
            errors=["Coverage terminated"],
        )
        assert resp.eligible is False
        assert len(resp.errors) == 1

    def test_frozen(self) -> None:
        resp = ClearinghouseEligibilityResponse(status="active")
        with pytest.raises(ValidationError):
            resp.eligible = True  # type: ignore[misc]


class TestClaimStatusResponse:
    """Tests for ClaimStatusResponse model."""

    def test_create_minimal(self) -> None:
        resp = ClaimStatusResponse(status="found")
        assert resp.status == "found"
        assert resp.claim_status is None
        assert resp.adjudication_date is None
        assert resp.reference_id is None

    def test_create_with_status(self) -> None:
        resp = ClaimStatusResponse(
            status="found",
            claim_status="paid",
            adjudication_date="2026-03-01",
            reference_id="CLM-456",
        )
        assert resp.claim_status == "paid"
        assert resp.adjudication_date == "2026-03-01"

    def test_frozen(self) -> None:
        resp = ClaimStatusResponse(status="found")
        with pytest.raises(ValidationError):
            resp.claim_status = "denied"  # type: ignore[misc]


class TestModelImports:
    """Verify models importable from clearinghouse package."""

    def test_import_from_clearinghouse(self) -> None:
        from claim_validator.clearinghouse import (
            ClaimStatusResponse,
            ClearinghouseEligibilityResponse,
            SubmissionResult,
        )

        assert SubmissionResult is not None
        assert ClearinghouseEligibilityResponse is not None
        assert ClaimStatusResponse is not None
