"""EligibilityPipeline — two-phase eligibility validation orchestrator."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.models.results import Finding
from claim_validator.validators.registry import ValidatorRegistry

if TYPE_CHECKING:
    from claim_validator.eligibility.models.request import EligibilityRequest
    from claim_validator.validators.base import BaseValidator


_SEVERITY_ORDER: dict[Severity, int] = {Severity.ERROR: 0, Severity.WARNING: 1}


class EligibilityPipeline:
    """Two-phase eligibility validation pipeline.

    Phase 1: Rule-based validators (offline, synchronous)
    Phase 2: AI interpretation (future)
    """

    def __init__(
        self,
        *,
        rule_validators: list[BaseValidator],
    ) -> None:
        self._rule_validators = rule_validators

    @classmethod
    def from_settings(
        cls,
        settings: ClaimValidatorSettings | None = None,
    ) -> EligibilityPipeline:
        """Create a pipeline from settings."""
        if settings is None:
            settings = ClaimValidatorSettings()
        registry = ValidatorRegistry()
        rule_vals = registry.create_validators(
            settings.eligibility_rule_validators,
        )
        return cls(rule_validators=rule_vals)

    def run(self, request: EligibilityRequest) -> EligibilityResult:
        """Execute the eligibility validation pipeline.

        Currently implements Phase 1 (rule-based) only.
        Phase 2 (AI) will be added in a future epic.
        """
        start = time.perf_counter()
        findings: list[Finding] = []

        # Phase 1: Rule-based validators
        for validator in self._rule_validators:
            try:
                output = validator.validate(request)
                findings.extend(output.findings)
            except Exception as exc:
                findings.append(
                    Finding(
                        code="VALIDATOR_ERROR",
                        message="Validator raised an unexpected exception",
                        severity=Severity.ERROR,
                        field_name="",
                        suggestion="Check validator implementation",
                        context={
                            "validator": type(validator).__name__,
                            "error": str(exc),
                        },
                    )
                )

        findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))

        elapsed = time.perf_counter() - start
        return EligibilityResult(
            findings=findings,
            execution_time=elapsed,
        )
