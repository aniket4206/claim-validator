"""EligibilityInterpreterAI — AI-powered eligibility response interpreter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator

if TYPE_CHECKING:
    from claim_validator.eligibility.models.deidentified import (
        DeidentifiedEligibilityResponse,
    )
    from claim_validator.models.deidentified import DeidentifiedClaim


class EligibilityInterpreterAI(BaseAIValidator):
    """Interprets de-identified eligibility data via LLM.

    Generates human-readable coverage summaries and actionable
    findings from eligibility response data.  All output uses
    ``AI_ELIG_`` code prefixes with ``WARNING`` severity only.
    """

    name = "EligibilityInterpreterAI"

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Not used — interpreter uses interpret() instead.

        Raises:
            NotImplementedError: Always. Use ``interpret()`` with
                ``DeidentifiedEligibilityResponse``.
        """
        raise NotImplementedError(
            "Use interpret() with DeidentifiedEligibilityResponse. "
            "The eligibility pipeline calls interpret() directly."
        )

    SYSTEM_PROMPT = (
        "You are a healthcare eligibility analyst. Interpret "
        "this de-identified eligibility response data and provide:\n\n"
        "1. A clear, concise summary of the coverage status and benefits\n"
        "2. Any coverage concerns, limitations, or gaps\n"
        "3. Plain-English explanations of any rejection errors\n\n"
        "Respond in JSON format:\n"
        '{"summary": "<coverage summary>", "findings": [\n'
        '  {"code": "AI_ELIG_<TYPE>", "message": "<str>", '
        '"suggestion": "<str>"}\n'
        "]}\n\n"
        "Valid finding codes:\n"
        "- AI_ELIG_COVERAGE_CONCERN: Coverage gap or limitation\n"
        "- AI_ELIG_LIMITATION: Specific benefit limitation\n"
        "- AI_ELIG_REJECTION_EXPLAINED: AAA rejection in plain English\n"
        "- AI_ELIG_PRIOR_AUTH_NEEDED: Prior auth requirement detected\n"
        "- AI_ELIG_BENEFIT_NOTE: General benefit information\n\n"
        "If no findings, respond: "
        '{"summary": "<summary>", "findings": []}\n\n'
        "IMPORTANT: Do not include any patient-identifying information."
    )

    _VALID_CODES = frozenset({
        "AI_ELIG_COVERAGE_CONCERN",
        "AI_ELIG_LIMITATION",
        "AI_ELIG_REJECTION_EXPLAINED",
        "AI_ELIG_PRIOR_AUTH_NEEDED",
        "AI_ELIG_BENEFIT_NOTE",
    })

    def interpret(
        self,
        response: DeidentifiedEligibilityResponse,
    ) -> tuple[str, list[Finding]]:
        """Interpret de-identified eligibility response.

        Args:
            response: PHI-stripped eligibility response.

        Returns:
            Tuple of (ai_summary, findings).
        """
        assert response.is_deidentified, (  # noqa: S101
            "Only DeidentifiedEligibilityResponse may be sent to the LLM"
        )
        prompt = self._build_user_prompt(response)
        llm_response = self._send_to_llm([
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ])
        return self._parse_response(llm_response)

    def _build_user_prompt(
        self,
        response: DeidentifiedEligibilityResponse,
    ) -> str:
        """Format de-identified eligibility data for LLM analysis."""
        parts: list[str] = []

        # Eligibility status
        if response.eligible is not None:
            status = "eligible" if response.eligible else "not eligible"
            parts.append(f"Eligibility status: {status}")

        # Coverage details
        if response.coverage:
            cov = response.coverage
            parts.append(f"Coverage status: {cov.status.value}")
            if cov.effective_year:
                parts.append(f"Coverage effective year: {cov.effective_year}")
            if cov.termination_year:
                parts.append(
                    f"Coverage termination year: {cov.termination_year}"
                )

        # Benefits
        for i, benefit in enumerate(response.benefits, start=1):
            benefit_parts: list[str] = []
            if benefit.service_type_code:
                benefit_parts.append(
                    f"service type {benefit.service_type_code}"
                )
            if benefit.service_type_name:
                benefit_parts.append(f"({benefit.service_type_name})")
            if benefit.copay is not None:
                benefit_parts.append(f"copay=${benefit.copay:.2f}")
            if benefit.coinsurance is not None:
                pct = benefit.coinsurance * 100
                benefit_parts.append(f"coinsurance={pct:.0f}%")
            if benefit.deductible is not None:
                benefit_parts.append(
                    f"deductible=${benefit.deductible:.2f}"
                )
            if benefit.in_network is not None:
                net = "in-network" if benefit.in_network else "out-of-network"
                benefit_parts.append(net)
            if benefit.prior_auth_required is True:
                benefit_parts.append("prior auth required")
            parts.append(f"Benefit {i}: {' '.join(benefit_parts)}")

        # AAA errors
        for error in response.errors:
            error_parts = [f"rejection code {error.rejection_code}"]
            if error.follow_up_code:
                error_parts.append(
                    f"follow-up code {error.follow_up_code}"
                )
            parts.append(f"Error: {', '.join(error_parts)}")

        return "\n".join(parts) if parts else "No eligibility data available."

    def _parse_response(
        self,
        llm_text: str,
    ) -> tuple[str, list[Finding]]:
        """Parse LLM response — JSON first, free-text fallback."""
        result = self._try_parse_json(llm_text)
        if result is not None:
            return result
        return self._parse_free_text(llm_text)

    def _try_parse_json(
        self,
        text: str,
    ) -> tuple[str, list[Finding]] | None:
        """Try to parse structured JSON response."""
        try:
            data = json.loads(text)
            summary = data.get("summary", "")
            items = data.get("findings", [])
            findings: list[Finding] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                code = item.get("code", "AI_ELIG_BENEFIT_NOTE")
                if code not in self._VALID_CODES:
                    code = "AI_ELIG_BENEFIT_NOTE"
                findings.append(
                    Finding(
                        code=code,
                        message=item.get("message", ""),
                        severity=Severity.WARNING,
                        field_name="",
                        suggestion=item.get("suggestion", ""),
                        context={},
                    )
                )
            return summary, findings
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _parse_free_text(
        self,
        text: str,
    ) -> tuple[str, list[Finding]]:
        """Parse free-text LLM response as fallback."""
        summary = text.strip()
        # Truncate very long responses
        if len(summary) > 500:
            summary = summary[:497] + "..."
        findings: list[Finding] = []
        lower = text.lower()
        if _indicates_coverage_concern(lower):
            findings.append(
                Finding(
                    code="AI_ELIG_COVERAGE_CONCERN",
                    message=(
                        "AI detected potential coverage concern"
                    ),
                    severity=Severity.WARNING,
                    field_name="",
                    suggestion=(
                        "Review coverage details with the patient."
                    ),
                    context={},
                )
            )
        return summary, findings


def _indicates_coverage_concern(text: str) -> bool:
    """Check if free-text signals a coverage concern."""
    return any(
        kw in text
        for kw in (
            "not covered",
            "coverage concern",
            "limitation",
            "terminated",
            "inactive",
            "denied",
            "rejection",
            "not eligible",
            "no coverage",
        )
    )
