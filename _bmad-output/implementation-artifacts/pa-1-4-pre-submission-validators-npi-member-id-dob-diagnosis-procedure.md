# Story PA-1.4: Pre-Submission Validators (NPI, Member ID, DOB, Diagnosis, Procedure)

Status: done

## Story

As a **developer**,
I want PA requests validated for NPI correctness, member ID presence, DOB validity, and diagnosis/procedure code accuracy,
so that requests with invalid data are caught offline before clearinghouse submission.

## Acceptance Criteria

1. **Given** a `PriorAuthRequest` with a valid NPI (passes Luhn check, e.g., `"1234567893"`)
   **When** `PANPIValidator.validate(request)` is called
   **Then** zero NPI-related findings are produced

2. **Given** a `PriorAuthRequest` with an invalid NPI (fails Luhn check or wrong length)
   **When** `PANPIValidator.validate(request)` is called
   **Then** a `Finding` with code `PA_INVALID_NPI`, severity `ERROR`, field_name `requester_npi` is produced
   **And** a separate `PA_INVALID_NPI_FORMAT` finding is produced when the NPI is not exactly 10 digits

3. **Given** a `PriorAuthRequest` with a non-empty subscriber member ID
   **When** `PAMemberIDValidator.validate(request)` is called
   **Then** zero member ID findings are produced

4. **Given** a `PriorAuthRequest` with an empty or whitespace-only subscriber member ID
   **When** `PAMemberIDValidator.validate(request)` is called
   **Then** a `Finding` with code `PA_MISSING_MEMBER_ID`, severity `ERROR`, field_name `subscriber.member_id` is produced

5. **Given** a `PriorAuthRequest` with a valid subscriber DOB (not in the future)
   **When** `PADateOfBirthValidator.validate(request)` is called
   **Then** zero DOB findings are produced

6. **Given** a `PriorAuthRequest` with a subscriber DOB in the future
   **When** `PADateOfBirthValidator.validate(request)` is called
   **Then** a `Finding` with code `PA_INVALID_DOB`, severity `ERROR` is produced
   **And** if `patient` is present with a future DOB, a separate finding is produced for `patient.dob`

7. **Given** a `PriorAuthRequest` with valid ICD-10 diagnosis codes (present in bundled code tables)
   **When** `PADiagnosisValidator.validate(request)` is called
   **Then** zero diagnosis findings are produced

8. **Given** a `PriorAuthRequest` with an unknown ICD-10 code
   **When** `PADiagnosisValidator.validate(request)` is called
   **Then** a `Finding` with code `PA_INVALID_DIAGNOSIS`, severity `ERROR`, and the position number in the message is produced
   **And** a `PA_INVALID_DIAGNOSIS_FORMAT` finding is produced when the code format is invalid

9. **Given** a `PriorAuthRequest` with valid CPT/HCPCS procedure codes in service lines
   **When** `PAProcedureValidator.validate(request)` is called
   **Then** zero procedure findings are produced

10. **Given** a `PriorAuthRequest` with an unknown CPT/HCPCS code
    **When** `PAProcedureValidator.validate(request)` is called
    **Then** a `Finding` with code `PA_INVALID_PROCEDURE`, severity `ERROR` is produced
    **And** a `PA_INVALID_PROCEDURE_FORMAT` finding is produced when the code format is invalid

11. **Given** any finding produced by these validators
    **When** I inspect the `message` field
    **Then** it references field names only, never actual PHI values (NFR12)

12. **Given** the 5 validators added to `DEFAULT_PA_RULE_VALIDATORS`
    **When** a developer uses default `ClaimValidatorSettings`
    **Then** all 5 PA validators are included in the default pipeline configuration

## Tasks / Subtasks

