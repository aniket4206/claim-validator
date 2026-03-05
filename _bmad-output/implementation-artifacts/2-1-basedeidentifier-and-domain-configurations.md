# Story 2.1: BaseDeidentifier and Domain Configurations

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want a single `BaseDeidentifier` class with domain-specific `DeidentificationConfig`,
so that HIPAA de-identification logic is maintained in one place across all 3 domains.

## Acceptance Criteria

1. **AC-1: DeidentificationConfig frozen dataclass**
   - **Given** a `DeidentificationConfig` is created with `name_fields`, `date_fields`, `id_fields`, `address_fields`, `age_field`
   - **When** the config is inspected
   - **Then** it is immutable (frozen) and all field tuples are typed as `tuple[str, ...]`
   - **And** `age_field` is `str | None` (some domains may not have an age field)

2. **AC-2: BaseDeidentifier strips PHI per config**
   - **Given** a `BaseDeidentifier(config)` instance and an input data dict
   - **When** `deidentify(data)` is called
   - **Then** all fields listed in `name_fields` are set to `None` in the output
   - **And** all fields listed in `id_fields` are set to `None` in the output
   - **And** all fields listed in `address_fields` are set to `None` in the output
   - **And** all fields listed in `date_fields` are reduced to year-only (`int | None`)
   - **And** the field named by `age_field` (if present) is capped at 90 per HIPAA Safe Harbor (FR12)
   - **And** non-PHI fields pass through unchanged

3. **AC-3: HIPAA Safe Harbor age cap (FR12)**
   - **Given** an input record has a DOB that computes to age 92
   - **When** de-identification runs
   - **Then** the age is capped to 90

4. **AC-4: Date reduction to year-only (FR13)**
   - **Given** an input record has date fields (e.g. `"2024-03-15"`)
   - **When** de-identification runs
   - **Then** dates are reduced to year-only integers (e.g. `2024`)

5. **AC-5: Domain-specific configs cover all 3 domains**
   - **Given** `CLAIM_DEID_CONFIG`, `ELIGIBILITY_DEID_CONFIG`, and `PA_DEID_CONFIG` are defined
   - **When** each is passed to `BaseDeidentifier`
   - **Then** the correct domain-specific PHI fields are stripped
   - **And** the 18 HIPAA identifiers are covered across all 3 configs (FR10, FR11)

6. **AC-6: Backward compatibility**
   - **Given** existing domain deidentifiers are not modified
   - **When** Story 2.1 is complete
   - **Then** all 1805+ existing tests still pass
   - **And** no existing pipeline behavior changes

7. **AC-7: Cross-cutting quality**
   - All new functions pass mypy strict, ruff clean, have docstrings
   - `shared/deidentifier/__init__.py` exports `BaseDeidentifier`, `DeidentificationConfig`, and domain configs with `__all__`

## Tasks / Subtasks

