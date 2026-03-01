"""Tests for eligibility response models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.models.response import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityResponse,
)


class TestCoverageInfo:
    def test_default_status_unknown(self) -> None:
        coverage = CoverageInfo()
        assert coverage.status == CoverageStatus.UNKNOWN

    def test_all_fields(self) -> None:
        coverage = CoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_date="2025-01-01",
            termination_date="2026-12-31",
            plan_name="Gold PPO",
            group_number="GRP001",
        )
        assert coverage.status == CoverageStatus.ACTIVE
        assert coverage.effective_date == date(2025, 1, 1)
        assert coverage.termination_date == date(2026, 12, 31)
        assert coverage.plan_name == "Gold PPO"
        assert coverage.group_number == "GRP001"

    def test_optional_fields_default_none(self) -> None:
        coverage = CoverageInfo()
        assert coverage.effective_date is None
        assert coverage.termination_date is None
        assert coverage.plan_name is None
        assert coverage.group_number is None

    def test_frozen(self) -> None:
        coverage = CoverageInfo()
        with pytest.raises(ValidationError):
            coverage.status = CoverageStatus.ACTIVE  # type: ignore[misc]

    def test_date_string_coercion(self) -> None:
        coverage = CoverageInfo(effective_date="2025-06-15")
        assert isinstance(coverage.effective_date, date)


class TestBenefitInfo:
    def test_all_fields_none_by_default(self) -> None:
        benefit = BenefitInfo()
        assert benefit.service_type_code is None
        assert benefit.service_type_name is None
        assert benefit.copay is None
        assert benefit.coinsurance is None
        assert benefit.deductible is None
        assert benefit.in_network is None
        assert benefit.prior_auth_required is None

    def test_all_fields_populated(self) -> None:
        benefit = BenefitInfo(
            service_type_code="30",
            service_type_name="Health Benefit Plan Coverage",
            copay=25.0,
            coinsurance=0.20,
            deductible=500.0,
            in_network=True,
            prior_auth_required=False,
        )
        assert benefit.service_type_code == "30"
        assert benefit.copay == 25.0
        assert benefit.coinsurance == 0.20
        assert benefit.deductible == 500.0
        assert benefit.in_network is True
        assert benefit.prior_auth_required is False

    def test_frozen(self) -> None:
        benefit = BenefitInfo(copay=25.0)
        with pytest.raises(ValidationError):
            benefit.copay = 50.0  # type: ignore[misc]

    def test_float_coercion(self) -> None:
        benefit = BenefitInfo(copay=25, deductible=500)
        assert isinstance(benefit.copay, float)
        assert isinstance(benefit.deductible, float)


class TestAAAError:
    def test_required_rejection_code(self) -> None:
        error = AAAError(rejection_code="57")
        assert error.rejection_code == "57"

    def test_optional_fields(self) -> None:
        error = AAAError(rejection_code="57")
        assert error.follow_up_code is None
        assert error.message == ""

    def test_all_fields(self) -> None:
        error = AAAError(
            rejection_code="57",
            follow_up_code="N",
            message="Patient not eligible",
        )
        assert error.rejection_code == "57"
        assert error.follow_up_code == "N"
        assert error.message == "Patient not eligible"

    def test_frozen(self) -> None:
        error = AAAError(rejection_code="57")
        with pytest.raises(ValidationError):
            error.rejection_code = "72"  # type: ignore[misc]

    def test_missing_rejection_code_raises(self) -> None:
        with pytest.raises(ValidationError):
            AAAError()  # type: ignore[call-arg]


class TestEligibilityResponse:
    def test_defaults(self) -> None:
        response = EligibilityResponse()
        assert response.eligible is None
        assert response.coverage is None
        assert response.benefits == []
        assert response.errors == []
        assert response.raw_response == {}

    def test_nested_coverage(self) -> None:
        response = EligibilityResponse(
            eligible=True,
            coverage=CoverageInfo(status=CoverageStatus.ACTIVE),
        )
        assert response.eligible is True
        assert response.coverage is not None
        assert response.coverage.status == CoverageStatus.ACTIVE

    def test_nested_benefits_list(self) -> None:
        benefits = [
            BenefitInfo(service_type_code="30", copay=25.0),
            BenefitInfo(service_type_code="47", deductible=1000.0),
        ]
        response = EligibilityResponse(benefits=benefits)
        assert len(response.benefits) == 2
        assert response.benefits[0].service_type_code == "30"
        assert response.benefits[1].deductible == 1000.0

    def test_nested_errors_list(self) -> None:
        errors = [
            AAAError(rejection_code="57", message="Patient not eligible"),
            AAAError(rejection_code="72", message="Invalid subscriber ID"),
        ]
        response = EligibilityResponse(errors=errors)
        assert len(response.errors) == 2
        assert response.errors[0].rejection_code == "57"
        assert response.errors[1].rejection_code == "72"

    def test_raw_response_dict(self) -> None:
        raw = {"controlNumber": "12345", "status": "active"}
        response = EligibilityResponse(raw_response=raw)
        assert response.raw_response == raw

    def test_frozen(self) -> None:
        response = EligibilityResponse()
        with pytest.raises(ValidationError):
            response.eligible = True  # type: ignore[misc]

    def test_full_response(self) -> None:
        response = EligibilityResponse(
            eligible=True,
            coverage=CoverageInfo(
                status=CoverageStatus.ACTIVE,
                plan_name="Gold PPO",
            ),
            benefits=[BenefitInfo(copay=25.0, in_network=True)],
            errors=[],
            raw_response={"raw": "data"},
        )
        assert response.eligible is True
        assert response.coverage is not None
        assert response.coverage.plan_name == "Gold PPO"
        assert len(response.benefits) == 1
        assert response.benefits[0].copay == 25.0
