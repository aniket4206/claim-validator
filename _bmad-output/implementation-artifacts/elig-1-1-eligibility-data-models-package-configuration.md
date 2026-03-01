# Story ELIG-1.1: Eligibility Data Models & Package Configuration

Status: done

## Story

As a **developer**,
I want typed Pydantic models to represent eligibility requests and responses,
So that I have a validated, immutable data layer for eligibility verification that integrates with the existing claim-validator package.

## Acceptance Criteria

1. **Given** a valid eligibility request as a Python dictionary
   **When** I construct `EligibilityRequest(**request_dict)` or `EligibilityRequest.model_validate(request_dict)`
   **Then** a frozen, immutable instance is created with all fields validated
   **And** string coercion works (e.g., `"1985-03-15"` → date)

2. **Given** an `EligibilityRequest` instance
   **When** I access its fields
   **Then** `provider_npi`, `provider_taxonomy`, `payer_id`, `subscriber_id`, `subscriber_first_name`, `subscriber_last_name`, `subscriber_dob`, `service_type_code`, and `date_of_service` are available
   **And** optional dependent fields (`patient_first_name`, `patient_last_name`, `patient_dob`, `relationship_code`) are `None` when not provided

3. **Given** the response models
   **When** I construct `EligibilityResponse`, `CoverageInfo`, `BenefitInfo`, `AAAError`
   **Then** all are frozen Pydantic models with `strict=False`
   **And** `EligibilityResponse` nests `CoverageInfo`, `list[BenefitInfo]`, `list[AAAError]`, and `raw_response: dict`

4. **Given** the `EligibilityResult` model
   **When** I inspect its fields
   **Then** it contains `eligible: bool | None`, `response: EligibilityResponse | None`, `findings: list[Finding]`, `ai_summary: str | None`, `passed: bool`, `raw_response: dict | None`, and `execution_time: float`
   **And** `passed` returns `True` only when zero ERROR-severity findings exist

5. **Given** the `CoverageStatus` enum in `eligibility/constants.py`
   **When** I import it
   **Then** it is a `StrEnum` with values `ACTIVE`, `INACTIVE`, `UNKNOWN`

6. **Given** the `exceptions.py` module
   **When** I import `ClearinghouseError`
   **Then** it is a subclass of `ClaimValidatorError`

7. **Given** the `ClaimValidatorSettings` in `conf.py`
   **When** I inspect new fields
   **Then** `stedi_api_key`, `stedi_environment`, `eligibility_rule_validators`, `skip_clearinghouse_on_rule_failure`, and `eligibility_skip_ai` are available with sensible defaults
   **And** all use `CLAIM_VALIDATOR_` env prefix

8. **Given** the `pyproject.toml`
   **When** I inspect optional extras
   **Then** a `stedi` extra exists with `httpx>=0.27`
   **And** the `all` extra includes `stedi`

## Tasks / Subtasks

- [x] Task 1: Create eligibility package directory structure with stub `__init__.py` files (AC: all)
  - [x]1.1: Create `eligibility/` subpackage with `__init__.py`
  - [x]1.2: Create `eligibility/models/` with `__init__.py`
  - [x]1.3: Create stub directories: `eligibility/validators/`, `eligibility/validators/rule_based/`, `eligibility/validators/ai/`, `eligibility/clearinghouse/`, `eligibility/code_tables/`, `eligibility/data/` — each with `__init__.py`
- [x] Task 2: Create eligibility data models (AC: 1, 2, 3, 4)
  - [x]2.1: Create `eligibility/models/request.py` — `EligibilityRequest` (flat, frozen)
  - [x]2.2: Create `eligibility/models/response.py` — `EligibilityResponse`, `CoverageInfo`, `BenefitInfo`, `AAAError` (nested, frozen)
  - [x]2.3: Create `eligibility/models/result.py` — `EligibilityResult` with `passed` property
  - [x]2.4: Create `eligibility/models/__init__.py` re-exports with sorted `__all__`
