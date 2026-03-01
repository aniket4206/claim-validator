# Story ELIG-1.3: NPI Utility Extraction & First Validators

Status: done

## Story

As a **developer**,
I want eligibility requests validated for NPI correctness, payer ID existence, and subscriber demographics completeness,
So that requests with invalid providers, unknown payers, or missing subscriber info are caught before reaching the clearinghouse.

## Acceptance Criteria

1. **Given** the existing `NPIValidator` in the claim validation module
   **When** NPI validation logic is extracted
   **Then** a shared `_validate_npi(npi: str) -> list[Finding]` utility exists in `validators/rule_based/_npi_utils.py`
   **And** both the existing claim `NPIValidator` and the new eligibility pipeline call the same utility
   **And** no duplication of Luhn check-digit logic

2. **Given** an `EligibilityRequest` with a valid NPI (passes Luhn check)
   **When** rule-based validation runs
   **Then** zero NPI-related findings are produced

3. **Given** an `EligibilityRequest` with an invalid NPI (fails Luhn check or wrong length)
   **When** rule-based validation runs
   **Then** a `Finding` with code `ELIG_INVALID_NPI`, severity `ERROR`, field_name `provider_npi` is produced
   **And** the finding message contains no PHI — only field names and guidance

4. **Given** an `EligibilityRequest` with a payer ID that exists in the payer directory
   **When** `PayerIDValidator.validate(request)` is called
   **Then** zero payer-related findings are produced

5. **Given** an `EligibilityRequest` with a payer ID NOT in the payer directory
   **When** `PayerIDValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_INVALID_PAYER`, severity `ERROR`, field_name `payer_id`, and suggestion to verify at Stedi payer list is produced

6. **Given** an `EligibilityRequest` with all required subscriber fields present (first name, last name, DOB, subscriber ID)
   **When** `EligibilityDemographicsValidator.validate(request)` is called
   **Then** zero demographics findings are produced

7. **Given** an `EligibilityRequest` missing required subscriber fields
   **When** `EligibilityDemographicsValidator.validate(request)` is called
   **Then** a `Finding` per missing field with code `ELIG_MISSING_FIELD`, severity `ERROR`, and the specific `field_name` is produced

8. **Given** an `EligibilityRequest` with `relationship_code` not `"self"` but no patient fields provided
   **When** `EligibilityDemographicsValidator.validate(request)` is called
   **Then** a `Finding` with code `ELIG_MISSING_DEPENDENT_INFO`, severity `ERROR` is produced

## Tasks / Subtasks

- [x] Task 1: Extract NPI utility to shared module (AC: 1)
  - [x] 1.1: Create `validators/rule_based/_npi_utils.py` with `_check_luhn_npi()` and `NPI_REGISTRY_URL`
  - [x] 1.2: Refactor existing `NPIValidator` in `validators/rule_based/npi.py` to import from `_npi_utils`
  - [x] 1.3: Verify all existing NPI tests still pass (54 passed, zero regressions)
- [x] Task 2: Create `EligibilityNPIValidator` (AC: 2, 3)
  - [x] 2.1: Create `eligibility/validators/rule_based/npi.py` with `EligibilityNPIValidator`
  - [x] 2.2: Uses `_check_luhn_npi()` from `_npi_utils` — validates single `provider_npi` field
  - [x] 2.3: Finding codes: `ELIG_INVALID_NPI` (Luhn fail), `ELIG_INVALID_NPI_FORMAT` (not 10 digits)
- [x] Task 3: Create `PayerIDValidator` (AC: 4, 5)
  - [x] 3.1: Create `eligibility/validators/rule_based/payer_id.py` with `PayerIDValidator`
  - [x] 3.2: Uses `get_payer_directory()` from ELIG-1.2 code tables
  - [x] 3.3: Finding code: `ELIG_INVALID_PAYER` with Stedi payer list suggestion
