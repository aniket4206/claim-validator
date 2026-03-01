# Story ELIG-1.4: Service Type, Date & Member ID Validators

Status: done

## Story

As a **developer**,
I want eligibility requests validated for service type codes, date validity, and member ID format,
So that requests with unknown service types, illogical dates, or malformed member IDs are caught offline.

## Acceptance Criteria

1. **Given** an `EligibilityRequest` with a valid X12 service type code (e.g., `"30"`)
   **When** `ServiceTypeValidator.validate(request)` is called
   **Then** zero service type findings are produced

2. **Given** an `EligibilityRequest` with an unknown service type code
   **When** `ServiceTypeValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_INVALID_SERVICE_TYPE`, severity `ERROR`, field_name `service_type_code` is produced

3. **Given** an `EligibilityRequest` with a valid date of service (present, not unreasonably far in the future)
   **When** `EligibilityDateValidator.validate(request)` is called
   **Then** zero date findings are produced

4. **Given** an `EligibilityRequest` with a date of service more than 1 year in the future
   **When** `EligibilityDateValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_FUTURE_DATE`, severity `WARNING`, field_name `date_of_service` is produced

5. **Given** an `EligibilityRequest` with a date of service more than 2 years in the past
   **When** `EligibilityDateValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_PAST_DATE`, severity `WARNING`, field_name `date_of_service` is produced

6. **Given** an `EligibilityRequest` with `date_of_service` set to `None`
   **When** `EligibilityDateValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_MISSING_DATE`, severity `ERROR`, field_name `date_of_service` is produced

7. **Given** an `EligibilityRequest` with a well-formatted subscriber ID (2+ alphanumeric chars)
   **When** `MemberIDValidator.validate(request)` is called
   **Then** zero member ID findings are produced

8. **Given** an `EligibilityRequest` with a subscriber ID that is 1 character or contains only non-alphanumeric characters
   **When** `MemberIDValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_INVALID_MEMBER_ID`, severity `ERROR`, field_name `subscriber_id` is produced

9. **Given** any finding produced by these validators
   **When** I inspect the `message` field
   **Then** it references field names only, never actual PHI values

## Tasks / Subtasks

- [x] Task 1: Create `ServiceTypeValidator` (AC: 1, 2, 9)
  - [x] 1.1: Create `eligibility/validators/rule_based/service_type.py` with `ServiceTypeValidator`
  - [x] 1.2: Uses `get_service_type()` from ELIG-1.2 code tables — follows `PayerIDValidator` pattern exactly
  - [x] 1.3: Finding code: `ELIG_INVALID_SERVICE_TYPE` with suggestion to verify X12 service type codes
- [x] Task 2: Create `EligibilityDateValidator` (AC: 3, 4, 5, 6, 9)
  - [x] 2.1: Create `eligibility/validators/rule_based/date.py` with `EligibilityDateValidator`
  - [x] 2.2: Check `date_of_service is None` → `ELIG_MISSING_DATE` (ERROR)
  - [x] 2.3: Check future date > 1 year → `ELIG_FUTURE_DATE` (WARNING)
  - [x] 2.4: Check past date > 2 years → `ELIG_PAST_DATE` (WARNING)
  - [x] 2.5: Use `datetime.date.today()` for comparisons — follows `TimelyFilingValidator` pattern
- [x] Task 3: Create `MemberIDValidator` (AC: 7, 8, 9)
  - [x] 3.1: Create `eligibility/validators/rule_based/member_id.py` with `MemberIDValidator`
  - [x] 3.2: Check subscriber_id has at least 2 alphanumeric chars — follows `SubscriberIDValidator` pattern
  - [x] 3.3: Finding code: `ELIG_INVALID_MEMBER_ID`
- [x] Task 4: Update re-exports in `__init__.py` files (AC: all)
  - [x] 4.1: Update `eligibility/validators/rule_based/__init__.py` — add all 3 new validators, keep sorted `__all__`
  - [x] 4.2: Update `eligibility/validators/__init__.py` — add all 3 new validators, keep sorted `__all__`
