"""Enums and constants for the eligibility verification module."""

from __future__ import annotations

from enum import StrEnum


class CoverageStatus(StrEnum):
    """Coverage status from eligibility response."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
