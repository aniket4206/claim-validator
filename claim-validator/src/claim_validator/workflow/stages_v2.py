"""V2 workflow stages — 7-stage cost-first pipeline.

Stage 1: Rule-Based Claim Validation  [GATE]
Stage 2: AI Claim Analysis            [NON-GATE]
Stage 3: Eligibility                  [GATE]
Stage 4: Prior Authorization          [GATE]
Stage 5: AI Pre-Submission Summary    [NON-GATE]
Stage 6: Claim Submission             [FINAL]
Stage 7: Claim Status                 [INFORMATIONAL]
"""

from __future__ import annotations

import logging
import time
from typing import Any

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.workflow.models import StageResult

logger = logging.getLogger(__name__)


def _resolve_ai_config(
    settings: Any, stage_config_attr: str,
) -> dict[str, Any] | None:
    """Resolve AI config for a stage: per-stage override > global ai_config.

    Args:
        settings: ClaimValidatorSettings instance.
        stage_config_attr: Attribute name for per-stage config
            (e.g. "ai_claim_analysis_config").

    Returns:
        AI config dict or None if no AI is configured for this stage.
    """
    if settings is None:
        return None
    # Per-stage override takes priority
    stage_config = getattr(settings, stage_config_attr, None)
    if stage_config:
        return stage_config
    # Fall back to global ai_config
    return settings.ai_config


def _get_llm_client_from_config(ai_config: dict[str, Any]) -> Any:
    """Create an LLM client from an AI config dict.

    Raises:
        ConfigurationError: If required keys (provider, api_key, model)
            are missing from the config dict.
    """
    from claim_validator.exceptions import ConfigurationError
    from claim_validator.llm.factory import get_llm_client

    missing = [k for k in ("provider", "api_key", "model") if k not in ai_config]
    if missing:
        raise ConfigurationError(
            f"AI config missing required keys: {', '.join(missing)}. "
            f"Expected keys: provider, api_key, model."
        )

    extra_kwargs = {
        k: v for k, v in ai_config.items()
        if k not in ("provider", "api_key", "model")
    }
    return get_llm_client(
        ai_config["provider"],
        api_key=ai_config["api_key"],
        model=ai_config["model"],
        **extra_kwargs,
    )


# ---------------------------------------------------------------------------
# Stage 1: Rule-Based Claim Validation [GATE]
# ---------------------------------------------------------------------------


class RuleBasedClaimStage:
    """Fast, free rule-based claim validation — catches obvious errors first."""

    name: str = "rule_based_claim"
    is_gate: bool = True

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        from claim_validator.validators.pipeline import ValidationPipeline

        start = time.perf_counter()

        claim_data = input_data.get("claim_data")
        if claim_data is None:
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="CLAIM_MISSING_DATA",
                        message="No claim data provided",
                        severity=Severity.ERROR,
                        field_name="claim_data",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )

        # Build pipeline with rule-based validators only (no AI)
        # Use pre-computed settings from workflow_context if available
        from claim_validator.conf import ClaimValidatorSettings

        wf = workflow_context or {}
        rule_settings = wf.get("_settings_rule_only")
        if rule_settings is None:
            rule_settings = (self._settings or ClaimValidatorSettings()).model_copy(
                update={"ai_validators": [], "skip_ai_on_rule_failure": True},
            )
        pipeline = ValidationPipeline.from_settings(rule_settings)
        result = pipeline.run(claim_data, validation_context=validation_context)

        elapsed = time.perf_counter() - start

        if workflow_context is not None:
            workflow_context["rule_based_claim_result"] = result

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=list(result.findings),
            execution_time=elapsed,
            detail=result,
        )


# ---------------------------------------------------------------------------
# Stage 2: AI Claim Analysis [NON-GATE]
# ---------------------------------------------------------------------------


