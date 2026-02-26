# Story 2.2: Completeness Validator

Status: review

## Story

As a **developer**,
I want claims validated for required CMS-1500 field presence,
so that claims with missing mandatory fields are caught before submission.

## Acceptance Criteria

1. **Given** a claim with all required CMS-1500 fields populated, **When** `CompletenessValidator.validate(claim)` is called, **Then** the output contains zero findings.

2. **Given** a claim missing required fields (e.g., no `billing_provider_npi`, no `diagnosis_codes`, no `lines`), **When** `CompletenessValidator.validate(claim)` is called, **Then** the output contains one `Finding` per missing field with code `MISSING_FIELD`, severity `ERROR`, the specific `field_name`, and a suggestion to provide the field.

3. **Given** a claim with empty string values for required fields, **When** `CompletenessValidator.validate(claim)` is called, **Then** empty strings are treated as missing and flagged.

4. **Given** a claim with lines that have missing required line-level fields (e.g., no `diagnosis_pointers`, no `service_date_from`), **When** `CompletenessValidator.validate(claim)` is called, **Then** the finding includes the `line_number` identifying which line is incomplete.

5. **Given** any finding produced by this validator, **When** I inspect the `message` field, **Then** it contains no PHI values — only field names and guidance.

## Tasks / Subtasks

