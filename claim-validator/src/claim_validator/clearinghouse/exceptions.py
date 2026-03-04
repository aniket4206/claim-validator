"""Exception hierarchy for clearinghouse operations."""

from __future__ import annotations

from claim_validator.exceptions import ClaimValidatorError


class ClearinghouseError(ClaimValidatorError):
    """Base exception for clearinghouse operations."""


class ClearinghouseAuthError(ClearinghouseError):
    """Authentication or authorization failure (HTTP 401/403)."""


class ClearinghouseValidationError(ClearinghouseError):
    """Request validation failure (HTTP 4xx, non-auth)."""


class ClearinghouseTimeoutError(ClearinghouseError):
    """Clearinghouse request timed out."""


class ClearinghouseServerError(ClearinghouseError):
    """Clearinghouse server error (HTTP 5xx)."""