- [x] Task 5: Write comprehensive tests (AC: 1-9)
  - [x] 5.1: `tests/test_eligibility/test_validators/test_service_type.py` — valid/invalid service types, validator name, PHI check
  - [x] 5.2: `tests/test_eligibility/test_validators/test_date.py` — missing, valid, future, past, edge cases (today, boundary dates)
  - [x] 5.3: `tests/test_eligibility/test_validators/test_member_id.py` — valid, short, non-alphanumeric, empty, validator name, PHI check
  - [x] 5.4: Full regression — all existing tests must pass (1308+ current)

## Dev Notes

### Architectural Context

This is the **second validators story** for the Eligibility module. Story 1.3 created 3 validators (NPI, PayerID, Demographics). This story adds the remaining 3 rule-based validators. Story 1.5 wires all 6 into the pipeline.

**Dependency chain:** Story 1.1 (models) → Story 1.2 (code tables) → Story 1.3 (first validators) → **Story 1.4 (remaining validators)** → Story 1.5 (pipeline)

### ServiceTypeValidator Pattern

```python
"""Service type validator — validates service type code against bundled code table."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.code_tables.service_types import get_service_type
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator


class ServiceTypeValidator(BaseValidator):
    """Validates service type code exists in X12 service type code table."""

    name = "ServiceTypeValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        result = get_service_type(claim.service_type_code)
        if result is None:
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_SERVICE_TYPE",
                    message="Service type code not found in X12 service type table",
                    severity=Severity.ERROR,
                    field_name="service_type_code",
                    suggestion="Use a valid X12 271 service type code (e.g., '30' for health benefit plan coverage)",
                )
            )
        return self._make_output(findings)
```

**Key details:**
- Mirrors `PayerIDValidator` pattern exactly — code table lookup, single finding
- `get_service_type(code)` normalizes with `.upper().strip()` before lookup (returns `str | None`)
- `service_type_code` has default `"30"` in model — so it's always present, never None

### EligibilityDateValidator Pattern

```python
"""Date validator — validates date of service for eligibility requests."""

from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_MAX_FUTURE_DAYS = 365  # 1 year
_MAX_PAST_DAYS = 730    # 2 years


class EligibilityDateValidator(BaseValidator):
    """Validates date of service for eligibility requests."""

    name = "EligibilityDateValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []

        if claim.date_of_service is None:
            findings.append(
                self._make_finding(
                    code="ELIG_MISSING_DATE",
                    message="Date of service is required for eligibility verification",
                    severity=Severity.ERROR,
                    field_name="date_of_service",
                    suggestion="Provide the date of service for the eligibility check",
                )
            )
            return self._make_output(findings)

        today = datetime.date.today()
        delta = (claim.date_of_service - today).days

        if delta > _MAX_FUTURE_DAYS:
            findings.append(
                self._make_finding(
                    code="ELIG_FUTURE_DATE",
                    message="Date of service is more than 1 year in the future",
                    severity=Severity.WARNING,
                    field_name="date_of_service",
                    suggestion="Verify the date of service is correct",
                )
            )

        if delta < -_MAX_PAST_DAYS:
            findings.append(
                self._make_finding(
                    code="ELIG_PAST_DATE",
                    message="Date of service is more than 2 years in the past",
                    severity=Severity.WARNING,
                    field_name="date_of_service",
                    suggestion="Verify the date of service is correct",
                )
            )

        return self._make_output(findings)
```

