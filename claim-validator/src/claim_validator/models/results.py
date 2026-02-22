"""Validation result models — Finding, ValidatorOutput, PhaseResult, PipelineResult."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from claim_validator.constants import Severity


class Finding(BaseModel):
    """Single validation finding with error code, message, severity, and fix suggestion."""

    model_config = ConfigDict(frozen=True, strict=False)

    code: str
    message: str
    severity: Severity
    field_name: str
    line_number: int | None = None
    suggestion: str = ""
    context: dict[str, Any] | None = None


class ValidatorOutput(BaseModel):
    """Output from a single validator run."""

    model_config = ConfigDict(frozen=True, strict=False)

    validator_name: str
    findings: list[Finding] = []


class PhaseResult(BaseModel):
    """Result from one validation phase (rule-based or AI)."""

    model_config = ConfigDict(frozen=True, strict=False)

    phase: str
    validator_outputs: list[ValidatorOutput] = []
    execution_time: float = 0.0

    @property
    def findings(self) -> list[Finding]:
        """Flat list of all findings from all validators in this phase."""
        result: list[Finding] = []
        for output in self.validator_outputs:
            result.extend(output.findings)
        return result


class PipelineResult(BaseModel):
    """Aggregated result from the full validation pipeline."""

    model_config = ConfigDict(frozen=True, strict=False)

    phase_results: list[PhaseResult] = []
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only if zero ERROR-severity findings. WARNINGs do not fail."""
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def findings(self) -> list[Finding]:
        """Flat list of all findings ordered by phase, severity (ERROR first), validator order."""
        all_findings: list[Finding] = []
        for phase_result in self.phase_results:
            for output in phase_result.validator_outputs:
                all_findings.extend(output.findings)
        return sorted(all_findings, key=lambda f: 0 if f.severity == Severity.ERROR else 1)

    @property
    def errors(self) -> list[Finding]:
        """All ERROR-severity findings."""
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        """All WARNING-severity findings."""
        return [f for f in self.findings if f.severity == Severity.WARNING]
