"""Pre-claim orchestrator — chains eligibility, PA determination, and PA validation.

Usage::

    from claim_validator import pre_claim_check, EligibilityRequest

    result = pre_claim_check(
        eligibility_request=EligibilityRequest(...),
        eligibility_response=response_271,   # optional
        pa_request=PriorAuthRequest(...),     # optional
    )
    if result.ready_to_submit:
        # safe to submit claim
        ...
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility.pipeline import EligibilityPipeline
from claim_validator.models.results import Finding
from claim_validator.models.workflow import PreClaimResult
from claim_validator.prior_auth.determination import determine_pa_required
from claim_validator.prior_auth.pipeline import PriorAuthPipeline

if TYPE_CHECKING:
    from claim_validator.eligibility.models.request import EligibilityRequest
    from claim_validator.eligibility.models.response import EligibilityResponse
    from claim_validator.prior_auth.models.request import PriorAuthRequest


_SEVERITY_ORDER: dict[Severity, int] = {Severity.ERROR: 0, Severity.WARNING: 1}


def pre_claim_check(
    eligibility_request: EligibilityRequest,
    *,
    eligibility_response: EligibilityResponse | None = None,
    pa_request: PriorAuthRequest | None = None,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    clearinghouse_config: dict[str, Any] | None = None,
) -> PreClaimResult:
    """Run the unified pre-claim check: eligibility -> PA determination -> PA validation.

    Args:
        eligibility_request: Eligibility request to validate.
        eligibility_response: Optional 271 response for AI interpretation
            and PA determination.
        pa_request: Optional prior-auth request. Used only when PA is
            determined to be required.
        settings: Optional settings override. Uses defaults if ``None``.
        ai_config: Optional AI provider config dict. Overrides
            ``settings.ai_config`` when both are provided.
        clearinghouse_config: Optional clearinghouse provider config dict.
            Keys: ``provider`` (required), plus provider-specific keys
            (``api_key``, ``secret``, etc.). Overrides
            ``settings.clearinghouse_config`` when both are provided.

    Returns:
        PreClaimResult with combined findings and ``ready_to_submit`` flag.
    """
    start = time.perf_counter()

    # Wire ai_config into settings (same pattern as check_eligibility)
    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(update={"ai_config": ai_config})
        else:
            settings = ClaimValidatorSettings(ai_config=ai_config)

    # Wire clearinghouse_config into settings
    if clearinghouse_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"clearinghouse_config": clearinghouse_config},
            )
        else:
            settings = ClaimValidatorSettings(
                clearinghouse_config=clearinghouse_config,
            )

    # --- Step 1: Eligibility validation ---
    elig_pipeline = EligibilityPipeline.from_settings(settings)
    elig_result = elig_pipeline.run(
        eligibility_request, response=eligibility_response,
    )

    all_findings: list[Finding] = list(elig_result.findings)
    ai_summary = elig_result.ai_summary

    elig_has_errors = any(f.severity == Severity.ERROR for f in elig_result.findings)
    if elig_has_errors:
        # Gate: eligibility failed — return early
        all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
        return PreClaimResult(
            ready_to_submit=False,
            eligibility=elig_result,
            findings=all_findings,
            ai_summary=ai_summary,
            execution_time=time.perf_counter() - start,
        )

    # --- Step 2: PA determination (only if we have a response to analyze) ---
    pa_determination = None
    pa_result = None

    if eligibility_response is not None:
        # determine_pa_required() expects a raw 271 dict with
        # "benefitsInformation".  EligibilityResponse stores the raw
        # payload in its ``raw_response`` field.
        raw_for_pa = getattr(eligibility_response, "raw_response", None) or {}
        pa_determination = determine_pa_required(raw_for_pa)

        if pa_determination.required:
            if pa_request is not None:
                # --- Step 3: PA validation ---
                pa_pipeline = PriorAuthPipeline.from_settings(settings)
                pa_result = pa_pipeline.run(pa_request)
                all_findings.extend(pa_result.findings)

                pa_has_errors = any(
                    f.severity == Severity.ERROR for f in pa_result.findings
                )
                all_findings.sort(
                    key=lambda f: _SEVERITY_ORDER.get(f.severity, 99),
                )
                return PreClaimResult(
                    ready_to_submit=not pa_has_errors,
                    eligibility=elig_result,
                    pa_determination=pa_determination,
                    pa_result=pa_result,
                    findings=all_findings,
                    ai_summary=ai_summary,
                    execution_time=time.perf_counter() - start,
                )

            # PA required but no pa_request provided
            all_findings.append(
                Finding(
                    code="PA_REQUIRED",
                    message=(
                        "Prior authorization is required but no PA request was provided"
                    ),
                    severity=Severity.WARNING,
                    field_name="pa_request",
                    suggestion=(
                        "Submit a PriorAuthRequest to complete pre-claim check"
                    ),
                    context={"reason": pa_determination.reason},
                ),
            )
            all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
            return PreClaimResult(
                ready_to_submit=False,
                eligibility=elig_result,
                pa_determination=pa_determination,
                findings=all_findings,
                ai_summary=ai_summary,
                execution_time=time.perf_counter() - start,
            )

    # Eligible, PA not required (or no response to check)
    all_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
    return PreClaimResult(
        ready_to_submit=True,
        eligibility=elig_result,
        pa_determination=pa_determination,
        findings=all_findings,
        ai_summary=ai_summary,
        execution_time=time.perf_counter() - start,
    )
