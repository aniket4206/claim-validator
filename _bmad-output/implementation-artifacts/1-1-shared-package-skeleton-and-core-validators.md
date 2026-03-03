# Story 1.1: Shared Package Skeleton and Core Validators

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want NPI, date, member ID, and demographics validation as pure functions in `shared/validators/`,
so that these rules exist in exactly one canonical location.

## Acceptance Criteria

1. **AC-1: shared/ package skeleton exists**
   - `src/claim_validator/shared/__init__.py` and `src/claim_validator/shared/validators/__init__.py` exist
   - `shared/validators/__init__.py` re-exports all 4 pure functions with `__all__`

2. **AC-2: validate_npi — valid NPI**
   - **Given** the shared/ package skeleton exists with `__init__.py` files
   - **When** `validate_npi(npi, field_name, code_prefix)` is called with a valid Luhn NPI (e.g., `"1234567893"`)
   - **Then** an empty findings list is returned
   - **And** calling with an invalid NPI returns a Finding with the correct code and field_name

3. **AC-3: validate_date — valid/invalid dates**
   - **Given** `validate_date(value, field_name, code_prefix)` is called
   - **When** the date is a valid ISO date string
   - **Then** an empty findings list is returned
   - **And** invalid/future dates return appropriate findings

4. **AC-4: validate_member_id — missing member ID**
   - **Given** `validate_member_id(member_id, field_name, code_prefix)` is called
   - **When** the member ID is None or empty
   - **Then** a Finding with severity ERROR is returned

5. **AC-5: validate_demographics — missing fields**
   - **Given** `validate_demographics(name, gender, dob, field_prefix, code_prefix)` is called
   - **When** required demographic fields are missing
   - **Then** individual findings per missing field are returned

6. **AC-6: Cross-cutting quality**
   - All functions are stateless (no side effects), have docstrings, pass mypy strict, and return `list[Finding]`
   - FR1, FR2, FR3, FR4, FR8 are satisfied

## Tasks / Subtasks

