"""Tests for DeidentificationConfig creation, immutability, and field types."""

from __future__ import annotations

import pytest

from claim_validator.shared.deidentifier.config import (
    CLAIM_DEID_CONFIG,
    ELIGIBILITY_DEID_CONFIG,
    PA_DEID_CONFIG,
    DeidentificationConfig,
)


class TestDeidentificationConfigCreation:
    """DeidentificationConfig can be created with all field categories."""

    def test_all_fields_specified(self) -> None:
        cfg = DeidentificationConfig(
            name_fields=("first_name", "last_name"),
            date_fields=("service_date",),
            id_fields=("ssn",),
            address_fields=("address",),
            age_field="dob",
        )
        assert cfg.name_fields == ("first_name", "last_name")
        assert cfg.date_fields == ("service_date",)
        assert cfg.id_fields == ("ssn",)
        assert cfg.address_fields == ("address",)
        assert cfg.age_field == "dob"

    def test_defaults_are_empty(self) -> None:
        cfg = DeidentificationConfig()
        assert cfg.name_fields == ()
        assert cfg.date_fields == ()
        assert cfg.id_fields == ()
        assert cfg.address_fields == ()
        assert cfg.age_field is None

    def test_age_field_none(self) -> None:
        cfg = DeidentificationConfig(age_field=None)
        assert cfg.age_field is None

    def test_age_field_str(self) -> None:
        cfg = DeidentificationConfig(age_field="patient_dob")
        assert cfg.age_field == "patient_dob"

    def test_single_name_field(self) -> None:
        cfg = DeidentificationConfig(name_fields=("full_name",))
        assert cfg.name_fields == ("full_name",)

    def test_multiple_id_fields(self) -> None:
        cfg = DeidentificationConfig(id_fields=("ssn", "member_id", "group_num"))
        assert len(cfg.id_fields) == 3


class TestDeidentificationConfigImmutability:
    """DeidentificationConfig is frozen — attributes cannot be reassigned."""

    def test_frozen_name_fields(self) -> None:
        cfg = DeidentificationConfig(name_fields=("name",))
        with pytest.raises(AttributeError):
            cfg.name_fields = ("other",)  # type: ignore[misc]

    def test_frozen_date_fields(self) -> None:
        cfg = DeidentificationConfig(date_fields=("dob",))
        with pytest.raises(AttributeError):
            cfg.date_fields = ("other",)  # type: ignore[misc]

    def test_frozen_id_fields(self) -> None:
        cfg = DeidentificationConfig(id_fields=("ssn",))
        with pytest.raises(AttributeError):
            cfg.id_fields = ("other",)  # type: ignore[misc]

    def test_frozen_address_fields(self) -> None:
        cfg = DeidentificationConfig(address_fields=("addr",))
        with pytest.raises(AttributeError):
            cfg.address_fields = ("other",)  # type: ignore[misc]

    def test_frozen_age_field(self) -> None:
        cfg = DeidentificationConfig(age_field="dob")
        with pytest.raises(AttributeError):
            cfg.age_field = "other"  # type: ignore[misc]


class TestDeidentificationConfigValidation:
    """DeidentificationConfig validates field overlap at creation time."""

    def test_age_field_in_date_fields_raises(self) -> None:
        with pytest.raises(ValueError, match="must not also appear in date_fields"):
            DeidentificationConfig(date_fields=("dob",), age_field="dob")

    def test_age_field_not_in_date_fields_ok(self) -> None:
        cfg = DeidentificationConfig(date_fields=("service_date",), age_field="dob")
        assert cfg.age_field == "dob"

    def test_age_field_none_with_date_fields_ok(self) -> None:
        cfg = DeidentificationConfig(date_fields=("dob",), age_field=None)
        assert cfg.age_field is None


class TestDeidentificationConfigFieldTypes:
    """All field tuples are typed as tuple[str, ...] and age_field as str | None."""

    def test_name_fields_is_tuple(self) -> None:
        cfg = DeidentificationConfig(name_fields=("a", "b"))
        assert isinstance(cfg.name_fields, tuple)

    def test_date_fields_is_tuple(self) -> None:
        cfg = DeidentificationConfig(date_fields=("a",))
        assert isinstance(cfg.date_fields, tuple)

    def test_id_fields_is_tuple(self) -> None:
        cfg = DeidentificationConfig(id_fields=("a",))
        assert isinstance(cfg.id_fields, tuple)

    def test_address_fields_is_tuple(self) -> None:
        cfg = DeidentificationConfig(address_fields=("a",))
        assert isinstance(cfg.address_fields, tuple)


class TestDomainConfigsExist:
    """Domain configs are importable and have correct types."""

    def test_claim_config_is_deidentification_config(self) -> None:
        assert isinstance(CLAIM_DEID_CONFIG, DeidentificationConfig)

    def test_eligibility_config_is_deidentification_config(self) -> None:
        assert isinstance(ELIGIBILITY_DEID_CONFIG, DeidentificationConfig)

    def test_pa_config_is_deidentification_config(self) -> None:
        assert isinstance(PA_DEID_CONFIG, DeidentificationConfig)

    def test_claim_has_age_field(self) -> None:
        assert CLAIM_DEID_CONFIG.age_field == "patient_dob"

    def test_eligibility_no_age_field(self) -> None:
        assert ELIGIBILITY_DEID_CONFIG.age_field is None

    def test_pa_has_age_field(self) -> None:
        assert PA_DEID_CONFIG.age_field == "patient_dob"

    def test_claim_has_name_fields(self) -> None:
        assert CLAIM_DEID_CONFIG.name_fields == ("patient_first_name", "patient_last_name")

    def test_claim_has_address_fields(self) -> None:
        assert len(CLAIM_DEID_CONFIG.address_fields) == 4

    def test_eligibility_no_address_fields(self) -> None:
        assert ELIGIBILITY_DEID_CONFIG.address_fields == ()

    def test_pa_has_address_fields(self) -> None:
        assert PA_DEID_CONFIG.address_fields == ("patient_address",)
