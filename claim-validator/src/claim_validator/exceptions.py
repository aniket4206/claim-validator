"""Exception hierarchy for claim-validator."""

from __future__ import annotations


class ClaimValidatorError(Exception):
    """Base exception for claim-validator library."""


class ValidationError(ClaimValidatorError):
    """Invalid input data (malformed claim, missing required fields)."""


class ConfigurationError(ClaimValidatorError):
    """Invalid library configuration (bad validator path, missing provider)."""


class LLMError(ClaimValidatorError):
    """LLM provider communication failure."""


class CodeTableError(ClaimValidatorError):
    """Code table loading or lookup failure."""


class PayerRoutingError(ClaimValidatorError):
    """Payer routing resolution failure (unknown payer ID, no routes available)."""
