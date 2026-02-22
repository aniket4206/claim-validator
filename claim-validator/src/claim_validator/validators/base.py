"""BaseValidator abstract base class."""

from __future__ import annotations

import abc
from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput


class BaseValidator(abc.ABC):
    """Abstract base class for all validators (rule-based and AI).

    Subclasses must set a ``name`` class attribute and implement ``validate()``.
    """

    name: str

    @abc.abstractmethod
    def validate(self, claim: ClaimData) -> ValidatorOutput:
        """Validate a claim and return findings.

        Must be stateless, must not modify the claim, and must return
        ``ValidatorOutput`` rather than raising for validation failures.
        """

    def _make_output(self, findings: list[Finding]) -> ValidatorOutput:
        """Build a ValidatorOutput from findings."""
        return ValidatorOutput(validator_name=self.name, findings=findings)

    def _make_finding(
        self,
        *,
        code: str,
        message: str,
        severity: Severity,
        field_name: str,
        line_number: int | None = None,
        suggestion: str = "",
        context: dict[str, Any] | None = None,
    ) -> Finding:
        """Convenience factory for creating a Finding."""
        return Finding(
            code=code,
            message=message,
            severity=severity,
            field_name=field_name,
            line_number=line_number,
            suggestion=suggestion,
            context=context,
        )
