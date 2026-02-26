# Story 2.5: Coding Validator

Status: review

## Story

As a **developer**,
I want diagnosis and procedure codes validated against bundled code tables,
so that claims with invalid ICD-10, CPT/HCPCS codes, or inconsistent diagnosis pointers are caught before submission.

## Acceptance Criteria

1. **Given** a claim with valid ICD-10-CM diagnosis codes that exist in the bundled table, **When** `CodingValidator.validate(claim)` is called, **Then** zero diagnosis code findings are produced.

2. **Given** a claim with an ICD-10 code not in the bundled table (e.g., `"Z99.99"`), **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_DIAGNOSIS_CODE`, severity `ERROR`, and `field_name` `"diagnosis_codes"` is produced.

3. **Given** a claim with an ICD-10 code in wrong format (e.g., too short, clearly malformed), **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_DIAGNOSIS_CODE_FORMAT`, severity `ERROR` is produced.

4. **Given** a claim line with a valid CPT/HCPCS procedure code that exists in the bundled table, **When** `CodingValidator.validate(claim)` is called, **Then** zero procedure code findings are produced for that line.

5. **Given** a claim line with a procedure code not found in the bundled HCPCS table, **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_PROCEDURE_CODE`, severity `ERROR`, `field_name` `"procedure_code"`, and `line_number` is produced.

6. **Given** a claim line with a procedure code in wrong format (not 5 alphanumeric characters), **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_PROCEDURE_CODE_FORMAT`, severity `ERROR`, and `line_number` is produced.

7. **Given** a claim line with modifiers present, **When** `CodingValidator.validate(claim)` is called, **Then** modifier format is validated (each must be 2 alphanumeric characters), and invalid modifiers produce a `Finding` with code `INVALID_MODIFIER_FORMAT`, severity `ERROR`, and `line_number`.

8. **Given** a claim line with diagnosis pointers referencing non-existent diagnosis positions (e.g., pointer `5` when only 3 diagnosis codes exist), **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `INVALID_DIAGNOSIS_POINTER`, severity `ERROR`, and `line_number` is produced.

9. **Given** a claim where a diagnosis code exists but no line references it via diagnosis_pointers, **When** `CodingValidator.validate(claim)` is called, **Then** a `Finding` with code `UNREFERENCED_DIAGNOSIS`, severity `WARNING` is produced.

10. **Given** a claim with empty `diagnosis_codes` list or empty `lines` list, **When** `CodingValidator.validate(claim)` is called, **Then** zero coding-related findings are produced (CompletenessValidator handles required-ness).

11. **Given** any coding finding, **When** I inspect the `message`, **Then** it references field names but never actual code values (no PHI in messages).

## Tasks / Subtasks

