"""Shared de-identification — BaseDeidentifier and domain configurations."""

from __future__ import annotations

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import (
    CLAIM_DEID_CONFIG,
    ELIGIBILITY_DEID_CONFIG,
    PA_DEID_CONFIG,
    DeidentificationConfig,
)

__all__ = [
    "BaseDeidentifier",
    "CLAIM_DEID_CONFIG",
    "DeidentificationConfig",
    "ELIGIBILITY_DEID_CONFIG",
    "PA_DEID_CONFIG",
]
