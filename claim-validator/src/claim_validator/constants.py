"""Enums and constants for claim-validator."""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Severity level for validation findings."""

    ERROR = "error"
    WARNING = "warning"


class ClaimType(StrEnum):
    """Type of healthcare claim."""

    PROFESSIONAL = "professional"
    INSTITUTIONAL = "institutional"
