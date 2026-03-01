"""Tests for PADateOfBirthValidator."""

from __future__ import annotations

from datetime import date, timedelta

from claim_validator.prior_auth.models.request import (
    PatientInfo,
    PriorAuthRequest,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.date_of_birth import (
    PADateOfBirthValidator,
)


def _make_request(
    subscriber_dob: date,
    patient_dob: date | None = None,
) -> PriorAuthRequest:
    patient = None
    if patient_dob is not None:
        patient = PatientInfo(
            first_name="John",
            last_name="Doe",
            dob=patient_dob,
        )
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=subscriber_dob,
        ),
        patient=patient,
    )


class TestPADateOfBirthValidatorValid:
    """AC5: Valid DOB → zero findings."""

    def test_past_dob(self) -> None:
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(date(1985, 3, 15)))
        assert len(result.findings) == 0

    def test_today_dob(self) -> None:
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(date.today()))
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(date(1985, 3, 15)))
        assert result.validator_name == "PADateOfBirthValidator"

    def test_valid_with_patient(self) -> None:
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(date(1985, 3, 15), date(2010, 6, 1)))
        assert len(result.findings) == 0


class TestPADateOfBirthValidatorFuture:
    """AC6: Future DOB → PA_INVALID_DOB."""

    def test_subscriber_future_dob(self) -> None:
        future = date.today() + timedelta(days=30)
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(future))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DOB"
        assert result.findings[0].severity.value == "error"
        assert result.findings[0].field_name == "subscriber.dob"

    def test_patient_future_dob(self) -> None:
        future = date.today() + timedelta(days=30)
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(date(1985, 3, 15), future))
        assert len(result.findings) == 1
        assert result.findings[0].code == "PA_INVALID_DOB"
        assert result.findings[0].field_name == "patient.dob"

    def test_both_future_dob(self) -> None:
        future = date.today() + timedelta(days=30)
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(future, future))
        assert len(result.findings) == 2
        fields = {f.field_name for f in result.findings}
        assert fields == {"subscriber.dob", "patient.dob"}

    def test_message_no_phi(self) -> None:
        """AC11: Message references field name, not actual DOB value."""
        future = date.today() + timedelta(days=30)
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(future))
        assert str(future) not in result.findings[0].message
        assert "subscriber.dob" in result.findings[0].message

    def test_no_patient_no_patient_finding(self) -> None:
        """No patient → only subscriber finding if subscriber DOB future."""
        future = date.today() + timedelta(days=30)
        v = PADateOfBirthValidator()
        result = v.validate(_make_request(future))
        assert len(result.findings) == 1
        assert result.findings[0].field_name == "subscriber.dob"
