"""Tests for EligibilityDateValidator."""

from __future__ import annotations

import datetime
from typing import Any

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.validators.rule_based.date import (
    EligibilityDateValidator,
)


class TestDateValidatorValid:
    """Tests for valid dates — zero findings."""

    def test_today_no_findings(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["date_of_service"] = datetime.date.today()
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_yesterday_no_findings(self, valid_request_dict: dict[str, Any]) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=1)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_30_days_future_no_findings(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=30)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_boundary_365_days_future_no_findings(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=365)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_boundary_730_days_past_no_findings(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=730)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 0

    def test_validator_name(self) -> None:
        assert EligibilityDateValidator.name == "EligibilityDateValidator"


class TestDateValidatorMissing:
    """Tests for missing date — ELIG_MISSING_DATE."""

    def test_fixture_triggers_missing_date(
        self, valid_request: EligibilityRequest
    ) -> None:
        """valid_request fixture has date_of_service=None → ELIG_MISSING_DATE."""
        validator = EligibilityDateValidator()
        output = validator.validate(valid_request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_MISSING_DATE"

    def test_none_date_produces_error(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        # date_of_service defaults to None
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        findings = [f for f in output.findings if f.code == "ELIG_MISSING_DATE"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_date_field_name(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "date_of_service"

    def test_missing_date_has_suggestion(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].suggestion != ""


class TestDateValidatorFuture:
    """Tests for far-future dates — ELIG_FUTURE_DATE."""

    def test_366_days_future_produces_warning(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=366)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_FUTURE_DATE"
        assert output.findings[0].severity == Severity.WARNING

    def test_2_years_future_produces_warning(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=800)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_FUTURE_DATE"

    def test_future_finding_field_name(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=400)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "date_of_service"

    def test_future_finding_has_suggestion(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=400)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].suggestion != ""

    def test_future_finding_has_delta_context(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() + datetime.timedelta(days=400)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].context is not None
        assert output.findings[0].context["delta_days"] == 400


class TestDateValidatorPast:
    """Tests for far-past dates — ELIG_PAST_DATE."""

    def test_731_days_past_produces_warning(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=731)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_PAST_DATE"
        assert output.findings[0].severity == Severity.WARNING

    def test_3_years_past_produces_warning(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=1100)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert len(output.findings) == 1
        assert output.findings[0].code == "ELIG_PAST_DATE"

    def test_past_finding_field_name(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=800)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].field_name == "date_of_service"

    def test_past_finding_has_delta_context(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        valid_request_dict["date_of_service"] = (
            datetime.date.today() - datetime.timedelta(days=800)
        )
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        assert output.findings[0].context is not None
        assert output.findings[0].context["delta_days"] == -800


class TestDateValidatorNoPhi:
    """Tests for PHI safety."""

    def test_no_phi_in_missing_date_message(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        for finding in output.findings:
            assert "Jane" not in finding.message
            assert "Doe" not in finding.message

    def test_no_phi_in_future_date_message(
        self, valid_request_dict: dict[str, Any]
    ) -> None:
        future = datetime.date.today() + datetime.timedelta(days=400)
        valid_request_dict["date_of_service"] = future
        request = EligibilityRequest(**valid_request_dict)
        validator = EligibilityDateValidator()
        output = validator.validate(request)
        for finding in output.findings:
            assert str(future) not in finding.message
