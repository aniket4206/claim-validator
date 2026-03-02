"""EligibilityPipeline — two-phase eligibility validation orchestrator."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.exceptions import LLMError
from claim_validator.models.results import Finding
from claim_validator.validators.registry import ValidatorRegistry

if TYPE_CHECKING:
    from claim_validator.eligibility.models.request import EligibilityRequest
    from claim_validator.eligibility.models.response import EligibilityResponse
    from claim_validator.eligibility.validators.ai.interpreter import (
        EligibilityInterpreterAI,
    )
    from claim_validator.validators.base import BaseValidator


_SEVERITY_ORDER: dict[Severity, int] = {Severity.ERROR: 0, Severity.WARNING: 1}


class EligibilityPipeline:
    """Two-phase eligibility validation pipeline.

    Phase 1: Rule-based validators (offline, synchronous)
    Phase 2: AI interpretation (requires LLM config + eligibility response)
    """

    def __init__(
        self,
        *,
        rule_validators: list[BaseValidator],
        ai_interpreter: EligibilityInterpreterAI | None = None,
        skip_ai_on_rule_failure: bool = True,
    ) -> None:
        self._rule_validators = rule_validators
        self._ai_interpreter = ai_interpreter
        self._skip_ai_on_rule_failure = skip_ai_on_rule_failure

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

        ai_interpreter = None
        if settings.ai_config and not settings.eligibility_skip_ai:
            from claim_validator.eligibility.validators.ai.interpreter import (
                EligibilityInterpreterAI,
            )
            from claim_validator.llm.factory import get_llm_client

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
            ai_interpreter = EligibilityInterpreterAI(
                llm_client=llm_client,
            )

        return cls(
            rule_validators=rule_vals,
            ai_interpreter=ai_interpreter,
            skip_ai_on_rule_failure=settings.eligibility_skip_ai_on_rule_failure,
        )

    def run(
        self,
        request: EligibilityRequest,
        *,
        response: EligibilityResponse | None = None,
    ) -> EligibilityResult:
        """Execute the eligibility validation pipeline.

        Args:
            request: Eligibility request to validate.
            response: Optional pre-fetched eligibility response
                for AI interpretation.
        """
        start = time.perf_counter()
        findings: list[Finding] = []
        ai_summary: str | None = None

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
        return EligibilityResult(
            eligible=response.eligible if response else None,
            response=response,
            findings=findings,
            ai_summary=ai_summary,
            execution_time=elapsed,
        )

    def _run_ai_phase(
        self,
        response: EligibilityResponse,
    ) -> tuple[str | None, list[Finding]]:
        """De-identify response and run AI interpretation."""
        from claim_validator.eligibility.deidentifier import (
            EligibilityDeidentifier,
        )

        assert self._ai_interpreter is not None  # noqa: S101

        try:
            deidentified = EligibilityDeidentifier.deidentify(response)
            ai_summary, ai_findings = self._ai_interpreter.interpret(
                deidentified,
            )
            return ai_summary, ai_findings
        except LLMError as exc:
            return None, [
                Finding(
                    code="AI_ELIG_PROVIDER_ERROR",
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
