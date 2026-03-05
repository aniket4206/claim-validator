# Story 1.3: Code-Table-Dependent Validators

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want diagnosis, procedure, and payer ID validation as pure functions in `shared/validators/`,
so that ICD-10, CPT/HCPCS, and payer lookups are maintained in one place.

## Acceptance Criteria

1. **AC-1: Diagnosis code validation**
   - **Given** `validate_diagnosis(codes, field_name, code_prefix)` is called with valid ICD-10 codes
   - **When** all codes exist in the shared ICD-10 code table
   - **Then** an empty findings list is returned
   - **And** codes with invalid format (not matching `[A-Za-z]\d{2}(\.\d{1,4})?`) return ERROR findings
   - **And** codes not found in the bundled ICD-10-CM table return ERROR findings with the code position in context

2. **AC-2: Procedure code validation**
   - **Given** `validate_procedure(codes, field_name, code_prefix)` is called
   - **When** the CPT/HCPCS code exists in the shared code table
   - **Then** an empty findings list is returned
   - **And** codes with invalid format (not matching `[A-Za-z0-9]{5}`) return ERROR findings
   - **And** unknown procedure codes return a WARNING finding

3. **AC-3: Payer ID validation**
   - **Given** `validate_payer_id(payer_id, field_name, code_prefix)` is called
   - **When** the payer ID exists in the shared payer directory
   - **Then** an empty findings list is returned
   - **And** unknown payer IDs return a WARNING finding

4. **AC-4: Code table integration**
   - All functions import code tables from `claim_validator.shared.code_tables` (D39)
   - `validate_diagnosis()` uses `lookup_icd10()` from shared code tables
   - `validate_procedure()` uses `lookup_hcpcs()` from shared code tables
   - `validate_payer_id()` uses `lookup_payer()` from shared code tables

5. **AC-5: Pure function contract**
   - All functions are stateless (no side effects)
   - All functions accept `field_name` and `code_prefix` parameters for domain-specific finding codes (D34)
   - All functions return `list[Finding]` with consistent structure
   - Zero PHI in findings — reference field names, never values

6. **AC-6: Cross-cutting quality**
   - All functions pass mypy strict, ruff clean, have docstrings
   - FR5, FR6, FR7 are satisfied
   - `shared/validators/__init__.py` updated to re-export new validators with `__all__`

## Tasks / Subtasks

