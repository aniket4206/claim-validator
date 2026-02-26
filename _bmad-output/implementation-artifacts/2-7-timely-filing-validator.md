# Story 2.7: Timely Filing Validator

Status: review

## Story

As a **developer**,
I want service dates validated for consistency and timely filing deadlines checked,
so that claims with date errors or past-deadline submissions are caught before submission.

## Acceptance Criteria

1. **Given** a claim with consistent dates (service date not in the future, service date after DOB, within filing deadline), **When** `TimelyFilingValidator.validate(claim)` is called, **Then** the output contains zero date-related findings.

2. **Given** a claim with a line whose `service_date_from` is in the future, **When** `TimelyFilingValidator.validate(claim)` is called, **Then** a `Finding` with code `FUTURE_SERVICE_DATE`, severity `ERROR`, `field_name` `"service_date_from"`, and `line_number` is produced.

3. **Given** a claim with a line whose `service_date_from` is before the patient's `patient_dob`, **When** `TimelyFilingValidator.validate(claim)` is called, **Then** a `Finding` with code `SERVICE_BEFORE_DOB`, severity `ERROR`, `field_name` `"service_date_from"`, and `line_number` is produced.

4. **Given** a claim filed beyond the payer's timely filing deadline (e.g., Medicare 365 days), **When** `TimelyFilingValidator.validate(claim)` is called, **Then** a `Finding` with code `TIMELY_FILING_EXCEEDED`, severity `ERROR`, `field_name` `"service_date_from"`, and a suggestion mentioning the payer's deadline is produced.

5. **Given** a claim with a `payer_id` that has a specific filing deadline in the bundled `timely_filing.json` data, **When** the validator checks the deadline, **Then** it uses the bundled payer-specific limit (e.g., AETNA=90 days, BCBS=180 days). **And** falls back to the `_default` (365 days) if the payer is not found.

6. **Given** a claim with a line where `service_date_from` is after `service_date_to`, **When** `TimelyFilingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_DATE_RANGE`, severity `ERROR`, `field_name` `"service_date_from"`, and `line_number` is produced.

7. **Given** a claim with empty `lines` list, **When** `TimelyFilingValidator.validate(claim)` is called, **Then** zero findings are produced (CompletenessValidator handles required-ness).

8. **Given** a claim with no `payer_id`, **When** `TimelyFilingValidator.validate(claim)` is called, **Then** no timely filing finding is produced (payer is needed for deadline lookup).

9. **Given** a claim with lines that have no `service_date_from` (None or empty), **When** `TimelyFilingValidator.validate(claim)` is called, **Then** those lines are silently skipped for date checks.

10. **Given** a claim where `filing_date` is not provided, **When** the validator checks timely filing, **Then** it uses today's date as the effective filing date.

11. **Given** any timely filing finding, **When** I inspect the `message`, **Then** it references field names but never actual date values or patient data (no PHI in messages).

## Tasks / Subtasks