class AIClaimAnalysisStage:
    """AI-powered clinical plausibility and coverage analysis."""

    name: str = "ai_claim_analysis"
    is_gate: bool = False

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        # Skip if no AI config or if rule-based already failed
        settings = self._settings
        if settings is None:
            return True, "No settings configured for AI analysis"
        ai_cfg = _resolve_ai_config(settings, "ai_claim_analysis_config")
        if not ai_cfg or not settings.ai_validators:
            return True, "No AI provider configured"
        rule_result = context.get("rule_based_claim_result")
        if rule_result is not None and not rule_result.passed:
            return True, "Rule-based validation failed — skipping AI"
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        from claim_validator.validators.pipeline import ValidationPipeline

        start = time.perf_counter()

        claim_data = input_data.get("claim_data")
        if claim_data is None:
            return StageResult(
                stage_name=self.name,
                passed=True,
                findings=[],
                execution_time=time.perf_counter() - start,
            )

        # Build pipeline with AI validators only (no rule-based)
        # Uses per-stage AI config if available, else global ai_config
        from claim_validator.conf import ClaimValidatorSettings

        ai_settings = self._settings or ClaimValidatorSettings()
        stage_ai = _resolve_ai_config(ai_settings, "ai_claim_analysis_config")
        updates: dict[str, Any] = {
            "rule_validators": [],
            "skip_ai_on_rule_failure": False,
        }
        if stage_ai:
            updates["ai_config"] = stage_ai
        ai_settings = ai_settings.model_copy(update=updates)
        pipeline = ValidationPipeline.from_settings(ai_settings)
        result = pipeline.run(claim_data, validation_context=validation_context)

        elapsed = time.perf_counter() - start

        if workflow_context is not None:
            workflow_context["ai_claim_result"] = result

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=list(result.findings),
            execution_time=elapsed,
            detail=result,
        )


# ---------------------------------------------------------------------------
# Stage 3: Eligibility [GATE]
# ---------------------------------------------------------------------------


class EligibilityGateStage:
    """Eligibility: rule-based request validation + clearinghouse check.

    On rejection, generates an AI summary if AI is configured.
    """

    name: str = "eligibility"
    is_gate: bool = True

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        from claim_validator.eligibility.pipeline import EligibilityPipeline

        start = time.perf_counter()

        request = input_data.get("eligibility_request")
        if request is None:
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="ELIG_MISSING_REQUEST",
                        message="No eligibility request provided",
                        severity=Severity.ERROR,
                        field_name="eligibility_request",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )

        response = input_data.get("eligibility_response")
        pipeline = EligibilityPipeline.from_settings(self._settings)
        result = pipeline.run(
            request, response=response,
            validation_context=validation_context,
        )

        elapsed = time.perf_counter() - start

        if workflow_context is not None:
            workflow_context["eligibility_result"] = result
            workflow_context["eligibility_response"] = response

        findings = list(result.findings)

        # If eligibility failed and AI is configured, generate a summary
        rejection_ai = _resolve_ai_config(
            self._settings, "ai_rejection_summary_config",
        )
        if not result.passed and rejection_ai:
            ai_summary = self._generate_rejection_summary(findings)
            if ai_summary and workflow_context is not None:
                workflow_context["eligibility_rejection_summary"] = ai_summary

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=findings,
            execution_time=elapsed,
            detail=result,
        )

    def _generate_rejection_summary(
        self, findings: list[Finding],
    ) -> str | None:
        """Generate AI summary of why eligibility was rejected."""
        ai_config = _resolve_ai_config(
            self._settings, "ai_rejection_summary_config",
        )
        if not ai_config:
            return None
        try:
            client = _get_llm_client_from_config(ai_config)
            from claim_validator.llm.base import Message

            findings_text = "\n".join(
                f"- [{f.severity.value}] {f.code}: {f.message}"
                for f in findings
            )
            messages = [
                Message(
                    role="system",
                    content=(
                        "You are a healthcare billing expert. Summarize why "
                        "this eligibility check failed in plain language for "
                        "billing staff. Include specific suggestions to fix "
                        "each issue. Be concise."
                    ),
                ),
                Message(
                    role="user",
                    content=f"Eligibility check findings:\n{findings_text}",
                ),
            ]
            return client.send_messages(messages)
        except Exception:
            logger.warning("Failed to generate eligibility rejection summary", exc_info=True)
            return None


# ---------------------------------------------------------------------------
# Stage 4: Prior Authorization [GATE]
# ---------------------------------------------------------------------------