- [x] Task 3: Create CoverageStatus enum and ClearinghouseError exception (AC: 5, 6)
  - [x]3.1: Create `eligibility/constants.py` with `CoverageStatus` StrEnum
  - [x]3.2: Add `ClearinghouseError(ClaimValidatorError)` to `src/claim_validator/exceptions.py`
- [x] Task 4: Extend settings and pyproject.toml (AC: 7, 8)
  - [x]4.1: Add eligibility fields to `ClaimValidatorSettings` in `conf.py`
  - [x]4.2: Add `[stedi]` optional dependency in `pyproject.toml`, update `all` extra
- [x] Task 5: Wire up re-exports (AC: all)
  - [x]5.1: Create `eligibility/__init__.py` with model re-exports and sorted `__all__`
  - [x]5.2: Add eligibility symbols to `src/claim_validator/__init__.py` with sorted `__all__`
- [x] Task 6: Write comprehensive tests (AC: 1-8)
  - [x]6.1: Create `tests/test_eligibility/` directory structure with `conftest.py`
  - [x]6.2: `test_models/test_request.py` — dict construction, model_validate, frozen, coercion, optional fields
  - [x]6.3: `test_models/test_response.py` — all 4 response models, nesting, frozen
  - [x]6.4: `test_models/test_result.py` — `passed` property logic, default fields
  - [x]6.5: `test_imports.py` — all re-exports from `claim_validator` and `claim_validator.eligibility`
  - [x]6.6: `test_conf.py` — new settings fields, defaults, env prefix
  - [x]6.7: `test_constants.py` — CoverageStatus enum values

## Dev Notes

### Architectural Context

This is the **foundation story** for the Eligibility Verification module (v1.x). It establishes the data layer, package structure, and configuration — analogous to PA-1.1 for the Prior Authorization module. All subsequent eligibility stories (1.2-1.5) depend on these models.

**Architecture Decisions:**
- **D15:** Flat `EligibilityRequest`, nested `EligibilityResponse` — frozen=True, strict=False
- **D23:** Extend existing `ClaimValidatorSettings` with flat eligibility fields
- **D20:** `AAAError` model for 271 AAA rejection segments (dual access pattern)

**Pipeline context (for future stories — do NOT implement pipeline in this story):**
- Three-phase: rule-based → clearinghouse (Stedi 270/271) → AI interpretation
- `check_eligibility()` top-level API (Story 1.5)
- `EligibilityResult` is the pipeline output type

### Model Specifications

#### EligibilityRequest (flat, frozen)

```python
class EligibilityRequest(BaseModel):
    """Eligibility verification request."""
    model_config = ConfigDict(frozen=True, strict=False)

    # Provider
    provider_npi: str
    provider_taxonomy: str | None = None

    # Payer
    payer_id: str

    # Subscriber (required)
    subscriber_id: str
    subscriber_first_name: str
    subscriber_last_name: str
    subscriber_dob: date

    # Service
    service_type_code: str = "30"    # Default: health benefit plan coverage
    date_of_service: date | None = None

    # Dependent/Patient (optional — when patient differs from subscriber)
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: date | None = None
    relationship_code: str | None = None
```

**Key differences from `PriorAuthRequest`:**
- Flat structure (no nested `SubscriberInfo`) — simpler for the 270 transaction
- `payer_id` is required (not optional like PA)
- `service_type_code` defaults to `"30"` (health benefit plan coverage)
- No `service_lines`, `diagnosis_codes`, or `clinical_info` — those are PA-specific

#### EligibilityResponse (nested, frozen)

```python
class CoverageInfo(BaseModel):
    """Coverage details from 271 response."""
    model_config = ConfigDict(frozen=True, strict=False)

    status: CoverageStatus = CoverageStatus.UNKNOWN
    effective_date: date | None = None
    termination_date: date | None = None
    plan_name: str | None = None
    group_number: str | None = None

class BenefitInfo(BaseModel):
    """Individual benefit from 271 EB segment."""
    model_config = ConfigDict(frozen=True, strict=False)

    service_type_code: str | None = None
    service_type_name: str | None = None
    copay: float | None = None
    coinsurance: float | None = None
    deductible: float | None = None
    in_network: bool | None = None
    prior_auth_required: bool | None = None

class AAAError(BaseModel):
    """AAA rejection from 271 response."""
    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    message: str = ""

class EligibilityResponse(BaseModel):
    """Structured 271 response."""
    model_config = ConfigDict(frozen=True, strict=False)

    eligible: bool | None = None
    coverage: CoverageInfo | None = None
    benefits: list[BenefitInfo] = []
    errors: list[AAAError] = []
    raw_response: dict[str, Any] = {}
```