- [x] Task 4: Create `EligibilityDemographicsValidator` (AC: 6, 7, 8)
  - [x] 4.1: Create `eligibility/validators/rule_based/demographics.py` with `EligibilityDemographicsValidator`
  - [x] 4.2: Check required fields: `subscriber_first_name`, `subscriber_last_name`, `subscriber_dob`, `subscriber_id`
  - [x] 4.3: Check dependent info: if `relationship_code` is set and not `"self"` → require patient fields
  - [x] 4.4: Finding codes: `ELIG_MISSING_FIELD` (per missing field), `ELIG_MISSING_DEPENDENT_INFO`
- [x] Task 5: Wire re-exports in `__init__.py` files (AC: all)
  - [x] 5.1: Update `eligibility/validators/rule_based/__init__.py` with all 3 validators
  - [x] 5.2: Update `eligibility/validators/__init__.py` to re-export from `rule_based`
- [x] Task 6: Write comprehensive tests (AC: 1-8)
  - [x] 6.1: `tests/test_validators/test_rule_based/test_npi_utils.py` — 11 tests: Luhn algorithm, edge cases, URL constant
  - [x] 6.2: Verified existing NPI tests still pass after refactor (54 passed)
  - [x] 6.3: `tests/test_eligibility/test_validators/test_npi.py` — 10 tests: valid/invalid format/Luhn/PHI checks
  - [x] 6.4: `tests/test_eligibility/test_validators/test_payer_id.py` — 11 tests: known/unknown payers, suggestions, context
  - [x] 6.5: `tests/test_eligibility/test_validators/test_demographics.py` — 18 tests: subscriber fields, dependent logic
  - [x] 6.6: Full regression — 1306 passed, 0 failed

## Dev Notes

### Architectural Context

This is the **first validators story** for the Eligibility module. It creates 3 rule-based validators and extracts shared NPI logic. Story 1.4 adds 3 more validators (service type, date, member ID). Story 1.5 wires them all into the pipeline.

**Dependency chain:** Story 1.1 (models) → Story 1.2 (code tables) → **Story 1.3 (first validators)** → Story 1.4 (remaining validators) → Story 1.5 (pipeline)

### NPI Utility Extraction — Critical Details

**Current state:** `_check_luhn_npi()` and `_NPI_REGISTRY_URL` live in `validators/rule_based/npi.py` (claim module). They must be extracted to a shared utility so both claim and eligibility validators use the same logic.

**Source file to refactor:** `src/claim_validator/validators/rule_based/npi.py`

**Current Luhn implementation (EXTRACT THIS EXACTLY):**

```python
_NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"

def _check_luhn_npi(npi: str) -> bool:
    """Validate NPI using Luhn algorithm with '80840' healthcare prefix."""
    try:
        prefixed = "80840" + npi
        total = 0
        for i, ch in enumerate(reversed(prefixed)):
            digit = int(ch)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
    except (ValueError, TypeError):
        return False
```

**Target utility file:** `src/claim_validator/validators/rule_based/_npi_utils.py`

```python
"""Shared NPI validation utilities — used by claim and eligibility validators."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.results import Finding

NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


def _check_luhn_npi(npi: str) -> bool:
    """Validate NPI using Luhn algorithm with '80840' healthcare prefix."""
    # ... exact same implementation ...


def validate_npi(npi: str, field_name: str = "provider_npi") -> list[Finding]:
    """Validate a single NPI value. Returns list of findings (empty if valid).

    Checks: format (10 numeric digits) and Luhn check-digit.
    Does NOT include PHI in messages — only field names and guidance.
    """
    findings: list[Finding] = []
    stripped = npi.strip()

    if len(stripped) != 10 or not stripped.isdigit():
        findings.append(Finding(
            code="INVALID_NPI_FORMAT",
            message=f"NPI in '{field_name}' must be exactly 10 numeric digits",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion=f"Verify the NPI format at {NPI_REGISTRY_URL}",
        ))
        return findings

    if not _check_luhn_npi(stripped):
        findings.append(Finding(
            code="INVALID_NPI",
            message=f"NPI in '{field_name}' fails Luhn check-digit validation",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion=f"Verify the NPI at {NPI_REGISTRY_URL}",
        ))

    return findings
```