class PriorAuthGateStage:
    """PA: rule-based determination + validation + ClaimMD submission.

    No AI. PA is a deterministic lookup problem.
    """

    name: str = "prior_auth"
    is_gate: bool = True

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        from claim_validator.prior_auth.determination import determine_pa_required

        start = time.perf_counter()
        wf = workflow_context or {}

        # Phase A: Determine if PA is required (rule-based)
        elig_response = wf.get("eligibility_response")
        raw = getattr(elig_response, "raw_response", None) or {}
        pa_det = determine_pa_required(raw)

        if workflow_context is not None:
            workflow_context["pa_determination"] = pa_det

        if not pa_det.required:
            return StageResult(
                stage_name=self.name,
                passed=True,
                skipped=True,
                skip_reason="Prior authorization not required",
                execution_time=time.perf_counter() - start,
                detail=pa_det,
            )

        # Phase B: Rule-based PA request validation
        pa_request = input_data.get("pa_request")
        if pa_request is None:
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="PA_REQUIRED_NO_REQUEST",
                        message="Prior authorization is required but no PA request was provided",
                        severity=Severity.WARNING,
                        field_name="pa_request",
                        suggestion="Submit a PriorAuthRequest to complete the workflow",
                    ),
                ],
                execution_time=time.perf_counter() - start,
                detail=pa_det,
            )

        # Force rule-based only — use pre-computed settings if available
        from claim_validator.conf import ClaimValidatorSettings
        from claim_validator.prior_auth.pipeline import PriorAuthPipeline

        wf = workflow_context or {}
        pa_settings = wf.get("_settings_pa_rule_only")
        if pa_settings is None:
            pa_settings = (self._settings or ClaimValidatorSettings()).model_copy(
                update={"pa_ai_validators": [], "pa_skip_ai": True},
            )
        pipeline = PriorAuthPipeline.from_settings(pa_settings)
        pa_result = pipeline.run(pa_request, validation_context=validation_context)

        if not pa_result.passed:
            elapsed = time.perf_counter() - start
            if workflow_context is not None:
                workflow_context["prior_auth_result"] = pa_result
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=list(pa_result.findings),
                execution_time=elapsed,
                detail=pa_result,
            )

        # Phase C: Submit to clearinghouse (ClaimMD) if configured
        findings = list(pa_result.findings)
        if self._settings and self._settings.clearinghouse_config:
            ch_findings = self._submit_pa_to_clearinghouse(
                pa_request, workflow_context,
            )
            findings.extend(ch_findings)

        elapsed = time.perf_counter() - start
        if workflow_context is not None:
            workflow_context["prior_auth_result"] = pa_result

        has_errors = any(f.severity == Severity.ERROR for f in findings)
        return StageResult(
            stage_name=self.name,
            passed=not has_errors,
            findings=findings,
            execution_time=elapsed,
            detail=pa_result,
        )

    def _submit_pa_to_clearinghouse(
        self,
        pa_request: Any,
        workflow_context: dict[str, Any] | None,
    ) -> list[Finding]:
        """Submit PA to clearinghouse and return any findings."""
        findings: list[Finding] = []
        try:
            # Use pooled client from workflow_context if available
            wf = workflow_context or {}
            ch_client = wf.get("_pooled_ch_client")
            if ch_client is None:
                from claim_validator.clearinghouse import build_clearinghouse_client

                ch_client = build_clearinghouse_client(
                    self._settings.clearinghouse_config,
                )
            if ch_client is None:
                return findings

            # Convert PA request to dict for clearinghouse
            pa_dict = (
                pa_request.model_dump()
                if hasattr(pa_request, "model_dump")
                else dict(pa_request)
            )

            result = ch_client.submit_prior_auth(pa_dict)

            if workflow_context is not None:
                workflow_context["pa_submission_result"] = result

            if not result.accepted:
                findings.append(
                    Finding(
                        code="PA_CLEARINGHOUSE_DENIED",
                        message=f"Prior authorization denied by clearinghouse: {result.status}",
                        severity=Severity.ERROR,
                        field_name="prior_auth",
                        suggestion="Review PA denial reasons and resubmit",
                        context={"errors": result.errors},
                    ),
                )
            else:
                findings.append(
                    Finding(
                        code="PA_CLEARINGHOUSE_APPROVED",
                        message=f"Prior authorization approved: {result.reference_id}",
                        severity=Severity.WARNING,
                        field_name="prior_auth",
                        context={"reference_id": result.reference_id},
                    ),
                )
            # Don't close pooled client — it's managed by process_claim_full
        except NotImplementedError:
            findings.append(
                Finding(
                    code="PA_SUBMISSION_NOT_SUPPORTED",
                    message="Clearinghouse provider does not support PA submission",
                    severity=Severity.WARNING,
                    field_name="prior_auth",
                    suggestion="Use ClaimMD for prior authorization submission",
                ),
            )
        except Exception:
            logger.warning("PA clearinghouse submission failed", exc_info=True)
            findings.append(
                Finding(
                    code="PA_SUBMISSION_ERROR",
                    message="Failed to submit PA to clearinghouse",
                    severity=Severity.WARNING,
                    field_name="prior_auth",
                    suggestion="PA validation passed but clearinghouse submission failed",
                ),
            )
        return findings


