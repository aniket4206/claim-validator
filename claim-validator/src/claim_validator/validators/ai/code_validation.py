"""CodeValidationAI — AI clinical plausibility validator."""

from __future__ import annotations

import json
import re

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator


class CodeValidationAI(BaseAIValidator):
    """Checks clinical plausibility of diagnosis-procedure pairs.

    Uses LLM analysis to detect combinations that are
    clinically implausible and likely to be denied.
    """

    name = "CodeValidationAI"

    SYSTEM_PROMPT = (
        "You are a medical coding auditor. Analyze the "
        "diagnosis-procedure combinations in this claim "
        "for clinical plausibility.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"line_number": <int>, "field_name": <str>, '
        '"reason": <str>}\n'
        "]}\n\n"
        "If all combinations are clinically plausible, "
        'respond: {"findings": []}\n\n'
        "Rules:\n"
        "- Flag gender-specific procedures billed for "
        "wrong gender\n"
        "- Flag age-inappropriate procedures\n"
        "- Flag diagnosis codes that do not clinically "
        "support the procedure\n"
        "- Only flag clear implausibilities, not "
        "borderline cases"
    )

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Analyze clinical plausibility of claim coding."""
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
        """Format de-identified claim for LLM analysis."""
        parts: list[str] = []
        if claim.patient_age is not None:
            parts.append(
                f"Patient age: {claim.patient_age}"
            )
        if claim.patient_gender:
            parts.append(
                f"Patient gender: {claim.patient_gender}"
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
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=item.get(
                        "reason",
                        "Clinical plausibility concern",
                    ),
                    severity=Severity.WARNING,
                    field_name=item.get(
                        "field_name", "procedure_code",
                    ),
                    line_number=item.get("line_number"),
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
        pattern = re.compile(
            r"[Ll]ine\s*(\d+)[:\s]+(.+?)(?:\n|$)",
        )
        for match in pattern.finditer(response):
            findings.append(
                self._make_finding(
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=match.group(2).strip(),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                    line_number=int(match.group(1)),
                )
            )

        if not findings and _indicates_issue(response):
            findings.append(
                self._make_finding(
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=(
                        "AI detected clinical plausibility"
                        " concern"
                    ),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                )
            )
        return findings


def _indicates_issue(text: str) -> bool:
    """Check if free-text response signals an issue."""
    lower = text.lower()
    return any(
        kw in lower
        for kw in (
            "implausible",
            "inappropriate",
            "mismatch",
            "inconsistent",
            "unlikely",
            "concern",
            "flag",
        )
    )