- [x] Task 1: Create diagnosis validator (AC: #1, #4, #5)
  - [x] 1.1: Create `src/claim_validator/shared/validators/diagnosis.py` with `validate_diagnosis()`
  - [x] 1.2: ICD-10 format regex: `^[A-Za-z]\d{2}(\.?\d{1,4})?$` (letter + 2 digits + optional dot + 1-4 digits, dotless variant supported)
  - [x] 1.3: Handle dot-variant normalization via `lookup_icd10()` (already handles J06.9 vs J069)
  - [x] 1.4: Finding codes: `{code_prefix}INVALID_DIAGNOSIS_FORMAT` (ERROR), `{code_prefix}INVALID_DIAGNOSIS` (ERROR)
  - [x] 1.5: Include position (1-indexed) in finding context for each invalid code
- [x] Task 2: Create procedure validator (AC: #2, #4, #5)
  - [x] 2.1: Create `src/claim_validator/shared/validators/procedure.py` with `validate_procedure()`
  - [x] 2.2: CPT/HCPCS format regex: `^[A-Za-z0-9]{5}$` (exactly 5 alphanumeric chars)
  - [x] 2.3: Finding codes: `{code_prefix}INVALID_PROCEDURE_FORMAT` (ERROR), `{code_prefix}INVALID_PROCEDURE` (WARNING)
  - [x] 2.4: Include position (1-indexed) in finding context for each invalid code
- [x] Task 3: Create payer ID validator (AC: #3, #4, #5)
  - [x] 3.1: Create `src/claim_validator/shared/validators/payer_id.py` with `validate_payer_id()`
  - [x] 3.2: Missing/empty payer ID → ERROR finding
  - [x] 3.3: Unknown payer ID (not in payer directory) → WARNING finding
  - [x] 3.4: Finding codes: `{code_prefix}MISSING_PAYER_ID` (ERROR), `{code_prefix}INVALID_PAYER` (WARNING)
- [x] Task 4: Update shared validators __init__.py (AC: #6)
  - [x] 4.1: Add re-exports for `validate_diagnosis`, `validate_procedure`, `validate_payer_id` to `shared/validators/__init__.py`
  - [x] 4.2: Update `__all__` list
- [x] Task 5: Create tests (AC: #1, #2, #3, #4, #5)
  - [x] 5.1: Create `tests/test_shared/test_validators/test_diagnosis.py` — 25 tests: valid codes, invalid format, unknown codes, dot variants, case insensitivity, code_prefix, field_name passthrough, empty list, PHI-leak assertions
  - [x] 5.2: Create `tests/test_shared/test_validators/test_procedure.py` — 21 tests: valid codes, invalid format, unknown codes (WARNING), code_prefix, field_name passthrough, empty list, PHI-leak assertions
  - [x] 5.3: Create `tests/test_shared/test_validators/test_payer_id.py` — 16 tests: valid payer, unknown payer (WARNING), missing payer (ERROR), code_prefix, field_name passthrough, case insensitivity, PHI-leak assertions
- [x] Task 6: Quality verification (AC: #6)
  - [x] 6.1: Run `mypy --strict` — zero errors on all new source files
  - [x] 6.2: Run `ruff check` — zero warnings
  - [x] 6.3: Run `pytest tests/test_shared/` — all pass (62 new + existing)
  - [x] 6.4: Verify all existing tests still pass (`pytest`) — 1760 passed, zero regressions

## Dev Notes

### Architecture Decision D34: Shared Validators (MANDATORY)

All shared validators are pure functions with `field_name` and `code_prefix` parameters. Domain validators become thin wrappers that call the shared function. From architecture.md:

```python
def validate_diagnosis(
    codes: list[str],
    field_name: str = "diagnosis_codes",
    code_prefix: str = "",
) -> list[Finding]:
    """Validate ICD-10-CM diagnosis codes against shared code table.

    Returns empty list if all codes are valid.
    """
```

### D39 Dependency: Shared Code Tables (Story 1.2 — DONE)

Story 1.3 validators MUST import from `shared.code_tables`, never from old domain paths:

```python
# CORRECT — use shared code tables from Story 1.2
from claim_validator.shared.code_tables import lookup_icd10, lookup_hcpcs, lookup_payer

# NEVER — old domain-specific paths
from claim_validator.code_tables import lookup_icd10  # OLD claims path
from claim_validator.eligibility.code_tables.payer_directory import get_payer_directory  # OLD elig path
```

### D43: Clean Break

- Story 1.3 ONLY creates new files in `shared/validators/`
- Does NOT modify existing domain validators (`validators/rule_based/coding.py`, `eligibility/validators/rule_based/payer_id.py`, `prior_auth/validators/rule_based/diagnosis.py`, `prior_auth/validators/rule_based/procedure.py`)
- Epic 3 will refactor domain validators to delegate to shared functions

### Existing Domain Validator Analysis

**What exists today that Story 1.3 consolidates:**

| Validator | Claims | Eligibility | Prior Auth |
|-----------|--------|-------------|------------|
| Diagnosis | `CodingValidator._check_diagnosis_codes()` in `validators/rule_based/coding.py` | — | `PADiagnosisValidator` in `prior_auth/validators/rule_based/diagnosis.py` |
| Procedure | `CodingValidator._check_procedure_codes()` in `validators/rule_based/coding.py` | — | `PAProcedureValidator` in `prior_auth/validators/rule_based/procedure.py` |
| Payer ID | (only presence check in CompletenessValidator) | `PayerIDValidator` in `eligibility/validators/rule_based/payer_id.py` | — |

### Diagnosis Validator Implementation Guide

**ICD-10 Format:** `^[A-Za-z]\d{2}(\.\d{1,4})?$`
- Letter + 2 digits + optional (dot + 1-4 digits)
- Examples: `A01`, `J06.9`, `M79.3`, `Z23`

**Logic flow:**
1. If `codes` is None or empty → return empty list (no codes to validate = no findings)
2. For each code in the list:
   a. Normalize: `code.strip()` (do NOT uppercase — lookup_icd10 handles normalization)
   b. Check format regex → if fails: `{code_prefix}INVALID_DIAGNOSIS_FORMAT` (ERROR)
   c. If format OK: `lookup_icd10(code)` → if None: `{code_prefix}INVALID_DIAGNOSIS` (ERROR)
3. Include `context={"position": i+1}` for each invalid code (1-indexed)

**Note on dot-variant handling:** `lookup_icd10()` already handles both `J06.9` and `J069` forms. The format regex accepts both forms too. No additional normalization needed.

### Procedure Validator Implementation Guide

**CPT/HCPCS Format:** `^[A-Za-z0-9]{5}$`
- Exactly 5 alphanumeric characters
- Examples: `99213`, `J0585`, `G0438`

**Logic flow:**
1. If `codes` is None or empty → return empty list
2. For each code in the list:
   a. Normalize: `code.strip()`
   b. Check format regex → if fails: `{code_prefix}INVALID_PROCEDURE_FORMAT` (ERROR)
   c. If format OK: `lookup_hcpcs(code)` → if None: `{code_prefix}INVALID_PROCEDURE` (WARNING)
3. Include `context={"position": i+1}` for each invalid code

**Severity note:** Unknown procedure codes are WARNING (not ERROR) per epic AC. The existing claims `CodingValidator` uses ERROR, but the shared function follows the epic's specification. Domain wrappers can override severity if needed.

### Payer ID Validator Implementation Guide

**Logic flow:**
1. If `payer_id` is None or empty/whitespace → `{code_prefix}MISSING_PAYER_ID` (ERROR)
2. `lookup_payer(payer_id)` → if None: `{code_prefix}INVALID_PAYER` (WARNING)
3. No format regex needed — payer IDs are free-form strings

**Severity note:** Unknown payer IDs are WARNING (not ERROR) per epic AC. The existing eligibility `PayerIDValidator` uses ERROR (`ELIG_INVALID_PAYER`), but the shared function follows the epic's specification.

### Finding Model (from `claim_validator.models.finding`)

```python
Finding(
    code=f"{code_prefix}INVALID_DIAGNOSIS",
    message="ICD-10 diagnosis code not found in code tables",
    severity=Severity.ERROR,
    field_name=field_name,
    line_number=None,
    suggestion="Verify ICD-10-CM code at https://www.icd10data.com",
    context={"position": 1},
)
```

**PHI rule:** `message` and `suggestion` MUST reference field names, not field values. `context` dict MAY include non-PHI computed values (position, length) but NEVER raw patient data or actual code values.

### Previous Story Intelligence

**Story 1.1 (shared package skeleton + core validators):**
- Created: `shared/__init__.py`, `shared/validators/__init__.py`, `npi.py`, `date.py`, `member_id.py`, `demographics.py`
- Pattern: pure function → `list[Finding]`, `field_name` + `code_prefix` params, stateless
- Learnings:
  - Use `.venv/bin/python -m pytest` (NOT `.venv/bin/pytest` — stale shebang)
  - PHI-leak tests: pass actual PHI values as inputs, assert they don't appear in output
  - `from __future__ import annotations` required on ALL new files
  - D43 compliance: create new files only, leave existing code untouched

**Story 1.2 (shared code tables consolidation):**
- Created: `shared/code_tables/` + `shared/data/` with all 9 tables + lookups
- Key functions Story 1.3 uses:
  - `lookup_icd10(code: str) -> str | None` — case insensitive, handles dot variants
  - `lookup_hcpcs(code: str) -> str | None` — case insensitive
  - `lookup_payer(payer_id: str) -> dict[str, str] | None` — case insensitive, returns `{name, type}`
- Learnings:
  - POS code "99" is valid — don't assume codes are invalid
  - `typing.cast()` needed for `load_json()` returns to satisfy mypy strict
  - Thread safety tests should use `threading.Lock` for shared lists

### Import Pattern

All new files must use:

```python
"""Module docstring."""

from __future__ import annotations

import re

from claim_validator.models.finding import Finding, Severity
from claim_validator.shared.code_tables import lookup_icd10  # or lookup_hcpcs, lookup_payer
```

**NEVER import domain models** in `shared/validators/`.

### What Story 1.3 Must NOT Create/Modify

- Do NOT modify existing domain validators (`coding.py`, `payer_id.py`, PA validators)
- Do NOT modify `shared/code_tables/` files — Story 1.2 output is stable
- Do NOT modify `claim_validator/__init__.py` — no new top-level exports yet
- Do NOT create `shared/deidentifier/` or `shared/pipeline/` — Stories 2.x
- Do NOT create domain wrapper validators — Epic 3

### Quality Requirements

- **mypy strict** — `python_version = "3.11"`, strict = true, pydantic plugin enabled
- **ruff** — line-length=100, rules E/F/I/N/W/UP
- **pytest** — all new + all existing tests must pass
- **Docstrings** — module-level AND function-level on all public functions (NFR27)
- **Stateless** — no shared mutable state, thread-safe by design (NFR12)

### Testing Requirements

1. **test_diagnosis.py**: Valid ICD-10 codes → empty list; invalid format → ERROR; unknown code → ERROR; dot-variant handling (J06.9 vs J069); case insensitivity; code_prefix passthrough; field_name passthrough; empty codes list → empty findings; multiple codes with mix of valid/invalid; PHI-leak assertion (actual codes in input, not in finding messages)
2. **test_procedure.py**: Valid HCPCS code → empty list; invalid format → ERROR; unknown code → WARNING; code_prefix passthrough; field_name passthrough; empty codes list → empty findings; multiple codes mixed; PHI-leak assertion
3. **test_payer_id.py**: Valid payer → empty list; unknown payer → WARNING; missing payer (None) → ERROR; empty string → ERROR; code_prefix passthrough; field_name passthrough; case insensitivity; whitespace trimming; PHI-leak assertion

### References

- [Source: architecture.md — D34: Shared validator pure functions, lines 2756, 2961-2987]
- [Source: architecture.md — D39: Shared code tables dependency, lines 2946]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: architecture.md — shared/validators/ directory layout, lines 3265-3273]
- [Source: architecture.md — Finding model structure, lines 485-502]
- [Source: architecture.md — Pure function enforcement rules, lines 3241-3243]
- [Source: architecture.md — Test structure, lines 3347-3354]
- [Source: prd.md — FR5: Canonical diagnosis code validator]
- [Source: prd.md — FR6: Canonical procedure code validator]
- [Source: prd.md — FR7: Canonical payer ID validator]
- [Source: epics.md — Story 1.3 acceptance criteria, lines 273-297]
- [Source: 1-1-shared-package-skeleton-and-core-validators.md — Previous story learnings]
- [Source: 1-2-shared-code-tables-consolidation.md — Code table functions available]
- [Source: validators/rule_based/coding.py — Existing claims diagnosis/procedure validation]
- [Source: eligibility/validators/rule_based/payer_id.py — Existing eligibility payer validation]
- [Source: prior_auth/validators/rule_based/diagnosis.py — Existing PA diagnosis validation]
- [Source: prior_auth/validators/rule_based/procedure.py — Existing PA procedure validation]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

### Completion Notes List

- ICD-10 format regex updated from `^[A-Za-z]\d{2}(\.\d{1,4})?$` to `^[A-Za-z]\d{2}(\.?\d{1,4})?$` to accept dotless variants (e.g. J069) that `lookup_icd10()` already handles
- Story spec said format regex accepts both dotted and dotless forms but the given regex did not — corrected in implementation
- Three-letter ICD-10 codes (e.g. A01) pass format validation but may not exist in the bundled code table — tests use known-valid codes from the table
- Unknown procedure codes are WARNING (per epic spec), not ERROR (as in existing claims CodingValidator)
- Unknown payer IDs are WARNING (per epic spec), not ERROR (as in existing eligibility PayerIDValidator)

### File List

**Source files (new):**
- `src/claim_validator/shared/validators/diagnosis.py`
- `src/claim_validator/shared/validators/procedure.py`
- `src/claim_validator/shared/validators/payer_id.py`

**Source files (modified):**
- `src/claim_validator/shared/validators/__init__.py` — added re-exports for 3 new validators

**Test files (new):**
- `tests/test_shared/test_validators/test_diagnosis.py` (25 tests)
- `tests/test_shared/test_validators/test_procedure.py` (21 tests)
- `tests/test_shared/test_validators/test_payer_id.py` (16 tests)
