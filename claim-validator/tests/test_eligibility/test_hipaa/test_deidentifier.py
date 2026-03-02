"""Tests for EligibilityDeidentifier — HIPAA Safe Harbor de-identification."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.deidentifier import EligibilityDeidentifier
from claim_validator.eligibility.models.deidentified import (
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
)
from claim_validator.eligibility.models.response import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityResponse,
)


def _full_phi_response() -> EligibilityResponse:
    """EligibilityResponse with all PHI fields populated."""
    return EligibilityResponse(
        eligible=True,
        coverage=CoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_date=datetime.date(2023, 1, 15),
            termination_date=datetime.date(2025, 12, 31),
            plan_name="Acme Corp Gold PPO - Dept 42",
            group_number="GRP-AC-2023-042",
        ),
        benefits=[
            BenefitInfo(
                service_type_code="30",
                service_type_name="Health Benefit Plan Coverage",
                copay=40.0,
                coinsurance=0.20,
                deductible=2500.0,
                in_network=True,
                prior_auth_required=False,
            ),
            BenefitInfo(
                service_type_code="88",
                service_type_name="Pharmacy",
                copay=15.0,
                coinsurance=None,
                deductible=None,
                in_network=True,
                prior_auth_required=True,
            ),
        ],
        errors=[
            AAAError(
                rejection_code="72",
                follow_up_code="C",
                message="Subscriber John Smith (ID: XYZ123) not found in plan",
            ),
            AAAError(
                rejection_code="75",
                follow_up_code=None,
                message="Patient Jane Doe DOB 1990-01-15 mismatch",
            ),
        ],
        raw_response={
            "subscriber": {
                "firstName": "John",
                "lastName": "Smith",
                "memberId": "XYZ123",
            },
            "tradingPartnerServiceId": "60054",
        },
    )


# --- Core de-identification tests ---


class TestDeidentifyBasic:
    """Test basic de-identification behavior."""

    def test_returns_deidentified_type(self) -> None:
        response = _full_phi_response()
        result = EligibilityDeidentifier.deidentify(response)
        assert isinstance(result, DeidentifiedEligibilityResponse)

    def test_is_deidentified_true(self) -> None:
        response = _full_phi_response()
        result = EligibilityDeidentifier.deidentify(response)
        assert result.is_deidentified is True

    def test_deterministic(self) -> None:
        response = _full_phi_response()
        r1 = EligibilityDeidentifier.deidentify(response)
        r2 = EligibilityDeidentifier.deidentify(response)
        assert r1 == r2

    def test_stateless(self) -> None:
        resp_a = _full_phi_response()
        resp_b = EligibilityResponse(eligible=False)
        r_a1 = EligibilityDeidentifier.deidentify(resp_a)
        _ = EligibilityDeidentifier.deidentify(resp_b)
        r_a2 = EligibilityDeidentifier.deidentify(resp_a)
        assert r_a1 == r_a2


# --- Coverage de-identification tests ---


class TestStripCoverage:
    """Test coverage PHI stripping — plan_name, group_number, dates."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = EligibilityDeidentifier.deidentify(self.response)

    def test_coverage_is_deidentified_type(self) -> None:
        assert isinstance(self.result.coverage, DeidentifiedCoverageInfo)

    def test_plan_name_stripped(self) -> None:
        assert not hasattr(self.result.coverage, "plan_name")

    def test_group_number_stripped(self) -> None:
        assert not hasattr(self.result.coverage, "group_number")

    def test_effective_date_year_only(self) -> None:
        assert self.result.coverage.effective_year == 2023

    def test_termination_date_year_only(self) -> None:
        assert self.result.coverage.termination_year == 2025

    def test_no_full_dates_in_coverage(self) -> None:
        cov_str = str(self.result.coverage.model_dump())
        assert "2023-01-15" not in cov_str
        assert "2025-12-31" not in cov_str

    def test_status_retained(self) -> None:
        assert self.result.coverage.status == CoverageStatus.ACTIVE


# --- AAA error de-identification tests ---


