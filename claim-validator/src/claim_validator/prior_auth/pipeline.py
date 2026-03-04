"""PriorAuthPipeline — two-phase PA validation orchestrator.

Delegates rule-based validation to ``BasePipeline``. AI interpretation
remains domain-specific (uses ``interpret()`` not ``validate_deidentified()``).
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.models.results import Finding
from claim_validator.prior_auth.models.result import PriorAuthResult
from claim_validator.shared.pipeline.config import PipelineConfig
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.shared.pipeline.engine import BasePipeline
from claim_validator.validators.registry import ValidatorRegistry

if TYPE_CHECKING:
    from claim_validator.prior_auth.models.request import PriorAuthRequest
    from claim_validator.prior_auth.models.response import PriorAuthResponse
    from claim_validator.prior_auth.validators.ai.interpreter import (
        PriorAuthInterpreterAI,
    )
    from claim_validator.validators.base import BaseValidator


_SEVERITY_ORDER: dict[Severity, int] = {Severity.ERROR: 0, Severity.WARNING: 1}


class PriorAuthPipeline:
    """Two-phase PA validation pipeline.

    Phase 1: Rule-based validators (delegated to BasePipeline)
    Phase 2: AI interpretation (requires LLM config + PA response)
    """

    def __init__(
        self,
        *,
        rule_validators: list[BaseValidator],
        ai_interpreter: PriorAuthInterpreterAI | None = None,
        skip_ai_on_rule_failure: bool = True,
    ) -> None:
        self._rule_validators = rule_validators
        self._ai_interpreter = ai_interpreter
        self._skip_ai_on_rule_failure = skip_ai_on_rule_failure
        self._base_pipeline = BasePipeline(
            PipelineConfig(
                domain="prior_auth",
                validators=tuple(rule_validators),
                code_prefix="",  # validators add PA_ prefix themselves
            )
        )

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

        ai_interpreter = None
        if settings.ai_config and not settings.pa_skip_ai:
            from claim_validator.llm.factory import get_llm_client
            from claim_validator.prior_auth.validators.ai.interpreter import (
                PriorAuthInterpreterAI,
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
            ai_interpreter = PriorAuthInterpreterAI(
                llm_client=llm_client,
            )

        return cls(
            rule_validators=rule_vals,
            ai_interpreter=ai_interpreter,
            skip_ai_on_rule_failure=settings.pa_skip_ai_on_rule_failure,
        )

    def run(
        self,
        request: PriorAuthRequest,
        *,
        response: PriorAuthResponse | None = None,
        validation_context: ValidationContext | None = None,
    ) -> PriorAuthResult:
        """Execute the PA validation pipeline.

        Args:
            request: PA request to validate.
            response: Optional pre-fetched PA response
                for AI interpretation.
            validation_context: Optional cross-stage validation context
                for passthrough optimization.
        """
        start = time.perf_counter()
        ai_summary: str | None = None

        # Phase 1: Delegate rule-based validation to BasePipeline
        rule_result = self._base_pipeline.run(
            request, validation_context=validation_context,
        )
        rule_phase = rule_result.phase_results[0]
        findings: list[Finding] = list(rule_phase.findings)

        # Phase 2: AI interpretation (if configured + response available)
        if self._ai_interpreter and response is not None:
            rule_has_errors = any(
                f.severity == Severity.ERROR for f in findings
            )
            if not rule_has_errors or not self._skip_ai_on_rule_failure:
                ai_summary, ai_findings = self._run_ai_phase(response)
                findings.extend(ai_findings)

        findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))

        elapsed = time.perf_counter() - start
        return PriorAuthResult(
            approved=response.is_approved if response else None,
            response=response,
            findings=findings,
            ai_summary=ai_summary,
            execution_time=elapsed,
        )

    def _run_ai_phase(
        self,
        response: PriorAuthResponse,
    ) -> tuple[str | None, list[Finding]]:
        """De-identify response and run AI interpretation."""
        from claim_validator.prior_auth.deidentifier import (
            PriorAuthDeidentifier,
        )

        assert self._ai_interpreter is not None  # noqa: S101

        try:
            deidentified = PriorAuthDeidentifier.deidentify(response)
            ai_summary, ai_findings = self._ai_interpreter.interpret(
                deidentified,
            )
            return ai_summary, ai_findings
        except LLMError as exc:
            return None, [
                Finding(
                    code="AI_PA_PROVIDER_ERROR",
                    message="AI interpretation unavailable",
                    severity=Severity.WARNING,
                    field_name="",
                    suggestion=(
                        "Rule-based results are still valid. "
                        "Retry when the AI provider is available."
                    ),
                    context={"error": str(exc)},
                ),
            ]
        except Exception as exc:
            return None, [
                Finding(
                    code="VALIDATOR_ERROR",
                    message="AI interpreter raised an unexpected exception",
                    severity=Severity.ERROR,
                    field_name="",
                    suggestion="Check AI interpreter implementation",
                    context={"error": str(exc)},
                ),
            ]
