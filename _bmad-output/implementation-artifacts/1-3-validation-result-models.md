# Story 1.3: Validation Result Models

Status: ready-for-dev

## Story

As a **developer**,
I want structured result objects for validation outcomes,
so that I can programmatically inspect findings with error codes, messages, severity, and fix suggestions.

## Acceptance Criteria

1. **Given** a `Finding` object, **When** I inspect its fields, **Then** it has `code` (str, UPPER_SNAKE_CASE), `message` (str, human-readable), `severity` (Severity enum), `field_name` (str), `line_number` (int | None), `suggestion` (str), and `context` (dict | None).

2. **Given** a list of `Finding` objects, **When** I construct a `ValidatorOutput`, **Then** a `ValidatorOutput` is created containing the validator name and findings list.

3. **Given** a `PipelineResult`, **When** I check `result.passed`, **Then** it returns `True` only if there are zero ERROR-severity findings, and WARNING-severity findings do not cause `passed` to be `False`.

4. **Given** a `PipelineResult`, **When** I access `result.findings`, **Then** I receive a flat list of all `Finding` objects from all validators, ordered by phase (rule-based first), then severity (ERROR first), then validator order.

5. **Given** a `PipelineResult`, **When** I access `result.phase_results` and `result.execution_time`, **Then** per-phase breakdown is available for debugging and total execution time is recorded.

6. **Given** any `Finding` object created by any validator, **When** I inspect `message` and `suggestion`, **Then** they reference field names only, never raw PHI values.

## Tasks / Subtasks

