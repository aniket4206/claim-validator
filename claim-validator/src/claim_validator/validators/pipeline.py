"""ValidationPipeline — two-phase execution orchestrator.

Delegates rule-phase execution to ``BasePipeline``.
AI phase remains domain-specific (multi-validator pattern).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.deidentifier.deidentifier import ClaimDeidentifier
from claim_validator.exceptions import LLMError
from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import (
    Finding,
    PhaseResult,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.shared.pipeline import BasePipeline, PipelineConfig
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.validators.registry import ValidatorRegistry

if TYPE_CHECKING:
    from claim_validator.validators.ai.base import BaseAIValidator
    from claim_validator.validators.base import BaseValidator


class _PipelineBuilder:
    """Fluent builder for constructing custom pipelines."""

    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def add(
        self, validator: BaseValidator | type[BaseValidator],
    ) -> _PipelineBuilder:
        """Add a validator instance or class to the pipeline."""
        if isinstance(validator, type):
            validator = validator()
        self._validators.append(validator)
        return self

    def build(self) -> ValidationPipeline:
        """Build a ValidationPipeline from added validators."""
        return ValidationPipeline(
            rule_validators=list(self._validators),
            ai_validators=[],
            skip_ai_on_rule_failure=True,
        )


class ValidationPipeline:
    """Two-phase validation pipeline orchestrator.

    Phase 1: Rule-based validators (delegated to BasePipeline)
    Phase 2: AI validators (network, conditional on phase 1)
    """

    def __init__(
        self,
        *,
        rule_validators: list[BaseValidator],
        ai_validators: list[BaseAIValidator],
        skip_ai_on_rule_failure: bool = True,
        clearinghouse_client: object | None = None,
    ) -> None:
        self._rule_validators = rule_validators
        self._ai_validators = ai_validators
        self._skip_ai_on_rule_failure = skip_ai_on_rule_failure
        # BasePipeline for rule-phase + clearinghouse execution
        self._base_pipeline = BasePipeline(PipelineConfig(
            domain="claim",
            validators=tuple(rule_validators),
            clearinghouse_client=clearinghouse_client,
            code_prefix="",
        ))

    @classmethod
    def from_settings(
        cls,
        settings: ClaimValidatorSettings | None = None,
    ) -> ValidationPipeline:
        """Create a pipeline from settings."""
        if settings is None:
            settings = ClaimValidatorSettings()
        registry = ValidatorRegistry()
        rule_vals = registry.create_validators(
            settings.rule_validators,
        )

        # Clearinghouse client (optional)
        ch_client = None
        if settings.clearinghouse_config:
            from claim_validator.clearinghouse.factory import (
                get_clearinghouse_client,
            )

            ch_config = dict(settings.clearinghouse_config)
            provider = ch_config.pop("provider")
            ch_client = get_clearinghouse_client(provider, **ch_config)

        ai_vals: list[BaseAIValidator] = []
        if settings.ai_config and settings.ai_validators:
            from claim_validator.llm.factory import (
                get_llm_client,
            )

            ai_config = settings.ai_config
            extra_kwargs = {
                k: v
                for k, v in ai_config.items()
                if k not in ("provider", "api_key", "model")
            }
            llm_client = get_llm_client(
                ai_config["provider"],
                api_key=ai_config["api_key"],
                model=ai_config["model"],
                **extra_kwargs,
            )
            ai_vals = registry.create_ai_validators(
                settings.ai_validators,
                llm_client=llm_client,
            )

        return cls(
            rule_validators=rule_vals,
            ai_validators=ai_vals,
            skip_ai_on_rule_failure=settings.skip_ai_on_rule_failure,
            clearinghouse_client=ch_client,
        )

    @classmethod
    def builder(cls) -> _PipelineBuilder:
        """Return a fluent builder for custom pipelines."""
        return _PipelineBuilder()

    def run(
        self,
        claim: ClaimData,
        *,
        validation_context: ValidationContext | None = None,
    ) -> PipelineResult:
        """Execute the full validation pipeline.

        Args:
            claim: Claim data to validate.
            validation_context: Optional cross-stage validation context
                for passthrough optimization.
        """
        start = time.perf_counter()
        phase_results: list[PhaseResult] = []

        # Phase 1 (+ optional Phase 2 clearinghouse): delegated to BasePipeline
        base_result = self._base_pipeline.run(
            claim, validation_context=validation_context,
        )
        phase_results.extend(base_result.phase_results)
        rule_phase = base_result.phase_results[0]

        # Phase 2: AI (conditional, domain-specific multi-validator)
        if self._ai_validators:
            rule_has_errors = any(
                f.severity == Severity.ERROR
                for f in rule_phase.findings
            )
            if (
                not rule_has_errors
                or not self._skip_ai_on_rule_failure
            ):
                deidentified = ClaimDeidentifier.deidentify(
                    claim,
                )
                ai_phase = self._run_ai_phase(deidentified)
                phase_results.append(ai_phase)

        elapsed = time.perf_counter() - start
        return PipelineResult(
            phase_results=phase_results,
            execution_time=elapsed,
        )

    def _run_ai_phase(
        self,
        claim: DeidentifiedClaim,
    ) -> PhaseResult:
        """Run AI validators with de-identified claim data."""
        start = time.perf_counter()
        outputs: list[ValidatorOutput] = []

        for validator in self._ai_validators:
            try:
                output = validator.validate_deidentified(
                    claim,
                )
                outputs.append(output)
            except LLMError as exc:
                outputs.append(
                    ValidatorOutput(
                        validator_name=validator.name,
                        findings=[
                            Finding(
                                code="AI_PROVIDER_ERROR",
                                message=(
                                    "AI validation unavailable"
                                ),
                                severity=Severity.WARNING,
                                field_name="",
                                suggestion=(
                                    "Rule-based results are"
                                    " still valid. Retry when"
                                    " the AI provider is"
                                    " available."
                                ),
                                context={
                                    "error": str(exc),
                                },
                            ),
                        ],
                    )
                )
            except Exception as exc:
                outputs.append(
                    ValidatorOutput(
                        validator_name=getattr(
                            validator, "name",
                            type(validator).__name__,
                        ),
                        findings=[
                            Finding(
                                code="VALIDATOR_ERROR",
                                message=(
                                    "Validator raised an"
                                    " unexpected exception"
                                ),
                                severity=Severity.ERROR,
                                field_name="",
                                suggestion=(
                                    "Check validator"
                                    " implementation"
                                ),
                                context={
                                    "error": str(exc),
                                },
                            ),
                        ],
                    )
                )

        elapsed = time.perf_counter() - start
        return PhaseResult(
            phase="ai",
            validator_outputs=outputs,
            execution_time=elapsed,
        )
