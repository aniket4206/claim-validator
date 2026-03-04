"""BasePipeline — configurable multi-phase pipeline engine.

Executes up to 3 phases in order: rule-based validators, clearinghouse,
AI interpretation. Phase gating, timing, and error handling are built in.
Domains provide PipelineConfig, never subclass ``run()``.
"""

from __future__ import annotations

import time
from typing import Any

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.models.results import (
    Finding,
    PhaseResult,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.shared.pipeline.config import PipelineConfig


class BasePipeline:
    """Configurable multi-phase pipeline engine.

    Executes up to 3 phases:
      1. Rule-based validators (always runs if validators configured)
      2. Clearinghouse (optional, gated by rule results)
      3. AI interpretation (optional, gated by rule results)

    Domains provide PipelineConfig, never subclass ``run()``.
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    @property
    def config(self) -> PipelineConfig:
        """The pipeline configuration."""
        return self._config

    def run(self, input_data: Any) -> PipelineResult:
        """Execute the full multi-phase pipeline.

        Args:
            input_data: Domain-specific input (e.g. ClaimData, dict).

        Returns:
            PipelineResult with per-phase results, timing, and findings.
        """
        start = time.perf_counter()
        phase_results: list[PhaseResult] = []

        # Phase 1: Rule-based validators
        rule_phase = self._run_rule_phase(input_data)
        phase_results.append(rule_phase)

        rule_has_errors = any(
            f.severity == Severity.ERROR for f in rule_phase.findings
        )

        # Phase 2: Clearinghouse (optional, gated)
        clearinghouse_skipped = False
        if self._config.clearinghouse_client is not None:
            if rule_has_errors and self._config.skip_clearinghouse_on_rule_failure:
                clearinghouse_skipped = True
            else:
                ch_phase = self._run_clearinghouse_phase(input_data)
                phase_results.append(ch_phase)

        # Phase 3: AI (optional, gated)
        if self._config.ai_interpreter is not None:
            should_skip = (
                clearinghouse_skipped
                or (rule_has_errors and self._config.skip_ai_on_rule_failure)
            )
            if not should_skip:
                ai_phase = self._run_ai_phase(input_data)
                phase_results.append(ai_phase)

        elapsed = time.perf_counter() - start
        return PipelineResult(
            phase_results=phase_results,
            execution_time=elapsed,
        )

    def _run_rule_phase(self, input_data: Any) -> PhaseResult:
        """Execute all rule-based validators and collect results."""
        start = time.perf_counter()
        outputs: list[ValidatorOutput] = []
        for validator in self._config.validators:
            try:
                output = validator.validate(input_data)
                outputs.append(output)
            except Exception as exc:
                outputs.append(
                    ValidatorOutput(
                        validator_name=getattr(
                            validator, "name", type(validator).__name__
                        ),
                        findings=[
                            Finding(
                                code=f"{self._config.code_prefix}VALIDATOR_ERROR",
                                message="Validator raised an unexpected exception",
                                severity=Severity.ERROR,
                                field_name="",
                                suggestion="Check validator implementation",
                                context={
                                    "validator": type(validator).__name__,
                                    "error": str(exc),
                                },
                            )
                        ],
                    )
                )
        elapsed = time.perf_counter() - start
        return PhaseResult(
            phase="rule_based", validator_outputs=outputs, execution_time=elapsed
        )

    def _run_clearinghouse_phase(self, input_data: Any) -> PhaseResult:
        """Execute the clearinghouse phase, dispatching by domain.

        Calls the appropriate clearinghouse method based on
        ``PipelineConfig.domain``:
          - ``"eligibility"`` → ``check_eligibility(input_data)``
          - ``"claim"`` → ``submit_claim(input_data)``
          - otherwise → ``check_claim_status(str(input_data))``

        ClearinghouseError subtypes are mapped to Finding severities:
          - ``ClearinghouseValidationError`` → WARNING (data issue)
          - ``ClearinghouseAuthError`` → ERROR (config issue)
          - ``ClearinghouseTimeoutError`` → ERROR (transient)
          - ``ClearinghouseError`` → ERROR (catch-all)
        """
        start = time.perf_counter()
        outputs: list[ValidatorOutput] = []
        try:
            client = self._config.clearinghouse_client
            domain = self._config.domain
            if domain == "eligibility":
                client.check_eligibility(input_data)
            elif domain == "claim":
                client.submit_claim(input_data)
            else:
                client.check_claim_status(str(input_data))
        except ClearinghouseValidationError as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="clearinghouse",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}CLEARINGHOUSE_VALIDATION",
                            message=str(exc),
                            severity=Severity.WARNING,
                            field_name="",
                            suggestion="Check request data for clearinghouse submission",
                        )
                    ],
                )
            )
        except ClearinghouseAuthError as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="clearinghouse",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}CLEARINGHOUSE_AUTH",
                            message="Clearinghouse authentication failed",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Check clearinghouse API credentials",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        except ClearinghouseTimeoutError as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="clearinghouse",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}CLEARINGHOUSE_TIMEOUT",
                            message="Clearinghouse request timed out",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Retry later or check network connectivity",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        except ClearinghouseError as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="clearinghouse",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}CLEARINGHOUSE_ERROR",
                            message="Clearinghouse call failed",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Check clearinghouse client configuration",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        except Exception as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="clearinghouse",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}CLEARINGHOUSE_ERROR",
                            message="Unexpected clearinghouse error",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Check clearinghouse client implementation",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        elapsed = time.perf_counter() - start
        return PhaseResult(
            phase="clearinghouse", validator_outputs=outputs, execution_time=elapsed
        )

    def _run_ai_phase(self, input_data: Any) -> PhaseResult:
        """Execute the AI interpretation phase with de-identification."""
        start = time.perf_counter()
        outputs: list[ValidatorOutput] = []

        # De-identify before AI consumption (FR40)
        try:
            deidentified = input_data
            if self._config.deidentifier is not None:
                deidentified = self._config.deidentifier.deidentify(input_data)
        except Exception as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name="deidentifier",
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}DEIDENTIFIER_ERROR",
                            message="De-identification failed before AI phase",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Check deidentifier configuration and input data",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
            elapsed = time.perf_counter() - start
            return PhaseResult(
                phase="ai", validator_outputs=outputs, execution_time=elapsed
            )

        # Call AI interpreter
        try:
            output = self._config.ai_interpreter.validate_deidentified(deidentified)
            outputs.append(output)
        except LLMError as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name=getattr(
                        self._config.ai_interpreter, "name", "ai"
                    ),
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}AI_PROVIDER_ERROR",
                            message="AI validation unavailable",
                            severity=Severity.WARNING,
                            field_name="",
                            suggestion=(
                                "Rule-based results are still valid. "
                                "Retry when AI provider is available."
                            ),
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        except Exception as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name=getattr(
                        self._config.ai_interpreter, "name", "ai"
                    ),
                    findings=[
                        Finding(
                            code=f"{self._config.code_prefix}VALIDATOR_ERROR",
                            message="AI interpreter raised an unexpected exception",
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion="Check AI interpreter implementation",
                            context={"error": str(exc)},
                        )
                    ],
                )
            )
        elapsed = time.perf_counter() - start
        return PhaseResult(
            phase="ai", validator_outputs=outputs, execution_time=elapsed
        )