class TestStripAAAErrors:
    """Test AAA error PHI stripping — message stripped, codes retained."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = EligibilityDeidentifier.deidentify(self.response)

    def test_error_count_preserved(self) -> None:
        assert len(self.result.errors) == 2

    def test_error_is_deidentified_type(self) -> None:
        assert isinstance(self.result.errors[0], DeidentifiedAAAError)

    def test_rejection_code_retained(self) -> None:
        assert self.result.errors[0].rejection_code == "72"
        assert self.result.errors[1].rejection_code == "75"

    def test_follow_up_code_retained(self) -> None:
        assert self.result.errors[0].follow_up_code == "C"
        assert self.result.errors[1].follow_up_code is None

    def test_message_stripped(self) -> None:
        assert not hasattr(self.result.errors[0], "message")

    def test_no_subscriber_info_in_errors(self) -> None:
        err_str = str([e.model_dump() for e in self.result.errors])
        assert "John" not in err_str
        assert "Smith" not in err_str
        assert "XYZ123" not in err_str
        assert "Jane" not in err_str
        assert "Doe" not in err_str
        assert "1990-01-15" not in err_str


# --- Raw response stripping ---


class TestStripRawResponse:
    """Test raw_response is completely removed."""

    def test_no_raw_response_field(self) -> None:
        response = _full_phi_response()
        result = EligibilityDeidentifier.deidentify(response)
        assert not hasattr(result, "raw_response")

    def test_no_raw_phi_in_output(self) -> None:
        response = _full_phi_response()
        result = EligibilityDeidentifier.deidentify(response)
        result_str = str(result.model_dump())
        assert "firstName" not in result_str
        assert "lastName" not in result_str
        assert "memberId" not in result_str


# --- Retained data tests ---


class TestRetainedData:
    """Test non-PHI data is retained correctly."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = EligibilityDeidentifier.deidentify(self.response)

    def test_eligible_retained(self) -> None:
        assert self.result.eligible is True

    def test_coverage_status_retained(self) -> None:
        assert self.result.coverage.status == CoverageStatus.ACTIVE

    def test_benefits_count_retained(self) -> None:
        assert len(self.result.benefits) == 2

    def test_error_codes_retained(self) -> None:
        codes = [e.rejection_code for e in self.result.errors]
        assert "72" in codes
        assert "75" in codes


# --- Benefits passthrough tests ---


class TestBenefitsPassthrough:
    """Test benefit fields pass through unchanged — no PHI in benefit data."""

    def setup_method(self) -> None:
        self.response = _full_phi_response()
        self.result = EligibilityDeidentifier.deidentify(self.response)
        self.benefit = self.result.benefits[0]

    def test_service_type_code_retained(self) -> None:
        assert self.benefit.service_type_code == "30"

    def test_service_type_name_retained(self) -> None:
        assert self.benefit.service_type_name == "Health Benefit Plan Coverage"

    def test_copay_retained(self) -> None:
        assert self.benefit.copay == 40.0

    def test_coinsurance_retained(self) -> None:
        assert self.benefit.coinsurance == 0.20

    def test_deductible_retained(self) -> None:
        assert self.benefit.deductible == 2500.0

    def test_in_network_retained(self) -> None:
        assert self.benefit.in_network is True

    def test_prior_auth_required_retained(self) -> None:
        assert self.benefit.prior_auth_required is False

    def test_second_benefit_retained(self) -> None:
        b2 = self.result.benefits[1]
        assert b2.service_type_code == "88"
        assert b2.service_type_name == "Pharmacy"
        assert b2.copay == 15.0
        assert b2.coinsurance is None
        assert b2.deductible is None
        assert b2.in_network is True
        assert b2.prior_auth_required is True