- [x] Task 1: Create shared/ package skeleton (AC: #1)
  - [x] 1.1: Create `src/claim_validator/shared/__init__.py` (minimal docstring)
  - [x] 1.2: Create `src/claim_validator/shared/validators/__init__.py` (re-exports all 4 functions)
- [x] Task 2: Implement validate_npi() (AC: #2, #6)
  - [x] 2.1: Create `src/claim_validator/shared/validators/npi.py`
  - [x] 2.2: Port `_check_luhn_npi()` private helper from `validators/rule_based/_npi_utils.py`
  - [x] 2.3: Implement `validate_npi(npi, field_name, code_prefix) -> list[Finding]`
  - [x] 2.4: Finding codes: `MISSING_NPI`, `INVALID_NPI_FORMAT`, `INVALID_NPI` (prefixed with code_prefix)
  - [x] 2.5: Write tests in `tests/test_shared/test_validators/test_npi.py`
- [x] Task 3: Implement validate_date() (AC: #3, #6)
  - [x] 3.1: Create `src/claim_validator/shared/validators/date.py`
  - [x] 3.2: Implement `validate_date(value, field_name, code_prefix) -> list[Finding]`
  - [x] 3.3: Handle: missing, invalid format, future dates, past dates
  - [x] 3.4: Write tests in `tests/test_shared/test_validators/test_date.py`
- [x] Task 4: Implement validate_member_id() (AC: #4, #6)
  - [x] 4.1: Create `src/claim_validator/shared/validators/member_id.py`
  - [x] 4.2: Implement `validate_member_id(member_id, field_name, code_prefix) -> list[Finding]`
  - [x] 4.3: Handle: None/empty → ERROR, insufficient alphanumeric characters
  - [x] 4.4: Write tests in `tests/test_shared/test_validators/test_member_id.py`
- [x] Task 5: Implement validate_demographics() (AC: #5, #6)
  - [x] 5.1: Create `src/claim_validator/shared/validators/demographics.py`
  - [x] 5.2: Implement `validate_demographics(name, gender, dob, field_prefix, code_prefix) -> list[Finding]`
  - [x] 5.3: Handle: missing name, invalid gender (not M/F/U), invalid DOB format, future DOB
  - [x] 5.4: Write tests in `tests/test_shared/test_validators/test_demographics.py`
- [x] Task 6: Create test infrastructure (AC: #6)
  - [x] 6.1: Create `tests/test_shared/__init__.py`
  - [x] 6.2: Create `tests/test_shared/test_validators/__init__.py`
  - [x] 6.3: Every test file includes PHI-leak assertions (no PHI values in Finding messages)
- [x] Task 7: Quality verification (AC: #6)
  - [x] 7.1: Run `mypy --strict` — zero errors on all new files
  - [x] 7.2: Run `ruff check` — zero warnings (line-length=100, rules E/F/I/N/W/UP)
  - [x] 7.3: Run `pytest tests/test_shared/` — all pass (85 tests)
  - [x] 7.4: Verify all existing tests still pass (`pytest`) — 1647 passed, 0 regressions

## Dev Notes

### Architecture Decision D34: Pure Function Pattern (MANDATORY)

All shared validators MUST follow this exact signature pattern from the architecture doc:

```python
def validate_npi(
    npi: str | None,
    field_name: str = "npi",
    code_prefix: str = "",
) -> list[Finding]:
    """Canonical NPI validation. Returns findings with configurable prefix."""
    findings: list[Finding] = []
    if not npi or not npi.strip():
        findings.append(Finding(
            code=f"{code_prefix}MISSING_NPI",
            message=f"NPI is required in '{field_name}'",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide a valid 10-digit NPI",
        ))
        return findings
    # ... format check, then Luhn check
    return findings
```

**Why `code_prefix` matters:** Domain wrappers pass prefixes to get domain-scoped codes:
- Claims: `code_prefix=""` → `INVALID_NPI`
- Eligibility: `code_prefix="ELIG_"` → `ELIG_INVALID_NPI`
- Prior Auth: `code_prefix="PA_"` → `PA_INVALID_NPI`

### Architecture Decision D43: Clean Break

- Story 1.1 ONLY creates new files — does NOT modify existing validators (that's Epic 3)
- `shared/validators/npi.py` is the canonical path
- No re-exports, no `__getattr__` hacks for old paths
- `claim_validator/__init__.py` is NOT modified in this story

### Finding Model (Return Type)

**Source:** `src/claim_validator/models/results.py`

```python
class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    code: str              # UPPER_SNAKE_CASE, e.g. "INVALID_NPI"
    message: str           # Human-readable, NO PHI values ever
    severity: Severity     # Severity.ERROR or Severity.WARNING
    field_name: str        # Field name, never the field value
    line_number: int | None = None
    suggestion: str = ""
    context: dict[str, Any] | None = None
```

**Severity enum** from `src/claim_validator/constants.py`:
```python
class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
```

### PHI Safety Rules (HIPAA — CRITICAL)

```python
# CORRECT — field name in message, no PHI
message=f"NPI in '{field_name}' fails Luhn check-digit validation"

# WRONG — field VALUE in message (PHI leak!)
message=f"NPI '{npi}' fails Luhn check-digit validation"
```

Context dict may contain computed non-PHI values (lengths, counts), NEVER raw patient data:
```python
context={"npi_length": len(npi)}        # OK — computed metadata
context={"npi_value": npi}              # NEVER — PHI leak
context={"alphanumeric_count": count}   # OK
```

### Existing Logic to Extract

**NPI — canonical source to port:**
- `validators/rule_based/_npi_utils.py` → `_check_luhn_npi()` with `"80840"` prefix algorithm
- Three existing validators duplicate this logic: `validators/rule_based/npi.py` (NPIValidator), `eligibility/validators/rule_based/npi.py` (EligibilityNPIValidator), `prior_auth/validators/rule_based/npi.py` (PANPIValidator)
- Known valid test NPIs: `"1234567893"`, `"1245319599"`, `"1306849450"`
- Known invalid test NPIs: `"1234567890"`, `"1234567891"`, `"9999999999"`

**Date — consolidate from:**
- `eligibility/validators/rule_based/date.py` → service date: future (+365d WARNING), past (-730d WARNING)
- `prior_auth/validators/rule_based/date_of_birth.py` → DOB: future DOB (ERROR)
- `validators/rule_based/demographics.py` → inline `_check_dob`: format + future check

**Member ID — consolidate from:**
- `eligibility/validators/rule_based/member_id.py` → min 2 alphanumeric chars
- `prior_auth/validators/rule_based/member_id.py` → presence-only (not empty)
- `validators/rule_based/subscriber_id.py` → min 1 alphanumeric char

**Demographics — consolidate from:**
- `validators/rule_based/demographics.py` → DOB format/future, gender M/F/U, self-relationship name match
- `eligibility/validators/rule_based/demographics.py` → required subscriber fields, dependent fields

### Finding Codes Reference

| Validator | Code (unprefixed) | Severity | When |
|---|---|---|---|
| NPI | `MISSING_NPI` | ERROR | None or empty |
| NPI | `INVALID_NPI_FORMAT` | ERROR | Not 10 digits |
| NPI | `INVALID_NPI` | ERROR | Fails Luhn check |
| Date | `MISSING_DATE` | ERROR | None or empty |
| Date | `INVALID_DATE_FORMAT` | ERROR | Unparseable ISO date |
| Date | `FUTURE_DATE` | WARNING | Date too far in future |
| Date | `PAST_DATE` | WARNING | Date too far in past |
| Member ID | `MISSING_MEMBER_ID` | ERROR | None or empty |
| Member ID | `INVALID_MEMBER_ID` | ERROR | Insufficient alphanumeric chars |
| Demographics | `MISSING_PATIENT_NAME` | ERROR | Name missing |
| Demographics | `INVALID_GENDER` | ERROR | Not M/F/U |
| Demographics | `INVALID_DOB_FORMAT` | ERROR | DOB unparseable |
| Demographics | `FUTURE_DOB` | ERROR | DOB in future |

### Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Pure function | `validate_{concept}()` | `validate_npi()`, `validate_date()` |
| Module file | `shared/validators/{concept}.py` | `shared/validators/npi.py` (NOT `npi_validator.py`) |
| Private helper | `_{verb}_{noun}()` | `_check_luhn_npi()` |
| Finding code | `UPPER_SNAKE_CASE` | `INVALID_NPI`, `MISSING_DATE` |

**Anti-patterns to avoid:**
- `check_npi()` — wrong verb (must be `validate_`)
- `npi_validation()` — wrong format
- `shared/validators/npi_validator.py` — no `_validator` suffix on files
- Hardcoding `"ELIG_INVALID_NPI"` in the shared function — the prefix is parameterized

### Import Pattern

All new files must use `from __future__ import annotations` (existing codebase convention):

```python
"""Canonical NPI validation — shared pure function for all domains."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding
```

**NEVER import domain models** (`ClaimData`, `EligibilityRequest`, `PriorAuthRequest`) in `shared/validators/`.

### Project Structure Notes

**Files to create:**
```
src/claim_validator/shared/                   # NEW directory
├── __init__.py                               # Minimal docstring
└── validators/                               # NEW directory
    ├── __init__.py                            # Re-exports all 4 functions + __all__
    ├── npi.py                                 # validate_npi()
    ├── date.py                                # validate_date()
    ├── member_id.py                           # validate_member_id()
    └── demographics.py                        # validate_demographics()

tests/test_shared/                            # NEW directory
├── __init__.py
└── test_validators/                          # NEW directory
    ├── __init__.py
    ├── test_npi.py
    ├── test_date.py
    ├── test_member_id.py
    └── test_demographics.py
```

**What Story 1.1 must NOT create/modify:**
- Do NOT modify `claim_validator/__init__.py` — no new exports yet
- Do NOT modify existing validators — thin wrapper refactoring is Epic 3
- Do NOT create `shared/code_tables/` or `shared/data/` — Story 1.2
- Do NOT create `shared/deidentifier/` or `shared/pipeline/` — Stories 2.x
- Do NOT add `shared/validators/diagnosis.py`, `procedure.py`, `payer_id.py` — Story 1.3

### Quality Requirements

- **mypy strict** — `python_version = "3.11"`, strict = true, pydantic plugin enabled
- **ruff** — line-length=100, rules E/F/I/N/W/UP
- **pytest** — all new + all existing tests must pass
- **Docstrings** — module-level AND function-level on all public functions (NFR27)
- **Stateless** — no module-level mutable state, no I/O, re-entrant safe (NFR12)
- **No PHI** — findings reference field names only, never values (NFR8)

### Testing Requirements

Each test file must include:
1. Valid input → empty findings list
2. Invalid input → correct `finding.code`, `finding.field_name`, `finding.severity`
3. `code_prefix` parameter → `finding.code` is correctly prefixed
4. PHI-leak assertion — no input values appear in `finding.message` or `finding.suggestion`
5. Statelessness — multiple calls are independent

**Known valid test NPIs:** `"1234567893"`, `"1245319599"`, `"1306849450"`
**Known invalid test NPIs:** `"1234567890"`, `"1234567891"`, `"9999999999"`

### References

- [Source: architecture.md — D34: Shared validator pure function design, lines 2756-2794, 2961-3014]
- [Source: architecture.md — D43: Clean break, import path migration, line 2921]
- [Source: architecture.md — shared/ directory layout, lines 3262-3270]
- [Source: architecture.md — test pattern for shared validators, lines 3206-3234]
- [Source: prd.md — FR1-FR4, FR8: Shared validator requirements, lines 278-284]
- [Source: prd.md — NFR1, NFR5, NFR8, NFR12, NFR21, NFR24-27: Quality constraints]
- [Source: epics.md — Story 1.1 acceptance criteria, lines 220-247]
- [Source: validators/rule_based/_npi_utils.py — Luhn algorithm implementation]
- [Source: models/results.py — Finding model definition]
- [Source: constants.py — Severity enum]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- pytest shebang pointed to stale venv; resolved by using `.venv/bin/python -m pytest` instead of `.venv/bin/pytest`

### Completion Notes List

- Created `shared/` package skeleton with `__init__.py` files (AC-1)
- Implemented `validate_npi()` with Luhn algorithm ported from `_npi_utils.py`, format check, and missing check. Finding codes: MISSING_NPI, INVALID_NPI_FORMAT, INVALID_NPI (AC-2)
- Implemented `validate_date()` supporting both `str` and `datetime.date` input, with configurable future/past day thresholds. Finding codes: MISSING_DATE, INVALID_DATE_FORMAT, FUTURE_DATE, PAST_DATE (AC-3)
- Implemented `validate_member_id()` with configurable `min_alphanumeric` threshold (default 2, matching eligibility domain). Finding codes: MISSING_MEMBER_ID, INVALID_MEMBER_ID (AC-4)
- Implemented `validate_demographics()` with separate `_check_name`, `_check_gender`, `_check_dob` helpers. Gender/DOB None is not an error (domain decides if required). Finding codes: MISSING_PATIENT_NAME, INVALID_GENDER, INVALID_DOB_FORMAT, FUTURE_DOB (AC-5)
- All functions are pure, stateless, typed, with docstrings. Pass mypy strict and ruff clean (AC-6)
- 85 new tests covering valid/invalid inputs, code_prefix, field_name passthrough, PHI-leak assertions, statelessness
- 1647 existing tests pass — zero regressions
- No existing files modified — D43 clean break compliance

### File List

New files created:
- `src/claim_validator/shared/__init__.py`
- `src/claim_validator/shared/validators/__init__.py`
- `src/claim_validator/shared/validators/npi.py`
- `src/claim_validator/shared/validators/date.py`
- `src/claim_validator/shared/validators/member_id.py`
- `src/claim_validator/shared/validators/demographics.py`
- `tests/test_shared/__init__.py`
- `tests/test_shared/test_validators/__init__.py`
- `tests/test_shared/test_validators/test_npi.py`
- `tests/test_shared/test_validators/test_date.py`
- `tests/test_shared/test_validators/test_member_id.py`
- `tests/test_shared/test_validators/test_demographics.py`