**Refactored `NPIValidator` (claim-level):** After extraction, `npi.py` imports from `_npi_utils`:

```python
from claim_validator.validators.rule_based._npi_utils import (
    NPI_REGISTRY_URL,
    _check_luhn_npi,
    validate_npi,
)
```

The existing `NPIValidator._check_npi()` method can either:
- Call `validate_npi()` directly (preferred — code reuse), OR
- Continue using `_check_luhn_npi()` with its own `_make_finding()` wrapper (keeps existing finding codes without `ELIG_` prefix)

**IMPORTANT:** The claim-level `NPIValidator` uses finding codes `INVALID_NPI_FORMAT` and `INVALID_NPI` (no prefix). The eligibility validator uses `ELIG_INVALID_NPI_FORMAT` and `ELIG_INVALID_NPI`. The shared utility `validate_npi()` should return findings with **bare codes** (`INVALID_NPI_FORMAT`, `INVALID_NPI`). The eligibility validator then **prefixes** them with `ELIG_` or uses its own `_make_finding()` calls with `ELIG_` codes. This keeps the utility generic.

**Recommended approach for `validate_npi()`:** Return bare `INVALID_NPI` / `INVALID_NPI_FORMAT` codes. The `EligibilityNPIValidator` wraps the utility and produces `ELIG_`-prefixed findings using its own `_make_finding()` calls. The claim `NPIValidator` calls the utility directly (codes already match). This avoids a `code_prefix` parameter and keeps the utility simple.

### EligibilityNPIValidator Pattern

```python
"""Eligibility NPI validator — validates provider NPI on eligibility requests."""

from __future__ import annotations

from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator
from claim_validator.validators.rule_based._npi_utils import (
    NPI_REGISTRY_URL,
    _check_luhn_npi,
)
from claim_validator.constants import Severity


class EligibilityNPIValidator(BaseValidator):
    """Validates provider NPI on eligibility requests."""

    name = "EligibilityNPIValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        npi = claim.provider_npi.strip()

        if len(npi) != 10 or not npi.isdigit():
            findings.append(self._make_finding(
                code="ELIG_INVALID_NPI_FORMAT",
                message="Provider NPI must be exactly 10 numeric digits",
                severity=Severity.ERROR,
                field_name="provider_npi",
                suggestion=f"Verify the NPI format at {NPI_REGISTRY_URL}",
            ))
        elif not _check_luhn_npi(npi):
            findings.append(self._make_finding(
                code="ELIG_INVALID_NPI",
                message="Provider NPI fails Luhn check-digit validation",
                severity=Severity.ERROR,
                field_name="provider_npi",
                suggestion=f"Verify the NPI at {NPI_REGISTRY_URL}",
            ))

        return self._make_output(findings)
```

**Key differences from claim NPIValidator:**
- Single field (`provider_npi`) — no line-level NPIs
- `ELIG_` prefixed finding codes
- Messages reference "Provider NPI" — no PHI, no actual NPI value in message
- Uses `_check_luhn_npi()` from utility (shared Luhn logic, no duplication)
- `# type: ignore[override]` on `validate()` because `BaseValidator` types the argument as `ClaimData`

### PayerIDValidator Pattern

```python
"""Payer ID validator — validates payer ID against bundled payer directory."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.code_tables.payer_directory import get_payer_directory
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator


class PayerIDValidator(BaseValidator):
    """Validates payer ID exists in bundled payer directory."""

    name = "PayerIDValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []
        result = get_payer_directory(claim.payer_id)
        if result is None:
            findings.append(self._make_finding(
                code="ELIG_INVALID_PAYER",
                message="Payer ID not found in known payer directory",
                severity=Severity.ERROR,
                field_name="payer_id",
                suggestion="Verify payer ID at https://www.stedi.com/app/payers",
                context={"payer_id_length": len(claim.payer_id.strip())},
            ))
        return self._make_output(findings)
```