# ---------------------------------------------------------------------------
# Stage 5: AI Pre-Submission Summary [NON-GATE]
# ---------------------------------------------------------------------------


class AIPreSubmissionStage:
    """Final AI check before claim submission — holistic sanity check."""

    name: str = "ai_pre_submission"
    is_gate: bool = False

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        ai_cfg = _resolve_ai_config(self._settings, "ai_pre_submission_config")
        if not ai_cfg:
            return True, "No AI provider configured"
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        start = time.perf_counter()

        try:
            from claim_validator.llm.base import Message

            ai_config = _resolve_ai_config(
                self._settings, "ai_pre_submission_config",
            )
            if not ai_config:
                return StageResult(
                    stage_name=self.name,
                    passed=True,
                    skipped=True,
                    skip_reason="No AI config",
                    execution_time=time.perf_counter() - start,
                )
            client = _get_llm_client_from_config(ai_config)

            # Build context summary from workflow
            wf = workflow_context or {}
            context_parts = []
            if wf.get("eligibility_result"):
                context_parts.append(
                    f"Eligibility: {'PASSED' if wf['eligibility_result'].passed else 'FAILED'}"
                )
            pa_det = wf.get("pa_determination")
            if pa_det:
                context_parts.append(
                    f"PA Required: {pa_det.required}"
                )
            if wf.get("prior_auth_result"):
                context_parts.append(
                    f"PA Validation: {'PASSED' if wf['prior_auth_result'].passed else 'FAILED'}"
                )

            messages = [
                Message(
                    role="system",
                    content=(
                        "You are a healthcare billing expert doing a final "
                        "review before claim submission. Review the workflow "
                        "status and flag any concerns. Be very concise — only "
                        "flag issues that would cause a claim denial. If "
                        "everything looks good, say 'Ready to submit.'"
                    ),
                ),
                Message(
                    role="user",
                    content="Workflow status:\n" + "\n".join(context_parts),
                ),
            ]

            summary = client.send_messages(messages)

            if workflow_context is not None:
                workflow_context["ai_pre_submission_summary"] = summary

            elapsed = time.perf_counter() - start
            return StageResult(
                stage_name=self.name,
                passed=True,
                findings=[],
                execution_time=elapsed,
                detail={"summary": summary},
            )

        except Exception:
            logger.warning("AI pre-submission check failed", exc_info=True)
            return StageResult(
                stage_name=self.name,
                passed=True,
                findings=[
                    Finding(
                        code="AI_PRE_SUBMISSION_UNAVAILABLE",
                        message="AI pre-submission check unavailable — proceeding without",
                        severity=Severity.WARNING,
                        field_name="",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )


# ---------------------------------------------------------------------------
# Stage 6: Claim Submission [FINAL]
# ---------------------------------------------------------------------------


class ClaimSubmissionStage:
    """Submit claim to clearinghouse."""

    name: str = "claim_submission"
    is_gate: bool = False

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if not self._settings or not self._settings.clearinghouse_config:
            return True, "No clearinghouse configured for submission"
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        start = time.perf_counter()

        claim_data = input_data.get("claim_data")
        if claim_data is None:
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="SUBMISSION_MISSING_DATA",
                        message="No claim data for submission",
                        severity=Severity.ERROR,
                        field_name="claim_data",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )

        try:
            # Use pooled client from workflow_context if available
            wf = workflow_context or {}
            ch_client = wf.get("_pooled_ch_client")
            if ch_client is None:
                from claim_validator.clearinghouse import build_clearinghouse_client

                ch_client = build_clearinghouse_client(
                    self._settings.clearinghouse_config,
                )
            if ch_client is None:
                return StageResult(
                    stage_name=self.name,
                    passed=False,
                    findings=[
                        Finding(
                            code="SUBMISSION_NO_CLIENT",
                            message="Could not create clearinghouse client",
                            severity=Severity.ERROR,
                            field_name="clearinghouse_config",
                        ),
                    ],
                    execution_time=time.perf_counter() - start,
                )

            claim_dict = (
                claim_data.model_dump()
                if hasattr(claim_data, "model_dump")
                else dict(claim_data)
            )
            result = ch_client.submit_claim(claim_dict)

            if workflow_context is not None:
                workflow_context["submission_result"] = result

            findings: list[Finding] = []
            if result.accepted:
                findings.append(
                    Finding(
                        code="CLAIM_SUBMITTED",
                        message=f"Claim submitted successfully: {result.reference_id}",
                        severity=Severity.WARNING,
                        field_name="claim_submission",
                        context={"reference_id": result.reference_id},
                    ),
                )
            else:
                findings.append(
                    Finding(
                        code="CLAIM_SUBMISSION_REJECTED",
                        message=f"Claim submission rejected: {result.status}",
                        severity=Severity.ERROR,
                        field_name="claim_submission",
                        context={"errors": result.errors},
                    ),
                )

            return StageResult(
                stage_name=self.name,
                passed=result.accepted,
                findings=findings,
                execution_time=time.perf_counter() - start,
                detail=result,
            )

        except Exception as exc:
            logger.exception("Claim submission failed")
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="SUBMISSION_ERROR",
                        message=f"Claim submission failed: {exc}",
                        severity=Severity.ERROR,
                        field_name="claim_submission",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )


