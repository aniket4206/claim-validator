# Story 1.2: Claim Data Models

Status: ready-for-dev

## Story

As a **developer**,
I want typed Pydantic models to represent healthcare claims,
so that I have a validated, framework-agnostic data layer for CMS-1500 claims.

## Acceptance Criteria

1. **Given** a valid claim as a Python dictionary, **When** I construct `ClaimData(**claim_dict)` or `ClaimData.model_validate(claim_dict)`, **Then** a frozen, immutable `ClaimData` instance is created with all fields validated, and string-to-number coercion works (e.g., `"150.00"` -> `float`).

2. **Given** a `ClaimData` instance, **When** I access `claim.lines`, **Then** I receive a sequence of `ClaimLineData` objects, each with `procedure_code`, `modifiers`, `diagnosis_pointers`, and `charge_amount` fields.

3. **Given** a `ClaimData` instance, **When** I access `claim.diagnosis_codes`, **Then** I receive a sequence of `DiagnosisCode` objects, each with `code`, pointer position, and `type`.

4. **Given** a `ClaimData` instance, **When** I attempt to modify any field (e.g., `claim.billing_provider_npi = "new"`), **Then** a `ValidationError` is raised because the model is frozen.

5. **Given** the constants module, **When** I import `Severity`, `ClaimType`, **Then** they are `StrEnum` types with values `Severity.ERROR`, `Severity.WARNING` and `ClaimType.PROFESSIONAL`, `ClaimType.INSTITUTIONAL`.

6. **Given** the exceptions module, **When** I import exception classes, **Then** `ClaimValidatorError` is the base, with `ValidationError`, `ConfigurationError`, `LLMError`, and `CodeTableError` as subclasses.

## Tasks / Subtasks