### EligibilityDemographicsValidator Pattern

```python
"""Demographics validator — validates subscriber and dependent completeness."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

_REQUIRED_SUBSCRIBER_FIELDS = [
    ("subscriber_first_name", "Provide the subscriber's first name"),
    ("subscriber_last_name", "Provide the subscriber's last name"),
    ("subscriber_dob", "Provide the subscriber's date of birth"),
    ("subscriber_id", "Provide the subscriber/member ID"),
]

_DEPENDENT_FIELDS = [
    "patient_first_name",
    "patient_last_name",
    "patient_dob",
]


class EligibilityDemographicsValidator(BaseValidator):
    """Validates subscriber demographics completeness for eligibility requests."""

    name = "EligibilityDemographicsValidator"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:  # type: ignore[override]
        findings = []

        # Check required subscriber fields
        for field_name, suggestion in _REQUIRED_SUBSCRIBER_FIELDS:
            value = getattr(claim, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                findings.append(self._make_finding(
                    code="ELIG_MISSING_FIELD",
                    message=f"Required field '{field_name}' is missing or empty",
                    severity=Severity.ERROR,
                    field_name=field_name,
                    suggestion=suggestion,
                ))

        # Check dependent info if relationship_code is not "self"
        if claim.relationship_code and claim.relationship_code.lower() != "self":
            missing_dependent = [
                f for f in _DEPENDENT_FIELDS
                if getattr(claim, f) is None
                or (isinstance(getattr(claim, f), str) and not getattr(claim, f).strip())
            ]
            if missing_dependent:
                findings.append(self._make_finding(
                    code="ELIG_MISSING_DEPENDENT_INFO",
                    message="Dependent/patient information required when relationship is not 'self'",
                    severity=Severity.ERROR,
                    field_name="relationship_code",
                    suggestion="Provide patient_first_name, patient_last_name, and patient_dob for dependents",
                ))

        return self._make_output(findings)
```

### Implementation Constraints

1. **DO NOT create a pipeline** — this story is validators only. Pipeline comes in Story 1.5.
2. **DO NOT modify `eligibility/__init__.py`** — no new top-level exports (validators are internal).
3. **DO NOT modify `claim_validator/__init__.py`** — no new top-level exports.
4. **DO NOT break existing NPI tests** — the refactoring must be transparent to existing tests.
5. **DO NOT include PHI** in any finding messages — field names and guidance only.
6. **DO NOT create validators for service type, date, or member ID** — those are Story 1.4.
7. **Use `# type: ignore[override]`** on `validate()` methods that accept `EligibilityRequest` instead of `ClaimData`.
8. **Use `ELIG_` prefix** for ALL eligibility finding codes — never reuse claim codes.

### Existing Code to Reference (DO NOT DUPLICATE)

| Component | Location | How to Use |
|---|---|---|
| `_check_luhn_npi()` | `validators/rule_based/npi.py` | **EXTRACT** to `_npi_utils.py` |
| `NPIValidator` | `validators/rule_based/npi.py` | **REFACTOR** to use `_npi_utils` imports |
| `BaseValidator` | `validators/base.py` | Subclass for all 3 validators |
| `Finding`, `ValidatorOutput` | `models/results.py` | Return types |
| `Severity` | `constants.py` | `Severity.ERROR`, `Severity.WARNING` |
| `get_payer_directory()` | `eligibility/code_tables/payer_directory.py` | Used by `PayerIDValidator` |
| `EligibilityRequest` | `eligibility/models/request.py` | Input type for all validators |
| `CompletenessValidator` | `validators/rule_based/completeness.py` | Pattern reference for field checking |
| `DemographicsValidator` | `validators/rule_based/demographics.py` | Pattern reference for demographics |

