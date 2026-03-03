"""Tests for BaseDeidentifier core logic — PHI stripping, age cap, date reduction."""

from __future__ import annotations

import datetime

import pytest

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import DeidentificationConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def name_config() -> DeidentificationConfig:
    """Config that only strips name fields."""
    return DeidentificationConfig(name_fields=("first_name", "last_name"))


@pytest.fixture()
def id_config() -> DeidentificationConfig:
    """Config that only strips id fields."""
    return DeidentificationConfig(id_fields=("ssn", "member_id"))


@pytest.fixture()
def address_config() -> DeidentificationConfig:
    """Config that only strips address fields."""
    return DeidentificationConfig(address_fields=("street", "city", "zip"))


@pytest.fixture()
def date_config() -> DeidentificationConfig:
    """Config that only reduces date fields."""
    return DeidentificationConfig(date_fields=("service_date", "admit_date"))


@pytest.fixture()
def age_config() -> DeidentificationConfig:
    """Config that only caps age."""
    return DeidentificationConfig(age_field="dob")


@pytest.fixture()
def full_config() -> DeidentificationConfig:
    """Config with all field categories populated."""
    return DeidentificationConfig(
        name_fields=("patient_name",),
        date_fields=("service_date",),
        id_fields=("member_id",),
        address_fields=("address",),
        age_field="dob",
    )


# ---------------------------------------------------------------------------
# Name stripping
# ---------------------------------------------------------------------------