- [x] Task 1: Create `prior_auth/validators/rule_based/` directory structure (AC: #1-#12)
  - [x] Create `prior_auth/validators/rule_based/__init__.py` with re-exports of all 5 validators
  - [x] Update `prior_auth/validators/__init__.py` to re-export from `rule_based`
- [x] Task 2: Create `PANPIValidator` in `prior_auth/validators/rule_based/npi.py` (AC: #1, #2, #11)
  - [x] Subclass `BaseValidator` with `name = "PANPIValidator"`
  - [x] Import `_check_luhn_npi` from `claim_validator.validators.rule_based.npi` (reuse, don't duplicate)
  - [x] Check `requester_npi` format: exactly 10 numeric digits → `PA_INVALID_NPI_FORMAT` if not
  - [x] Check Luhn algorithm → `PA_INVALID_NPI` if fails
  - [x] Skip validation if `requester_npi` is empty/whitespace (CompletenessValidator handles presence)
  - [x] Finding messages reference field names only — no PHI
- [x] Task 3: Create `PAMemberIDValidator` in `prior_auth/validators/rule_based/member_id.py` (AC: #3, #4, #11)
  - [x] Subclass `BaseValidator` with `name = "PAMemberIDValidator"`
  - [x] Access `request.subscriber.member_id`
  - [x] Check non-empty after strip → `PA_MISSING_MEMBER_ID` if empty/whitespace
  - [x] Return zero findings for valid member IDs
- [x] Task 4: Create `PADateOfBirthValidator` in `prior_auth/validators/rule_based/date_of_birth.py` (AC: #5, #6, #11)
  - [x] Subclass `BaseValidator` with `name = "PADateOfBirthValidator"`
  - [x] Check `request.subscriber.dob` is not in the future → `PA_INVALID_DOB` with field `subscriber.dob`
  - [x] If `request.patient` exists, check `request.patient.dob` not in the future → `PA_INVALID_DOB` with field `patient.dob`
- [x] Task 5: Create `PADiagnosisValidator` in `prior_auth/validators/rule_based/diagnosis.py` (AC: #7, #8, #11)
  - [x] Subclass `BaseValidator` with `name = "PADiagnosisValidator"`
  - [x] Import `lookup_icd10` from `claim_validator.code_tables` (reuse existing code tables)
  - [x] Iterate `request.diagnosis_codes` (list[str])
  - [x] Check ICD-10 format via regex `^[A-Za-z]\d{2}(\.\d{1,4})?$` → `PA_INVALID_DIAGNOSIS_FORMAT` if invalid
  - [x] Check code exists in bundled table via `lookup_icd10(code)` → `PA_INVALID_DIAGNOSIS` if not found
  - [x] Include position number in message (e.g., "Diagnosis code at position 1")
- [x] Task 6: Create `PAProcedureValidator` in `prior_auth/validators/rule_based/procedure.py` (AC: #9, #10, #11)
  - [x] Subclass `BaseValidator` with `name = "PAProcedureValidator"`
  - [x] Import `lookup_hcpcs` from `claim_validator.code_tables` (reuse existing code tables)
  - [x] Iterate `request.service_lines` (list[ServiceLine]), access `line.cpt_code`
  - [x] Check procedure code format via regex `^[A-Za-z0-9]{5}$` → `PA_INVALID_PROCEDURE_FORMAT` if invalid
  - [x] Check code exists in bundled table via `lookup_hcpcs(code)` → `PA_INVALID_PROCEDURE` if not found
  - [x] Use `line_number` parameter (1-indexed line position) for per-line findings
- [x] Task 7: Update `DEFAULT_PA_RULE_VALIDATORS` in `conf.py` (AC: #12)
  - [x] Add 5 dotted paths to `DEFAULT_PA_RULE_VALIDATORS` list
  - [x] Maintain alphabetical order
- [x] Task 8: Update re-exports (AC: #12)
  - [x] Add 5 validators to `prior_auth/validators/rule_based/__init__.py` re-exports
  - [x] Update `prior_auth/validators/__init__.py` to re-export all 5 validators
  - [x] Keep `__all__` lists alphabetically sorted
- [x] Task 9: Create comprehensive test suite (AC: #1-#12)
  - [x] `tests/test_prior_auth/test_validators/__init__.py`
  - [x] `tests/test_prior_auth/test_validators/conftest.py` with shared fixtures
  - [x] `tests/test_prior_auth/test_validators/test_npi.py` — valid NPI, invalid format, Luhn failure, empty/None skip
  - [x] `tests/test_prior_auth/test_validators/test_member_id.py` — non-empty pass, empty/whitespace fail
  - [x] `tests/test_prior_auth/test_validators/test_date_of_birth.py` — valid DOB, future DOB, patient DOB
  - [x] `tests/test_prior_auth/test_validators/test_diagnosis.py` — valid codes, invalid format, unknown code, empty list
  - [x] `tests/test_prior_auth/test_validators/test_procedure.py` — valid codes, invalid format, unknown code, empty service lines
  - [x] PHI safety tests: verify no PHI values in any finding message across all validators
  - [x] Re-export tests: verify all validators importable from `prior_auth.validators`
  - [x] Default config test: verify `DEFAULT_PA_RULE_VALIDATORS` contains all 5 validator paths

## Dev Notes

### Architecture Decisions

**D25: PA Model Design** — `PriorAuthRequest` is flat, frozen, `strict=False`. Validators receive this typed model, not raw dicts.

**BaseValidator Contract** — All validators subclass `BaseValidator` from `claim_validator.validators.base`:
- Set `name` class attribute (unique identifier string)
- Override `validate(self, request) -> ValidatorOutput`
- Use `self._make_output(findings)` to build output
- Use `self._make_finding(code=..., message=..., severity=..., field_name=..., ...)` to build findings
- Must be stateless, must not modify input, must not make network calls

**Parameter Type Override** — `BaseValidator.validate()` is typed as `claim: ClaimData`. PA validators override with `request: PriorAuthRequest`. Since `from __future__ import annotations` defers evaluation, this works at runtime. Add `# type: ignore[override]` if mypy strict mode flags it.

### Existing Code to Reuse (DO NOT DUPLICATE)

**NPI Luhn Check — import from existing module:**
```python
from claim_validator.validators.rule_based.npi import _check_luhn_npi
```
Location: `src/claim_validator/validators/rule_based/npi.py:13-27`
Signature: `_check_luhn_npi(npi: str) -> bool`
Logic: Prefixes NPI with "80840", applies Luhn algorithm, returns True if valid.

**ICD-10 Code Lookup — import from existing code tables:**
```python
from claim_validator.code_tables import lookup_icd10
```
Location: `src/claim_validator/code_tables/icd10.py`
Signature: `lookup_icd10(code: str) -> str | None`
Logic: Normalizes to uppercase, checks with/without dot separator. Returns description or None.

**HCPCS Code Lookup — import from existing code tables:**
```python
from claim_validator.code_tables import lookup_hcpcs
```
Location: `src/claim_validator/code_tables/hcpcs.py`
Signature: `lookup_hcpcs(code: str) -> str | None`
Logic: Normalizes to uppercase, returns description or None.

### Finding Code Reference

| Finding Code | Severity | Field | When |
|---|---|---|---|
| `PA_INVALID_NPI_FORMAT` | ERROR | `requester_npi` | NPI not exactly 10 numeric digits |
| `PA_INVALID_NPI` | ERROR | `requester_npi` | NPI fails Luhn check |
| `PA_MISSING_MEMBER_ID` | ERROR | `subscriber.member_id` | Member ID empty/whitespace |
| `PA_INVALID_DOB` | ERROR | `subscriber.dob` or `patient.dob` | DOB is in the future |
| `PA_INVALID_DIAGNOSIS_FORMAT` | ERROR | `diagnosis_codes` | ICD-10 code wrong format |
| `PA_INVALID_DIAGNOSIS` | ERROR | `diagnosis_codes` | ICD-10 code not in code table |
| `PA_INVALID_PROCEDURE_FORMAT` | ERROR | `cpt_code` | CPT/HCPCS code wrong format |
| `PA_INVALID_PROCEDURE` | ERROR | `cpt_code` | CPT/HCPCS code not in code table |

### PriorAuthRequest Model (DO NOT modify)

From `src/claim_validator/prior_auth/models/request.py`:

```python
class PriorAuthRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    requester_npi: str
    requester_taxonomy: str | None = None
    payer_id: str | None = None
    subscriber: SubscriberInfo          # member_id, first_name, last_name, dob
    patient: PatientInfo | None = None  # first_name, last_name, dob, gender, relationship
    diagnosis_codes: list[str] = []
    service_lines: list[ServiceLine] = []  # cpt_code, quantity, from_date, to_date, place_of_service_code
    request_category_code: RequestCategoryCode = RequestCategoryCode.HEALTH_SERVICES_REVIEW
    certification_type_code: CertificationTypeCode = CertificationTypeCode.INITIAL
    clinical_info: str | None = None
```

Key field access patterns:
- NPI: `request.requester_npi` (str, required)
- Member ID: `request.subscriber.member_id` (str, required)
- DOB: `request.subscriber.dob` (date, required), `request.patient.dob` (date, if patient exists)
- Diagnosis: `request.diagnosis_codes` (list[str], may be empty)
- Procedure: `request.service_lines[i].cpt_code` (str, required per ServiceLine)

### Validator Implementation Pattern

Follow the existing `NPIValidator` pattern in `src/claim_validator/validators/rule_based/npi.py`:

```python
"""PANPIValidator — NPI validation for prior authorization requests."""

from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.rule_based.npi import _check_luhn_npi

_NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


class PANPIValidator(BaseValidator):
    """Validates requester NPI on prior authorization requests."""

    name = "PANPIValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []
        npi = request.requester_npi
        if not npi or not npi.strip():
            return self._make_output(findings)
        npi = npi.strip()
        # ... format check, Luhn check ...
        return self._make_output(findings)
```

### Regex Patterns (from existing CodingValidator)

```python
_ICD10_PATTERN = re.compile(r"^[A-Za-z]\d{2}(\.\d{1,4})?$")
_PROCEDURE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{5}$")
```

Both patterns are already used in `src/claim_validator/validators/rule_based/coding.py`. Reuse the same regex patterns (copy the constants, don't import private module constants).

### Previous Story Learnings (PA-1.1, PA-1.2, PA-1.3)

From PA-1.1:
- All models use `ConfigDict(frozen=True, strict=False)` — do NOT change
- Re-exports go in `prior_auth/__init__.py` AND top-level `claim_validator/__init__.py`
- Keep `__all__` lists alphabetically sorted
- Use `from __future__ import annotations` on every file

From PA-1.2:
- Keep functions simple and stateless (single-responsibility)
- Normalize inputs (`.upper().strip()`) before comparison
- Return `None` (or appropriate default) for invalid/missing input — don't raise exceptions
- Test files need `from __future__ import annotations`
- Use conftest.py for shared fixtures
- Code review caught: missing re-export tests, missing performance tests, missing `from __future__ import annotations` in `__init__.py`

From PA-1.3:
- Code review caught: "first wins" logic was wrong — use "most restrictive wins" for multi-value scanning
- Finding messages reference field names, not values
- Edge case tests are critical: empty, None, whitespace, unexpected types
- Test all re-exports explicitly

### Test Fixture Pattern

Create `tests/test_prior_auth/test_validators/conftest.py` with shared fixtures:

```python
"""Shared fixtures for PA validator tests."""

from __future__ import annotations

from datetime import date

import pytest

from claim_validator.prior_auth.models.request import (
    PatientInfo,
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)


@pytest.fixture
def valid_request() -> PriorAuthRequest:
    """Minimal valid PriorAuthRequest for validator tests."""
    return PriorAuthRequest(
        requester_npi="1234567893",  # Valid Luhn NPI
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=["J06.9"],  # Valid ICD-10
        service_lines=[
            ServiceLine(cpt_code="99213"),  # Valid CPT
        ],
    )
```

Test NPIs:
- Valid Luhn: `"1234567893"` (passes check digit)
- Invalid Luhn: `"1234567890"` (fails check digit)
- Invalid format: `"123"` (too short), `"12345678901"` (too long), `"123456789A"` (non-numeric)

### Project Structure Notes

**New files to create:**

```
src/claim_validator/prior_auth/validators/
├── rule_based/
│   ├── __init__.py          # Re-exports all 5 validators
│   ├── npi.py               # PANPIValidator
│   ├── member_id.py         # PAMemberIDValidator
│   ├── date_of_birth.py     # PADateOfBirthValidator
│   ├── diagnosis.py         # PADiagnosisValidator
│   └── procedure.py         # PAProcedureValidator

tests/test_prior_auth/test_validators/
├── __init__.py
├── conftest.py              # Shared test fixtures
├── test_npi.py
├── test_member_id.py
├── test_date_of_birth.py
├── test_diagnosis.py
└── test_procedure.py
```

**Existing files to modify:**

| File | Change |
|---|---|
| `src/claim_validator/prior_auth/validators/__init__.py` | Add re-exports from `rule_based` subpackage |
| `src/claim_validator/conf.py` | Populate `DEFAULT_PA_RULE_VALIDATORS` with 5 dotted paths |

**Files NOT to touch:**
- `src/claim_validator/prior_auth/models/` — all models already exist
- `src/claim_validator/prior_auth/constants.py` — no new enums needed
- `src/claim_validator/prior_auth/code_tables/` — not modified (PA validators use existing `claim_validator.code_tables`)
- `src/claim_validator/prior_auth/determination.py` — not related to this story
- `src/claim_validator/__init__.py` — validators are NOT re-exported at top level (only models/functions are)
- `src/claim_validator/validators/base.py` — do NOT modify BaseValidator
- `src/claim_validator/validators/rule_based/npi.py` — import from it, don't modify it
- `pyproject.toml` — no new dependencies

### HIPAA Compliance

- Finding `message` fields reference field NAMES only, never actual VALUES
- Good: `"NPI in 'requester_npi' must be exactly 10 numeric digits"`
- Bad: `"NPI '1234567890' is invalid"` (exposes actual NPI value)
- Good: `"Diagnosis code at position 1 in 'diagnosis_codes' not found in bundled ICD-10-CM table"`
- Bad: `"Diagnosis code J06.9 not found"` (exposes actual diagnosis — reveals patient condition)
- `context` dict MAY include non-PHI computed values (e.g., `{"code_length": 3}`) but NEVER raw patient data

### Performance (NFR1)

- Target: < 100ms for all 5 validators combined on a typical PA request
- Code table lookups (`lookup_icd10`, `lookup_hcpcs`) are lazy-loaded + cached — first call ~200ms, subsequent < 1ms
- Regex compilation at module level (not per-call)
- No I/O beyond initial code table loading

### References

- [Source: architecture.md — BaseValidator contract, lines 560-580]
- [Source: architecture.md — PA validator naming conventions, lines 2125-2138]
- [Source: architecture.md — PA finding code conventions, lines 2140-2148]
- [Source: architecture.md — PA file structure, lines 2254-2303]
- [Source: architecture.md — PA validator example (PADiagnosisValidator), lines 2216-2232]
- [Source: architecture.md — PA pipeline phase 1 validators, lines 2030-2042]
- [Source: prd.md — FR11-FR15: Pre-submission validation requirements]
- [Source: prd.md — NFR1: Rule-based validation < 100ms]
- [Source: prd.md — NFR12: No PHI in error messages]
- [Source: epics.md — PA Epic 1, Story 1.4]
- [Source: project-context.md — PA naming conventions, finding code prefixes]
- [Source: validators/rule_based/npi.py — NPI Luhn check implementation]
- [Source: validators/rule_based/coding.py — ICD-10 and HCPCS validation patterns]
- [Source: code_tables/__init__.py — lookup_icd10, lookup_hcpcs exports]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- 2 test data fixes: `J069` (no-dot ICD-10) doesn't match format regex `^[A-Za-z]\d{2}(\.\d{1,4})?$` — consistent with existing CodingValidator; `J0120` not in bundled HCPCS table — changed to `A4206`
- 1 ruff I001 import sorting in `test_re_exports_and_config.py` — auto-fixed with `--fix`
- 1 existing test updated: `test_default_pa_rule_validators_empty` → `test_default_pa_rule_validators` (no longer empty after populating defaults)

### Completion Notes List

- Created 5 PA validators in `prior_auth/validators/rule_based/`: PANPIValidator, PAMemberIDValidator, PADateOfBirthValidator, PADiagnosisValidator, PAProcedureValidator
- All validators subclass BaseValidator, implement `validate(request) -> ValidatorOutput` with `# type: ignore[override]`
- PANPIValidator: reuses `_check_luhn_npi` from `claim_validator.validators.rule_based.npi`, checks format (10 digits) then Luhn, skips empty/whitespace
- PAMemberIDValidator: checks `subscriber.member_id` is non-empty after strip
- PADateOfBirthValidator: checks subscriber and optional patient DOB not in future
- PADiagnosisValidator: validates ICD-10 format via regex, then looks up in bundled code table via `lookup_icd10()`
- PAProcedureValidator: validates CPT/HCPCS format via regex, then looks up in bundled code table via `lookup_hcpcs()`, uses `line_number` for per-line findings
- All finding messages reference field NAMES only, never actual PHI values (HIPAA NFR12 compliance)
- 8 finding codes implemented: PA_INVALID_NPI_FORMAT, PA_INVALID_NPI, PA_MISSING_MEMBER_ID, PA_INVALID_DOB, PA_INVALID_DIAGNOSIS_FORMAT, PA_INVALID_DIAGNOSIS, PA_INVALID_PROCEDURE_FORMAT, PA_INVALID_PROCEDURE
- Populated `DEFAULT_PA_RULE_VALIDATORS` in `conf.py` with 5 dotted paths (alphabetical)
- Re-exports in `prior_auth/validators/rule_based/__init__.py` and `prior_auth/validators/__init__.py`
- 63 new tests across 6 test files: test_npi (11), test_member_id (6), test_date_of_birth (9), test_diagnosis (12), test_procedure (11), test_re_exports_and_config (12 — re-exports + config + PHI safety)
- Updated 1 existing test in `test_conf.py` to reflect non-empty default validators
- All 937 tests pass (63 new + 874 existing), zero regressions
- All ACs satisfied: AC1-2 (NPI), AC3-4 (Member ID), AC5-6 (DOB), AC7-8 (Diagnosis), AC9-10 (Procedure), AC11 (PHI safety), AC12 (config/re-exports)

### File List

**New files:**
- `src/claim_validator/prior_auth/validators/rule_based/__init__.py`
- `src/claim_validator/prior_auth/validators/rule_based/npi.py`
- `src/claim_validator/prior_auth/validators/rule_based/member_id.py`
- `src/claim_validator/prior_auth/validators/rule_based/date_of_birth.py`
- `src/claim_validator/prior_auth/validators/rule_based/diagnosis.py`
- `src/claim_validator/prior_auth/validators/rule_based/procedure.py`
- `tests/test_prior_auth/test_validators/__init__.py`
- `tests/test_prior_auth/test_validators/conftest.py`
- `tests/test_prior_auth/test_validators/test_npi.py`
- `tests/test_prior_auth/test_validators/test_member_id.py`
- `tests/test_prior_auth/test_validators/test_date_of_birth.py`
- `tests/test_prior_auth/test_validators/test_diagnosis.py`
- `tests/test_prior_auth/test_validators/test_procedure.py`
- `tests/test_prior_auth/test_validators/test_re_exports_and_config.py`

### Code Review Fixes

| # | Severity | Issue | Fix Applied |
|---|----------|-------|-------------|
| 1 | HIGH | Conditional test assertions using `if result.findings:` — tests pass even when validator returns no findings | Made assertions unconditional with verified not-in-table codes (X99.9, ZZ999) |
| 2 | MEDIUM | ICD-10 regex `^[A-Za-z]\d{2}(\.\d{1,4})?$` too strict — rejects dotless codes (J069) common in X12 EDI | Updated to `^[A-Za-z]\d{2}(\.\d{1,4}|\d{1,4})?$`; added `test_valid_dotless_code` |
| 3 | MEDIUM | Unused `subscriber` and `patient` fixtures in conftest.py | Removed unused fixtures, kept only `valid_request` |
| 4 | MEDIUM | Missing performance test for NFR1 (< 100ms for all 5 validators) | Added `TestPerformance.test_all_validators_under_100ms` to test_re_exports_and_config.py |
| 5 | MEDIUM | `field_name="procedure_code"` in PAProcedureValidator doesn't match model field `cpt_code` | Changed `field_name` and message text to reference `cpt_code` |

### Code Review Action Items (LOW — deferred)

- [ ] **#6**: `PANPIValidator` imports private function `_check_luhn_npi` across module boundary. Consider extracting to a shared utility module (e.g., `claim_validator.utils.npi`) if more PA modules need it.
- [ ] **#7**: `test_valid_three_char_code` only asserts no format findings — doesn't assert zero total findings. Strengthen to `assert len(result.findings) == 0` if 3-char codes should also pass lookup.

**Modified files:**
- `src/claim_validator/prior_auth/validators/__init__.py` (re-exports from rule_based subpackage)
- `src/claim_validator/conf.py` (populated DEFAULT_PA_RULE_VALIDATORS with 5 validator paths)
- `tests/test_prior_auth/test_conf.py` (updated test to expect 5 default validators instead of empty)