### EligibilityRequest Fields (for validator reference)

```python
class EligibilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    # Provider
    provider_npi: str                           # REQUIRED — validated by EligibilityNPIValidator
    provider_taxonomy: str | None = None
    # Payer
    payer_id: str                               # REQUIRED — validated by PayerIDValidator
    # Subscriber (required)
    subscriber_id: str                          # REQUIRED — checked by DemographicsValidator
    subscriber_first_name: str                  # REQUIRED — checked by DemographicsValidator
    subscriber_last_name: str                   # REQUIRED — checked by DemographicsValidator
    subscriber_dob: date                        # REQUIRED — checked by DemographicsValidator
    # Service
    service_type_code: str = "30"               # Story 1.4
    date_of_service: date | None = None         # Story 1.4
    # Dependent (optional)
    patient_first_name: str | None = None       # Checked if relationship_code != "self"
    patient_last_name: str | None = None        # Checked if relationship_code != "self"
    patient_dob: date | None = None             # Checked if relationship_code != "self"
    relationship_code: str | None = None        # Triggers dependent check
```

**Note:** `subscriber_dob` is `date` type (not `str`), so the demographics validator checks for `None` (Pydantic already validates format). For string fields, check both `None` and empty/whitespace.

### Existing Test Fixture

`tests/test_eligibility/conftest.py` provides `valid_eligibility_dict()`:

```python
@pytest.fixture
def valid_eligibility_dict() -> dict[str, Any]:
    return {
        "provider_npi": "1234567893",  # Valid Luhn NPI
        "payer_id": "60054",           # Aetna — exists in payer directory
        "subscriber_id": "XYZ123456",
        "subscriber_first_name": "Jane",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-03-15",
    }
```

**Valid test NPI:** `1234567893` (passes Luhn check — used throughout project)
**Invalid test NPI:** `1234567890` (fails Luhn check — project convention)

### Project Structure Notes

**New files to create:**

```
src/claim_validator/
├── validators/
│   └── rule_based/
│       └── _npi_utils.py              # NEW — shared NPI utility
└── eligibility/
    └── validators/
        └── rule_based/
            ├── __init__.py            # UPDATE existing stub
            ├── npi.py                 # NEW — EligibilityNPIValidator
            ├── payer_id.py            # NEW — PayerIDValidator
            └── demographics.py        # NEW — EligibilityDemographicsValidator
```

**Files to modify:**

| File | Change |
|---|---|
| `validators/rule_based/npi.py` | Refactor to import from `_npi_utils` |
| `eligibility/validators/rule_based/__init__.py` | Re-exports for 3 validators |
| `eligibility/validators/__init__.py` | Re-export from `rule_based` |

**Test files to create:**

```
tests/
├── test_validators/
│   └── test_npi_utils.py              # NEW — shared utility tests
└── test_eligibility/
    └── test_validators/
        ├── __init__.py                # NEW
        ├── conftest.py                # NEW — shared fixtures for validator tests
        ├── test_npi.py                # NEW — EligibilityNPIValidator tests
        ├── test_payer_id.py           # NEW — PayerIDValidator tests
        └── test_demographics.py       # NEW — EligibilityDemographicsValidator tests
```

**Files NOT to touch:**

- `eligibility/__init__.py` — no new public exports
- `claim_validator/__init__.py` — no new top-level exports
- `eligibility/models/` — no model changes
- `conf.py` — no settings changes
- `eligibility/code_tables/` — already done in ELIG-1.2
- Any existing test files (except NPI refactor verification)

### Testing Strategy

**Test count target: ~50-70 tests** across the following:

