"""Tests for eligibility constants — AC 5."""

from __future__ import annotations

from enum import StrEnum

from claim_validator.eligibility.constants import CoverageStatus


class TestCoverageStatus:
    """AC 5: CoverageStatus is a StrEnum with ACTIVE, INACTIVE, UNKNOWN."""

    def test_is_str_enum(self) -> None:
        assert issubclass(CoverageStatus, StrEnum)

    def test_has_three_members(self) -> None:
        assert len(CoverageStatus) == 3

    def test_active_value(self) -> None:
        assert CoverageStatus.ACTIVE == "active"
        assert CoverageStatus.ACTIVE.value == "active"

    def test_inactive_value(self) -> None:
        assert CoverageStatus.INACTIVE == "inactive"
        assert CoverageStatus.INACTIVE.value == "inactive"

    def test_unknown_value(self) -> None:
        assert CoverageStatus.UNKNOWN == "unknown"
        assert CoverageStatus.UNKNOWN.value == "unknown"

    def test_values_are_lowercase(self) -> None:
        for member in CoverageStatus:
            assert member.value == member.value.lower()

    def test_string_comparison(self) -> None:
        assert CoverageStatus.ACTIVE == "active"
        assert CoverageStatus.INACTIVE == "inactive"
