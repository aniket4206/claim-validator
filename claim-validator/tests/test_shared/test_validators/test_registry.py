"""Tests for shared validator registry."""

from __future__ import annotations

import pytest

from claim_validator.exceptions import ConfigurationError
from claim_validator.shared.validators.date import validate_date
from claim_validator.shared.validators.demographics import validate_demographics
from claim_validator.shared.validators.diagnosis import validate_diagnosis
from claim_validator.shared.validators.member_id import validate_member_id
from claim_validator.shared.validators.npi import validate_npi
from claim_validator.shared.validators.payer_id import validate_payer_id
from claim_validator.shared.validators.procedure import validate_procedure
from claim_validator.shared.validators.registry import (
    VALIDATORS,
    ValidatorFunc,
    get_validator,
    list_validators,
)

EXPECTED_IDS = [
    "date",
    "demographics",
    "diagnosis",
    "member_id",
    "npi",
    "payer_id",
    "procedure",
]


class TestRegistryPopulation:
    """Registry is populated at import time with all 7 shared validators."""

    def test_all_seven_registered(self) -> None:
        assert len(VALIDATORS) == 7

    def test_registered_ids_match(self) -> None:
        assert sorted(VALIDATORS.keys()) == EXPECTED_IDS

    def test_registry_populated_at_import(self) -> None:
        # VALIDATORS is a module-level dict populated by _register_all()
        # at import time — it should never be empty after import.
        assert VALIDATORS, "Registry should be populated at import time"


class TestGetValidator:
    """get_validator returns the correct function or raises ConfigurationError."""

    @pytest.mark.parametrize(
        ("vid", "expected_func"),
        [
            ("npi", validate_npi),
            ("date", validate_date),
            ("member_id", validate_member_id),
            ("demographics", validate_demographics),
            ("diagnosis", validate_diagnosis),
            ("procedure", validate_procedure),
            ("payer_id", validate_payer_id),
        ],
    )
    def test_returns_correct_function(
        self, vid: str, expected_func: ValidatorFunc
    ) -> None:
        assert get_validator(vid) is expected_func

    def test_unknown_id_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Unknown shared validator"):
            get_validator("NONEXISTENT")

    def test_error_message_lists_available(self) -> None:
        with pytest.raises(ConfigurationError, match="Available:"):
            get_validator("bogus")


class TestListValidators:
    """list_validators returns sorted list of all registered IDs."""

    def test_returns_sorted_list(self) -> None:
        result = list_validators()
        assert result == EXPECTED_IDS

    def test_returns_new_list_each_call(self) -> None:
        r1 = list_validators()
        r2 = list_validators()
        assert r1 is not r2
        assert r1 == r2


class TestCallable:
    """Each registered function is callable."""

    @pytest.mark.parametrize("vid", EXPECTED_IDS)
    def test_validator_is_callable(self, vid: str) -> None:
        func = get_validator(vid)
        assert callable(func)