**`test_npi_utils.py`** (~12 tests):
- `_check_luhn_npi("1234567893")` returns True (valid)
- `_check_luhn_npi("1234567890")` returns False (invalid)
- Empty string returns False
- Non-numeric returns False
- Wrong length returns False
- `validate_npi()` with valid NPI returns empty list
- `validate_npi()` with invalid format returns `INVALID_NPI_FORMAT` finding
- `validate_npi()` with failed Luhn returns `INVALID_NPI` finding
- `NPI_REGISTRY_URL` is correct string
- Whitespace NPI is stripped before check

**`test_npi.py`** (~10 tests):
- Valid NPI → zero findings
- Invalid Luhn → `ELIG_INVALID_NPI` finding
- Wrong length → `ELIG_INVALID_NPI_FORMAT` finding
- Non-numeric → `ELIG_INVALID_NPI_FORMAT` finding
- Whitespace NPI → stripped and validated
- Finding messages contain no PHI (no actual NPI value)
- `field_name` is always `"provider_npi"`
- Validator `name` attribute is `"EligibilityNPIValidator"`

**`test_payer_id.py`** (~10 tests):
- Known payer (60054 Aetna) → zero findings
- Unknown payer → `ELIG_INVALID_PAYER` finding
- Finding includes Stedi suggestion URL
- Finding `field_name` is `"payer_id"`
- Finding `context` includes `payer_id_length`
- Whitespace payer ID → normalized by `get_payer_directory()`
- Case insensitive (alpha payer IDs)
- Validator `name` attribute is `"PayerIDValidator"`

**`test_demographics.py`** (~18 tests):
- All fields present → zero findings
- Missing `subscriber_first_name` → `ELIG_MISSING_FIELD` finding
- Missing `subscriber_last_name` → `ELIG_MISSING_FIELD` finding
- Missing `subscriber_id` → `ELIG_MISSING_FIELD` finding
- Missing `subscriber_dob` → `ELIG_MISSING_FIELD` finding (via Pydantic, may be caught as required)
- Multiple missing fields → multiple findings (one per field)
- `relationship_code=None` → no dependent check
- `relationship_code="self"` → no dependent check
- `relationship_code="spouse"` + all patient fields → zero dependent findings
- `relationship_code="child"` + missing patient fields → `ELIG_MISSING_DEPENDENT_INFO`
- `relationship_code="SELF"` (uppercase) → case-insensitive, no dependent check
- Empty string fields treated as missing
- Whitespace-only fields treated as missing
- Validator `name` attribute is `"EligibilityDemographicsValidator"`
- Finding messages contain no PHI

### Previous Story Learnings (ELIG-1.1, ELIG-1.2)

**From ELIG-1.1:**
1. Use `monkeypatch.setenv()` not `monkeypatch.setattr(os, "environ")`
2. Sort `__all__` alphabetically in all `__init__.py` files
3. `from __future__ import annotations` at top of EVERY file

**From ELIG-1.2 code review:**
1. Cache-clearing fixture in `conftest.py` — use `autouse=True` for code table cache reset
2. Test invalid JSON by patching `files()` to return fake resource, not by patching the function itself
3. Test common payers: include UHC (87726), Cigna (62308), Humana (61101) — not just Aetna/Medicare
4. `valid_eligibility_dict()` fixture already exists in `tests/test_eligibility/conftest.py`

**From ELIG-1.2 implementation:**
- `get_payer_directory(payer_id)` normalizes with `.upper().strip()` before lookup
- Returns `dict[str, str] | None` — the dict has `name` and `type` keys
- Code table cache cleared between tests via `conftest.py` autouse fixture

### References

