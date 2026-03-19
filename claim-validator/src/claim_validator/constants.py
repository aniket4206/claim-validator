"""Enums and constants for claim-validator."""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    """Severity level for validation findings."""

    ERROR = "error"
    WARNING = "warning"


class ClaimType(StrEnum):
    """Type of healthcare claim (X12 transaction set)."""

    PROFESSIONAL = "professional"
    INSTITUTIONAL = "institutional"
    DENTAL = "dental"

    # X12 aliases
    EDI_837P = "professional"
    EDI_837I = "institutional"
    EDI_837D = "dental"
