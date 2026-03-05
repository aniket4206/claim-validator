"""Workflow stages — Stage protocol and concrete implementations."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol, runtime_checkable

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.workflow.models import StageResult

logger = logging.getLogger(__name__)


@runtime_checkable
class Stage(Protocol):
    """Protocol for a workflow stage."""

    name: str
    is_gate: bool

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Return (should_skip, reason) based on workflow context."""
        ...

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        """Execute the stage and return a StageResult."""
        ...


class EligibilityStage:
    """Eligibility validation stage (gate)."""

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
            elapsed = time.perf_counter() - start
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
                execution_time=elapsed,
            )

        response = input_data.get("eligibility_response")
        pipeline = EligibilityPipeline.from_settings(self._settings)

        result = pipeline.run(
            request, response=response,
            validation_context=validation_context,
        )

        elapsed = time.perf_counter() - start

        # Store result in workflow_context for downstream stages
        if workflow_context is not None:
            workflow_context["eligibility_result"] = result
            workflow_context["eligibility_response"] = response

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=list(result.findings),
            execution_time=elapsed,
            detail=result,
        )


class PADeterminationStage:
    """PA determination stage (non-gate, informational)."""

    name: str = "pa_determination"
    is_gate: bool = False

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        response = context.get("eligibility_response")
        if response is None:
            return True, "No eligibility response available for PA determination"
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
        response = wf.get("eligibility_response")
        raw = getattr(response, "raw_response", None) or {}

        findings: list[Finding] = []
        if not raw:
            findings.append(
                Finding(
                    code="PA_DET_EMPTY_DATA",
                    message="PA determination based on empty eligibility data",
                    severity=Severity.WARNING,
                    field_name="eligibility_response",
                    suggestion="Provide a 271 response for accurate PA determination",
                ),
            )

        pa_det = determine_pa_required(raw)

        if workflow_context is not None:
            workflow_context["pa_determination"] = pa_det

        elapsed = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            passed=True,
            findings=findings,
            execution_time=elapsed,
            detail=pa_det,
        )


class PriorAuthStage:
    """Prior authorization validation stage (gate)."""

    name: str = "prior_auth"
    is_gate: bool = True

    def __init__(self, settings: Any = None) -> None:
        self._settings = settings

    def should_skip(
        self, context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        pa_det = context.get("pa_determination")
        if pa_det is None or not pa_det.required:
            return True, "Prior authorization not required"
        return False, None

    def run(
        self,
        input_data: Any,
        *,
        validation_context: ValidationContext | None = None,
        workflow_context: dict[str, Any] | None = None,
    ) -> StageResult:
        from claim_validator.prior_auth.pipeline import PriorAuthPipeline

        start = time.perf_counter()
        pipeline = PriorAuthPipeline.from_settings(self._settings)

        pa_request = input_data.get("pa_request")
        if pa_request is None:
            elapsed = time.perf_counter() - start
            return StageResult(
                stage_name=self.name,
                passed=False,
                findings=[
                    Finding(
                        code="PA_REQUIRED",
                        message="Prior authorization is required but no PA request was provided",
                        severity=Severity.WARNING,
                        field_name="pa_request",
                        suggestion="Submit a PriorAuthRequest to complete the workflow",
                    ),
                ],
                execution_time=elapsed,
            )

        result = pipeline.run(
            pa_request, validation_context=validation_context,
        )

        elapsed = time.perf_counter() - start

        if workflow_context is not None:
            workflow_context["prior_auth_result"] = result

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=list(result.findings),
            execution_time=elapsed,
            detail=result,
        )


class ClaimValidationStage:
    """Claim validation stage (non-gate, final)."""

    name: str = "claim_validation"
    is_gate: bool = False

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
            elapsed = time.perf_counter() - start
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
                execution_time=elapsed,
            )

        pipeline = ValidationPipeline.from_settings(self._settings)
        result = pipeline.run(
            claim_data, validation_context=validation_context,
        )

        elapsed = time.perf_counter() - start

        if workflow_context is not None:
            workflow_context["claim_validation_result"] = result

        return StageResult(
            stage_name=self.name,
            passed=result.passed,
            findings=list(result.findings),
            execution_time=elapsed,
            detail=result,
        )
