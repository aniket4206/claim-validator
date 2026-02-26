# Story 2.6: Monetary & Duplicate Validators

Status: review

## Story

As a **developer**,
I want charge amounts validated and duplicate lines detected,
so that claims with financial errors or redundant lines are caught before submission.

## Acceptance Criteria

1. **Given** a claim where all line charge amounts are positive, **When** `MonetaryValidator.validate(claim)` is called, **Then** the output contains zero monetary findings.

2. **Given** a claim with a line that has zero or negative charge amount, **When** `MonetaryValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_CHARGE_AMOUNT`, severity `ERROR`, `field_name` `"charge_amount"`, and `line_number` is produced.

3. **Given** a claim where `total_charge` is provided and line charges (charge_amount * units) do not sum to total_charge within a tolerance of 0.01, **When** `MonetaryValidator.validate(claim)` is called, **Then** a `Finding` with code `CHARGE_TOTAL_MISMATCH`, severity `ERROR`, `field_name` `"total_charge"` is produced.

4. **Given** a claim where `total_charge` is `None` (not provided), **When** `MonetaryValidator.validate(claim)` is called, **Then** no total mismatch finding is produced (total_charge is optional).

5. **Given** a claim where total_charge exactly matches the sum of (charge_amount * units) for all lines, **When** `MonetaryValidator.validate(claim)` is called, **Then** zero total mismatch findings are produced.

6. **Given** a claim with empty `lines` list, **When** `MonetaryValidator.validate(claim)` is called, **Then** zero monetary findings are produced (CompletenessValidator handles required-ness).

7. **Given** a claim with no duplicate lines (different procedure codes or different service dates), **When** `DuplicateValidator.validate(claim)` is called, **Then** the output contains zero duplicate findings.

8. **Given** a claim with two lines having the same procedure code, same modifiers, and same service_date_from, **When** `DuplicateValidator.validate(claim)` is called, **Then** a `Finding` with code `DUPLICATE_LINE`, severity `WARNING`, `field_name` `"lines"`, and `line_number` identifying the later duplicate line is produced.

9. **Given** a claim with two lines having the same procedure code but different modifiers, **When** `DuplicateValidator.validate(claim)` is called, **Then** zero duplicate findings are produced (modifiers distinguish procedures).

10. **Given** a claim with two lines having the same procedure code but different service dates, **When** `DuplicateValidator.validate(claim)` is called, **Then** zero duplicate findings are produced (different dates = different services).

11. **Given** a claim with empty `lines` list, **When** `DuplicateValidator.validate(claim)` is called, **Then** zero duplicate findings are produced.

12. **Given** any monetary or duplicate finding, **When** I inspect the `message`, **Then** it references field names but never actual charge values or code values (no PHI in messages).

## Tasks / Subtasks

