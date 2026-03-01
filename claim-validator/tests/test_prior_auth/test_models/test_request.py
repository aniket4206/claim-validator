"""Tests for prior authorization request models."""

from __future__ import annotations

from datetime import date

import pydantic
import pytest

from claim_validator.prior_auth.constants import (
    CertificationTypeCode,
    RequestCategoryCode,
)
from claim_validator.prior_auth.models.request import (
    PatientInfo,
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)

# ---------------------------------------------------------------------------
# SubscriberInfo
# ---------------------------------------------------------------------------


class TestSubscriberInfo:
    def test_create_with_required_fields(self) -> None:
        sub = SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        )
        assert sub.member_id == "MEM001"
        assert sub.first_name == "Jane"
        assert sub.last_name == "Doe"
        assert sub.dob == date(1985, 3, 15)

    def test_frozen(self) -> None:
        sub = SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        )
        with pytest.raises(pydantic.ValidationError):
            sub.member_id = "CHANGED"  # type: ignore[misc]

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                # missing last_name
                dob=date(1985, 3, 15),
            )  # type: ignore[call-arg]

    def test_dob_coerces_string(self) -> None:
        """strict=False allows string -> date coercion."""
        sub = SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob="1985-03-15",  # type: ignore[arg-type]
        )
        assert sub.dob == date(1985, 3, 15)


# ---------------------------------------------------------------------------
# PatientInfo
# ---------------------------------------------------------------------------


class TestPatientInfo:
    def test_create_with_required_fields(self) -> None:
        patient = PatientInfo(
            first_name="John",
            last_name="Doe",
            dob=date(2010, 6, 1),
        )
        assert patient.first_name == "John"
        assert patient.gender is None
        assert patient.relationship is None

    def test_create_with_all_fields(self) -> None:
        patient = PatientInfo(
            first_name="John",
            last_name="Doe",
            dob=date(2010, 6, 1),
            gender="M",
            relationship="19",
        )
        assert patient.gender == "M"
        assert patient.relationship == "19"

    def test_frozen(self) -> None:
        patient = PatientInfo(
            first_name="John",
            last_name="Doe",
            dob=date(2010, 6, 1),
        )
        with pytest.raises(pydantic.ValidationError):
            patient.first_name = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ServiceLine
# ---------------------------------------------------------------------------


class TestServiceLine:
    def test_create_with_defaults(self) -> None:
        line = ServiceLine(cpt_code="99213")
        assert line.cpt_code == "99213"
        assert line.quantity == 1
        assert line.from_date is None
        assert line.to_date is None
        assert line.place_of_service_code is None

    def test_create_with_all_fields(self) -> None:
        line = ServiceLine(
            cpt_code="27447",
            quantity=1,
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 1),
            place_of_service_code="21",
        )
        assert line.cpt_code == "27447"
        assert line.from_date == date(2026, 4, 1)
        assert line.place_of_service_code == "21"

    def test_frozen(self) -> None:
        line = ServiceLine(cpt_code="99213")
        with pytest.raises(pydantic.ValidationError):
            line.cpt_code = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PriorAuthRequest
# ---------------------------------------------------------------------------


class TestPriorAuthRequest:
    def test_create_minimal(self, subscriber: SubscriberInfo) -> None:
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=subscriber,
        )
        assert req.requester_npi == "1234567893"
        assert req.subscriber.member_id == "MEM001"
        assert req.patient is None
        assert req.diagnosis_codes == []
        assert req.service_lines == []
        assert req.request_category_code == RequestCategoryCode.HEALTH_SERVICES_REVIEW
        assert req.certification_type_code == CertificationTypeCode.INITIAL
        assert req.clinical_info is None
        assert req.requester_taxonomy is None
        assert req.payer_id is None

    def test_create_full(self, subscriber: SubscriberInfo) -> None:
        patient = PatientInfo(
            first_name="John",
            last_name="Doe",
            dob=date(2010, 6, 1),
        )
        line = ServiceLine(cpt_code="27447", quantity=1)
        req = PriorAuthRequest(
            requester_npi="1234567893",
            requester_taxonomy="207X00000X",
            payer_id="12345",
            subscriber=subscriber,
            patient=patient,
            diagnosis_codes=["M17.11"],
            service_lines=[line],
            request_category_code=RequestCategoryCode.SPECIALTY_CARE_REVIEW,
            certification_type_code=CertificationTypeCode.INITIAL,
            clinical_info="Patient has severe OA.",
        )
        assert req.patient is not None
        assert req.patient.first_name == "John"
        assert len(req.diagnosis_codes) == 1
        assert len(req.service_lines) == 1
        assert req.request_category_code == RequestCategoryCode.SPECIALTY_CARE_REVIEW

    def test_frozen(self, subscriber: SubscriberInfo) -> None:
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=subscriber,
        )
        with pytest.raises(pydantic.ValidationError):
            req.requester_npi = "CHANGED"  # type: ignore[misc]

    def test_missing_required_npi_raises(self, subscriber: SubscriberInfo) -> None:
        with pytest.raises(pydantic.ValidationError):
            PriorAuthRequest(subscriber=subscriber)  # type: ignore[call-arg]

    def test_missing_required_subscriber_raises(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            PriorAuthRequest(requester_npi="1234567893")  # type: ignore[call-arg]

    def test_enum_coercion_request_category(self, subscriber: SubscriberInfo) -> None:
        """strict=False allows string -> enum coercion."""
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=subscriber,
            request_category_code="AR",  # type: ignore[arg-type]
        )
        assert req.request_category_code == RequestCategoryCode.ADMISSION_REVIEW

    def test_enum_coercion_certification_type(self, subscriber: SubscriberInfo) -> None:
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=subscriber,
            certification_type_code="R",  # type: ignore[arg-type]
        )
        assert req.certification_type_code == CertificationTypeCode.RENEWAL

    def test_model_validate_from_dict(self) -> None:
        """AC1: PriorAuthRequest.model_validate(request_dict) works."""
        data = {
            "requester_npi": "1234567893",
            "subscriber": {
                "member_id": "MEM001",
                "first_name": "Jane",
                "last_name": "Doe",
                "dob": "1985-03-15",
            },
            "diagnosis_codes": ["M17.11"],
            "service_lines": [{"cpt_code": "27447"}],
        }
        req = PriorAuthRequest.model_validate(data)
        assert req.requester_npi == "1234567893"
        assert req.subscriber.member_id == "MEM001"
        assert req.subscriber.dob == date(1985, 3, 15)
        assert len(req.diagnosis_codes) == 1
        assert len(req.service_lines) == 1
        assert req.service_lines[0].cpt_code == "27447"
