"""Clearinghouse client abstraction layer.

Provides a pluggable interface for healthcare clearinghouse providers
(Stedi, Claim.MD, Waystar) with a unified ABC, factory, exception
hierarchy, and response models.
"""

from __future__ import annotations

from typing import Any

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


def build_clearinghouse_client(
    config: dict[str, Any] | None,
) -> BaseClearinghouseClient | None:
    """Build a clearinghouse client from a config dict.

    Convenience wrapper around :func:`get_clearinghouse_client` that
    extracts the ``provider`` key and passes remaining keys as kwargs.
    Returns ``None`` when *config* is ``None`` or empty.

    Args:
        config: Dict with ``provider`` key (required) plus provider-specific
            keys (``api_key``, ``secret``, ``account_key``, ``base_url``, etc.).

    Returns:
        A configured clearinghouse client, or ``None``.
    """
    if not config:
        return None
    config = dict(config)  # shallow copy to avoid mutating caller's dict
    provider = config.pop("provider")
    return get_clearinghouse_client(provider, **config)


__all__ = [
    "BaseClearinghouseClient",
    "ClaimStatusResponse",
    "ClearinghouseAuthError",
    "ClearinghouseEligibilityResponse",
    "ClearinghouseError",
    "ClearinghouseServerError",
    "ClearinghouseTimeoutError",
    "ClearinghouseValidationError",
    "build_clearinghouse_client",
    "get_clearinghouse_client",
    "HMACAuth",
    "SubmissionResult",
]
