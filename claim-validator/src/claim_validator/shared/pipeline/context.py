"""ValidationContext — cross-stage passthrough tracker.

Records which validation categories have already passed so that later
pipeline stages can skip redundant validators and reuse prior findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from claim_validator.models.results import Finding


@dataclass
class ValidatorResult:
    """Outcome of a single validator execution, tagged by category."""

    validator_name: str
    category: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ValidationContext:
    """Tracks validation results across pipeline stages.

    Keyed by category (e.g. ``"npi"``, ``"member_id"``, ``"demographics"``).
    When a category has already passed, later stages can skip their
    equivalent validator and reuse the prior findings instead.
    """

    _results: dict[str, ValidatorResult] = field(default_factory=dict)

    def record(
        self,
        validator_name: str,
        category: str,
        passed: bool,
        findings: list[Finding] | None = None,
    ) -> None:
        """Record the result of a validator execution.

        Note: if the same category is recorded again (e.g. by a downstream
        stage), the previous result is overwritten (last-write-wins).
        """
        self._results[category] = ValidatorResult(
            validator_name=validator_name,
            category=category,
            passed=passed,
            findings=list(findings) if findings else [],
        )

    def has_passed(self, category: str) -> bool:
        """Return True if the given category has been recorded as passed."""
        result = self._results.get(category)
        return result is not None and result.passed

    def get_prior_findings(self, category: str) -> list[Finding]:
        """Return findings from a previously-passed category, or empty list."""
        result = self._results.get(category)
        if result is None:
            return []
        return list(result.findings)


# Mapping from validator name → passthrough category.
# Validators not listed here are never subject to passthrough.
VALIDATOR_CATEGORY_MAP: dict[str, str] = {
    # NPI validators
    "EligibilityNPIValidator": "npi",
    "PANPIValidator": "npi",
    "NPIValidator": "npi",
    # Member ID / Subscriber ID validators
    "MemberIDValidator": "member_id",
    "PAMemberIDValidator": "member_id",
    "SubscriberIDValidator": "member_id",
    # Demographics validators
    "EligibilityDemographicsValidator": "demographics",
    "DemographicsValidator": "demographics",
}