#### EligibilityResult (pipeline output)

```python
class EligibilityResult(BaseModel):
    """Complete result from eligibility verification pipeline."""
    model_config = ConfigDict(frozen=True, strict=False)

    eligible: bool | None = None
    response: EligibilityResponse | None = None
    findings: list[Finding] = []
    ai_summary: str | None = None
    raw_response: dict[str, Any] | None = None
    execution_time: float = 0.0

    @property
    def passed(self) -> bool:
        """True only when zero ERROR-severity findings exist."""
        return not any(f.severity == Severity.ERROR for f in self.findings)
```

**Note:** `passed` is a computed property, NOT a stored field. This matches the pattern from `PipelineResult.passed` and `PriorAuthResult.passed`.

### CoverageStatus Enum

```python
class CoverageStatus(StrEnum):
    """Coverage status from 271 eligibility response."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"
```

Place in `eligibility/constants.py` (following the PA pattern where PA-specific enums go in `prior_auth/constants.py`).

### ClearinghouseError Exception

```python
class ClearinghouseError(ClaimValidatorError):
    """Clearinghouse communication failure (HTTP errors, timeouts)."""
```

Add to `src/claim_validator/exceptions.py` AFTER `CodeTableError`. This is a cross-cutting exception used by both eligibility and PA clearinghouse integrations.

### Settings Extension

Add to `ClaimValidatorSettings` in `conf.py`:

```python
# Eligibility settings
stedi_api_key: str | None = None
stedi_environment: str = "sandbox"
eligibility_rule_validators: list[str] = []    # Empty for now — Story 1.3+ adds validators
eligibility_ai_validators: list[str] = []
skip_clearinghouse_on_rule_failure: bool = True
eligibility_skip_ai: bool = False
```

**IMPORTANT:** `eligibility_rule_validators` defaults to empty list `[]` in this story. The default validator list (`DEFAULT_ELIG_RULE_VALIDATORS`) will be added in Story 1.3 when the first validators are created. This avoids referencing validator classes that don't exist yet.

### pyproject.toml Changes

```toml
[project.optional-dependencies]
stedi = ["httpx>=0.27"]           # NEW
all = ["claim-validator[ai,stedi,server,django,fastapi]"]  # ADD stedi
```

**Note:** `httpx>=0.27` is already a dependency of the `[ai]` extra. The `[stedi]` extra makes it independently available for developers who only need clearinghouse integration without AI.

### Re-export Pattern

**`eligibility/__init__.py`** should re-export:
```python
from claim_validator.eligibility.constants import CoverageStatus
from claim_validator.eligibility.models import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResult,
)

__all__ = [
    "AAAError",
    "BenefitInfo",
    "CoverageInfo",
    "CoverageStatus",
    "EligibilityRequest",
    "EligibilityResponse",
    "EligibilityResult",
]
```

**`src/claim_validator/__init__.py`** — add eligibility imports:
```python
from claim_validator.eligibility import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    CoverageStatus,
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResult,
)
```

Also add `ClearinghouseError` to the existing exceptions import block. Update `__all__` with all new symbols in alphabetical order.

### Implementation Constraints

1. **DO NOT create validators** — this story is models + config only. Validators come in Stories 1.3-1.4.
2. **DO NOT create pipeline** — `EligibilityPipeline` comes in Story 1.5.
3. **DO NOT create code tables** — payer directory and service types come in Story 1.2.
4. **DO NOT create clearinghouse client** — `BaseClearinghouseClient` comes in Elig Epic 2.
5. **DO NOT create `_api.py`** — `check_eligibility()` comes in Story 1.5.
6. **DO NOT create `deidentified.py`** — `DeidentifiedEligibilityResponse` comes in Elig Epic 3.
7. **Stub directories only** — create `validators/`, `clearinghouse/`, `code_tables/`, `data/` with empty `__init__.py` files so the package structure is ready for future stories.

