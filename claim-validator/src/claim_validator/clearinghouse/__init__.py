"""Clearinghouse client abstraction layer.

Provides a pluggable interface for healthcare clearinghouse providers
(Stedi, Claim.MD, Waystar) with a unified ABC, factory, exception
hierarchy, and response models.
"""

from __future__ import annotations

from claim_validator.clearinghouse.auth import HMACAuth
from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.factory import get_clearinghouse_client
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)

__all__ = [
    "BaseClearinghouseClient",
    "ClaimStatusResponse",
    "ClearinghouseAuthError",
    "ClearinghouseEligibilityResponse",
    "ClearinghouseError",
    "ClearinghouseServerError",
    "ClearinghouseTimeoutError",
    "ClearinghouseValidationError",
    "get_clearinghouse_client",
    "HMACAuth",
    "SubmissionResult",
]
