"""Tests for prior authorization enums and constants."""

from __future__ import annotations

import pytest

from claim_validator.prior_auth.constants import (
    CertificationActionCode,
    CertificationTypeCode,
    RequestCategoryCode,
)

# ---------------------------------------------------------------------------
# CertificationActionCode
# ---------------------------------------------------------------------------


class TestCertificationActionCode:
    def test_all_hcr_action_codes_present(self) -> None:
        expected = {"A1", "A2", "A3", "A4", "A6", "CT", "NA"}
        actual = {member.value for member in CertificationActionCode}
        assert actual == expected

    def test_certified_in_total(self) -> None:
        assert CertificationActionCode.CERTIFIED_IN_TOTAL == "A1"

    def test_certified_partial(self) -> None:
        assert CertificationActionCode.CERTIFIED_PARTIAL == "A2"

    def test_not_certified(self) -> None:
        assert CertificationActionCode.NOT_CERTIFIED == "A3"

    def test_pended(self) -> None:
        assert CertificationActionCode.PENDED == "A4"

    def test_modified(self) -> None:
        assert CertificationActionCode.MODIFIED == "A6"

    def test_contact_payer(self) -> None:
        assert CertificationActionCode.CONTACT_PAYER == "CT"

    def test_no_action_required(self) -> None:
        assert CertificationActionCode.NO_ACTION_REQUIRED == "NA"

    def test_is_str_subclass(self) -> None:
        assert isinstance(CertificationActionCode.CERTIFIED_IN_TOTAL, str)

    def test_lookup_by_value(self) -> None:
        assert CertificationActionCode("A1") == CertificationActionCode.CERTIFIED_IN_TOTAL

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            CertificationActionCode("ZZ")


# ---------------------------------------------------------------------------
# RequestCategoryCode
# ---------------------------------------------------------------------------


class TestRequestCategoryCode:
    def test_all_category_codes_present(self) -> None:
        expected = {"AR", "HS", "SC", "IN"}
        actual = {member.value for member in RequestCategoryCode}
        assert actual == expected

    def test_health_services_review(self) -> None:
        assert RequestCategoryCode.HEALTH_SERVICES_REVIEW == "HS"

    def test_admission_review(self) -> None:
        assert RequestCategoryCode.ADMISSION_REVIEW == "AR"

    def test_specialty_care_review(self) -> None:
        assert RequestCategoryCode.SPECIALTY_CARE_REVIEW == "SC"

    def test_initial_review(self) -> None:
        assert RequestCategoryCode.INITIAL_REVIEW == "IN"

    def test_is_str_subclass(self) -> None:
        assert isinstance(RequestCategoryCode.HEALTH_SERVICES_REVIEW, str)


# ---------------------------------------------------------------------------
# CertificationTypeCode
# ---------------------------------------------------------------------------


class TestCertificationTypeCode:
    def test_all_type_codes_present(self) -> None:
        expected = {"I", "R", "S", "E"}
        actual = {member.value for member in CertificationTypeCode}
        assert actual == expected

    def test_initial(self) -> None:
        assert CertificationTypeCode.INITIAL == "I"

    def test_renewal(self) -> None:
        assert CertificationTypeCode.RENEWAL == "R"

    def test_revised(self) -> None:
        assert CertificationTypeCode.REVISED == "S"

    def test_extension(self) -> None:
        assert CertificationTypeCode.EXTENSION == "E"

    def test_is_str_subclass(self) -> None:
        assert isinstance(CertificationTypeCode.INITIAL, str)
