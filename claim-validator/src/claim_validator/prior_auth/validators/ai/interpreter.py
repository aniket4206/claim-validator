"""PriorAuthInterpreterAI — AI-powered prior authorization response interpreter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator

if TYPE_CHECKING:
    from claim_validator.models.deidentified import DeidentifiedClaim
    from claim_validator.prior_auth.models.deidentified import (
        DeidentifiedPriorAuthResponse,
    )


class PriorAuthInterpreterAI(BaseAIValidator):
    """Interprets de-identified prior authorization data via LLM.

    Generates human-readable PA decision summaries and actionable
    findings from PA response data.  All output uses ``AI_PA_``
    code prefixes with ``WARNING`` severity only.
    """

    name = "PriorAuthInterpreterAI"

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Not used — interpreter uses interpret() instead.

        Raises:
            NotImplementedError: Always. Use ``interpret()`` with
                ``DeidentifiedPriorAuthResponse``.
        """
        raise NotImplementedError(
            "Use interpret() with DeidentifiedPriorAuthResponse. "
            "The prior auth pipeline calls interpret() directly."
        )

    SYSTEM_PROMPT = (
        "You are a healthcare prior authorization analyst. Interpret "
        "this de-identified PA response data and provide:\n\n"
        "1. A clear, concise summary of the authorization decision\n"
        "2. Any denial reasons with plain-English explanations\n"
        "3. Recommended next steps (appeal strategy, additional info needed)\n\n"
        "Respond in JSON format:\n"
        '{"summary": "<decision summary>", "findings": [\n'
        '  {"code": "AI_PA_<TYPE>", "message": "<str>", '
        '"suggestion": "<str>"}\n'
        "]}\n\n"
        "Valid finding codes:\n"
        "- AI_PA_APPROVAL_SUMMARY: Approved case explanation\n"
        "- AI_PA_DENIAL_EXPLAINED: Denial interpretation + appeal strategy\n"
        "- AI_PA_PENDED_NEXT_STEPS: Pended case follow-up recommendations\n"
        "- AI_PA_CLINICAL_CONCERN: Clinical issue detected\n"
        "- AI_PA_GENERAL_NOTE: General PA information\n\n"
        "If no findings, respond: "
        '{"summary": "<summary>", "findings": []}\n\n'
        "IMPORTANT: Do not include any patient-identifying information."
    )

    _VALID_CODES = frozenset({
        "AI_PA_APPROVAL_SUMMARY",
        "AI_PA_DENIAL_EXPLAINED",
        "AI_PA_PENDED_NEXT_STEPS",
        "AI_PA_CLINICAL_CONCERN",
        "AI_PA_GENERAL_NOTE",
    })

    def interpret(
        self,
        response: DeidentifiedPriorAuthResponse,
    ) -> tuple[str, list[Finding]]:
        """Interpret de-identified prior authorization response.

        Args:
            response: PHI-stripped PA response.

        Returns:
            Tuple of (ai_summary, findings).
        """
        assert response.is_deidentified, (  # noqa: S101
            "Only DeidentifiedPriorAuthResponse may be sent to the LLM"
        )
        prompt = self._build_user_prompt(response)
        llm_response = self._send_to_llm([
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ])
        return self._parse_response(llm_response)

    def _build_user_prompt(
        self,
        response: DeidentifiedPriorAuthResponse,
    ) -> str:
        """Format de-identified PA data for LLM analysis."""
        parts: list[str] = []

        # Overall action code
        if response.action_code is not None:
            parts.append(f"Action code: {response.action_code.value}")

        # Decision reason
        if response.decision_reason_code:
            parts.append(
                f"Decision reason code: {response.decision_reason_code}"
            )

        # Date range (year only — no PHI)
        if response.effective_year is not None:
            parts.append(f"Effective year: {response.effective_year}")
        if response.expiration_year is not None:
            parts.append(f"Expiration year: {response.expiration_year}")

        # Service line decisions
        for i, sld in enumerate(response.service_line_decisions, start=1):
            sld_parts: list[str] = []
            if sld.cpt_code:
                sld_parts.append(f"CPT {sld.cpt_code}")
            if sld.action_code is not None:
                sld_parts.append(f"action {sld.action_code.value}")
            if sld.approved_quantity is not None:
                sld_parts.append(f"quantity {sld.approved_quantity}")
            parts.append(
                f"Service line {i}: {', '.join(sld_parts)}"
                if sld_parts
                else f"Service line {i}: no details"
            )

        # Error codes
        for error in response.errors:
            error_parts = [f"rejection code {error.rejection_code}"]
            if error.follow_up_code:
                error_parts.append(
                    f"follow-up code {error.follow_up_code}"
                )
            parts.append(f"Error: {', '.join(error_parts)}")

        return "\n".join(parts) if parts else "No PA response data available."

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
                code = item.get("code", "AI_PA_GENERAL_NOTE")
                if code not in self._VALID_CODES:
                    code = "AI_PA_GENERAL_NOTE"
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
        if len(summary) > 500:
            summary = summary[:497] + "..."
        findings: list[Finding] = []
        lower = text.lower()
        if _indicates_pa_concern(lower):
            findings.append(
                Finding(
                    code="AI_PA_CLINICAL_CONCERN",
                    message="AI detected potential PA concern",
                    severity=Severity.WARNING,
                    field_name="",
                    suggestion=(
                        "Review the PA decision and consider appeal options."
                    ),
                    context={},
                )
            )
        return summary, findings


def _indicates_pa_concern(text: str) -> bool:
    """Check if free-text signals a PA concern."""
    return any(
        kw in text
        for kw in (
            "denied",
            "not certified",
            "appeal",
            "pended",
            "pending review",
            "additional information needed",
        )
    )
