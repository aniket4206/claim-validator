"""Tests for TimelyFilingValidator — date consistency and timely filing."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.timely_filing import (
    TimelyFilingValidator,
)


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid dates."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "payer_id": "BCBS001",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ],
    }


# --- Valid dates ---


class TestTimelyFilingValidatorValid:
    """Tests for claims with valid, consistent dates."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_consistent_dates_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "TimelyFilingValidator"

    def test_empty_lines_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["lines"] = []
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_no_service_date_skipped(self) -> None:
        data = _valid_claim_dict()
        del data["lines"][0]["service_date_from"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_no_payer_id_no_timely_filing(self) -> None:
        data = _valid_claim_dict()
        del data["payer_id"]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        timely = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert timely == []


# --- Future service date ---


class TestTimelyFilingFutureDate:
    """Tests for future service date detection."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_future_service_date(self) -> None:
        data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"][0]["service_date_from"] = future.isoformat()
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "FUTURE_SERVICE_DATE"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "service_date_from"
        assert findings[0].line_number == 1

    def test_today_not_future(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["service_date_from"] = (
            datetime.date.today().isoformat()
        )
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "FUTURE_SERVICE_DATE"
        ]
        assert findings == []

    def test_multiple_future_dates(self) -> None:
        data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": future.isoformat(),
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": future.isoformat(),
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "FUTURE_SERVICE_DATE"
        ]
        assert len(findings) == 2
        assert {f.line_number for f in findings} == {1, 2}


# --- Service before DOB ---


class TestTimelyFilingServiceBeforeDOB:
    """Tests for service date before DOB detection."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_service_before_dob(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "2000-06-15"
        data["lines"][0]["service_date_from"] = "2000-01-01"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "SERVICE_BEFORE_DOB"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "service_date_from"
        assert findings[0].line_number == 1

    def test_service_on_dob_no_finding(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "1990-01-15"
        data["lines"][0]["service_date_from"] = "1990-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "SERVICE_BEFORE_DOB"
        ]
        assert findings == []

    def test_no_dob_skips_check(self) -> None:
        data = _valid_claim_dict()
        del data["patient_dob"]
        data["lines"][0]["service_date_from"] = "1950-01-01"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "SERVICE_BEFORE_DOB"
        ]
        assert findings == []


# --- Invalid date range ---


class TestTimelyFilingDateRange:
    """Tests for service_date_from after service_date_to."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_date_from_after_date_to(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["service_date_from"] = "2026-01-20"
        data["lines"][0]["service_date_to"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DATE_RANGE"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "service_date_from"
        assert findings[0].line_number == 1

    def test_same_from_and_to_no_finding(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["service_date_from"] = "2026-01-15"
        data["lines"][0]["service_date_to"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DATE_RANGE"
        ]
        assert findings == []

    def test_no_date_to_no_range_check(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["service_date_from"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "INVALID_DATE_RANGE"
        ]
        assert findings == []


# --- Timely filing ---


class TestTimelyFilingDeadline:
    """Tests for timely filing deadline detection."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_timely_filing_exceeded(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["lines"][0]["service_date_from"] = "2024-01-01"
        data["filing_date"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "service_date_from"

    def test_within_deadline_no_finding(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["lines"][0]["service_date_from"] = "2026-01-01"
        data["filing_date"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert findings == []

    def test_payer_specific_deadline(self) -> None:
        """AETNA has 90-day deadline."""
        data = _valid_claim_dict()
        data["payer_id"] = "AETNA"
        data["lines"][0]["service_date_from"] = "2025-09-01"
        data["filing_date"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert len(findings) == 1

    def test_unknown_payer_uses_default(self) -> None:
        """Unknown payer falls back to _default (365 days)."""
        data = _valid_claim_dict()
        data["payer_id"] = "UNKNOWN_PAYER_XYZ"
        data["lines"][0]["service_date_from"] = "2026-01-01"
        data["filing_date"] = "2026-06-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert findings == []

    def test_filing_date_not_provided_uses_today(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["lines"][0]["service_date_from"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert findings == []

    def test_filing_date_provided(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["lines"][0]["service_date_from"] = "2024-06-01"
        data["filing_date"] = "2025-12-01"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert len(findings) == 1

    def test_earliest_service_date_used(self) -> None:
        """Uses earliest service date across all lines."""
        data = _valid_claim_dict()
        data["payer_id"] = "AETNA"
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": "2025-09-01",
            },
        ]
        data["filing_date"] = "2026-01-20"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        # 2025-09-01 → 2026-01-20 = 141 days > 90 (AETNA)
        assert len(findings) == 1


# --- Finding quality ---


class TestTimelyFilingFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_no_phi_in_messages(self) -> None:
        data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"][0]["service_date_from"] = future.isoformat()
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert future.isoformat() not in finding.message
            assert future.isoformat() not in finding.suggestion
            assert "1990-01-15" not in finding.message
            assert "Jane" not in finding.message

    def test_all_severities_error(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "2030-01-01"
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"][0]["service_date_from"] = future.isoformat()
        data["lines"][0]["service_date_to"] = "2025-01-01"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert finding.severity == Severity.ERROR

    def test_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"][0]["service_date_from"] = future.isoformat()
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "FUTURE_SERVICE_DATE"
        ]
        assert findings[0].suggestion != ""

    def test_timely_filing_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["lines"][0]["service_date_from"] = "2024-01-01"
        data["filing_date"] = "2026-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert findings[0].suggestion != ""


# --- Statelessness ---


class TestTimelyFilingStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        bad_data["lines"][0]["service_date_from"] = (
            future.isoformat()
        )
        bad = ClaimData(**bad_data)

        r1 = self.validator.validate(good)
        r2 = self.validator.validate(bad)
        r3 = self.validator.validate(good)

        assert r1.findings == []
        assert len(r2.findings) >= 1
        assert r3.findings == []

    def test_returns_validator_output(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.validator_name == "TimelyFilingValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.lines[0].procedure_code == "99213"
        assert claim.lines[0].charge_amount == 150.00


# --- Edge cases ---


class TestTimelyFilingEdgeCases:
    """Tests for edge cases and unparseable dates."""

    def setup_method(self) -> None:
        self.validator = TimelyFilingValidator()

    def test_unparseable_service_date_skipped(self) -> None:
        data = _valid_claim_dict()
        data["lines"][0]["service_date_from"] = "not-a-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_unparseable_filing_date_uses_today(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "MEDICARE"
        data["filing_date"] = "bad-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        # Service date is recent, so no timely filing issue
        assert findings == []

    def test_empty_payer_id_no_timely_filing(self) -> None:
        data = _valid_claim_dict()
        data["payer_id"] = "  "
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "TIMELY_FILING_EXCEEDED"
        ]
        assert findings == []

    def test_mixed_valid_invalid_dates(self) -> None:
        """Lines with unparseable dates are skipped."""
        data = _valid_claim_dict()
        future = datetime.date.today() + datetime.timedelta(days=30)
        data["lines"] = [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "not-a-date",
            },
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "service_date_from": future.isoformat(),
            },
        ]
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings
            if f.code == "FUTURE_SERVICE_DATE"
        ]
        assert len(findings) == 1
        assert findings[0].line_number == 2