### Existing Code to Reference (DO NOT DUPLICATE)

| Component | Location | How to Use |
|---|---|---|
| `Finding` | `models/results.py` | Import in `EligibilityResult` for type hint |
| `Severity` | `constants.py` | Import in `EligibilityResult` for `passed` property |
| `ClaimValidatorError` | `exceptions.py` | Subclass for `ClearinghouseError` |
| `ClaimValidatorSettings` | `conf.py` | Extend with eligibility fields |
| `PriorAuthRequest` | `prior_auth/models/request.py` | Pattern reference for flat model style |
| `PriorAuthResponse` | `prior_auth/models/response.py` | Pattern reference for nested model style |
| `PriorAuthResult` | `prior_auth/models/result.py` | Pattern reference for `passed` property |
| `CertificationActionCode` | `prior_auth/constants.py` | Pattern reference for domain StrEnum |

### Project Structure Notes

**New files to create:**

```
src/claim_validator/eligibility/
├── __init__.py                       # Re-exports eligibility symbols
├── constants.py                      # CoverageStatus enum
├── models/
│   ├── __init__.py                   # Re-exports all eligibility models
│   ├── request.py                    # EligibilityRequest
│   ├── response.py                   # EligibilityResponse, CoverageInfo, BenefitInfo, AAAError
│   └── result.py                     # EligibilityResult
├── validators/
│   ├── __init__.py                   # Stub (populated in Story 1.3)
│   ├── rule_based/
│   │   └── __init__.py               # Stub (populated in Story 1.3)
│   └── ai/
│       └── __init__.py               # Stub (populated in Elig Epic 3)
├── clearinghouse/
│   └── __init__.py                   # Stub (populated in Elig Epic 2)
├── code_tables/
│   └── __init__.py                   # Stub (populated in Story 1.2)
└── data/
    └── __init__.py                   # Stub (populated in Story 1.2)
```

**New test files:**

```
tests/test_eligibility/
├── __init__.py
├── conftest.py                       # Shared fixtures (valid request dict, etc.)
├── test_imports.py                   # Re-export verification
├── test_conf.py                      # Settings extension tests
├── test_constants.py                 # CoverageStatus enum tests
├── test_models/
│   ├── __init__.py
│   ├── test_request.py               # EligibilityRequest tests
│   ├── test_response.py              # Response model tests (4 models)
│   └── test_result.py                # EligibilityResult + passed property
└── test_hipaa/
    └── __init__.py                   # Stub (populated in later stories)
```

**Files to modify:**

| File | Change |
|---|---|
| `src/claim_validator/exceptions.py` | Add `ClearinghouseError` class |
| `src/claim_validator/conf.py` | Add 6 eligibility settings fields |
| `src/claim_validator/__init__.py` | Add eligibility imports and `__all__` entries |
| `pyproject.toml` | Add `stedi` extra, update `all` extra |

**Files NOT to touch:**

- `src/claim_validator/constants.py` — CoverageStatus goes in `eligibility/constants.py` (PA pattern)
- `src/claim_validator/prior_auth/` — No PA changes
- `src/claim_validator/validators/` — No claim validator changes
- `src/claim_validator/models/` — No claim model changes
- Any existing test files

### Previous Story Learnings (PA-1.1 — Closest Analogue)

**Critical lessons to apply:**

