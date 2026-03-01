"""Tests for PAServiceDateValidator."""

from __future__ import annotations

from datetime import date, timedelta

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.service_date import (
    PAServiceDateValidator,
)


def _make_request(
    from_date: date | None = None,
    to_date: date | None = None,
    lines: list[ServiceLine] | None = None,
) -> PriorAuthRequest:
    if lines is not None:
        service_lines = lines
    else:
        service_lines = [
            ServiceLine(cpt_code="99213", from_date=from_date, to_date=to_date),
        ]
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        service_lines=service_lines,
    )


class TestPAServiceDateValidatorValid:
    """AC1: Valid future service dates → zero findings."""

    def test_valid_future_date(self) -> None:
        v = PAServiceDateValidator()
        future = date.today() + timedelta(days=30)
        result = v.validate(_make_request(from_date=future))
        assert len(result.findings) == 0

    def test_today_is_valid(self) -> None:
        v = PAServiceDateValidator()
        result = v.validate(_make_request(from_date=date.today()))
        assert len(result.findings) == 0

    def test_none_dates_skipped(self) -> None:
        v = PAServiceDateValidator()
        result = v.validate(_make_request(from_date=None, to_date=None))
        assert len(result.findings) == 0

    def test_empty_service_lines(self) -> None:
        v = PAServiceDateValidator()
        result = v.validate(_make_request(lines=[]))
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PAServiceDateValidator()
        future = date.today() + timedelta(days=10)
        result = v.validate(_make_request(from_date=future))
        assert result.validator_name == "PAServiceDateValidator"

    def test_valid_date_range(self) -> None:
        v = PAServiceDateValidator()
        start = date.today() + timedelta(days=10)
        end = date.today() + timedelta(days=20)
        result = v.validate(_make_request(from_date=start, to_date=end))
        assert len(result.findings) == 0

    def test_same_from_and_to_date(self) -> None:
        v = PAServiceDateValidator()
        d = date.today() + timedelta(days=10)
        result = v.validate(_make_request(from_date=d, to_date=d))
        assert len(result.findings) == 0


class TestPAServiceDateValidatorPastDate:
    """AC2: Past service date → PA_SERVICE_DATE_PAST."""

    def test_past_date(self) -> None:
        v = PAServiceDateValidator()
        past = date.today() - timedelta(days=1)
        result = v.validate(_make_request(from_date=past))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_SERVICE_DATE_PAST"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "service_lines[].from_date"

    def test_past_date_line_number(self) -> None:
        v = PAServiceDateValidator()
        past = date.today() - timedelta(days=5)
        future = date.today() + timedelta(days=10)
        lines = [
            ServiceLine(cpt_code="99213", from_date=future),
            ServiceLine(cpt_code="99214", from_date=past),
        ]
        result = v.validate(_make_request(lines=lines))
        past_findings = [f for f in result.findings if f.code == "PA_SERVICE_DATE_PAST"]
        assert len(past_findings) == 1
        assert past_findings[0].line_number == 2


class TestPAServiceDateValidatorFarFuture:
    """AC3: Far-future service date → PA_SERVICE_DATE_FUTURE."""

    def test_far_future_date(self) -> None:
        v = PAServiceDateValidator()
        far_future = date.today() + timedelta(days=400)
        result = v.validate(_make_request(from_date=far_future))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_SERVICE_DATE_FUTURE"
        assert result.findings[0].severity.value == "warning"

    def test_exactly_365_days_is_valid(self) -> None:
        v = PAServiceDateValidator()
        boundary = date.today() + timedelta(days=365)
        result = v.validate(_make_request(from_date=boundary))
        assert len(result.findings) == 0

    def test_366_days_is_warning(self) -> None:
        v = PAServiceDateValidator()
        beyond = date.today() + timedelta(days=366)
        result = v.validate(_make_request(from_date=beyond))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_SERVICE_DATE_FUTURE"


class TestPAServiceDateValidatorRangeInvalid:
    """Service date range to_date before from_date → PA_SERVICE_DATE_RANGE_INVALID."""

    def test_to_date_before_from_date(self) -> None:
        v = PAServiceDateValidator()
        start = date.today() + timedelta(days=20)
        end = date.today() + timedelta(days=10)
        result = v.validate(_make_request(from_date=start, to_date=end))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_SERVICE_DATE_RANGE_INVALID"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "service_lines[].to_date"


class TestPAServiceDateValidatorPHISafety:
    """AC15: No PHI in finding messages."""

    def test_no_phi_in_past_date_message(self) -> None:
        v = PAServiceDateValidator()
        past = date(2024, 1, 15)
        result = v.validate(_make_request(from_date=past))
        assert len(result.findings) > 0
        for f in result.findings:
            assert "2024-01-15" not in f.message
            assert "2024" not in f.message