# --- Edge case tests ---


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_response(self) -> None:
        response = EligibilityResponse()
        result = EligibilityDeidentifier.deidentify(response)
        assert isinstance(result, DeidentifiedEligibilityResponse)
        assert result.eligible is None
        assert result.coverage is None
        assert result.benefits == []
        assert result.errors == []

    def test_none_coverage(self) -> None:
        response = EligibilityResponse(coverage=None)
        result = EligibilityDeidentifier.deidentify(response)
        assert result.coverage is None

    def test_coverage_with_none_dates(self) -> None:
        response = EligibilityResponse(
            coverage=CoverageInfo(
                status=CoverageStatus.UNKNOWN,
                effective_date=None,
                termination_date=None,
            ),
        )
        result = EligibilityDeidentifier.deidentify(response)
        assert result.coverage.effective_year is None
        assert result.coverage.termination_year is None

    def test_empty_benefits_list(self) -> None:
        response = EligibilityResponse(benefits=[])
        result = EligibilityDeidentifier.deidentify(response)
        assert result.benefits == []

    def test_empty_errors_list(self) -> None:
        response = EligibilityResponse(errors=[])
        result = EligibilityDeidentifier.deidentify(response)
        assert result.errors == []

    def test_error_with_empty_message(self) -> None:
        response = EligibilityResponse(
            errors=[AAAError(rejection_code="42", message="")],
        )
        result = EligibilityDeidentifier.deidentify(response)
        assert result.errors[0].rejection_code == "42"
        assert result.errors[0].follow_up_code is None

    def test_eligible_false_retained(self) -> None:
        response = EligibilityResponse(eligible=False)
        result = EligibilityDeidentifier.deidentify(response)
        assert result.eligible is False

    def test_eligible_none_retained(self) -> None:
        response = EligibilityResponse(eligible=None)
        result = EligibilityDeidentifier.deidentify(response)
        assert result.eligible is None


# --- PHI leak sweep ---


class TestPHILeakSweep:
    """Comprehensive sweep: no PHI values appear anywhere in output."""

    def test_no_phi_in_full_dump(self) -> None:
        response = _full_phi_response()
        result = EligibilityDeidentifier.deidentify(response)
        dump_str = str(result.model_dump())

        # Names
        assert "John" not in dump_str
        assert "Smith" not in dump_str
        assert "Jane" not in dump_str
        assert "Doe" not in dump_str

        # Member IDs
        assert "XYZ123" not in dump_str

        # Group identifiers
        assert "GRP-AC-2023-042" not in dump_str
        assert "Acme Corp" not in dump_str
        assert "Dept 42" not in dump_str

        # Full dates (year alone is OK)
        assert "2023-01-15" not in dump_str
        assert "2025-12-31" not in dump_str
        assert "1990-01-15" not in dump_str

        # Raw response fields
        assert "firstName" not in dump_str
        assert "lastName" not in dump_str
        assert "memberId" not in dump_str


# --- Type distinction tests ---


class TestTypeDistinction:
    """Verify raw EligibilityResponse is distinguishable from de-identified."""

    def test_raw_response_lacks_is_deidentified(self) -> None:
        raw = EligibilityResponse(eligible=True)
        assert not hasattr(raw, "is_deidentified")

    def test_deidentified_has_is_deidentified(self) -> None:
        result = EligibilityDeidentifier.deidentify(EligibilityResponse())
        assert result.is_deidentified is True


# --- Frozen enforcement tests ---


class TestFrozenEnforcement:
    """Verify de-identified models reject mutation (HIPAA immutability)."""

    def test_deidentified_response_frozen(self) -> None:
        result = EligibilityDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.eligible = False

    def test_deidentified_coverage_frozen(self) -> None:
        result = EligibilityDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.coverage.status = CoverageStatus.INACTIVE

    def test_deidentified_error_frozen(self) -> None:
        result = EligibilityDeidentifier.deidentify(_full_phi_response())
        with pytest.raises(ValidationError):
            result.errors[0].rejection_code = "99"


# --- Import tests ---


class TestImports:
    """Test de-identification types importable from expected locations."""

    def test_deidentifier_from_eligibility(self) -> None:
        from claim_validator.eligibility import EligibilityDeidentifier

        assert EligibilityDeidentifier is not None

    def test_deidentified_response_from_eligibility(self) -> None:
        from claim_validator.eligibility import DeidentifiedEligibilityResponse

        assert DeidentifiedEligibilityResponse is not None

    def test_deidentifier_from_top_level(self) -> None:
        from claim_validator import EligibilityDeidentifier

        assert EligibilityDeidentifier is not None

    def test_deidentified_response_from_top_level(self) -> None:
        from claim_validator import DeidentifiedEligibilityResponse

        assert DeidentifiedEligibilityResponse is not None

    def test_deidentified_coverage_from_top_level(self) -> None:
        from claim_validator import DeidentifiedCoverageInfo

        assert DeidentifiedCoverageInfo is not None

    def test_deidentified_aaa_error_from_top_level(self) -> None:
        from claim_validator import DeidentifiedAAAError

        assert DeidentifiedAAAError is not None