# ---------------------------------------------------------------------------
# Stage 7: Claim Status [INFORMATIONAL]
# ---------------------------------------------------------------------------


class ClaimStatusStage:
    """Optional: check claim status after submission."""

    name: str = "claim_status"
    is_gate: bool = False

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        submission = context.get("submission_result")
        if submission is None or not submission.accepted:
            return True, "No successful submission to check status for"
        if not submission.reference_id:
            return True, "No reference ID for status check"
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        start = time.perf_counter()

        wf = workflow_context or {}
        submission = wf.get("submission_result")

        try:
            # Use pooled client from workflow_context if available
            ch_client = wf.get("_pooled_ch_client")
            if ch_client is None:
                from claim_validator.clearinghouse import build_clearinghouse_client

                ch_client = build_clearinghouse_client(
                    self._settings.clearinghouse_config if self._settings else None,
                )
            if ch_client is None:
                return StageResult(
                    stage_name=self.name,
                    passed=True,
                    skipped=True,
                    skip_reason="No clearinghouse for status check",
                    execution_time=time.perf_counter() - start,
                )

            result = ch_client.check_claim_status(submission.reference_id)

            if workflow_context is not None:
                workflow_context["claim_status_result"] = result

            return StageResult(
                stage_name=self.name,
                passed=True,
                findings=[],
                execution_time=time.perf_counter() - start,
                detail=result,
            )

        except Exception:
            logger.warning("Claim status check failed", exc_info=True)
            return StageResult(
                stage_name=self.name,
                passed=True,
                findings=[
                    Finding(
                        code="STATUS_CHECK_FAILED",
                        message="Claim status check failed — claim was already submitted",
                        severity=Severity.WARNING,
                        field_name="claim_status",
                    ),
                ],
                execution_time=time.perf_counter() - start,
            )
