"""Tests for shared NPI validation utilities."""

from __future__ import annotations

from claim_validator.validators.rule_based._npi_utils import (
    NPI_REGISTRY_URL,
    _check_luhn_npi,
)


class TestCheckLuhnNPI:
    """Tests for _check_luhn_npi() Luhn algorithm."""

    def test_valid_npi_1234567893(self) -> None:
        assert _check_luhn_npi("1234567893") is True

    def test_valid_npi_1245319599(self) -> None:
        assert _check_luhn_npi("1245319599") is True

    def test_valid_npi_1306849450(self) -> None:
        assert _check_luhn_npi("1306849450") is True

    def test_invalid_npi_1234567890(self) -> None:
        assert _check_luhn_npi("1234567890") is False

    def test_invalid_npi_1234567891(self) -> None:
        assert _check_luhn_npi("1234567891") is False

    def test_empty_string_returns_false(self) -> None:
        assert _check_luhn_npi("") is False

    def test_non_numeric_returns_false(self) -> None:
        assert _check_luhn_npi("abcdefghij") is False

    def test_short_string_returns_false(self) -> None:
        assert _check_luhn_npi("123") is False

    def test_none_like_input_returns_false(self) -> None:
        """TypeError is caught and returns False."""
        assert _check_luhn_npi(None) is False  # type: ignore[arg-type]


class TestNPIRegistryURL:
    """Tests for NPI_REGISTRY_URL constant."""

    def test_url_is_correct(self) -> None:
        assert NPI_REGISTRY_URL == "https://npiregistry.cms.hhs.gov"

    def test_url_is_string(self) -> None:
        assert isinstance(NPI_REGISTRY_URL, str)
