"""PriorAuthAI — AI prior authorization validator."""

from __future__ import annotations

import json
import re

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator


class PriorAuthAI(BaseAIValidator):
    """Identifies services likely to require prior authorization.

    Uses LLM analysis to flag procedures that commonly
    need payer pre-approval before submission.
    """

    name = "PriorAuthAI"

    SYSTEM_PROMPT = (
        "You are a healthcare prior authorization specialist. "
        "Analyze this claim to identify services that likely "
        "require prior authorization.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"field_name": <str>, "line_number": <int>, '
        '"reason": <str>}\n'
        "]}\n\n"
        "If no services require prior authorization, "
        'respond: {"findings": []}\n\n'
        "Consider:\n"
        "- High-cost imaging (MRI, CT, PET)\n"
        "- Surgical procedures above typical thresholds\n"
        "- Specialty medications and infusions\n"
        "- Durable medical equipment\n"
        "- Payer-specific prior auth requirements"
    )

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Evaluate prior authorization requirements."""
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
        """Format de-identified claim for auth analysis."""
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
                    code="AI_PRIOR_AUTH_LIKELY",
                    message=item.get(
                        "reason",
                        "Prior authorization likely required",
                    ),
                    severity=Severity.WARNING,
                    field_name=item.get(
                        "field_name", "procedure_code",
                    ),
                    line_number=item.get("line_number"),
                    suggestion=(
                        "Verify prior authorization status "
                        "with the payer before submission."
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
        if _indicates_prior_auth(lower):
            findings.append(
                self._make_finding(
                    code="AI_PRIOR_AUTH_LIKELY",
                    message=(
                        "AI detected potential prior"
                        " authorization requirement"
                    ),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                    suggestion=(
                        "Verify prior authorization status "
                        "with the payer before submission."
                    ),
                )
            )
        return findings


_NEGATION_RE = re.compile(
    r"(no\s+services|none\s+of|do\s+not|does\s+not|"
    r"not\s+require|no\s+.{0,30}require)",
)

_AUTH_KEYWORDS = (
    "requires prior authorization",
    "requires prior auth",
    "requires preauthorization",
    "requires precertification",
    "likely requires",
    "typically requires",
    "needs prior auth",
)


def _indicates_prior_auth(text: str) -> bool:
    """Check if free-text signals prior auth needed."""
    if _NEGATION_RE.search(text):
        return False
    return any(kw in text for kw in _AUTH_KEYWORDS)