1. **`from __future__ import annotations`** at the top of EVERY file (PA-1.1 review caught 2 missing instances)
2. **`ConfigDict(frozen=True, strict=False)`** on EVERY model — no exceptions
3. **Sort `__all__` alphabetically** in all `__init__.py` files (PA-1.1 review issue #1)
4. **Test `model_validate()` constructor** explicitly — it's in AC #1
5. **Test immutability (frozen)** — `with pytest.raises(ValidationError): model.field = "changed"`
6. **Test string coercion** — `"1985-03-15"` → `date(1985, 3, 15)` (AC #1)
7. **One model file per domain concept** — request.py, response.py, result.py
8. **Docstrings on all public classes**
9. **Optional fields use `str | None = None`** (not `Optional[str]`)
10. **Collections use `list[X] = []`** (not `List[X]`)
11. **Settings fields added DIRECTLY to `ClaimValidatorSettings`** — do NOT create a new settings class
12. **Create `conftest.py` for shared fixtures** — avoids duplication in later stories

### Testing Strategy

**Test count target: ~60-80 tests** across the following test classes:

**`test_request.py`** (~15 tests):
- `TestEligibilityRequest`: dict construction, model_validate, all required fields, optional fields None, frozen immutability, date string coercion, missing required field raises, invalid type raises

**`test_response.py`** (~25 tests):
- `TestCoverageInfo`: construction, frozen, default status=UNKNOWN
- `TestBenefitInfo`: all optional fields None, frozen, float types
- `TestAAAError`: required rejection_code, optional follow_up/message, frozen
- `TestEligibilityResponse`: nesting (CoverageInfo, list[BenefitInfo], list[AAAError]), raw_response dict, frozen, defaults

**`test_result.py`** (~10 tests):
- `TestEligibilityResult`: all fields, passed property (True when no ERRORs, False when ERROR exists), default values, frozen

**`test_imports.py`** (~10 tests):
- All 7 eligibility symbols importable from `claim_validator`
- All 7 symbols importable from `claim_validator.eligibility`
- `ClearinghouseError` importable from `claim_validator`

**`test_conf.py`** (~8 tests):
- New fields exist with defaults
- `stedi_api_key` defaults to None
- `stedi_environment` defaults to "sandbox"
- `eligibility_rule_validators` defaults to []
- `skip_clearinghouse_on_rule_failure` defaults to True
- `eligibility_skip_ai` defaults to False
- Env prefix works: `CLAIM_VALIDATOR_STEDI_API_KEY`

**`test_constants.py`** (~5 tests):
- `CoverageStatus` is a `StrEnum`
- Has exactly 3 members: ACTIVE, INACTIVE, UNKNOWN
- Values are lowercase strings

### Test Fixture Pattern

```python
# tests/test_eligibility/conftest.py
from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def valid_eligibility_dict() -> dict[str, Any]:
    """Minimal valid eligibility request as a plain dict."""
    return {
        "provider_npi": "1234567893",
        "payer_id": "60054",
        "subscriber_id": "XYZ123456",
        "subscriber_first_name": "Jane",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-03-15",
    }
```

**Note:** Keep fixtures minimal. Only required fields + valid NPI (`1234567893` passes Luhn). String date for coercion testing. No optional fields in the base fixture.

### References

- [Source: architecture.md — D15: Flat request, nested response]
- [Source: architecture.md — D20: AAAError dual access model]
- [Source: architecture.md — D23: Settings extension with flat fields]
- [Source: epics.md — Elig Epic 1, Story 1.1: All 8 ACs]
- [Source: epics.md — FR1-FR7: Eligibility Request Data Management]
- [Source: epics.md — FR40: EligibilityResult model]
- [Source: epics.md — FR41: Settings via CLAIM_VALIDATOR_ env prefix]
- [Source: project-context.md — Model patterns (frozen=True, strict=False)]
- [Source: project-context.md — Finding code prefixes: ELIG_, AI_ELIG_]
- [Source: project-context.md — Naming conventions]
- [Source: prior_auth/models/request.py — PriorAuthRequest pattern reference]
- [Source: prior_auth/models/response.py — PriorAuthResponse pattern reference]
- [Source: prior_auth/models/result.py — PriorAuthResult.passed property reference]
- [Source: prior_auth/constants.py — Domain StrEnum pattern reference]
- [Source: pa-1-1 story — Package scaffolding learnings, code review issues]
- [Source: pa-1-2 story — Code tables learnings]
- [Source: pa-2-2 story — Code review findings (docstring accuracy, normalization)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Session transcript available in project .claude directory

### Completion Notes List

- All 6 tasks and 18 subtasks completed
- 84 eligibility-specific tests written and passing
- Full regression suite: 1201 passed, 0 failed
- Ruff lint: all checks passed (4 initial issues fixed — import sorting, unused import, line length)
- Applied all PA-1.1 lessons: `from __future__ import annotations` in every file, sorted `__all__`, frozen models, `model_validate()` tests, string coercion tests
- `eligibility_rule_validators` defaults to `[]` (validators not yet created — Story 1.3)
- `eligibility_ai_validators` added as additional settings field beyond spec (mirrors PA pattern)
- Stub directories created for validators/, clearinghouse/, code_tables/, data/ — ready for future stories

### File List

**New source files (12):**
- `src/claim_validator/eligibility/__init__.py` — re-exports all eligibility symbols
- `src/claim_validator/eligibility/constants.py` — CoverageStatus StrEnum
- `src/claim_validator/eligibility/models/__init__.py` — model re-exports
- `src/claim_validator/eligibility/models/request.py` — EligibilityRequest
- `src/claim_validator/eligibility/models/response.py` — CoverageInfo, BenefitInfo, AAAError, EligibilityResponse
- `src/claim_validator/eligibility/models/result.py` — EligibilityResult with passed property
- `src/claim_validator/eligibility/validators/__init__.py` — stub
- `src/claim_validator/eligibility/validators/rule_based/__init__.py` — stub
- `src/claim_validator/eligibility/validators/ai/__init__.py` — stub
- `src/claim_validator/eligibility/clearinghouse/__init__.py` — stub
- `src/claim_validator/eligibility/code_tables/__init__.py` — stub
- `src/claim_validator/eligibility/data/__init__.py` — stub

**Modified source files (4):**
- `src/claim_validator/__init__.py` — added eligibility imports + ClearinghouseError
- `src/claim_validator/exceptions.py` — added ClearinghouseError class
- `src/claim_validator/conf.py` — added 6 eligibility settings fields
- `pyproject.toml` — added [stedi] extra, updated [all]

**New test files (10):**
- `tests/test_eligibility/__init__.py`
- `tests/test_eligibility/conftest.py` — valid_eligibility_dict fixture
- `tests/test_eligibility/test_constants.py` — 7 tests
- `tests/test_eligibility/test_conf.py` — 8 tests
- `tests/test_eligibility/test_imports.py` — 22 tests
- `tests/test_eligibility/test_models/__init__.py`
- `tests/test_eligibility/test_models/test_request.py` — 18 tests
- `tests/test_eligibility/test_models/test_response.py` — 24 tests (CoverageInfo, BenefitInfo, AAAError, EligibilityResponse)
- `tests/test_eligibility/test_models/test_result.py` — 8 tests (defaults, passed property)
- `tests/test_eligibility/test_hipaa/__init__.py` — stub

## Senior Developer Code Review

**Reviewer:** Claude Opus 4.6 | **Date:** 2026-03-01 | **Outcome:** APPROVED

| # | Severity | File:Line | Issue | Resolution |
|---|----------|-----------|-------|------------|
| 1 | MEDIUM | `test_conf.py:39` | `monkeypatch.setattr(os, "environ")` replaces entire dict object — `monkeypatch.setenv()` is safer | **FIXED** — replaced with `monkeypatch.setenv()` calls |
| 2 | MEDIUM | `test_response.py` | Missing `model_validate()` tests for response models | Non-blocking — AC 1 only requires request model |
| 3 | MEDIUM | `conf.py:61` | `skip_clearinghouse_on_rule_failure` not namespaced — inconsistent with `eligibility_*` pattern | **FIXED** — renamed to `skip_clearinghouse_on_eligibility_failure` |
| 4 | LOW | `test_conf.py:35` | `monkeypatch` typed as `object` not `pytest.MonkeyPatch` | **FIXED** — updated type annotation as part of fix #1 |
| 5 | LOW | `test_request.py` | No test for extra/unknown fields behavior | Non-blocking |
| 6 | LOW | `test_conf.py:41-46` | `test_env_prefix` only tests 2 of 6 settings via env vars | Non-blocking |

**Post-fix verification:** 1201 tests passed, ruff clean.