- [x] Task 1: Implement `MonetaryValidator` in `src/claim_validator/validators/rule_based/monetary.py` (AC: #1-#6, #12)
  - [x] Subclass `BaseValidator` with `name = "MonetaryValidator"`
  - [x] `_check_line_charges()`: Validate each line's charge_amount > 0
  - [x] `_check_total_charge()`: If total_charge is provided, compare against sum of (charge_amount * units) for all lines, with 0.01 tolerance
  - [x] Skip if lines is empty (CompletenessValidator handles required-ness)
  - [x] No PHI in messages — never include actual charge values
- [x] Task 2: Implement `DuplicateValidator` in `src/claim_validator/validators/rule_based/duplicate.py` (AC: #7-#12)
  - [x] Subclass `BaseValidator` with `name = "DuplicateValidator"`
  - [x] `_check_duplicate_lines()`: Detect lines with same (procedure_code, sorted modifiers, service_date_from) tuple
  - [x] DUPLICATE_LINE is WARNING (not ERROR) — duplicates may be intentional (e.g., bilateral procedures)
  - [x] line_number on finding identifies the later duplicate line
  - [x] Skip if lines is empty
  - [x] No PHI in messages
- [x] Task 3: Write tests in `tests/test_validators/test_rule_based/test_monetary.py` (AC: #1-#6, #12)
  - [x] Test valid positive charges → zero findings
  - [x] Test zero charge_amount → `INVALID_CHARGE_AMOUNT`
  - [x] Test negative charge_amount → `INVALID_CHARGE_AMOUNT`
  - [x] Test total_charge matches line sum → zero findings
  - [x] Test total_charge mismatch → `CHARGE_TOTAL_MISMATCH`
  - [x] Test total_charge within tolerance (0.01) → zero findings
  - [x] Test total_charge is None → no mismatch finding
  - [x] Test empty lines → no findings
  - [x] Test multiple invalid charges → multiple findings
  - [x] Test severity is ERROR for all monetary findings
  - [x] Test line_number present on line-level charge findings
  - [x] Test suggestion present on findings
  - [x] Test no PHI in finding messages
  - [x] Test validator statelessness
- [x] Task 4: Write tests in `tests/test_validators/test_rule_based/test_duplicate.py` (AC: #7-#12)
  - [x] Test no duplicate lines → zero findings
  - [x] Test duplicate lines (same code, modifiers, date) → `DUPLICATE_LINE`
  - [x] Test same code, different modifiers → no duplicate finding
  - [x] Test same code, different service_date_from → no duplicate finding
  - [x] Test empty lines → no findings
  - [x] Test triple duplicate → two findings (2nd and 3rd flagged)
  - [x] Test severity is WARNING for DUPLICATE_LINE
  - [x] Test line_number identifies the later duplicate
  - [x] Test suggestion present on findings
  - [x] Test no PHI in finding messages
  - [x] Test validator statelessness
- [x] Task 5: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `MonetaryValidator` and `DuplicateValidator` re-exports
- [x] Task 6: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors
  - [x] `uv run pytest` — all tests pass (369 = 327 existing + 42 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.5)

- CodingValidator established patterns: module-level compiled regex, private `_check_*` helper methods, `self._make_output(findings)`
- Test pattern: helper `_valid_claim_dict()` returning baseline valid claim, class-based tests with `setup_method`
- Line iteration: `for idx, line in enumerate(claim.lines, start=1)` — line_number is 1-indexed
- Empty/whitespace strings handled via `not value or not value.strip()`
- Format check short-circuits before deeper validation
- 327 tests passing, ruff/mypy clean (33 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `test_rule_based/` directory and `__init__.py` already exist
- Line-length limit is 100 characters — wrap long strings with implicit concatenation

### Relevant ClaimData Fields

| Field | Location | Type | Validator Scope |
|---|---|---|---|
| `total_charge` | `ClaimData` | `float \| None = None` | MonetaryValidator — total mismatch |
| `lines` | `ClaimData` | `list[ClaimLineData]` | Both validators iterate lines |
| `lines[].charge_amount` | `ClaimLineData` | `float` | MonetaryValidator — positive check |
| `lines[].units` | `ClaimLineData` | `float = 1.0` | MonetaryValidator — extended charge |
| `lines[].procedure_code` | `ClaimLineData` | `str` | DuplicateValidator — duplicate key |
| `lines[].modifiers` | `ClaimLineData` | `list[str] = []` | DuplicateValidator — duplicate key |
| `lines[].service_date_from` | `ClaimLineData` | `str \| None = None` | DuplicateValidator — duplicate key |

### Finding Codes

| Code | Meaning | Severity | Scope |
|---|---|---|---|
| `INVALID_CHARGE_AMOUNT` | Charge amount is zero or negative | `ERROR` | Line-level |
| `CHARGE_TOTAL_MISMATCH` | Line charges don't sum to total_charge | `ERROR` | Claim-level |
| `DUPLICATE_LINE` | Duplicate line detected | `WARNING` | Line-level (later line) |

### Implementation Spec

```python
# src/claim_validator/validators/rule_based/monetary.py
"""MonetaryValidator -- charge amount and total validation."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_CHARGE_TOLERANCE = 0.01


class MonetaryValidator(BaseValidator):
    """Validates charge amounts and total charge consistency."""

    name = "MonetaryValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_line_charges(claim, findings)
        self._check_total_charge(claim, findings)

        return self._make_output(findings)

    def _check_line_charges(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        for idx, line in enumerate(claim.lines, start=1):
            if line.charge_amount <= 0:
                findings.append(
                    self._make_finding(
                        code="INVALID_CHARGE_AMOUNT",
                        message=(
                            "Charge amount in 'charge_amount'"
                            " must be a positive value"
                        ),
                        severity=Severity.ERROR,
                        field_name="charge_amount",
                        line_number=idx,
                        suggestion=(
                            "Verify the charge amount for"
                            " this service line"
                            " (CMS-1500 Box 24.F)"
                        ),
                    )
                )

    def _check_total_charge(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if claim.total_charge is None or not claim.lines:
            return

        computed_total = sum(
            line.charge_amount * line.units
            for line in claim.lines
        )

        if abs(claim.total_charge - computed_total) > _CHARGE_TOLERANCE:
            findings.append(
                self._make_finding(
                    code="CHARGE_TOTAL_MISMATCH",
                    message=(
                        "Total in 'total_charge' does not"
                        " match sum of line charges"
                    ),
                    severity=Severity.ERROR,
                    field_name="total_charge",
                    suggestion=(
                        "Ensure total charge equals"
                        " the sum of all line"
                        " (charge_amount * units)"
                        " (CMS-1500 Box 28)"
                    ),
                )
            )
```

```python
# src/claim_validator/validators/rule_based/duplicate.py
"""DuplicateValidator -- duplicate claim line detection."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class DuplicateValidator(BaseValidator):
    """Detects duplicate claim lines within a single claim."""

    name = "DuplicateValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_duplicate_lines(claim, findings)

        return self._make_output(findings)

    def _check_duplicate_lines(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        seen: dict[tuple, int] = {}

        for idx, line in enumerate(claim.lines, start=1):
            key = (
                line.procedure_code.strip(),
                tuple(sorted(line.modifiers)),
                (line.service_date_from or "").strip(),
            )

            if key in seen:
                findings.append(
                    self._make_finding(
                        code="DUPLICATE_LINE",
                        message=(
                            "Service line in 'lines'"
                            " appears to be a duplicate"
                            " of an earlier line"
                        ),
                        severity=Severity.WARNING,
                        field_name="lines",
                        line_number=idx,
                        suggestion=(
                            "Review duplicate service"
                            " lines — if intentional,"
                            " add distinguishing"
                            " modifiers (e.g., 50, LT,"
                            " RT)"
                        ),
                    )
                )
            else:
                seen[key] = idx
```

### Key Design Decisions

- **MonetaryValidator** checks two things: individual line charges > 0 and total charge consistency
- `total_charge` is optional — if not provided, no total mismatch check is performed
- Floating-point comparison uses `_CHARGE_TOLERANCE = 0.01` to account for rounding
- Extended charge per line = `charge_amount * units` (units defaults to 1.0)
- **DuplicateValidator** detects lines with same (procedure_code, sorted modifiers, service_date_from)
- Modifiers are sorted before comparison so order doesn't matter
- `DUPLICATE_LINE` is `WARNING` (not `ERROR`) — bilateral procedures, therapy services, etc. may legitimately repeat
- Finding's `line_number` identifies the later duplicate line, not the first occurrence
- Empty lines silently skipped — CompletenessValidator handles required field presence
- Messages reference field names, not actual values (no PHI)

### Anti-Patterns to Avoid

- **DO NOT** include actual charge amounts in finding messages — no PHI
- **DO NOT** validate empty lines — CompletenessValidator handles that
- **DO NOT** use exact float comparison for total_charge — use tolerance
- **DO NOT** store state between validate() calls
- **DO NOT** raise exceptions for validation failures — return findings
- **DO NOT** flag duplicate lines as ERROR — duplicates may be intentional
- **DO NOT** compare `service_date_to` in duplicate key — only `service_date_from` is the primary service date
- **DO NOT** use integer comparison for charges — they are floats

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR14** | Validate charge amounts are positive and line totals consistent |
| **FR16** | Detect duplicate claim lines within a single claim |
| **NFR1** | Rule-based latency < 50ms — no I/O, simple arithmetic and dict lookups |
| **NFR8** | Zero network calls for rule-based |
| **NFR10** | No PHI in outputs — field names only in messages |
| **NFR15** | Stateless validation |
| **D10** | Dotted paths: `claim_validator.validators.rule_based.monetary.MonetaryValidator`, `claim_validator.validators.rule_based.duplicate.DuplicateValidator` |

### conf.py Default Validators

Both validators are already listed in `DEFAULT_RULE_VALIDATORS` in `conf.py`:
```python
"claim_validator.validators.rule_based.monetary.MonetaryValidator",
"claim_validator.validators.rule_based.duplicate.DuplicateValidator",
```
No configuration changes needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.6] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR14] — Charge amount validation
- [Source: _bmad-output/planning-artifacts/prd.md#FR16] — Duplicate line detection
- [Source: CMS-1500 Form] — Box 24.F (Charges), Box 28 (Total Charge)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- RED phase: Both test files confirmed ImportError before implementation
- GREEN phase: MonetaryValidator (2 check methods) and DuplicateValidator (1 check method) implemented from story spec
- All 12 acceptance criteria covered by 42 tests across 10 test classes
- MonetaryValidator: `_check_line_charges()` validates charge_amount > 0, `_check_total_charge()` compares total_charge to sum of (charge_amount * units) with 0.01 tolerance
- DuplicateValidator: `_check_duplicate_lines()` uses (procedure_code, sorted modifiers, service_date_from) tuple as duplicate key; flags later duplicate lines as WARNING
- No PHI in any finding messages — verified by explicit tests
- Both validators already listed in conf.py DEFAULT_RULE_VALIDATORS
- 369 tests pass (327 existing + 42 new), ruff clean, mypy clean (35 source files)

### File List

- `src/claim_validator/validators/rule_based/monetary.py` — NEW: MonetaryValidator
- `src/claim_validator/validators/rule_based/duplicate.py` — NEW: DuplicateValidator
- `src/claim_validator/validators/rule_based/__init__.py` — MODIFIED: Added re-exports
- `tests/test_validators/test_rule_based/test_monetary.py` — NEW: 24 tests
- `tests/test_validators/test_rule_based/test_duplicate.py` — NEW: 18 tests

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 369 tests pass, status → review |