- [ ] Task 1: Implement Finding model (AC: #1)
  - [ ] Create frozen Pydantic model in `models/results.py`
  - [ ] Fields: `code`, `message`, `severity`, `field_name`, `line_number`, `suggestion`, `context`
  - [ ] `severity` typed as `Severity` enum, `line_number` as `int | None`, `context` as `dict[str, Any] | None`
- [ ] Task 2: Implement ValidatorOutput model (AC: #2)
  - [ ] Create frozen Pydantic model with `validator_name: str` and `findings: list[Finding]`
- [ ] Task 3: Implement PhaseResult model (AC: #5)
  - [ ] Create frozen model with `phase: str`, `validator_outputs: list[ValidatorOutput]`, `execution_time: float`
  - [ ] Add computed property `findings` that flattens all outputs into a single list
- [ ] Task 4: Implement PipelineResult model (AC: #3, #4, #5)
  - [ ] Create frozen model with `phase_results: list[PhaseResult]`, `execution_time: float`
  - [ ] Implement `passed` property: True only if zero ERROR-severity findings
  - [ ] Implement `findings` property: flat list ordered by phase, then severity (ERROR first), then validator order
  - [ ] Implement `errors` and `warnings` convenience properties
- [ ] Task 5: Wire up re-exports (AC: all)
  - [ ] Add `Finding`, `ValidatorOutput`, `PipelineResult` to `models/__init__.py`
  - [ ] Add to `claim_validator/__init__.py` `__all__`
- [ ] Task 6: Write tests (AC: all)
  - [ ] `tests/test_models/test_results.py` — all result model behaviors
  - [ ] Test `passed` with zero findings, ERROR-only, WARNING-only, mixed
  - [ ] Test findings ordering: phase → severity → validator order
  - [ ] Test PhaseResult flattening
  - [ ] Test no PHI in finding fields (convention test)
- [ ] Task 7: Verify tooling
  - [ ] `uv run ruff check .` — zero warnings
  - [ ] `uv run mypy src/` — zero errors
  - [ ] `uv run pytest` — all tests pass

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/` — edit existing placeholder `src/claim_validator/models/results.py`.

### Previous Story Intelligence (Story 1.2)

- `Severity` StrEnum implemented in `constants.py` with `ERROR = "error"` and `WARNING = "warning"`
- All models use `frozen=True`, `strict=False` via `ConfigDict`
- `models/__init__.py` re-exports `ClaimData`, `ClaimLineData`, `DiagnosisCode`
- `claim_validator/__init__.py` re-exports all public symbols with `__all__`
- Pattern: `from __future__ import annotations` at top of every file
- 35 tests passing, ruff/mypy/pytest all green

### Model Design

All three result models go in `src/claim_validator/models/results.py`:

```python
class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    code: str                           # UPPER_SNAKE_CASE, e.g. "INVALID_NPI"
    message: str                        # Human-readable, NO PHI values
    severity: Severity                  # Severity.ERROR or Severity.WARNING
    field_name: str                     # e.g. "billing_provider_npi"
    line_number: int | None = None      # None for claim-level, int for line-level
    suggestion: str = ""                # Actionable fix suggestion, NO PHI values
    context: dict[str, Any] | None = None  # Non-PHI computed values (check digits, code lookups)


class ValidatorOutput(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    validator_name: str
    findings: list[Finding] = []


class PhaseResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    phase: str                                    # "rule_based" or "ai"
    validator_outputs: list[ValidatorOutput] = []
    execution_time: float = 0.0                   # seconds
```

### PipelineResult — The Key Model

`PipelineResult` needs computed properties (not stored fields) for `passed`, `findings`, `errors`, `warnings`. Use `@property` since the model is frozen and these are derived:

```python
class PipelineResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    phase_results: list[PhaseResult] = []
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only if zero ERROR-severity findings."""
        return not any(f.severity == Severity.ERROR for f in self.findings)

    @property
    def findings(self) -> list[Finding]:
        """Flat list of all findings, ordered: phase -> severity (ERROR first) -> validator order."""
        all_findings: list[Finding] = []
        for phase_result in self.phase_results:
            for output in phase_result.validator_outputs:
                all_findings.extend(output.findings)
        # Sort: errors before warnings, preserve phase and validator order as stable sort
        return sorted(all_findings, key=lambda f: (0 if f.severity == Severity.ERROR else 1))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]
```

### Findings Ordering Logic (AC #4)

The ordering requirement is: **phase (rule-based first), then severity (ERROR first), then validator order**.

Since `phase_results` is already ordered (rule-based phase added first, AI phase second), and `validator_outputs` within each phase are ordered by pipeline execution, the base order from iteration is already correct for phase and validator order. We only need to sort by severity within that, using a **stable sort** so that phase/validator order is preserved for findings of the same severity.

Implementation: iterate phase_results in order, collect all findings, then stable-sort by severity (ERROR=0, WARNING=1).

### PHI Safety in Findings (AC #6)

This AC is a **convention** enforced by validators (Epic 2), not by the Finding model itself. The model doesn't validate message content. However, tests should document the convention:

```python
def test_finding_phi_convention() -> None:
    """Findings must reference field names, not PHI values."""
    # CORRECT: references field name
    good = Finding(code="INVALID_NPI", message="NPI fails Luhn check", severity=Severity.ERROR, field_name="billing_provider_npi")
    assert "1234567890" not in good.message  # No actual NPI in message

    # Convention: validators must follow this pattern
    # The model doesn't enforce it — validators do
```

### Anti-Patterns to Avoid

- **DO NOT** make `passed`, `findings`, `errors`, `warnings` stored fields — they are computed `@property` from `phase_results`
- **DO NOT** add a `findings` field to `PipelineResult` — it's derived from `phase_results` to avoid data duplication
- **DO NOT** use `@computed_field` (Pydantic v2) — plain `@property` is simpler and doesn't add to serialization
- **DO NOT** validate that `code` is UPPER_SNAKE_CASE in the model — that's a convention enforced by code review and naming patterns
- **DO NOT** add `from __future__ import annotations` **and** use `dict[str, Any]` in Pydantic model field annotations at the same time if it causes issues — Pydantic needs real types at runtime for validation. If `from __future__ import annotations` causes Pydantic to fail on `dict[str, Any]`, use `Dict[str, Any]` from typing or remove the future import from this file only. Test this.

### Important: `from __future__ import annotations` and Pydantic

Pydantic 2.x with `ConfigDict` handles `from __future__ import annotations` correctly in most cases. The existing `models/claim.py` uses it successfully. However, `dict[str, Any]` in `context: dict[str, Any] | None` should work fine since Python 3.11+ supports this natively and Pydantic evaluates annotations at class creation time. If any issue arises, fall back to `Optional[dict[str, Any]]`.

### Architecture Compliance

| Decision | Requirement for This Story |
|---|---|
| **D3: Pydantic models** | `frozen=True`, `strict=False` on all models |
| **D13: Import/export** | Re-export `Finding`, `ValidatorOutput`, `PipelineResult` at top level |
| **Naming** | `Finding`, `ValidatorOutput`, `PhaseResult`, `PipelineResult` — no `Data` suffix for result types |
| **PHI safety** | Finding `message`/`suggestion` must not contain PHI — convention, not model enforcement |
| **Communication pattern** | `PipelineResult.passed` = True iff zero ERROR findings. WARNINGs are advisory |

### File Targets

| File | Action | Contents |
|---|---|---|
| `src/claim_validator/models/results.py` | Edit (exists, placeholder) | `Finding`, `ValidatorOutput`, `PhaseResult`, `PipelineResult` |
| `src/claim_validator/models/__init__.py` | Edit | Add re-exports for new models |
| `src/claim_validator/__init__.py` | Edit | Add `Finding`, `ValidatorOutput`, `PipelineResult` to `__all__` |
| `tests/test_models/test_results.py` | Create | All result model tests |

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns] — Finding field format, PHI rule
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] — PipelineResult.passed logic, findings ordering
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture] — Two-phase execution, result aggregation
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3] — Full acceptance criteria

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
