"""Enums and constants for the eligibility verification module."""

from __future__ import annotations

from enum import StrEnum


class CoverageStatus(StrEnum):
    """Coverage status from 271 eligibility response."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
