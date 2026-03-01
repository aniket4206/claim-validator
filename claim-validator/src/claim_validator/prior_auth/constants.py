"""Enums and constants for prior authorization module."""

from __future__ import annotations

from enum import StrEnum


class CertificationActionCode(StrEnum):
    """HCR action codes from X12 278 response (005010X217)."""

    CERTIFIED_IN_TOTAL = "A1"
    CERTIFIED_PARTIAL = "A2"
    NOT_CERTIFIED = "A3"
    PENDED = "A4"
    MODIFIED = "A6"
    CONTACT_PAYER = "CT"
    NO_ACTION_REQUIRED = "NA"


class RequestCategoryCode(StrEnum):
    """UM request category codes for 278 prior authorization requests."""

    ADMISSION_REVIEW = "AR"
    HEALTH_SERVICES_REVIEW = "HS"
    SPECIALTY_CARE_REVIEW = "SC"
    INITIAL_REVIEW = "IN"


class CertificationTypeCode(StrEnum):
    """UM certification type codes for 278 prior authorization requests."""

    INITIAL = "I"
    RENEWAL = "R"
    REVISED = "S"
    EXTENSION = "E"
