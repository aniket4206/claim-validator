"""Tests for constants module — StrEnum values."""

from __future__ import annotations

from enum import StrEnum

from claim_validator import ClaimType, Severity


class TestSeverity:
    def test_is_str_enum(self) -> None:
        assert issubclass(Severity, StrEnum)

    def test_error_value(self) -> None:
        assert Severity.ERROR == "error"

    def test_warning_value(self) -> None:
        assert Severity.WARNING == "warning"

    def test_members(self) -> None:
        assert set(Severity) == {Severity.ERROR, Severity.WARNING}


class TestClaimType:
    def test_is_str_enum(self) -> None:
        assert issubclass(ClaimType, StrEnum)

    def test_professional_value(self) -> None:
        assert ClaimType.PROFESSIONAL == "professional"

    def test_institutional_value(self) -> None:
        assert ClaimType.INSTITUTIONAL == "institutional"

    def test_members(self) -> None:
        assert set(ClaimType) == {ClaimType.PROFESSIONAL, ClaimType.INSTITUTIONAL}