**Key details:**
- `date_of_service` is `date | None` — Pydantic already coerces strings to `date`. No string parsing needed.
- Missing date → ERROR (early return). Future/past → WARNING (both can fire independently but won't in practice).
- Uses module-level constants `_MAX_FUTURE_DAYS` and `_MAX_PAST_DAYS` for testability and clarity.
- Follows `TimelyFilingValidator` pattern: `datetime.date.today()` for comparisons.
- `delta` is positive for future dates, negative for past dates.

### MemberIDValidator Pattern

```python
"""Member ID validator — validates subscriber ID format for eligibility requests."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_MIN_ALPHANUMERIC = 2
_ALPHANUMERIC_PATTERN = re.compile(r"[A-Za-z0-9]")


class MemberIDValidator(BaseValidator):
    """Validates subscriber/member ID format for eligibility requests."""

    name = "MemberIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        sub_id = claim.subscriber_id.strip()

        alphanumeric_count = len(_ALPHANUMERIC_PATTERN.findall(sub_id))
        if alphanumeric_count < _MIN_ALPHANUMERIC:
            findings.append(
                self._make_finding(
                    code="ELIG_INVALID_MEMBER_ID",
                    message="Subscriber ID must contain at least 2 alphanumeric characters",
                    severity=Severity.ERROR,
                    field_name="subscriber_id",
                    suggestion="Verify the member/subscriber ID from the insurance card",
                )
            )

        return self._make_output(findings)
```

**Key details:**
- Mirrors claim `SubscriberIDValidator` but with stricter check: 2+ alphanumeric (not just 1).
- `subscriber_id: str` is required by Pydantic — never None. Can be empty string `""`.
- `EligibilityDemographicsValidator` already checks for empty/whitespace subscriber_id with `ELIG_MISSING_FIELD`. This validator handles format quality.
- Empty string → `alphanumeric_count == 0 < 2` → finding produced. This is correct overlap with demographics (different code, different message).

### Implementation Constraints

1. **DO NOT create a pipeline** — this story is validators only. Pipeline comes in Story 1.5.
2. **DO NOT modify `eligibility/__init__.py`** — no new top-level exports (validators are internal).
3. **DO NOT modify `claim_validator/__init__.py`** — no new top-level exports.
4. **DO NOT include PHI** in any finding messages — field names and guidance only.
5. **DO NOT create validators for NPI, payer ID, or demographics** — those are Story 1.3 (done).
6. **Use `# type: ignore[override]`** on `validate()` methods that accept `EligibilityRequest` instead of `ClaimData`.
7. **Use `ELIG_` prefix** for ALL eligibility finding codes — never reuse claim codes.
8. **DO NOT modify `conftest.py`** unless truly needed — existing fixtures work for these validators.

### Existing Code to Reference (DO NOT DUPLICATE)

| Component | Location | How to Use |
|---|---|---|
| `BaseValidator` | `validators/base.py` | Subclass for all 3 validators |
| `Finding`, `ValidatorOutput` | `models/results.py` | Return types |
| `Severity` | `constants.py` | `Severity.ERROR`, `Severity.WARNING` |
| `get_service_type()` | `eligibility/code_tables/service_types.py` | Used by `ServiceTypeValidator` |
| `EligibilityRequest` | `eligibility/models/request.py` | Input type for all validators |
| `PayerIDValidator` | `eligibility/validators/rule_based/payer_id.py` | Pattern for code table lookup validator |
| `TimelyFilingValidator` | `validators/rule_based/timely_filing.py` | Pattern for date comparison logic |
| `SubscriberIDValidator` | `validators/rule_based/subscriber_id.py` | Pattern for ID format validation |
| `EligibilityDemographicsValidator` | `eligibility/validators/rule_based/demographics.py` | Already checks empty subscriber_id |

### EligibilityRequest Fields (for validator reference)

```python
class EligibilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    # Provider
    provider_npi: str                           # Story 1.3
    provider_taxonomy: str | None = None
    # Payer
    payer_id: str                               # Story 1.3
    # Subscriber (required)
    subscriber_id: str                          # THIS STORY — MemberIDValidator
    subscriber_first_name: str                  # Story 1.3
    subscriber_last_name: str                   # Story 1.3
    subscriber_dob: date                        # Story 1.3
    # Service
    service_type_code: str = "30"               # THIS STORY — ServiceTypeValidator
    date_of_service: date | None = None         # THIS STORY — EligibilityDateValidator
    # Dependent (optional)
    patient_first_name: str | None = None       # Story 1.3
    patient_last_name: str | None = None        # Story 1.3
    patient_dob: date | None = None             # Story 1.3
    relationship_code: str | None = None        # Story 1.3
```

**Critical type details:**
- `service_type_code: str = "30"` — always present, never None (has default)
- `date_of_service: date | None = None` — optional, can be None. When provided, Pydantic coerces strings.
- `subscriber_id: str` — required, never None. Can be empty string.

### Testing Strategy

**Test count target: ~40-55 tests** across the following:

**`test_service_type.py`** (~10 tests):
- Valid code `"30"` (health benefit plan) → zero findings
- Valid code `"1"` (medical care) → zero findings
- Unknown code `"ZZZZ"` → `ELIG_INVALID_SERVICE_TYPE`, ERROR
- Validator name is `"ServiceTypeValidator"`
- Finding field_name is `"service_type_code"`
- Finding has suggestion
- Case insensitive (lowercase code matches)
- Whitespace code stripped
- No PHI in message (code value not in message)
- Default code `"30"` works (via `valid_request` fixture)

**`test_date.py`** (~15 tests):
- Today's date → zero findings
- Yesterday → zero findings
- 1 year in future exactly → zero findings (boundary)
- >1 year in future → `ELIG_FUTURE_DATE`, WARNING
- 2 years ago exactly → zero findings (boundary)
- >2 years ago → `ELIG_PAST_DATE`, WARNING
- `None` date → `ELIG_MISSING_DATE`, ERROR
- Validator name is `"EligibilityDateValidator"`
- Finding field_name is `"date_of_service"` for all 3 codes
- Finding has suggestion
- No PHI in messages
- Date in valid range → zero findings
- Boundary: 366 days in future → WARNING
- Boundary: 731 days in past → WARNING

**`test_member_id.py`** (~12 tests):
- Normal ID `"XYZ123456"` → zero findings
- Short but valid `"AB"` → zero findings (2 alphanumeric)
- Single char `"A"` → `ELIG_INVALID_MEMBER_ID`, ERROR
- Empty string `""` → `ELIG_INVALID_MEMBER_ID`, ERROR
- Non-alphanumeric only `"---"` → `ELIG_INVALID_MEMBER_ID`, ERROR
- Mixed `"A-1"` → zero findings (2 alphanumeric chars)
- Whitespace only `"   "` → `ELIG_INVALID_MEMBER_ID`, ERROR
- Validator name is `"MemberIDValidator"`
- Finding field_name is `"subscriber_id"`
- Finding has suggestion
- No PHI in message (actual ID not in message)
- Long ID is fine `"ABCDEFGHIJ123456789"` → zero findings

### Previous Story Learnings (ELIG-1.1 through ELIG-1.3)

**From ELIG-1.1:**
1. Use `monkeypatch.setenv()` not `monkeypatch.setattr(os, "environ")`
2. Sort `__all__` alphabetically in all `__init__.py` files
3. `from __future__ import annotations` at top of EVERY file

**From ELIG-1.2 code review:**
1. Cache-clearing fixture in `conftest.py` — use `autouse=True` for code table cache reset
2. Test common data: don't just test one example, cover multiple realistic cases
3. `valid_eligibility_dict()` fixture already exists in `tests/test_eligibility/conftest.py`

**From ELIG-1.3 implementation:**
1. Each validator is a single file with a single class — keep it simple
2. `# type: ignore[override]` on `validate()` — required for all eligibility validators
3. Test fixtures: `valid_request` (EligibilityRequest) and `valid_request_dict` (dict) in `test_validators/conftest.py`
4. Use `self._make_finding()` and `self._make_output()` from `BaseValidator`
5. No PHI in messages — test explicitly with `assert "actual_value" not in finding.message`

**From ELIG-1.3 code review:**
1. Cache `getattr()` results — don't call it multiple times in comprehensions
2. Include context dicts in findings when useful (e.g., `{"missing_fields": [...]}`)
3. Comment defense-in-depth checks that can't fire due to Pydantic validation

### Project Structure Notes

**New files to create:**

```
src/claim_validator/eligibility/validators/rule_based/
├── service_type.py        # NEW — ServiceTypeValidator
├── date.py                # NEW — EligibilityDateValidator
└── member_id.py           # NEW — MemberIDValidator
```

**Files to modify:**

| File | Change |
|---|---|
| `eligibility/validators/rule_based/__init__.py` | Add 3 new validators, keep sorted `__all__` |
| `eligibility/validators/__init__.py` | Add 3 new validators, keep sorted `__all__` |

**Test files to create:**

```
tests/test_eligibility/test_validators/
├── test_service_type.py   # NEW — ServiceTypeValidator tests
├── test_date.py           # NEW — EligibilityDateValidator tests
└── test_member_id.py      # NEW — MemberIDValidator tests
```

**Files NOT to touch:**
- `eligibility/__init__.py` — no new public exports
- `claim_validator/__init__.py` — no new top-level exports
- `eligibility/models/` — no model changes
- `eligibility/code_tables/` — already done in ELIG-1.2
- `tests/test_eligibility/test_validators/conftest.py` — existing fixtures work
- Any validator files from Story 1.3

### References

- [Source: architecture.md — D16: Separate EligibilityPipeline, three-phase]
- [Source: architecture.md — Adding a New Eligibility Validator (6-step pattern)]
- [Source: architecture.md — NFR1: <100ms rule-based eligibility validation]
- [Source: epics.md — Elig Epic 1, Story 1.4: All 9 ACs]
- [Source: project-context.md — Finding Code Prefixes: ELIG_ for eligibility rule-based]
- [Source: project-context.md — Naming: {Name}Validator pattern]
- [Source: project-context.md — HIPAA: NEVER include PHI in finding messages]
- [Source: project-context.md — Testing: tests/test_{module}/test_{name}.py]
- [Source: validators/base.py — BaseValidator._make_output(), _make_finding()]
- [Source: models/results.py — Finding, ValidatorOutput (frozen Pydantic)]
- [Source: eligibility/models/request.py — EligibilityRequest field definitions]
- [Source: eligibility/code_tables/service_types.py — get_service_type() API]
- [Source: validators/rule_based/timely_filing.py — Date comparison patterns]
- [Source: validators/rule_based/subscriber_id.py — Member ID format validation pattern]
- [Source: elig-1-3 story — First validators, code review learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Ruff E501 line too long in service_type.py suggestion string — split into multi-line

### Completion Notes List

- All 3 validators implemented following existing patterns (PayerIDValidator, TimelyFilingValidator, SubscriberIDValidator)
- ServiceTypeValidator: code table lookup via get_service_type(), mirrors PayerIDValidator exactly
- EligibilityDateValidator: None→ERROR (early return), >365d future→WARNING, >730d past→WARNING
- MemberIDValidator: 2+ alphanumeric chars required, mirrors SubscriberIDValidator with stricter threshold
- 41 new tests: 10 service type, 18 date, 13 member ID
- Full regression: 1349 passed (1308 existing + 41 new)
- Ruff clean, no lint issues
- No conftest.py modifications needed — existing fixtures worked for all validators
- No PHI in any finding messages — verified by explicit tests

### File List

**New files:**
- `src/claim_validator/eligibility/validators/rule_based/service_type.py`
- `src/claim_validator/eligibility/validators/rule_based/date.py`
- `src/claim_validator/eligibility/validators/rule_based/member_id.py`
- `tests/test_eligibility/test_validators/test_service_type.py`
- `tests/test_eligibility/test_validators/test_date.py`
- `tests/test_eligibility/test_validators/test_member_id.py`

**Modified files:**
- `src/claim_validator/eligibility/validators/rule_based/__init__.py`
- `src/claim_validator/eligibility/validators/__init__.py`