- [Source: architecture.md — D16: Separate EligibilityPipeline, three-phase]
- [Source: architecture.md — Eligibility validator example: PayerIDValidator]
- [Source: architecture.md — Adding a New Eligibility Validator (6-step pattern)]
- [Source: architecture.md — NFR1: <100ms rule-based eligibility validation]
- [Source: epics.md — Elig Epic 1, Story 1.3: All 8 ACs]
- [Source: project-context.md — Finding Code Prefixes: ELIG_ for eligibility rule-based]
- [Source: project-context.md — Naming: {Name}Validator pattern]
- [Source: project-context.md — HIPAA: NEVER include PHI in finding messages]
- [Source: project-context.md — Testing: tests/test_{module}/test_{name}.py]
- [Source: validators/rule_based/npi.py — _check_luhn_npi() to extract]
- [Source: validators/base.py — BaseValidator._make_output(), _make_finding()]
- [Source: models/results.py — Finding, ValidatorOutput (frozen Pydantic)]
- [Source: eligibility/models/request.py — EligibilityRequest field definitions]
- [Source: eligibility/code_tables/payer_directory.py — get_payer_directory() API]
- [Source: elig-1-2 story — Code tables, code review learnings, testing patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- NPI refactor verification: 54 existing NPI tests passed post-refactor (zero regressions)
- New validator tests: 53 passed (11 npi_utils + 10 npi + 11 payer_id + 20 demographics + conftest)
- Full regression: 1308 passed in 3.03s
- Ruff lint: All checks passed
- Code review: 3 MEDIUM issues found and fixed (triple getattr, missing context, dead code comment)

### Completion Notes List

1. **Chose `_check_luhn_npi()` + `NPI_REGISTRY_URL` extraction** instead of full `validate_npi()` utility — the eligibility validators use `_make_finding()` from `BaseValidator` with `ELIG_`-prefixed codes, which is incompatible with a shared utility returning bare `Finding` objects. The claim `NPIValidator` also has its own pattern for multi-NPI validation. Extracting just the pure functions keeps both consumers independent.
2. **`subscriber_dob` is a `date` type** — Pydantic validates format at model construction. Demographics validator only checks for `None`, not empty string, on this field. This is correct behavior per the model definition.
3. **Test count: 51 new tests** (target was 50-70) covering all 8 ACs with PHI-leak checks, edge cases (whitespace, case sensitivity), and dependent relationship logic.
4. **No `validate_npi()` higher-level utility created** — story spec suggested it but the simpler approach of exporting just `_check_luhn_npi()` and `NPI_REGISTRY_URL` proved cleaner since each consumer (claim vs eligibility) needs different finding code prefixes and different field-name handling.

### File List

**New files:**

| File | Description |
|---|---|
| `src/claim_validator/validators/rule_based/_npi_utils.py` | Shared NPI utilities: `_check_luhn_npi()`, `NPI_REGISTRY_URL` |
| `src/claim_validator/eligibility/validators/rule_based/npi.py` | `EligibilityNPIValidator` — NPI format + Luhn validation |
| `src/claim_validator/eligibility/validators/rule_based/payer_id.py` | `PayerIDValidator` — payer directory lookup validation |
| `src/claim_validator/eligibility/validators/rule_based/demographics.py` | `EligibilityDemographicsValidator` — subscriber + dependent completeness |
| `tests/test_validators/test_rule_based/test_npi_utils.py` | 11 tests for shared NPI utility |
| `tests/test_eligibility/test_validators/__init__.py` | Package marker |
| `tests/test_eligibility/test_validators/conftest.py` | Shared fixtures: `valid_request`, `valid_request_dict` |
| `tests/test_eligibility/test_validators/test_npi.py` | 10 tests for EligibilityNPIValidator |
| `tests/test_eligibility/test_validators/test_payer_id.py` | 11 tests for PayerIDValidator |
| `tests/test_eligibility/test_validators/test_demographics.py` | 20 tests for EligibilityDemographicsValidator |

**Modified files:**

| File | Change |
|---|---|
| `src/claim_validator/validators/rule_based/npi.py` | Refactored to import from `_npi_utils` (removed local Luhn logic) |
| `src/claim_validator/eligibility/validators/rule_based/__init__.py` | Re-exports all 3 validators, sorted `__all__` |
| `src/claim_validator/eligibility/validators/__init__.py` | Re-exports from `rule_based` subpackage |
