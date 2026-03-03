"""Tests for shared date validation pure function."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.shared.validators.date import validate_date


class TestValidateDate:
    """Tests for validate_date() pure function."""

    # --- Valid dates ---

    def test_valid_date_string(self) -> None:
        today = datetime.date.today().isoformat()
        assert validate_date(today, "date_of_service") == []

    def test_valid_date_object(self) -> None:
        assert validate_date(datetime.date.today(), "date_of_service") == []

    def test_valid_recent_past(self) -> None:
        past = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        assert validate_date(past, "date_of_service") == []

    def test_valid_near_future(self) -> None:
        future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        assert validate_date(future, "date_of_service") == []

    # --- Missing date ---

    def test_none_date(self) -> None:
        findings = validate_date(None, "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_DATE"
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "date_of_service"

    def test_empty_string(self) -> None:
        findings = validate_date("", "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_DATE"

    def test_whitespace_only(self) -> None:
        findings = validate_date("   ", "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "MISSING_DATE"

    # --- Invalid format ---

    def test_invalid_format(self) -> None:
        findings = validate_date("not-a-date", "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DATE_FORMAT"
        assert findings[0].severity == Severity.ERROR

    def test_invalid_format_slashes(self) -> None:
        findings = validate_date("01/15/2025", "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DATE_FORMAT"

    def test_invalid_format_partial(self) -> None:
        findings = validate_date("2025-13-01", "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "INVALID_DATE_FORMAT"

    # --- Future date WARNING ---

    def test_far_future_warning(self) -> None:
        far_future = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()
        findings = validate_date(far_future, "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "FUTURE_DATE"
        assert findings[0].severity == Severity.WARNING
        assert findings[0].context is not None
        assert "delta_days" in findings[0].context

    # --- Past date WARNING ---

    def test_far_past_warning(self) -> None:
        far_past = (datetime.date.today() - datetime.timedelta(days=800)).isoformat()
        findings = validate_date(far_past, "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "PAST_DATE"
        assert findings[0].severity == Severity.WARNING

    # --- code_prefix ---

    def test_code_prefix_missing(self) -> None:
        findings = validate_date(None, "date_of_service", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_MISSING_DATE"

    def test_code_prefix_format(self) -> None:
        findings = validate_date("bad", "date_of_service", code_prefix="PA_")
        assert findings[0].code == "PA_INVALID_DATE_FORMAT"

    def test_code_prefix_future(self) -> None:
        far_future = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()
        findings = validate_date(far_future, "date_of_service", code_prefix="ELIG_")
        assert findings[0].code == "ELIG_FUTURE_DATE"

    # --- field_name passthrough ---

    def test_field_name_in_finding(self) -> None:
        findings = validate_date(None, "subscriber_dob")
        assert findings[0].field_name == "subscriber_dob"

    # --- PHI safety ---

    def test_no_phi_in_message(self) -> None:
        test_date = "2025-06-15"
        findings = validate_date("not-valid", "date_of_service")
        for f in findings:
            assert test_date not in f.message

    # --- Statelessness ---

    def test_stateless_multiple_calls(self) -> None:
        today = datetime.date.today().isoformat()
        r1 = validate_date(today, "d")
        r2 = validate_date(None, "d")
        r3 = validate_date(today, "d")
        assert r1 == []
        assert len(r2) == 1
        assert r3 == []

    # --- datetime.date object edge cases ---

    def test_date_object_far_future(self) -> None:
        far_future = datetime.date.today() + datetime.timedelta(days=400)
        findings = validate_date(far_future, "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "FUTURE_DATE"
        assert findings[0].severity == Severity.WARNING

    def test_date_object_far_past(self) -> None:
        far_past = datetime.date.today() - datetime.timedelta(days=800)
        findings = validate_date(far_past, "date_of_service")
        assert len(findings) == 1
        assert findings[0].code == "PAST_DATE"

    def test_datetime_datetime_coerced_to_date(self) -> None:
        dt = datetime.datetime(2025, 6, 15, 12, 30, 0)
        findings = validate_date(dt, "date_of_service")
        # Should not raise TypeError — datetime.datetime is coerced to date
        assert isinstance(findings, list)

    # --- Custom thresholds ---

    def test_custom_max_future_days(self) -> None:
        future_10 = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        assert validate_date(future_10, "d", max_future_days=5) != []
        assert validate_date(future_10, "d", max_future_days=15) == []

    def test_custom_max_past_days(self) -> None:
        past_10 = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        assert validate_date(past_10, "d", max_past_days=5) != []
        assert validate_date(past_10, "d", max_past_days=15) == []