- [x] Task 1: Implement `CodingValidator` in `src/claim_validator/validators/rule_based/coding.py` (AC: #1-#11)
  - [x] Subclass `BaseValidator` with `name = "CodingValidator"`
  - [x] `_check_diagnosis_codes()`: Validate each diagnosis code format (3-7 chars, letter+digits pattern) and existence via `lookup_icd10()`
  - [x] `_check_procedure_codes()`: Validate each line's procedure_code format (5 alphanumeric) and existence via `lookup_hcpcs()`
  - [x] `_check_modifiers()`: Validate each modifier on each line (2 alphanumeric characters)
  - [x] `_check_diagnosis_pointers()`: Validate each line's pointers reference valid diagnosis positions
  - [x] `_check_unreferenced_diagnoses()`: Warn if any diagnosis code is not referenced by any line
  - [x] Skip if diagnosis_codes or lines are empty (CompletenessValidator handles required-ness)
  - [x] No PHI in messages — never include actual code values
- [x] Task 2: Write tests in `tests/test_validators/test_rule_based/test_coding.py` (AC: #1-#11)
  - [x] Test valid ICD-10 codes → zero diagnosis findings
  - [x] Test invalid ICD-10 code (not in table) → `INVALID_DIAGNOSIS_CODE`
  - [x] Test invalid ICD-10 format (too short, malformed) → `INVALID_DIAGNOSIS_CODE_FORMAT`
  - [x] Test valid procedure code → zero procedure findings
  - [x] Test invalid procedure code (not in table) → `INVALID_PROCEDURE_CODE`
  - [x] Test invalid procedure code format → `INVALID_PROCEDURE_CODE_FORMAT`
  - [x] Test valid modifiers → zero modifier findings
  - [x] Test invalid modifier format → `INVALID_MODIFIER_FORMAT`
  - [x] Test valid diagnosis pointers → zero pointer findings
  - [x] Test invalid diagnosis pointers → `INVALID_DIAGNOSIS_POINTER`
  - [x] Test unreferenced diagnosis → `UNREFERENCED_DIAGNOSIS` (WARNING)
  - [x] Test empty diagnosis_codes → no findings
  - [x] Test empty lines → no findings
  - [x] Test no PHI in finding messages
  - [x] Test severity is ERROR for all except UNREFERENCED (WARNING)
  - [x] Test line_number present on line-level findings
  - [x] Test suggestion present on findings
  - [x] Test validator statelessness
- [x] Task 3: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `CodingValidator` re-export
- [x] Task 4: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors
  - [x] `uv run pytest` — all tests pass (280 existing + 47 new = 327)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.4)

- SubscriberIDValidator + DemographicsValidator established patterns: module-level constants, private `_check_*` helper methods, `self._make_output(findings)`
- Test pattern: helper `_valid_claim_dict()` returning baseline valid claim, class-based tests with `setup_method`
- Line iteration: `for idx, line in enumerate(claim.lines, start=1)` — line_number is 1-indexed
- Empty/whitespace strings handled via `not value or not value.strip()`
- Format check short-circuits before deeper validation (e.g., format before table lookup)
- 280 tests passing, ruff/mypy clean (32 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `test_rule_based/` directory and `__init__.py` already exist
- Line-length limit is 100 characters — wrap long strings with implicit concatenation

### Relevant ClaimData Fields

| Field | Location | Type | Validator Scope |
|---|---|---|---|
| `diagnosis_codes` | `ClaimData` | `list[DiagnosisCode]` | CodingValidator — format + existence |
| `diagnosis_codes[].code` | `DiagnosisCode` | `str` | ICD-10-CM format and table lookup |
| `diagnosis_codes[].pointer` | `DiagnosisCode` | `int = 1` | Position in diagnosis list |
| `lines[].procedure_code` | `ClaimLineData` | `str` | CPT/HCPCS format and table lookup |
| `lines[].modifiers` | `ClaimLineData` | `list[str] = []` | Modifier format validation |
| `lines[].diagnosis_pointers` | `ClaimLineData` | `list[int] = []` | Pointer consistency check |

### Code Table Lookup Functions

| Function | Module | Input | Output |
|---|---|---|---|
| `lookup_icd10(code)` | `code_tables.icd10` | `str` (e.g., `"J06.9"`) | `str` (description) or `None` |
| `lookup_hcpcs(code)` | `code_tables.hcpcs` | `str` (e.g., `"99213"`) | `str` (description) or `None` |

**Important**: `lookup_icd10()` already handles codes with/without dot separator, case-insensitively. `lookup_hcpcs()` is also case-insensitive. Both strip whitespace. Return `None` if code not found.

### Finding Codes

| Code | Meaning | Severity | Scope |
|---|---|---|---|
| `INVALID_DIAGNOSIS_CODE_FORMAT` | ICD-10 code doesn't match expected format | `ERROR` | Claim-level, per-diagnosis |
| `INVALID_DIAGNOSIS_CODE` | ICD-10 code not found in bundled table | `ERROR` | Claim-level, per-diagnosis |
| `INVALID_PROCEDURE_CODE_FORMAT` | Procedure code doesn't match expected format | `ERROR` | Line-level |
| `INVALID_PROCEDURE_CODE` | Procedure code not found in bundled HCPCS table | `ERROR` | Line-level |
| `INVALID_MODIFIER_FORMAT` | Modifier is not 2 alphanumeric characters | `ERROR` | Line-level |
| `INVALID_DIAGNOSIS_POINTER` | Diagnosis pointer references non-existent position | `ERROR` | Line-level |
| `UNREFERENCED_DIAGNOSIS` | Diagnosis code not referenced by any line | `WARNING` | Claim-level |

### Diagnosis Pointer Consistency Logic

`DiagnosisCode` has a `pointer` field (default 1) which represents the position in the claim's diagnosis list. Lines reference diagnoses via `diagnosis_pointers: list[int]`.

**Validation logic**:
- For each line, each value in `diagnosis_pointers` must correspond to a valid `pointer` value in `claim.diagnosis_codes`
- Build a set of valid pointers: `{dx.pointer for dx in claim.diagnosis_codes}`
- For each line pointer, check if it exists in the valid pointers set
- After processing all lines, check which diagnosis pointers were never referenced by any line

### Implementation Spec

```python
# src/claim_validator/validators/rule_based/coding.py
from __future__ import annotations

import re

from claim_validator.code_tables import lookup_hcpcs, lookup_icd10
from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# ICD-10-CM format: letter followed by 2+ digits, optional dot, optional more characters
# Minimum 3 chars (e.g., "A09"), maximum 7 chars (e.g., "S72.001")
_ICD10_PATTERN = re.compile(r"^[A-Za-z]\d{2}(\.\d{1,4})?$")

# Procedure code format: 5 alphanumeric characters
_PROCEDURE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{5}$")

# Modifier format: 2 alphanumeric characters
_MODIFIER_PATTERN = re.compile(r"^[A-Za-z0-9]{2}$")


class CodingValidator(BaseValidator):
    """Validates diagnosis codes, procedure codes, modifiers,
    and diagnosis pointer consistency."""

    name = "CodingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_diagnosis_codes(claim, findings)
        self._check_procedure_codes(claim, findings)
        self._check_modifiers(claim, findings)
        self._check_diagnosis_pointers(claim, findings)
        self._check_unreferenced_diagnoses(claim, findings)

        return self._make_output(findings)

    def _check_diagnosis_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes:
            return  # CompletenessValidator handles required

        for i, dx in enumerate(claim.diagnosis_codes, start=1):
            code = dx.code.strip() if dx.code else ""
            if not code:
                continue  # CompletenessValidator handles required

            # Format check first
            if not _ICD10_PATTERN.match(code):
                findings.append(
                    self._make_finding(
                        code="INVALID_DIAGNOSIS_CODE_FORMAT",
                        message=(
                            f"Diagnosis code at position {i} in"
                            " 'diagnosis_codes' has invalid format"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "ICD-10-CM codes must start with a letter"
                            " followed by 2+ digits (e.g., J06.9)"
                        ),
                    )
                )
                continue  # Skip table lookup if format is wrong

            # Table existence check
            if lookup_icd10(code) is None:
                findings.append(
                    self._make_finding(
                        code="INVALID_DIAGNOSIS_CODE",
                        message=(
                            f"Diagnosis code at position {i} in"
                            " 'diagnosis_codes' not found in"
                            " bundled ICD-10-CM table"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "Verify the ICD-10-CM code against"
                            " the current CMS code set"
                        ),
                    )
                )

    def _check_procedure_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return  # CompletenessValidator handles required

        for idx, line in enumerate(claim.lines, start=1):
            code = line.procedure_code.strip()
            if not code:
                continue  # CompletenessValidator handles required

            # Format check first
            if not _PROCEDURE_CODE_PATTERN.match(code):
                findings.append(
                    self._make_finding(
                        code="INVALID_PROCEDURE_CODE_FORMAT",
                        message=(
                            "Procedure code in 'procedure_code'"
                            " must be exactly 5 alphanumeric"
                            " characters"
                        ),
                        severity=Severity.ERROR,
                        field_name="procedure_code",
                        line_number=idx,
                        suggestion=(
                            "CPT codes are 5 digits (e.g., 99213)."
                            " HCPCS codes are letter + 4 digits"
                            " (e.g., J0120)"
                        ),
                    )
                )
                continue  # Skip table lookup if format is wrong

            # Table existence check
            if lookup_hcpcs(code) is None:
                findings.append(
                    self._make_finding(
                        code="INVALID_PROCEDURE_CODE",
                        message=(
                            "Procedure code in 'procedure_code'"
                            " not found in bundled"
                            " CPT/HCPCS table"
                        ),
                        severity=Severity.ERROR,
                        field_name="procedure_code",
                        line_number=idx,
                        suggestion=(
                            "Verify the CPT/HCPCS code against"
                            " the current code set"
                        ),
                    )
                )

    def _check_modifiers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        for idx, line in enumerate(claim.lines, start=1):
            for mod in line.modifiers:
                mod_stripped = mod.strip() if mod else ""
                if not mod_stripped:
                    continue

                if not _MODIFIER_PATTERN.match(mod_stripped):
                    findings.append(
                        self._make_finding(
                            code="INVALID_MODIFIER_FORMAT",
                            message=(
                                "Modifier in 'modifiers' must be"
                                " exactly 2 alphanumeric characters"
                            ),
                            severity=Severity.ERROR,
                            field_name="modifiers",
                            line_number=idx,
                            suggestion=(
                                "Modifiers are 2-character codes"
                                " (e.g., 25, 59, TC)"
                            ),
                        )
                    )

    def _check_diagnosis_pointers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        valid_pointers = {
            dx.pointer for dx in claim.diagnosis_codes
        }

        for idx, line in enumerate(claim.lines, start=1):
            for ptr in line.diagnosis_pointers:
                if ptr not in valid_pointers:
                    findings.append(
                        self._make_finding(
                            code="INVALID_DIAGNOSIS_POINTER",
                            message=(
                                "Diagnosis pointer in"
                                " 'diagnosis_pointers' references"
                                " a non-existent diagnosis position"
                            ),
                            severity=Severity.ERROR,
                            field_name="diagnosis_pointers",
                            line_number=idx,
                            suggestion=(
                                "Each diagnosis pointer must"
                                " reference a valid pointer value"
                                " in the claim's diagnosis codes"
                            ),
                        )
                    )

    def _check_unreferenced_diagnoses(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        # Collect all pointers referenced by any line
        referenced_pointers: set[int] = set()
        for line in claim.lines:
            referenced_pointers.update(line.diagnosis_pointers)

        # Check each diagnosis code is referenced
        for dx in claim.diagnosis_codes:
            if dx.pointer not in referenced_pointers:
                findings.append(
                    self._make_finding(
                        code="UNREFERENCED_DIAGNOSIS",
                        message=(
                            "Diagnosis code in 'diagnosis_codes'"
                            " is not referenced by any"
                            " service line"
                        ),
                        severity=Severity.WARNING,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "Each diagnosis code should be"
                            " referenced by at least one"
                            " service line via diagnosis_pointers"
                        ),
                    )
                )
```

### Key Design Decisions

- **CodingValidator** validates diagnosis codes, procedure codes, modifiers, and diagnosis pointer consistency in a single validator
- Format checks short-circuit before table lookups (avoid confusing "code not found" when format is wrong)
- `lookup_icd10()` and `lookup_hcpcs()` are used directly — they handle normalization internally
- ICD-10 format: letter + 2 digits + optional dot + optional 1-4 more characters (e.g., `A09`, `J06.9`, `S72.001A`)
- Procedure code format: exactly 5 alphanumeric characters (covers both CPT `99213` and HCPCS `J0120`)
- Modifier format: exactly 2 alphanumeric characters (e.g., `25`, `59`, `TC`)
- Diagnosis pointer validation uses a set of valid pointer values from diagnosis_codes
- Unreferenced diagnosis is `WARNING` (not `ERROR`) — some claims legitimately have diagnosis codes that don't map to specific lines
- Empty diagnosis_codes or lines silently skipped — CompletenessValidator handles required field presence
- Messages reference positions and field names, not actual code values (no PHI)

### Anti-Patterns to Avoid

- **DO NOT** include actual code values in finding messages — that could be considered PHI-adjacent
- **DO NOT** validate fields that are empty — CompletenessValidator handles that
- **DO NOT** make network calls — use bundled code tables only
- **DO NOT** store state between validate() calls
- **DO NOT** raise exceptions for validation failures — return findings
- **DO NOT** produce both FORMAT and NOT_FOUND findings for the same code — if format is wrong, skip table lookup
- **DO NOT** validate modifiers against a table — only format check (modifier tables are complex and payer-specific)
- **DO NOT** use `len(claim.diagnosis_codes)` as the valid range — use the actual `pointer` values from DiagnosisCode objects

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR11** | Validate ICD-10-CM diagnosis code format and existence against bundled code tables |
| **FR12** | Validate CPT/HCPCS procedure code format and modifier validity |
| **FR13** | Validate diagnosis pointer consistency between lines and diagnosis codes |
| **NFR1** | Rule-based latency < 50ms — code table lookups are O(1) after first load |
| **NFR8** | Zero network calls for rule-based |
| **NFR10** | No PHI in outputs — field names only in messages |
| **NFR15** | Stateless validation |
| **D10** | Dotted path: `claim_validator.validators.rule_based.coding.CodingValidator` |

### conf.py Default Validators

`CodingValidator` is already listed in `DEFAULT_RULE_VALIDATORS` in `conf.py`:
```python
"claim_validator.validators.rule_based.coding.CodingValidator",
```
No configuration changes needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.5] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR11] — ICD-10-CM code validation
- [Source: _bmad-output/planning-artifacts/prd.md#FR12] — CPT/HCPCS format + modifiers
- [Source: _bmad-output/planning-artifacts/prd.md#FR13] — Diagnosis pointer consistency
- [Source: CMS-1500 Form] — Box 21 (Diagnosis Codes), Box 24.D (Procedure Codes), Box 24.E (Diagnosis Pointers)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
N/A — no debugging issues encountered

### Completion Notes List
- RED phase: 47 tests written across 8 test classes (Valid, Diagnosis, Procedure, Modifier, Pointers, Unreferenced, Findings, Statelessness)
- GREEN phase: CodingValidator implemented with 5 private check methods
- Format checks short-circuit before table lookups (no double findings)
- ICD-10 pattern: `^[A-Za-z]\d{2}(\.\d{1,4})?$`
- Procedure code pattern: `^[A-Za-z0-9]{5}$`
- Modifier pattern: `^[A-Za-z0-9]{2}$`
- Diagnosis pointer validation uses set of valid pointer values from DiagnosisCode objects
- UNREFERENCED_DIAGNOSIS is WARNING, all others are ERROR
- No PHI in messages — uses positions and field names only
- All strings kept under 100 character line limit with implicit concatenation
- 327 tests pass (280 existing + 47 new), ruff clean, mypy clean (33 source files)

### File List
- `src/claim_validator/validators/rule_based/coding.py` — NEW: CodingValidator implementation
- `src/claim_validator/validators/rule_based/__init__.py` — MODIFIED: Added CodingValidator re-export
- `tests/test_validators/test_rule_based/test_coding.py` — NEW: 47 tests across 8 classes

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 327 tests pass, tooling clean |