- [x] Task 1: Implement `CompletenessValidator` in `src/claim_validator/validators/rule_based/completeness.py` (AC: #1-#5)
  - [x] Subclass `BaseValidator` with `name = "CompletenessValidator"`
  - [x] Define required claim-level fields constant
  - [x] Define required line-level fields constant
  - [x] Check claim-level `str | None` fields for None or empty string
  - [x] Check `diagnosis_codes` list is non-empty
  - [x] Check `lines` list is non-empty
  - [x] Check line-level `diagnosis_pointers` is non-empty for each line
  - [x] Check line-level `service_date_from` is not None/empty for each line
  - [x] Return `ValidatorOutput` via `self._make_output(findings)`
- [x] Task 2: Write tests in `tests/test_validators/test_rule_based/test_completeness.py` (AC: all)
  - [x] Test all-fields-present claim returns zero findings
  - [x] Test each required claim-level field missing individually
  - [x] Test empty string treated as missing
  - [x] Test missing `diagnosis_codes` (empty list)
  - [x] Test missing `lines` (empty list)
  - [x] Test missing line-level `diagnosis_pointers` (empty list on a line)
  - [x] Test missing line-level `service_date_from`
  - [x] Test `line_number` is set correctly for line-level findings
  - [x] Test multiple missing fields produce multiple findings
  - [x] Test finding code is always `MISSING_FIELD`
  - [x] Test finding severity is always `ERROR`
  - [x] Test finding `field_name` matches the missing field
  - [x] Test finding messages contain no PHI
  - [x] Test finding suggestions are actionable
  - [x] Test validator is stateless (multiple calls, independent results)
- [x] Task 3: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `CompletenessValidator` re-export
- [x] Task 4: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors
  - [x] `uv run pytest` — all tests pass (154 existing + 39 new = 193 total)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/` — this is the first concrete rule-based validator.

### Previous Story Intelligence (Story 2.1)

- `BaseValidator` ABC implemented at `src/claim_validator/validators/base.py`
- `_make_output(findings)` returns `ValidatorOutput` — always use this
- `_make_finding(*, code, message, severity, field_name, line_number, suggestion, context)` — keyword-only args
- Registry test paths use `test_validators.test_registry.StubValidator` format (NOT `tests.test_validators...`)
- Ruff catches unused imports and unsorted imports — fix immediately
- 154 tests passing, ruff/mypy/pytest all green
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`

### ClaimData Model Fields (from `models/claim.py`)

All claim-level fields are optional with defaults. The completeness validator checks which ones are present.

**Claim-level fields (all `str | None = None` unless noted):**

| Field | Type | CMS-1500 Box | Required for Completeness? |
|---|---|---|---|
| `billing_provider_npi` | `str \| None` | Box 33a | **YES** |
| `billing_provider_taxonomy` | `str \| None` | Box 33a | No (optional) |
| `rendering_provider_npi` | `str \| None` | Box 24J | No (optional) |
| `subscriber_id` | `str \| None` | Box 1a | **YES** |
| `subscriber_first_name` | `str \| None` | Box 4 | No (validated by Demographics) |
| `subscriber_last_name` | `str \| None` | Box 4 | No (validated by Demographics) |
| `subscriber_dob` | `str \| None` | Box | No (validated by Demographics) |
| `subscriber_gender` | `str \| None` | Box | No (validated by Demographics) |
| `patient_first_name` | `str \| None` | Box 2 | **YES** |
| `patient_last_name` | `str \| None` | Box 2 | **YES** |
| `patient_dob` | `str \| None` | Box 3 | **YES** |
| `patient_gender` | `str \| None` | Box 3 | **YES** |
| `patient_relationship` | `str \| None` | Box 6 | No (validated by Demographics) |
| `payer_id` | `str \| None` | Box 11 | **YES** |
| `payer_name` | `str \| None` | Box 11c | No (optional) |
| `claim_type` | `str = "professional"` | — | No (has default) |
| `place_of_service` | `str \| None` | Box 24B | No (can be line-level) |
| `total_charge` | `float \| None` | Box 28 | No (validated by Monetary) |
| `filing_date` | `str \| None` | — | No (validated by TimelyFiling) |
| `diagnosis_codes` | `list[DiagnosisCode] = []` | Box 21 | **YES** (non-empty) |
| `lines` | `list[ClaimLineData] = []` | Box 24 | **YES** (non-empty) |

**Required claim-level fields for completeness:**
1. `billing_provider_npi`
2. `subscriber_id`
3. `patient_first_name`
4. `patient_last_name`
5. `patient_dob`
6. `patient_gender`
7. `payer_id`
8. `diagnosis_codes` (must be non-empty list)
9. `lines` (must be non-empty list)

**Line-level fields (ClaimLineData):**

| Field | Type | CMS-1500 Box | Required for Completeness? |
|---|---|---|---|
| `procedure_code` | `str` | Box 24D | Pydantic-required (always present) |
| `modifiers` | `list[str] = []` | Box 24D | No |
| `diagnosis_pointers` | `list[int] = []` | Box 24E | **YES** (non-empty) |
| `charge_amount` | `float` | Box 24F | Pydantic-required (always present) |
| `units` | `float = 1.0` | Box 24G | No (has default) |
| `service_date_from` | `str \| None` | Box 24A | **YES** |
| `service_date_to` | `str \| None` | Box 24A | No (same-day service OK) |
| `place_of_service` | `str \| None` | Box 24B | No (can use claim-level) |
| `rendering_provider_npi` | `str \| None` | Box 24J | No (optional) |

**Required line-level fields for completeness:**
1. `diagnosis_pointers` (must be non-empty list)
2. `service_date_from` (must not be None or empty)

Note: `procedure_code` and `charge_amount` are Pydantic-required — they can never be None/missing if a `ClaimLineData` exists, so the completeness validator does NOT need to check them.

### Implementation Spec

```python
# src/claim_validator/validators/rule_based/completeness.py
from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Required claim-level string fields (must not be None or empty string)
_REQUIRED_CLAIM_FIELDS: list[tuple[str, str]] = [
    ("billing_provider_npi", "Billing provider NPI is required (CMS-1500 Box 33a)"),
    ("subscriber_id", "Subscriber/insurance ID is required (CMS-1500 Box 1a)"),
    ("patient_first_name", "Patient first name is required (CMS-1500 Box 2)"),
    ("patient_last_name", "Patient last name is required (CMS-1500 Box 2)"),
    ("patient_dob", "Patient date of birth is required (CMS-1500 Box 3)"),
    ("patient_gender", "Patient gender is required (CMS-1500 Box 3)"),
    ("payer_id", "Payer ID is required (CMS-1500 Box 11)"),
]


class CompletenessValidator(BaseValidator):
    """Validates that all required CMS-1500 fields are present and non-empty."""

    name = "CompletenessValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        # Check required claim-level string fields
        for field_name, suggestion in _REQUIRED_CLAIM_FIELDS:
            value = getattr(claim, field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message=f"Required field '{field_name}' is missing or empty",
                        severity=Severity.ERROR,
                        field_name=field_name,
                        suggestion=suggestion,
                    )
                )

        # Check diagnosis_codes is non-empty
        if not claim.diagnosis_codes:
            findings.append(
                self._make_finding(
                    code="MISSING_FIELD",
                    message="At least one diagnosis code is required",
                    severity=Severity.ERROR,
                    field_name="diagnosis_codes",
                    suggestion="Add at least one ICD-10 diagnosis code (CMS-1500 Box 21)",
                )
            )

        # Check lines is non-empty
        if not claim.lines:
            findings.append(
                self._make_finding(
                    code="MISSING_FIELD",
                    message="At least one service line is required",
                    severity=Severity.ERROR,
                    field_name="lines",
                    suggestion="Add at least one service line (CMS-1500 Box 24)",
                )
            )

        # Check required line-level fields
        for idx, line in enumerate(claim.lines, start=1):
            if not line.diagnosis_pointers:
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message="Service line is missing diagnosis pointers",
                        severity=Severity.ERROR,
                        field_name="diagnosis_pointers",
                        line_number=idx,
                        suggestion="Link at least one diagnosis code to this line (CMS-1500 Box 24E)",
                    )
                )

            if not line.service_date_from or (
                isinstance(line.service_date_from, str) and not line.service_date_from.strip()
            ):
                findings.append(
                    self._make_finding(
                        code="MISSING_FIELD",
                        message="Service line is missing service date",
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion="Provide a service date for this line (CMS-1500 Box 24A)",
                    )
                )

        return self._make_output(findings)
```

**Key points:**
- All finding codes are `MISSING_FIELD` — this is the single error code for completeness issues
- All findings are `Severity.ERROR` — missing required fields always fail the claim
- `line_number` is 1-indexed (human-friendly) for line-level findings
- Messages reference field names only, never PHI values
- `getattr(claim, field_name)` reads from the frozen Pydantic model
- Empty strings and whitespace-only strings are treated as missing

### Test Strategy

```python
# tests/test_validators/test_rule_based/test_completeness.py

# Use a complete valid claim dict as base, then selectively remove fields

COMPLETE_CLAIM_DICT = {
    "billing_provider_npi": "1234567893",
    "subscriber_id": "XYZ123456",
    "patient_first_name": "Jane",
    "patient_last_name": "Doe",
    "patient_dob": "1990-01-15",
    "patient_gender": "F",
    "payer_id": "BCBS001",
    "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
    "lines": [
        {
            "procedure_code": "99213",
            "diagnosis_pointers": [1],
            "charge_amount": 150.00,
            "service_date_from": "2026-01-15",
        },
    ],
}
```

Tests cover all acceptance criteria with specific test cases for:
- Complete claim → zero findings
- Each required claim field missing → exactly one MISSING_FIELD finding
- Empty string values → treated as missing
- Whitespace-only strings → treated as missing
- Missing diagnosis_codes (empty list) → MISSING_FIELD
- Missing lines (empty list) → MISSING_FIELD
- Line missing diagnosis_pointers → MISSING_FIELD with line_number
- Line missing service_date_from → MISSING_FIELD with line_number
- Multiple missing fields → multiple findings
- All finding codes are `MISSING_FIELD`
- All severities are `ERROR`
- No PHI in messages
- Validator statelessness

### Test Directory Setup

Create `tests/test_validators/test_rule_based/` directory with `__init__.py`:
```
tests/
└── test_validators/
    ├── __init__.py          # Already exists (Story 2.1)
    ├── test_base.py         # Already exists (Story 2.1)
    ├── test_registry.py     # Already exists (Story 2.1)
    └── test_rule_based/     # NEW — create this
        ├── __init__.py      # NEW — empty marker
        └── test_completeness.py  # NEW — tests
```

### Anti-Patterns to Avoid

- **DO NOT** check `procedure_code` or `charge_amount` on lines — these are Pydantic-required and will never be None
- **DO NOT** validate field FORMAT (NPI format, DOB format) — that's other validators' job
- **DO NOT** include PHI values in finding messages — use field names only
- **DO NOT** raise exceptions for missing fields — return findings
- **DO NOT** check subscriber demographics (first/last name, DOB, gender) — that's the Demographics validator's scope
- **DO NOT** check `total_charge` or monetary values — that's the Monetary validator's scope
- **DO NOT** check `filing_date` — that's the TimelyFiling validator's scope
- **DO NOT** modify the claim object — it's frozen
- **DO NOT** add `rendering_provider_npi` to required fields — it's optional per CMS-1500

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR7** | Validate all required CMS-1500 fields are present and non-empty |
| **NFR1** | Rule-based latency < 50ms — validator must be lightweight (no I/O) |
| **NFR10** | No PHI in outputs — messages reference field names, not values |
| **NFR15** | Stateless validation — no state between `validate()` calls |
| **D10** | Dotted path: `claim_validator.validators.rule_based.completeness.CompletenessValidator` |

### Existing Imports Available

From `claim_validator`:
- `ClaimData` — `from claim_validator.models.claim import ClaimData`
- `Finding` — `from claim_validator.models.results import Finding`
- `ValidatorOutput` — `from claim_validator.models.results import ValidatorOutput`
- `Severity` — `from claim_validator.constants import Severity`
- `BaseValidator` — `from claim_validator.validators.base import BaseValidator`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns — Validator implementation contract]
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns — `validators/rule_based/completeness.py`]
- [Source: _bmad-output/planning-artifacts/prd.md#FR7] — Required CMS-1500 field validation
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns — `{Name}Validator` convention]
- [Source: CMS-1500 Form Reference] — Box numbers for required fields

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- No issues encountered — tests passed on first implementation attempt
- Whitespace-only string handling works correctly via `not value.strip()` check

### Completion Notes List

- All 5 acceptance criteria met
- AC1: Complete claim returns zero findings (test_complete_claim_has_zero_findings)
- AC2: Missing fields produce MISSING_FIELD findings with correct field_name and suggestion (7 parametrized tests x 3 = 21 tests)
- AC3: Empty strings and whitespace-only strings treated as missing (14 parametrized tests)
- AC4: Line-level findings include line_number (1-indexed) for diagnosis_pointers and service_date_from
- AC5: No PHI in messages — tested explicitly against known values
- 39 new tests added, 193 total tests passing
- ruff check, mypy all clean
- First concrete rule-based validator — establishes the pattern for Stories 2.3-2.7

### File List

| File | Action | Description |
|---|---|---|
| `src/claim_validator/validators/rule_based/completeness.py` | Created | CompletenessValidator implementation |
| `src/claim_validator/validators/rule_based/__init__.py` | Modified | Added CompletenessValidator re-export |
| `tests/test_validators/test_rule_based/test_completeness.py` | Created | 39 tests for completeness validation |

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 193 tests passing, tooling clean |
