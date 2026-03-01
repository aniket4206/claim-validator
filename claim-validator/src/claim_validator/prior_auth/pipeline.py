"""PriorAuthPipeline — three-phase PA validation orchestrator."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.prior_auth.models.result import PriorAuthResult
from claim_validator.validators.registry import ValidatorRegistry

if TYPE_CHECKING:
    from claim_validator.prior_auth.models.request import PriorAuthRequest
    from claim_validator.validators.base import BaseValidator


class PriorAuthPipeline:
    """Three-phase PA validation pipeline.

    Phase 1: Rule-based validators (offline, synchronous)
    Phase 2: Clearinghouse 278 submission (future — Epic 3)
    Phase 3: AI interpretation (future — Epic 4)
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
    ) -> PriorAuthPipeline:
        """Create a pipeline from settings."""
        if settings is None:
            settings = ClaimValidatorSettings()
        registry = ValidatorRegistry()
        rule_vals = registry.create_validators(settings.pa_rule_validators)
        return cls(rule_validators=rule_vals)

    def run(self, request: PriorAuthRequest) -> PriorAuthResult:
        """Execute the PA validation pipeline.

        Currently implements Phase 1 (rule-based) only.
        Phases 2 and 3 will be added in future epics.
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
                        context={"error": str(exc)},
                    )
                )

        elapsed = time.perf_counter() - start
        return PriorAuthResult(
            findings=findings,
            execution_time=elapsed,
        )