- [x] Task 1: Implement `TimelyFilingValidator` in `src/claim_validator/validators/rule_based/timely_filing.py` (AC: #1-#11)
  - [x] Subclass `BaseValidator` with `name = "TimelyFilingValidator"`
  - [x] `_check_service_dates()`: For each line, validate future date, DOB comparison, date range
  - [x] `_check_timely_filing()`: Compare filing date against earliest service date using payer deadline
  - [x] Parse dates with `datetime.date.fromisoformat()`, skip line on parse failure
  - [x] Use `get_filing_deadline(payer_id)` from code_tables for deadline lookup
  - [x] Skip if lines is empty, skip if no payer_id for timely filing check
  - [x] No PHI in messages — never include actual date values
- [x] Task 2: Write tests in `tests/test_validators/test_rule_based/test_timely_filing.py` (AC: #1-#11)
  - [x] Test consistent dates → zero findings
  - [x] Test future service date → `FUTURE_SERVICE_DATE`
  - [x] Test service date before DOB → `SERVICE_BEFORE_DOB`
  - [x] Test timely filing exceeded → `TIMELY_FILING_EXCEEDED`
  - [x] Test payer-specific deadline from bundled data
  - [x] Test unknown payer falls back to _default (365 days)
  - [x] Test service_date_from after service_date_to → `INVALID_DATE_RANGE`
  - [x] Test empty lines → no findings
  - [x] Test no payer_id → no timely filing finding
  - [x] Test lines with no service_date_from → skipped silently
  - [x] Test filing_date not provided → uses today's date
  - [x] Test filing_date provided → uses that date
  - [x] Test multiple lines with different date errors → multiple findings
  - [x] Test severity is ERROR for all findings
  - [x] Test line_number present on line-level findings
  - [x] Test suggestion present on findings
  - [x] Test no PHI in finding messages
  - [x] Test validator statelessness
- [x] Task 3: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `TimelyFilingValidator` re-export
- [x] Task 4: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors
  - [x] `uv run pytest` — all tests pass (401 = 369 existing + 32 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.6)

- MonetaryValidator/DuplicateValidator established patterns: private `_check_*` helper methods, `self._make_output(findings)`
- Test pattern: helper `_valid_claim_dict()` returning baseline valid claim, class-based tests with `setup_method`
- Line iteration: `for idx, line in enumerate(claim.lines, start=1)` — line_number is 1-indexed
- Empty lines silently skipped — CompletenessValidator handles required-ness
- 369 tests passing, ruff/mypy clean (35 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `test_rule_based/` directory and `__init__.py` already exist
- Line-length limit is 100 characters — wrap long strings with implicit concatenation

### Relevant ClaimData Fields

| Field | Location | Type | Validator Scope |
|---|---|---|---|
| `patient_dob` | `ClaimData` | `str \| None = None` | SERVICE_BEFORE_DOB — parsed to date for comparison |
| `payer_id` | `ClaimData` | `str \| None = None` | Timely filing — passed to `get_filing_deadline()` |
| `filing_date` | `ClaimData` | `str \| None = None` | Timely filing — filing date; `today()` if not provided |
| `lines` | `ClaimData` | `list[ClaimLineData]` | Iterate for date checks |
| `lines[].service_date_from` | `ClaimLineData` | `str \| None = None` | All date checks use this field |
| `lines[].service_date_to` | `ClaimLineData` | `str \| None = None` | INVALID_DATE_RANGE — compared with service_date_from |

### Finding Codes

| Code | Meaning | Severity | Scope |
|---|---|---|---|
| `FUTURE_SERVICE_DATE` | Service date is in the future | `ERROR` | Line-level |
| `SERVICE_BEFORE_DOB` | Service date is before patient's date of birth | `ERROR` | Line-level |
| `TIMELY_FILING_EXCEEDED` | Claim filed beyond payer's timely filing deadline | `ERROR` | Claim-level |
| `INVALID_DATE_RANGE` | service_date_from is after service_date_to | `ERROR` | Line-level |

### Timely Filing Code Table API

```python
from claim_validator.code_tables.timely_filing import get_filing_deadline

# Returns deadline in days (int) or None
deadline = get_filing_deadline("MEDICARE")  # → 365
deadline = get_filing_deadline("AETNA")     # → 90
deadline = get_filing_deadline("UNKNOWN")   # → 365 (_default fallback)
# Input is auto-normalized: .upper().strip()
```

Bundled payer deadlines:
```
AETNA: 90, BCBS: 180, CHAMPVA: 365, CIGNA: 90, HUMANA: 365,
MEDICAID: 365, MEDICARE: 365, TRICARE: 365, UHC: 180, UNITED: 180,
_default: 365
```

### Date Handling Pattern (from DemographicsValidator)

```python
import datetime

# Always strip before parsing
dob = claim.patient_dob
if not dob or not dob.strip():
    return  # skip — CompletenessValidator owns presence checks

try:
    dob_date = datetime.date.fromisoformat(dob.strip())
except ValueError:
    return  # skip — unparseable dates silently skipped

if dob_date > datetime.date.today():
    # finding...
```

### Implementation Spec

```python
# src/claim_validator/validators/rule_based/timely_filing.py
"""TimelyFilingValidator -- date consistency and timely filing checks."""

from __future__ import annotations

import datetime

from claim_validator.code_tables.timely_filing import (
    get_filing_deadline,
)
from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class TimelyFilingValidator(BaseValidator):
    """Validates service date consistency and timely filing deadlines."""

    name = "TimelyFilingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_service_dates(claim, findings)
        self._check_timely_filing(claim, findings)

        return self._make_output(findings)

    def _check_service_dates(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        dob_date = self._parse_date(claim.patient_dob)
        today = datetime.date.today()

        for idx, line in enumerate(claim.lines, start=1):
            from_date = self._parse_date(
                line.service_date_from,
            )
            if from_date is None:
                continue

            if from_date > today:
                findings.append(
                    self._make_finding(
                        code="FUTURE_SERVICE_DATE",
                        message=(
                            "Date in 'service_date_from'"
                            " must not be in the future"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Verify the service date"
                            " (CMS-1500 Box 24.A)"
                        ),
                    )
                )

            if dob_date is not None and from_date < dob_date:
                findings.append(
                    self._make_finding(
                        code="SERVICE_BEFORE_DOB",
                        message=(
                            "Date in 'service_date_from'"
                            " is before 'patient_dob'"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Verify the service date"
                            " and patient date of"
                            " birth"
                        ),
                    )
                )

            to_date = self._parse_date(line.service_date_to)
            if to_date is not None and from_date > to_date:
                findings.append(
                    self._make_finding(
                        code="INVALID_DATE_RANGE",
                        message=(
                            "Date in 'service_date_from'"
                            " is after"
                            " 'service_date_to'"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Ensure service start date"
                            " is on or before end"
                            " date (CMS-1500"
                            " Box 24.A)"
                        ),
                    )
                )

    def _check_timely_filing(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return
        if not claim.payer_id or not claim.payer_id.strip():
            return

        deadline = get_filing_deadline(claim.payer_id)
        if deadline is None:
            return

        filing_date = self._parse_date(claim.filing_date)
        if filing_date is None:
            filing_date = datetime.date.today()

        earliest = self._earliest_service_date(claim)
        if earliest is None:
            return

        days_elapsed = (filing_date - earliest).days
        if days_elapsed > deadline:
            findings.append(
                self._make_finding(
                    code="TIMELY_FILING_EXCEEDED",
                    message=(
                        "Claim may exceed the"
                        " payer's timely filing"
                        " deadline"
                    ),
                    severity=Severity.ERROR,
                    field_name="service_date_from",
                    suggestion=(
                        "Check the payer's timely"
                        " filing limit and submit"
                        " promptly"
                    ),
                )
            )

    @staticmethod
    def _parse_date(
        value: str | None,
    ) -> datetime.date | None:
        if not value or not value.strip():
            return None
        try:
            return datetime.date.fromisoformat(
                value.strip(),
            )
        except ValueError:
            return None

    def _earliest_service_date(
        self, claim: ClaimData,
    ) -> datetime.date | None:
        earliest: datetime.date | None = None
        for line in claim.lines:
            d = self._parse_date(line.service_date_from)
            if d is not None:
                if earliest is None or d < earliest:
                    earliest = d
        return earliest
```

### Key Design Decisions

- **TimelyFilingValidator** checks two things: per-line date consistency (future, DOB, range) and claim-level timely filing
- Dates are `str | None` in the model — always parsed with `datetime.date.fromisoformat()` after `.strip()`
- Unparseable dates are silently skipped (return `None` from `_parse_date`), no format-validation findings
- `patient_dob` is parsed once and reused for all lines (efficiency)
- `today()` is called once per `_check_service_dates` invocation to avoid clock skew across lines
- Timely filing uses the **earliest** valid `service_date_from` across all lines
- If `filing_date` is not provided or unparseable, `today()` is used as fallback
- If `payer_id` is missing, timely filing check is skipped entirely
- `get_filing_deadline()` handles payer ID normalization and `_default` fallback internally
- All finding severities are `ERROR` — late claims are denied, not just warned
- `_parse_date` is a `@staticmethod` helper — stateless, reusable
- Messages reference field names, not actual values (no PHI)

### Anti-Patterns to Avoid

- **DO NOT** include actual date values in finding messages — no PHI
- **DO NOT** validate date format separately — silently skip unparseable dates
- **DO NOT** skip timely filing if filing_date is missing — use `today()` as fallback
- **DO NOT** store state between validate() calls
- **DO NOT** raise exceptions for validation failures — return findings
- **DO NOT** duplicate DOB format validation — DemographicsValidator handles `INVALID_DOB_FORMAT`
- **DO NOT** call `today()` multiple times in _check_service_dates — cache it once
- **DO NOT** use `strptime` — use `fromisoformat()` (simpler, faster, Python 3.11+)
- **DO NOT** hard-code payer deadlines — use `get_filing_deadline()` from code_tables

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR15** | Validate date consistency (service dates, DOB, filing date) |
| **FR17** | Check service dates against configurable payer-specific timely filing deadlines |
| **NFR1** | Rule-based latency < 50ms — no I/O, simple date arithmetic |
| **NFR8** | Zero network calls for rule-based |
| **NFR10** | No PHI in outputs — field names only in messages |
| **NFR15** | Stateless validation |
| **D10** | Dotted path: `claim_validator.validators.rule_based.timely_filing.TimelyFilingValidator` |

### conf.py Default Validators

TimelyFilingValidator is already listed in `DEFAULT_RULE_VALIDATORS` in `conf.py`:
```python
"claim_validator.validators.rule_based.timely_filing.TimelyFilingValidator",
```
No configuration changes needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.7] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR15] — Date consistency validation
- [Source: _bmad-output/planning-artifacts/prd.md#FR17] — Timely filing deadlines
- [Source: CMS-1500 Form] — Box 24.A (Dates of Service), Box 3 (Patient DOB)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation, no debugging required.

### Completion Notes List

- RED phase: test_timely_filing.py confirmed ImportError before implementation
- GREEN phase: TimelyFilingValidator implemented from story spec with 2 check methods
- All 11 acceptance criteria covered by 32 tests across 8 test classes
- `_check_service_dates()`: future date, DOB comparison, date range — per-line checks
- `_check_timely_filing()`: claim-level deadline check using `get_filing_deadline()` from code_tables
- `_parse_date()` static helper: parses `str | None` to `datetime.date | None`, skips unparseable
- `_earliest_service_date()`: finds earliest valid service date across all lines
- Uses `today()` as fallback when `filing_date` not provided or unparseable
- No PHI in any finding messages — verified by explicit tests
- TimelyFilingValidator already listed in conf.py DEFAULT_RULE_VALIDATORS
- Fixed unused `patch` import in test file (ruff F401)
- 401 tests pass (369 existing + 32 new), ruff clean, mypy clean (36 source files)

### File List

- `src/claim_validator/validators/rule_based/timely_filing.py` — NEW: TimelyFilingValidator
- `src/claim_validator/validators/rule_based/__init__.py` — MODIFIED: Added TimelyFilingValidator re-export
- `tests/test_validators/test_rule_based/test_timely_filing.py` — NEW: 32 tests

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 401 tests pass, status → review |