- [ ] Task 1: Implement constants module (AC: #5)
  - [ ] Create `Severity` StrEnum with `ERROR` and `WARNING` values
  - [ ] Create `ClaimType` StrEnum with `PROFESSIONAL` and `INSTITUTIONAL` values
  - [ ] Export from `constants.py`
- [ ] Task 2: Implement exceptions module (AC: #6)
  - [ ] Create `ClaimValidatorError(Exception)` base class
  - [ ] Create `ValidationError(ClaimValidatorError)`
  - [ ] Create `ConfigurationError(ClaimValidatorError)`
  - [ ] Create `LLMError(ClaimValidatorError)`
  - [ ] Create `CodeTableError(ClaimValidatorError)`
- [ ] Task 3: Implement DiagnosisCode model (AC: #3)
  - [ ] Create frozen Pydantic model with `code: str`, `pointer: int`, `type: str` fields
  - [ ] Use `strict=False` for lax coercion
- [ ] Task 4: Implement ClaimLineData model (AC: #2)
  - [ ] Create frozen Pydantic model with `procedure_code`, `modifiers`, `diagnosis_pointers`, `charge_amount`, `service_date_from`, `service_date_to`, `place_of_service`, `units`
  - [ ] Ensure `charge_amount` coerces strings to float (strict=False)
  - [ ] `modifiers` defaults to empty list, `diagnosis_pointers` defaults to empty list
- [ ] Task 5: Implement ClaimData model (AC: #1, #4)
  - [ ] Create frozen Pydantic model with all CMS-1500 claim-level fields
  - [ ] Include `lines: list[ClaimLineData]`, `diagnosis_codes: list[DiagnosisCode]`
  - [ ] Include billing/rendering provider NPIs, subscriber fields, patient demographics, payer info
  - [ ] Ensure frozen immutability raises on field modification
  - [ ] Ensure dict input works via `model_validate()`
- [ ] Task 6: Wire up re-exports (AC: all)
  - [ ] Export all models from `models/__init__.py`
  - [ ] Add `Severity`, `ClaimType`, exceptions, and models to `claim_validator/__init__.py` `__all__`
- [ ] Task 7: Write tests (AC: all)
  - [ ] `tests/test_models/test_claim.py` — ClaimData, ClaimLineData, DiagnosisCode construction, frozen behavior, coercion
  - [ ] `tests/test_constants.py` — StrEnum values
  - [ ] `tests/test_exceptions.py` — exception hierarchy
  - [ ] Update `tests/conftest.py` with `valid_claim_dict` fixture
- [ ] Task 8: Verify tooling (AC: all)
  - [ ] `uv run ruff check .` — zero warnings
  - [ ] `uv run mypy src/` — zero errors
  - [ ] `uv run pytest` — all tests pass

## Dev Notes

### Project Location

The `claim-validator` library lives at `/home/lnv-20/Documents/claude/claim-validator/` (sibling to the Django project). All files in this story are within that directory.

### Previous Story Intelligence (Story 1.1)

- Project initialized with `uv init --lib --build-backend hatchling`
- Placeholder files already exist at the target locations — **edit them, do not create new files**
- hatch-vcs auto-generates `_version.py` — excluded from ruff/mypy in pyproject.toml
- All tooling passes: ruff, mypy strict, pytest
- `pydantic>=2.0,<3.0` already in dependencies
- Empty `__init__.py` files exist in all subpackages

### Pydantic Model Design (Architecture Decision D3)

All models MUST use `frozen=True` and `strict=False`:

```python
from pydantic import BaseModel

class DiagnosisCode(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    code: str
    pointer: int
    type: str = "principal"  # "principal" or "other"
```

**Why frozen=True:** Immutability guarantees thread-safe claims. Validators cannot accidentally modify claim data.

**Why strict=False:** Lax coercion means `ClaimData(charge_amount="150.00")` works — critical for dict-based input DX where users may pass strings from JSON/databases.

### CMS-1500 Field Reference

The `ClaimData` model represents a CMS-1500 professional claim. Key fields to include:

**Claim-Level Fields:**
| Field | Type | Required | CMS-1500 Box | Notes |
|---|---|---|---|---|
| `billing_provider_npi` | `str` | Yes | 33a | 10-digit NPI |
| `billing_provider_taxonomy` | `str \| None` | No | 33b | Taxonomy code |
| `rendering_provider_npi` | `str \| None` | No | 24J | If different from billing |
| `subscriber_id` | `str` | Yes | 1a | Insurance member ID |
| `subscriber_first_name` | `str \| None` | No | 4 | PHI — field name only in findings |
| `subscriber_last_name` | `str \| None` | No | 4 | PHI |
| `subscriber_dob` | `str \| None` | No | — | PHI — ISO format date string |
| `subscriber_gender` | `str \| None` | No | — | M/F/U |
| `patient_first_name` | `str \| None` | No | 2 | PHI |
| `patient_last_name` | `str \| None` | No | 2 | PHI |
| `patient_dob` | `str \| None` | No | 3 | PHI — ISO format |
| `patient_gender` | `str \| None` | No | 3 | M/F/U |
| `patient_relationship` | `str \| None` | No | 6 | self/spouse/child/other |
| `payer_id` | `str \| None` | No | — | Payer identifier |
| `payer_name` | `str \| None` | No | 11c | Payer name |
| `claim_type` | `str` | No | — | "professional" default |
| `place_of_service` | `str \| None` | No | 24B | POS code (e.g., "11") |
| `total_charge` | `float \| None` | No | 28 | Claim total |
| `filing_date` | `str \| None` | No | — | Date claim is submitted |
| `diagnosis_codes` | `list[DiagnosisCode]` | Yes | 21 | At least 1 required |
| `lines` | `list[ClaimLineData]` | Yes | 24 | At least 1 required |

**Line-Level Fields (ClaimLineData):**
| Field | Type | Required | CMS-1500 Box | Notes |
|---|---|---|---|---|
| `procedure_code` | `str` | Yes | 24D | CPT/HCPCS code |
| `modifiers` | `list[str]` | No | 24D | Up to 4 modifiers |
| `diagnosis_pointers` | `list[int]` | Yes | 24E | 1-based pointers to diagnosis_codes |
| `charge_amount` | `float` | Yes | 24F | Must coerce from string |
| `units` | `float` | No | 24G | Default 1.0 |
| `service_date_from` | `str \| None` | No | 24A | ISO date string |
| `service_date_to` | `str \| None` | No | 24A | ISO date string |
| `place_of_service` | `str \| None` | No | 24B | Overrides claim-level POS |
| `rendering_provider_npi` | `str \| None` | No | 24J | Line-level rendering NPI |

### Implementation Pattern — Use `str` for Dates, Not `date` Objects

Use `str | None` for all date fields (DOB, service dates, filing date), NOT `datetime.date`. Rationale:
- Dict input from JSON/databases often has dates as strings
- Validators (Story 2.7) will parse and check date consistency
- Keeps the model simple — no import-time date parsing complexity
- Format validation happens in validators, not in the model

### Constants StrEnum Pattern

```python
from enum import StrEnum

class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"

class ClaimType(StrEnum):
    PROFESSIONAL = "professional"
    INSTITUTIONAL = "institutional"
```

Use `StrEnum` (Python 3.11+) — not Django `TextChoices`, not plain strings.

### Exception Hierarchy Pattern

```python
class ClaimValidatorError(Exception):
    """Base exception for claim-validator library."""

class ValidationError(ClaimValidatorError):
    """Invalid input data (malformed claim, missing required fields)."""

class ConfigurationError(ClaimValidatorError):
    """Invalid library configuration (bad validator path, missing provider)."""

class LLMError(ClaimValidatorError):
    """LLM provider communication failure."""

class CodeTableError(ClaimValidatorError):
    """Code table loading or lookup failure."""
```

All exceptions are simple — no custom `__init__` needed. Keep them as one-liners with docstrings.

### Re-Export Pattern for `__init__.py`

After implementation, `models/__init__.py` should re-export:
```python
from claim_validator.models.claim import ClaimData, ClaimLineData, DiagnosisCode
```

And `claim_validator/__init__.py` should add to its imports and `__all__`:
```python
from claim_validator.constants import ClaimType, Severity
from claim_validator.exceptions import (
    ClaimValidatorError,
    CodeTableError,
    ConfigurationError,
    LLMError,
    ValidationError,
)
from claim_validator.models import ClaimData, ClaimLineData, DiagnosisCode
```

### Test Fixture — `valid_claim_dict`

Add this to `tests/conftest.py` for reuse across all future test files:

```python
@pytest.fixture
def valid_claim_dict() -> dict:
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
            },
        ],
    }
```

Use NPI `1234567893` (valid Luhn) in all test fixtures.

### Anti-Patterns to Avoid

- **DO NOT** use `datetime.date` for date fields — use `str | None`
- **DO NOT** add validators (field_validator, model_validator) to ClaimData — keep the model as a pure data container. Validation logic lives in validator classes (Epic 2)
- **DO NOT** make any field `Required` that isn't universally needed — validators check completeness, the model allows partial claims
- **DO NOT** add PHI values in test assertions or test output — use field names only
- **DO NOT** import from Django — this is a standalone library
- **DO NOT** add `__init__` methods to Pydantic models — use `model_config = ConfigDict(...)` pattern
- **DO NOT** name the exception `ValidationError` without being careful — Pydantic also has `ValidationError`. Import as `from claim_validator.exceptions import ValidationError as ClaimValidationError` in test files if needed, or ensure no collision

### Naming Note on ValidationError

Both Pydantic and this library define `ValidationError`. In the library code this is fine — they live in different modules. In tests, be careful:
- `pydantic.ValidationError` — raised by Pydantic when model construction fails (e.g., wrong types)
- `claim_validator.exceptions.ValidationError` — raised by the library for invalid input before validation runs

The AC #4 test ("frozen model raises ValidationError") will raise **Pydantic's** `ValidationError`, not ours. Test should import `pydantic.ValidationError` for that assertion.

### Architecture Compliance

| Decision | Requirement for This Story |
|---|---|
| **D3: Pydantic models** | `frozen=True`, `strict=False` on all models |
| **D13: Import/export** | Re-export from `models/__init__.py` and top-level `__init__.py` |
| **Naming** | Models: `ClaimData`, `ClaimLineData`, `DiagnosisCode`. Enums: `Severity`, `ClaimType`. Exceptions: `{Name}Error` |
| **One file per domain** | `claim.py` for claim models, `constants.py` for enums, `exceptions.py` for errors |
| **PHI safety** | No PHI values in test fixtures beyond field names. Use `"1234567893"` for NPI, `"XYZ123456"` for subscriber ID |

### File Targets

| File | Action | Contents |
|---|---|---|
| `src/claim_validator/constants.py` | Edit (exists, placeholder) | `Severity`, `ClaimType` StrEnums |
| `src/claim_validator/exceptions.py` | Edit (exists, placeholder) | Exception hierarchy |
| `src/claim_validator/models/claim.py` | Edit (exists, placeholder) | `DiagnosisCode`, `ClaimLineData`, `ClaimData` |
| `src/claim_validator/models/__init__.py` | Edit (exists, empty) | Re-exports |
| `src/claim_validator/__init__.py` | Edit (exists) | Add new exports to `__all__` |
| `tests/conftest.py` | Edit (exists, placeholder) | `valid_claim_dict` fixture |
| `tests/test_models/test_claim.py` | Create | Model tests |
| `tests/test_constants.py` | Create | Enum tests |
| `tests/test_exceptions.py` | Create | Exception tests |

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions] — D3: frozen=True, strict=False
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] — Model naming, constant naming, exception naming
- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns] — Exception hierarchy, Finding format
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns] — models/ directory, constants.py, exceptions.py
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/prd.md#Data Models & Input] — FR34-FR37

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