- [x] Task 1: Create shared deidentifier package (AC: #7)
  - [x] 1.1: Create `src/claim_validator/shared/deidentifier/__init__.py`
  - [x] 1.2: Create `src/claim_validator/shared/deidentifier/config.py`
  - [x] 1.3: Create `src/claim_validator/shared/deidentifier/base.py`
- [x] Task 2: Implement DeidentificationConfig (AC: #1)
  - [x] 2.1: Define frozen dataclass with `name_fields: tuple[str, ...]`, `date_fields: tuple[str, ...]`, `id_fields: tuple[str, ...]`, `address_fields: tuple[str, ...]`, `age_field: str | None`
  - [x] 2.2: Validate all field tuples are properly typed for mypy strict
- [x] Task 3: Implement BaseDeidentifier core logic (AC: #2, #3, #4)
  - [x] 3.1: Implement `__init__(self, config: DeidentificationConfig)` storing config
  - [x] 3.2: Implement `deidentify(self, data: dict[str, Any]) -> dict[str, Any]` — core PHI stripping
  - [x] 3.3: Implement `_strip_names(data, fields)` — set name fields to `None`
  - [x] 3.4: Implement `_strip_ids(data, fields)` — set identifier fields to `None`
  - [x] 3.5: Implement `_strip_addresses(data, fields)` — set address fields to `None`
  - [x] 3.6: Implement `_reduce_dates(data, fields)` — convert date strings/objects to year-only `int | None`
  - [x] 3.7: Implement `_cap_age(data, age_field)` — compute age from DOB string and cap at 90 (FR12)
  - [x] 3.8: Static utility `extract_year(date_value)` — reusable date-to-year conversion
  - [x] 3.9: Static utility `compute_age(dob_str)` — reusable DOB-to-capped-age conversion
- [x] Task 4: Define domain configs (AC: #5)
  - [x] 4.1: Define `CLAIM_DEID_CONFIG` with claim-specific PHI field names
  - [x] 4.2: Define `ELIGIBILITY_DEID_CONFIG` with eligibility-specific PHI field names
  - [x] 4.3: Define `PA_DEID_CONFIG` with prior-auth-specific PHI field names
- [x] Task 5: Update package exports (AC: #7)
  - [x] 5.1: Update `shared/deidentifier/__init__.py` with re-exports and `__all__`
  - [x] 5.2: Update `shared/__init__.py` if needed
- [x] Task 6: Create tests (AC: #1, #2, #3, #4, #5, #6)
  - [x] 6.1: Create `tests/test_shared/test_deidentifier/` package
  - [x] 6.2: Create `test_config.py` — config creation, immutability, field types
  - [x] 6.3: Create `test_base.py` — name stripping, id stripping, address stripping, date reduction, age capping, non-PHI passthrough, mixed data
  - [x] 6.4: Create `test_domain_configs.py` — each domain config strips correct fields, age cap per domain, date reduction per domain, 18 HIPAA identifiers coverage
- [x] Task 7: Quality verification (AC: #6, #7)
  - [x] 7.1: Run `mypy --strict` — zero errors on all new source files
  - [x] 7.2: Run `ruff check` on ALL new files (source AND test)
  - [x] 7.3: Run `pytest tests/test_shared/test_deidentifier/` — all pass
  - [x] 7.4: Run full `pytest` — all 1805+ existing tests still pass, zero regressions

## Dev Notes

### Architecture Decision D35: Shared De-identifier (MANDATORY)

`BaseDeidentifier` implements the core 18-identifier stripping logic once. Each domain provides a `DeidentificationConfig` specifying which model fields contain which PHI types. Domain classes (`ClaimDeidentifier`, `EligibilityDeidentifier`, `PriorAuthDeidentifier`) become thin subclasses that only set their config in `__init__`, never override `deidentify()`.

**Enforcement Guideline #4:** Domain de-identifiers set config in `__init__`, never override `deidentify()`.

### Design: Dict-Based Interface

The `BaseDeidentifier.deidentify()` operates on `dict[str, Any]` (not domain Pydantic models). This keeps the shared base decoupled from domain model types. Domain subclasses (in Epic 3) will:
1. Call `input_model.model_dump()` to get a dict
2. Call `super().deidentify(data_dict)` to strip PHI
3. Construct their domain-specific output model from the cleaned dict

For Story 2.1, we test `deidentify()` with plain dicts. Domain model integration is Epic 3.

### Implementation Guide: DeidentificationConfig

```python
# shared/deidentifier/config.py
"""De-identification configuration — specifies PHI field categories per domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeidentificationConfig:
    """Immutable configuration specifying which fields contain PHI.

    Each field tuple lists the dict keys that should be stripped/transformed
    during de-identification. The base class handles stripping; domain
    subclasses only set the config.

    Attributes:
        name_fields: Fields containing person names — set to None.
        date_fields: Fields containing dates — reduced to year-only int.
        id_fields: Fields containing identifiers (SSN, member ID, etc.) — set to None.
        address_fields: Fields containing address components — set to None.
        age_field: Field containing DOB string for age computation with 90+ cap.
                   Set to None if domain has no DOB field.
    """

    name_fields: tuple[str, ...] = ()
    date_fields: tuple[str, ...] = ()
    id_fields: tuple[str, ...] = ()
    address_fields: tuple[str, ...] = ()
    age_field: str | None = None
```

### Implementation Guide: BaseDeidentifier

```python
# shared/deidentifier/base.py
"""BaseDeidentifier — HIPAA Safe Harbor de-identification engine."""

from __future__ import annotations

import datetime
from typing import Any

from claim_validator.shared.deidentifier.config import DeidentificationConfig

_SAFE_HARBOR_AGE_CAP = 90


class BaseDeidentifier:
    """Base de-identifier — strips 18 HIPAA identifiers per domain config.

    Subclasses set config in __init__(), never override deidentify().
    """

    def __init__(self, config: DeidentificationConfig) -> None:
        self._config = config

    @property
    def config(self) -> DeidentificationConfig:
        """The de-identification configuration."""
        return self._config

    def deidentify(self, data: dict[str, Any]) -> dict[str, Any]:
        """Strip PHI from a data dict per config.

        Args:
            data: Input data dict (e.g. from model_dump()).

        Returns:
            New dict with PHI fields stripped/transformed.
            Original dict is NOT mutated.
        """
        result = {**data}  # shallow copy — never mutate input

        # Strip names
        for field in self._config.name_fields:
            if field in result:
                result[field] = None

        # Strip identifiers
        for field in self._config.id_fields:
            if field in result:
                result[field] = None

        # Strip addresses
        for field in self._config.address_fields:
            if field in result:
                result[field] = None

        # Reduce dates to year-only
        for field in self._config.date_fields:
            if field in result:
                result[field] = self.extract_year(result[field])

        # Age cap from DOB
        if self._config.age_field and self._config.age_field in result:
            result[self._config.age_field] = self.compute_age(
                result[self._config.age_field]
            )

        return result

    @staticmethod
    def extract_year(date_value: str | datetime.date | None) -> int | None:
        """Extract year from a date string or date object.

        Returns None if input is None or unparseable.
        """
        if date_value is None:
            return None
        if isinstance(date_value, datetime.date):
            return date_value.year
        try:
            return datetime.date.fromisoformat(date_value).year
        except (ValueError, TypeError):
            return None

    @staticmethod
    def compute_age(dob_str: str | None) -> int | None:
        """Compute age from DOB string, capped at 90 per HIPAA Safe Harbor.

        Returns None if input is None or unparseable.
        """
        if not dob_str:
            return None
        try:
            dob = datetime.date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            return None
        today = datetime.date.today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        return min(age, _SAFE_HARBOR_AGE_CAP)
```

### Implementation Guide: Domain Configs

```python
# In shared/deidentifier/config.py (after DeidentificationConfig class)

# --- Domain Configs ---

CLAIM_DEID_CONFIG = DeidentificationConfig(
    name_fields=("patient_first_name", "patient_last_name"),
    date_fields=("service_date_from", "service_date_to"),
    id_fields=("subscriber_id",),
    address_fields=(
        "patient_address", "patient_city", "patient_state", "patient_zip",
    ),
    age_field="patient_dob",
)

ELIGIBILITY_DEID_CONFIG = DeidentificationConfig(
    name_fields=("subscriber_name",),
    date_fields=("effective_date", "termination_date"),
    id_fields=("member_id", "group_number"),
    address_fields=(),
    age_field=None,  # eligibility doesn't have DOB in response
)

PA_DEID_CONFIG = DeidentificationConfig(
    name_fields=("patient_name",),
    date_fields=("effective_date", "expiration_date"),
    id_fields=("authorization_number", "member_id"),
    address_fields=("patient_address",),
    age_field="patient_dob",
)
```

**Important:** These configs specify the TOP-LEVEL flat fields only. Nested objects (claim lines, coverage info, service line decisions) and their PHI handling are domain-specific concerns addressed in Epic 3 when domain deidentifiers are refactored to extend `BaseDeidentifier`.

### Existing Domain Deidentifiers (DO NOT MODIFY)

| Domain | File | Class | Method | Input → Output |
|--------|------|-------|--------|----------------|
| Claims | `deidentifier/deidentifier.py` | `ClaimDeidentifier` | `@classmethod deidentify(cls, claim: ClaimData) -> DeidentifiedClaim` | Strips DOB→age(cap 90), dates→year, subscriber_id dropped |
| Eligibility | `eligibility/deidentifier.py` | `EligibilityDeidentifier` | `@classmethod deidentify(cls, response) -> DeidentifiedEligibilityResponse` | Strips plan_name, group_number, dates→year, error messages |
| Prior Auth | `prior_auth/deidentifier.py` | `PriorAuthDeidentifier` | `@classmethod deidentify(cls, response) -> DeidentifiedPriorAuthResponse` | Strips auth_number, decision descriptions, dates→year, error messages |

All three use:
- `@classmethod` pattern (stateless)
- `_extract_year()` for date→year conversion
- Claims has `_compute_age()` with `_SAFE_HARBOR_AGE_CAP = 90`
- Frozen Pydantic output models with `is_deidentified -> Literal[True]` property

The new `BaseDeidentifier` follows the same logic but uses instance-based config (D35) instead of classmethods. Existing domain deidentifiers remain untouched until Epic 3.

### D43: Clean Break

- Story 2.1 ONLY creates new files in `shared/deidentifier/`
- Does NOT modify existing domain deidentifiers (`deidentifier/deidentifier.py`, `eligibility/deidentifier.py`, `prior_auth/deidentifier.py`)
- Does NOT modify existing de-identified models (`models/deidentified.py`, `eligibility/models/deidentified.py`, `prior_auth/models/deidentified.py`)
- Does NOT modify existing pipelines
- Does NOT modify `conf.py`

### Previous Story Intelligence

**Story 1.1 (shared package skeleton + core validators):**
- Pattern: pure functions → `list[Finding]`, `field_name` + `code_prefix` params, stateless
- Learnings:
  - Use `.venv/bin/python -m pytest` (NOT `.venv/bin/pytest` — stale shebang)
  - PHI-leak tests: pass actual PHI values as inputs, assert they don't appear in output
  - `from __future__ import annotations` required on ALL new files
  - D43 compliance: create new files only, leave existing code untouched

**Story 1.3 (code-table-dependent validators):**
- Import ordering: `claim_validator.constants` before `claim_validator.shared.*`
- `Callable` must be from `collections.abc` not `typing` (ruff UP035)

**Story 1.4 (validator stage registration):**
- Defensive dict copy: `kwargs = {**data_extractor(vid)}` to avoid mutating caller's dict
- Run ruff on BOTH source AND test files (code review caught missed test file linting)
- `collections.abc` sorts before `dataclasses` in imports

### What Story 2.1 Must NOT Create/Modify

- Do NOT modify existing domain deidentifiers — Epic 3 refactors them
- Do NOT modify existing de-identified Pydantic models — Epic 3
- Do NOT modify existing pipelines — Epic 2 Story 2.3 / Epic 3
- Do NOT modify `conf.py` — Epic 4
- Do NOT create `shared/pipeline/` — Story 2.3
- Do NOT create domain thin subclasses that extend BaseDeidentifier — Epic 3
- Do NOT import domain models (ClaimData, EligibilityResponse, etc.) in `shared/deidentifier/`

### Quality Requirements

- **mypy strict** — `python_version = "3.11"`, strict = true, pydantic plugin enabled
- **ruff** — line-length=100, rules E/F/I/N/W/UP; run on ALL files (source + test)
- **pytest** — all new + all existing tests must pass (1805+)
- **Docstrings** — module-level AND function-level on all public functions (NFR27)
- **Stateless** — `deidentify()` must never mutate input dict; always return a new dict
- **Thread-safe** — no shared mutable state (NFR12)

### Testing Requirements

1. **test_config.py**: `DeidentificationConfig` creation with all field categories; frozen immutability; default empty tuples; domain configs have correct fields
2. **test_base.py**: Name fields stripped to `None`; ID fields stripped to `None`; address fields stripped to `None`; date fields reduced to year-only int; DOB age cap at 90 (FR12); date reduction for ISO strings and `datetime.date` objects; `None` inputs handled gracefully; non-PHI fields pass through unchanged; `extract_year()` static method; `compute_age()` static method; original dict not mutated; empty config returns data unchanged
3. **test_domain_configs.py**: `CLAIM_DEID_CONFIG` strips subscriber_id, patient names, addresses, reduces dates, caps age; `ELIGIBILITY_DEID_CONFIG` strips subscriber_name, group_number, reduces dates; `PA_DEID_CONFIG` strips patient_name, auth_number, member_id, addresses, reduces dates, caps age; non-PHI fields survive for all 3 domains

### References

- [Source: architecture.md — D5: De-identification position, pipeline-integrated]
- [Source: architecture.md — D6: PHI boundary enforcement, type-driven + runtime]
- [Source: architecture.md — D35: Shared de-identifier base, BaseDeidentifier + DeidentificationConfig]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: architecture.md — Enforcement Guideline #4: Domain de-identifiers set config only]
- [Source: epics.md — Epic 2, Story 2.1 acceptance criteria]
- [Source: epics.md — FR10: Base de-identifier for 18 identifiers]
- [Source: epics.md — FR11: Domain-specific de-id config]
- [Source: epics.md — FR12: HIPAA Safe Harbor age cap]
- [Source: epics.md — FR13: Year-only dates for LLM]
- [Source: deidentifier/deidentifier.py — Existing ClaimDeidentifier pattern]
- [Source: eligibility/deidentifier.py — Existing EligibilityDeidentifier pattern]
- [Source: prior_auth/deidentifier.py — Existing PriorAuthDeidentifier pattern]
- [Source: 1-4-validator-stage-registration.md — Previous story learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Ruff I001: import ordering in test_base.py and test_domain_configs.py — auto-fixed with `ruff check --fix`
- Ruff F401: unused `datetime` import in test_domain_configs.py — auto-fixed with `ruff check --fix`
- Task 5.2: `shared/__init__.py` not modified — already has generic docstring, deidentifier subpackage is importable via `shared.deidentifier.*` without changes

### Completion Notes List

- Implemented `DeidentificationConfig` frozen dataclass with 5 PHI field categories (AC-1)
- Implemented `BaseDeidentifier` with dict-based `deidentify()` method — strips names, IDs, addresses, reduces dates to year-only, caps age at 90 per HIPAA Safe Harbor (AC-2, AC-3, AC-4)
- Refactored strip logic into static helper methods: `_strip_names`, `_strip_ids`, `_strip_addresses`, `_reduce_dates`, `_cap_age`
- Implemented reusable `extract_year()` and `compute_age()` static utilities
- Defined 3 domain configs: `CLAIM_DEID_CONFIG`, `ELIGIBILITY_DEID_CONFIG`, `PA_DEID_CONFIG` (AC-5)
- No existing domain deidentifiers modified — D43 clean break compliance (AC-6)
- 94 new tests across 3 test files, 1899 total tests passing, zero regressions
- mypy strict clean, ruff clean on all source + test files (AC-7)
- Code review: fixed `compute_age()` returning negative for future DOB — now returns None
- Code review: added `__post_init__` validation to `DeidentificationConfig` preventing `age_field` overlap with `date_fields`
- Code review: added 4 new tests (98 total new tests, 1903 total passing)

### File List

- `src/claim_validator/shared/deidentifier/__init__.py` — NEW: package init with re-exports and `__all__`
- `src/claim_validator/shared/deidentifier/config.py` — NEW: `DeidentificationConfig` dataclass + 3 domain configs
- `src/claim_validator/shared/deidentifier/base.py` — NEW: `BaseDeidentifier` class with PHI stripping engine
- `tests/test_shared/test_deidentifier/__init__.py` — NEW: test package init
- `tests/test_shared/test_deidentifier/test_config.py` — NEW: 28 tests for config creation, immutability, field types, overlap validation
- `tests/test_shared/test_deidentifier/test_base.py` — NEW: 39 tests for PHI stripping, age cap, date reduction, static utilities
- `tests/test_shared/test_deidentifier/test_domain_configs.py` — NEW: 31 tests for domain configs, HIPAA coverage, input immutability

### Change Log

- 2026-03-03: Implemented BaseDeidentifier and domain configurations (Story 2.1) — 3 source files, 3 test files, 94 new tests
- 2026-03-03: Code review fixes — `compute_age()` future DOB guard, `DeidentificationConfig` field overlap validation, 4 new tests (98 total)