class TestStripNames:
    """Name fields are set to None."""

    def test_single_name_stripped(self, name_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(name_config)
        result = deid.deidentify({"first_name": "John", "last_name": "Doe", "code": "X"})
        assert result["first_name"] is None
        assert result["last_name"] is None

    def test_non_phi_preserved(self, name_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(name_config)
        result = deid.deidentify({"first_name": "Jane", "code": "A123"})
        assert result["code"] == "A123"

    def test_missing_name_field_ignored(self, name_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(name_config)
        result = deid.deidentify({"code": "X"})
        assert "first_name" not in result
        assert result["code"] == "X"

    def test_phi_value_not_in_output(self, name_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(name_config)
        result = deid.deidentify({"first_name": "SensitiveName", "last_name": "SecretSurname"})
        values = list(result.values())
        assert "SensitiveName" not in values
        assert "SecretSurname" not in values


# ---------------------------------------------------------------------------
# ID stripping
# ---------------------------------------------------------------------------


class TestStripIds:
    """Identifier fields are set to None."""

    def test_ids_stripped(self, id_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(id_config)
        result = deid.deidentify({"ssn": "123-45-6789", "member_id": "M123", "code": "Y"})
        assert result["ssn"] is None
        assert result["member_id"] is None
        assert result["code"] == "Y"

    def test_phi_ssn_not_in_output(self, id_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(id_config)
        result = deid.deidentify({"ssn": "999-88-7777", "member_id": "MEM456"})
        values = list(result.values())
        assert "999-88-7777" not in values
        assert "MEM456" not in values


# ---------------------------------------------------------------------------
# Address stripping
# ---------------------------------------------------------------------------


class TestStripAddresses:
    """Address fields are set to None."""

    def test_addresses_stripped(self, address_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(address_config)
        result = deid.deidentify({"street": "123 Main", "city": "NYC", "zip": "10001"})
        assert result["street"] is None
        assert result["city"] is None
        assert result["zip"] is None

    def test_phi_address_not_in_output(self, address_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(address_config)
        result = deid.deidentify({"street": "742 Evergreen Terrace"})
        values = list(result.values())
        assert "742 Evergreen Terrace" not in values


# ---------------------------------------------------------------------------
# Date reduction
# ---------------------------------------------------------------------------


class TestReduceDates:
    """Date fields are reduced to year-only int."""

    def test_iso_string_to_year(self, date_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(date_config)
        result = deid.deidentify({"service_date": "2024-03-15", "admit_date": "2023-12-01"})
        assert result["service_date"] == 2024
        assert result["admit_date"] == 2023

    def test_date_object_to_year(self, date_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(date_config)
        result = deid.deidentify({"service_date": datetime.date(2022, 7, 4)})
        assert result["service_date"] == 2022

    def test_none_date_stays_none(self, date_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(date_config)
        result = deid.deidentify({"service_date": None})
        assert result["service_date"] is None

    def test_invalid_date_string_becomes_none(self, date_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(date_config)
        result = deid.deidentify({"service_date": "not-a-date"})
        assert result["service_date"] is None

    def test_missing_date_field_ignored(self, date_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(date_config)
        result = deid.deidentify({"other": "value"})
        assert "service_date" not in result


# ---------------------------------------------------------------------------
# Age capping
# ---------------------------------------------------------------------------


class TestCapAge:
    """DOB age is computed and capped at 90 per HIPAA Safe Harbor."""

    def test_age_under_90(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        today = datetime.date.today()
        young_dob = today.replace(year=today.year - 30)
        result = deid.deidentify({"dob": young_dob.isoformat()})
        assert result["dob"] == 30

    def test_age_exactly_90(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        today = datetime.date.today()
        dob_90 = today.replace(year=today.year - 90)
        result = deid.deidentify({"dob": dob_90.isoformat()})
        assert result["dob"] == 90

    def test_age_over_90_capped(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        result = deid.deidentify({"dob": "1920-01-01"})
        assert result["dob"] == 90

    def test_age_92_capped_to_90(self, age_config: DeidentificationConfig) -> None:
        """AC-3: age 92 → capped to 90."""
        deid = BaseDeidentifier(age_config)
        today = datetime.date.today()
        dob_92 = today.replace(year=today.year - 92)
        result = deid.deidentify({"dob": dob_92.isoformat()})
        assert result["dob"] == 90

    def test_none_dob(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        result = deid.deidentify({"dob": None})
        assert result["dob"] is None

    def test_invalid_dob_string(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        result = deid.deidentify({"dob": "invalid"})
        assert result["dob"] is None

    def test_missing_age_field_no_error(self, age_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(age_config)
        result = deid.deidentify({"other": "val"})
        assert "dob" not in result

    def test_no_age_field_config(self) -> None:
        """Config with age_field=None skips age processing."""
        cfg = DeidentificationConfig(age_field=None)
        deid = BaseDeidentifier(cfg)
        result = deid.deidentify({"dob": "1990-01-01"})
        assert result["dob"] == "1990-01-01"  # untouched


# ---------------------------------------------------------------------------
# Non-PHI passthrough
# ---------------------------------------------------------------------------


class TestNonPhiPassthrough:
    """Non-PHI fields pass through unchanged."""

    def test_non_phi_fields_preserved(self, full_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(full_config)
        data = {
            "patient_name": "John Doe",
            "service_date": "2024-01-15",
            "member_id": "M123",
            "address": "123 Main St",
            "dob": "1990-06-15",
            "diagnosis_code": "J06.9",
            "procedure_code": "99213",
            "amount": 150.00,
        }
        result = deid.deidentify(data)
        assert result["diagnosis_code"] == "J06.9"
        assert result["procedure_code"] == "99213"
        assert result["amount"] == 150.00

    def test_empty_dict_returns_empty(self) -> None:
        cfg = DeidentificationConfig()
        deid = BaseDeidentifier(cfg)
        assert deid.deidentify({}) == {}


# ---------------------------------------------------------------------------
# Input immutability
# ---------------------------------------------------------------------------


class TestInputImmutability:
    """deidentify() must never mutate the input dict."""

    def test_original_dict_not_mutated(self, full_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(full_config)
        original = {
            "patient_name": "Jane Doe",
            "service_date": "2024-06-01",
            "member_id": "M999",
            "address": "456 Oak Ave",
            "dob": "1985-03-20",
        }
        original_copy = {**original}
        deid.deidentify(original)
        assert original == original_copy


# ---------------------------------------------------------------------------
# Empty config
# ---------------------------------------------------------------------------


class TestEmptyConfig:
    """An empty config returns data unchanged."""

    def test_empty_config_passthrough(self) -> None:
        cfg = DeidentificationConfig()
        deid = BaseDeidentifier(cfg)
        data = {"a": 1, "b": "hello", "c": None}
        result = deid.deidentify(data)
        assert result == data

    def test_empty_config_returns_new_dict(self) -> None:
        cfg = DeidentificationConfig()
        deid = BaseDeidentifier(cfg)
        data = {"x": 1}
        result = deid.deidentify(data)
        assert result is not data


# ---------------------------------------------------------------------------
# Static utilities
# ---------------------------------------------------------------------------


class TestExtractYear:
    """extract_year() static method."""

    def test_iso_string(self) -> None:
        assert BaseDeidentifier.extract_year("2024-03-15") == 2024

    def test_date_object(self) -> None:
        assert BaseDeidentifier.extract_year(datetime.date(2023, 12, 1)) == 2023

    def test_none_input(self) -> None:
        assert BaseDeidentifier.extract_year(None) is None

    def test_invalid_string(self) -> None:
        assert BaseDeidentifier.extract_year("not-a-date") is None

    def test_empty_string(self) -> None:
        assert BaseDeidentifier.extract_year("") is None


class TestComputeAge:
    """compute_age() static method — HIPAA Safe Harbor age cap at 90."""

    def test_young_person(self) -> None:
        today = datetime.date.today()
        dob = today.replace(year=today.year - 25)
        assert BaseDeidentifier.compute_age(dob.isoformat()) == 25

    def test_cap_at_90(self) -> None:
        assert BaseDeidentifier.compute_age("1920-01-01") == 90

    def test_none_input(self) -> None:
        assert BaseDeidentifier.compute_age(None) is None

    def test_empty_string(self) -> None:
        assert BaseDeidentifier.compute_age("") is None

    def test_invalid_string(self) -> None:
        assert BaseDeidentifier.compute_age("bad-date") is None

    def test_birthday_not_yet_passed(self) -> None:
        """If birthday hasn't occurred this year, age is one less."""
        today = datetime.date.today()
        # Use December 31 so it almost certainly hasn't passed for most test dates
        future_birthday = datetime.date(today.year - 40, 12, 31)
        if today.month == 12 and today.day == 31:
            # Edge case: if today IS Dec 31, birthday already passed
            assert BaseDeidentifier.compute_age(future_birthday.isoformat()) == 40
        else:
            assert BaseDeidentifier.compute_age(future_birthday.isoformat()) == 39

    def test_future_dob_returns_none(self) -> None:
        """Future DOB is nonsensical — returns None instead of negative age."""
        assert BaseDeidentifier.compute_age("2030-01-01") is None


# ---------------------------------------------------------------------------
# Config property
# ---------------------------------------------------------------------------


class TestConfigProperty:
    """BaseDeidentifier.config exposes the config."""

    def test_config_accessible(self, full_config: DeidentificationConfig) -> None:
        deid = BaseDeidentifier(full_config)
        assert deid.config is full_config
