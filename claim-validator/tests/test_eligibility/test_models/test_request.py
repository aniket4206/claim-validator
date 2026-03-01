"""Tests for EligibilityRequest model."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from claim_validator.eligibility.models.request import EligibilityRequest


class TestEligibilityRequestConstruction:
    """AC 1: dict construction, model_validate, frozen, coercion."""

    def test_construct_from_dict(self, valid_eligibility_dict: dict[str, Any]) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.provider_npi == "1234567893"
        assert request.payer_id == "60054"
        assert request.subscriber_id == "XYZ123456"

    def test_model_validate(self, valid_eligibility_dict: dict[str, Any]) -> None:
        request = EligibilityRequest.model_validate(valid_eligibility_dict)
        assert request.provider_npi == "1234567893"
        assert request.subscriber_first_name == "Jane"

    def test_frozen_immutability(self, valid_eligibility_dict: dict[str, Any]) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        with pytest.raises(ValidationError):
            request.provider_npi = "changed"  # type: ignore[misc]

    def test_date_string_coercion(self, valid_eligibility_dict: dict[str, Any]) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        assert isinstance(request.subscriber_dob, date)
        assert request.subscriber_dob == date(1985, 3, 15)

    def test_date_of_service_coercion(self, valid_eligibility_dict: dict[str, Any]) -> None:
        valid_eligibility_dict["date_of_service"] = "2026-04-01"
        request = EligibilityRequest(**valid_eligibility_dict)
        assert isinstance(request.date_of_service, date)
        assert request.date_of_service == date(2026, 4, 1)

    def test_date_object_accepted(self, valid_eligibility_dict: dict[str, Any]) -> None:
        valid_eligibility_dict["subscriber_dob"] = date(1985, 3, 15)
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.subscriber_dob == date(1985, 3, 15)


class TestEligibilityRequestFields:
    """AC 2: all required and optional fields."""

    def test_required_fields_present(self, valid_eligibility_dict: dict[str, Any]) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.provider_npi == "1234567893"
        assert request.payer_id == "60054"
        assert request.subscriber_id == "XYZ123456"
        assert request.subscriber_first_name == "Jane"
        assert request.subscriber_last_name == "Doe"
        assert request.subscriber_dob == date(1985, 3, 15)

    def test_optional_fields_default_none(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.provider_taxonomy is None
        assert request.date_of_service is None
        assert request.patient_first_name is None
        assert request.patient_last_name is None
        assert request.patient_dob is None
        assert request.relationship_code is None

    def test_service_type_code_default(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.service_type_code == "30"

    def test_service_type_code_override(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        valid_eligibility_dict["service_type_code"] = "47"
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.service_type_code == "47"

    def test_dependent_fields_populated(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        valid_eligibility_dict["patient_first_name"] = "John"
        valid_eligibility_dict["patient_last_name"] = "Doe"
        valid_eligibility_dict["patient_dob"] = "2010-06-15"
        valid_eligibility_dict["relationship_code"] = "19"
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.patient_first_name == "John"
        assert request.patient_last_name == "Doe"
        assert request.patient_dob == date(2010, 6, 15)
        assert request.relationship_code == "19"

    def test_provider_taxonomy_populated(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        valid_eligibility_dict["provider_taxonomy"] = "207Q00000X"
        request = EligibilityRequest(**valid_eligibility_dict)
        assert request.provider_taxonomy == "207Q00000X"


class TestEligibilityRequestValidation:
    """Missing required fields should raise."""

    def test_missing_provider_npi_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["provider_npi"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)

    def test_missing_payer_id_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["payer_id"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)

    def test_missing_subscriber_id_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["subscriber_id"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)

    def test_missing_subscriber_dob_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["subscriber_dob"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)

    def test_missing_subscriber_first_name_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["subscriber_first_name"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)

    def test_missing_subscriber_last_name_raises(
        self, valid_eligibility_dict: dict[str, Any]
    ) -> None:
        del valid_eligibility_dict["subscriber_last_name"]
        with pytest.raises(ValidationError):
            EligibilityRequest(**valid_eligibility_dict)
