"""CoverageCheckAI — AI medical necessity & coverage validator."""

from __future__ import annotations

import json

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator


class CoverageCheckAI(BaseAIValidator):
    """Evaluates medical necessity and coverage concerns.

    Uses LLM analysis to detect services likely to be
    denied for medical necessity or coverage reasons.
    """

    name = "CoverageCheckAI"

    SYSTEM_PROMPT = (
        "You are a healthcare coverage analyst. Evaluate "
        "this claim for potential medical necessity and "
        "coverage concerns.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"field_name": <str>, "reason": <str>, '
        '"documentation": <str>}\n'
        "]}\n\n"
        "If no coverage concerns, respond: "
        '{"findings": []}\n\n'
        "Consider:\n"
        "- Services that commonly require medical "
        "necessity documentation\n"
        "- Diagnosis codes that may not support the "
        "procedure for coverage purposes\n"
        "- High-cost services with strict coverage "
        "criteria\n"
        "- Payer-specific coverage patterns"
    )

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Evaluate coverage and medical necessity."""
        prompt = self._build_user_prompt(claim)
        response = self._send_to_llm([
            Message(
                role="system", content=self.SYSTEM_PROMPT,
            ),
            Message(role="user", content=prompt),
        ])
        findings = self._parse_response(response)
        return self._make_output(findings)

    def _build_user_prompt(
        self,
        claim: DeidentifiedClaim,
    ) -> str:
        """Format de-identified claim for coverage analysis."""
        parts: list[str] = []
        if claim.patient_age is not None:
            parts.append(
                f"Patient age: {claim.patient_age}"
            )
        if claim.patient_gender:
            parts.append(
                f"Patient gender: {claim.patient_gender}"
            )
        if claim.payer_id:
            parts.append(f"Payer ID: {claim.payer_id}")
        if claim.payer_name:
            parts.append(
                f"Payer name: {claim.payer_name}"
            )
        if claim.place_of_service:
            parts.append(
                f"Place of service: "
                f"{claim.place_of_service}"
            )

        if claim.diagnosis_codes:
            codes = ", ".join(
                str(d.get("code", ""))
                for d in claim.diagnosis_codes
            )
            parts.append(f"Diagnosis codes: {codes}")

        for i, line in enumerate(claim.lines, start=1):
            mods = (
                f" (modifiers: {', '.join(line.modifiers)})"
                if line.modifiers
                else ""
            )
            parts.append(
                f"Line {i}: {line.procedure_code}{mods}"
                f" charge=${line.charge_amount:.2f}"
            )

        if claim.total_charge is not None:
            parts.append(
                f"Total charge: ${claim.total_charge:.2f}"
            )

        return "\n".join(parts)

    def _parse_response(
        self,
        response: str,
    ) -> list[Finding]:
        """Parse LLM response — JSON first, regex fallback."""
        findings = self._try_parse_json(response)
        if findings is not None:
            return findings
        return self._parse_free_text(response)

    def _try_parse_json(
        self,
        response: str,
    ) -> list[Finding] | None:
        """Try to parse structured JSON response."""
        try:
            data = json.loads(response)
            items = data.get("findings", [])
            if not items:
                return []
            return [
                self._make_finding(
                    code="AI_COVERAGE_CONCERN",
                    message=item.get(
                        "reason",
                        "Coverage concern detected",
                    ),
                    severity=Severity.WARNING,
                    field_name=item.get(
                        "field_name", "procedure_code",
                    ),
                    suggestion=item.get(
                        "documentation", "",
                    ),
                )
                for item in items
                if isinstance(item, dict)
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _parse_free_text(
        self,
        response: str,
    ) -> list[Finding]:
        """Parse free-text response via regex fallback."""
        findings: list[Finding] = []
        lower = response.lower()
        if _indicates_coverage_concern(lower):
            findings.append(
                self._make_finding(
                    code="AI_COVERAGE_CONCERN",
                    message=(
                        "AI detected potential coverage"
                        " or medical necessity concern"
                    ),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                    suggestion=(
                        "Review medical necessity"
                        " documentation before"
                        " submission."
                    ),
                )
            )
        return findings


def _indicates_coverage_concern(text: str) -> bool:
    """Check if free-text signals a coverage concern."""
    return any(
        kw in text
        for kw in (
            "coverage concern",
            "medical necessity",
            "not covered",
            "may be denied",
            "documentation required",
            "coverage risk",
            "deny",
            "denial",
        )
    )
