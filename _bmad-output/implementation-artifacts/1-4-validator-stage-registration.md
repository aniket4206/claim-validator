# Story 1.4: Validator Stage Registration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want shared validators registerable for specific pipeline stages via configuration,
so that each domain can select which validators to run without hard-coding.

## Acceptance Criteria

1. **AC-1: Validator registry maps IDs to shared functions**
   - **Given** a shared validator registry exists
   - **When** `get_validator("npi")` is called
   - **Then** it returns the `validate_npi` function from `shared/validators/`
   - **And** all 7 shared validators are registered: npi, date, member_id, demographics, diagnosis, procedure, payer_id

2. **AC-2: Stage configuration maps stage names to validator ID lists**
   - **Given** a `StageValidatorConfig` is created with `{"rule_based": ["npi", "demographics", "diagnosis"]}`
   - **When** the stage validators are resolved
   - **Then** only the 3 specified validators are returned
   - **And** they are returned in configuration order

3. **AC-3: Domain-specific invocation parameters**
   - **Given** a `run_stage_validators()` function is called with `code_prefix="PA_"` and domain-specific field mappings
   - **When** each validator function is invoked
   - **Then** the correct `field_name` and `code_prefix` are passed through to each function
   - **And** findings are returned with domain-prefixed codes (e.g. `PA_INVALID_NPI`)

4. **AC-4: Default stage configurations per domain**
   - **Given** no explicit stage configuration is provided
   - **When** `get_default_stage_config(domain)` is called for "claim", "eligibility", or "prior_auth"
   - **Then** the default validator set for that domain is returned
   - **And** it matches the validators currently used by each domain pipeline

5. **AC-5: Backward compatibility**
   - **Given** existing domain pipelines have hardcoded validator lists
   - **When** Story 1.4 is complete
   - **Then** no existing pipeline behavior changes
   - **And** no existing tests break
   - **And** all 1760+ existing tests still pass

6. **AC-6: Cross-cutting quality**
   - All new functions pass mypy strict, ruff clean, have docstrings
   - FR9 is satisfied
   - `shared/validators/__init__.py` updated to re-export registry functions with `__all__`

## Tasks / Subtasks

- [x] Task 1: Create shared validator registry (AC: #1)
  - [x] 1.1: Create `src/claim_validator/shared/validators/registry.py`
  - [x] 1.2: Define `VALIDATORS: dict[str, ValidatorFunc]` mapping IDs → shared pure functions
  - [x] 1.3: Implement `get_validator(name: str) -> ValidatorFunc` with `KeyError` → `ConfigurationError`
  - [x] 1.4: Implement `list_validators() -> list[str]` returning all registered IDs
  - [x] 1.5: Define `ValidatorFunc` type alias for the shared function signature
- [x] Task 2: Create stage configuration model (AC: #2, #4)
  - [x] 2.1: Create `src/claim_validator/shared/validators/stage.py`
  - [x] 2.2: Define `StageValidatorConfig` frozen dataclass with `validators: tuple[str, ...]`
  - [x] 2.3: Implement `resolve_validators(config: StageValidatorConfig) -> tuple[ValidatorFunc, ...]`
  - [x] 2.4: Validate all IDs exist in registry during resolution (fail fast)
  - [x] 2.5: Define `DEFAULT_CLAIM_VALIDATORS`, `DEFAULT_ELIGIBILITY_VALIDATORS`, `DEFAULT_PA_VALIDATORS` tuples
  - [x] 2.6: Implement `get_default_stage_config(domain: str) -> StageValidatorConfig`
- [x] Task 3: Create stage runner function (AC: #3)
  - [x] 3.1: Implement `run_stage_validators(config, data_extractor, code_prefix, **kwargs) -> list[Finding]`
  - [x] 3.2: `data_extractor` is a callable that takes a validator ID and returns the function's arguments dict
  - [x] 3.3: Each validator invoked with correct `field_name` and `code_prefix`
  - [x] 3.4: Findings from all validators aggregated and returned
- [x] Task 4: Update shared validators __init__.py (AC: #6)
  - [x] 4.1: Add re-exports for `get_validator`, `list_validators`, `StageValidatorConfig`, `get_default_stage_config`, `run_stage_validators`
  - [x] 4.2: Update `__all__` list
- [x] Task 5: Create tests (AC: #1, #2, #3, #4, #5)
  - [x] 5.1: Create `tests/test_shared/test_validators/test_registry.py` — all 7 validators registered, get_validator returns correct function, unknown ID raises ConfigurationError, list_validators returns all IDs
  - [x] 5.2: Create `tests/test_shared/test_validators/test_stage.py` — StageValidatorConfig creation, resolve_validators returns correct functions in order, invalid ID fails fast, default configs per domain, run_stage_validators with code_prefix passthrough, run_stage_validators aggregates findings
- [x] Task 6: Quality verification (AC: #5, #6)
  - [x] 6.1: Run `mypy --strict` — zero errors on all new source files
  - [x] 6.2: Run `ruff check` — zero warnings
  - [x] 6.3: Run `pytest tests/test_shared/` — all pass (new + existing)
  - [x] 6.4: Verify all existing tests still pass (`pytest`) — zero regressions

## Dev Notes

### Architecture Decision D10: Validator Registry (MANDATORY)

The existing `ValidatorRegistry` (at `validators/registry.py`) uses dotted-path strings with `importlib.import_module()` to load `BaseValidator` subclasses. Story 1.4 does NOT modify that class — it creates a parallel registry specifically for shared pure functions.

The new `shared/validators/registry.py` maps short string IDs (e.g. `"npi"`, `"diagnosis"`) to the shared pure functions. This is the bridge that allows configuration-driven stage composition without requiring `BaseValidator` wrappers.

```python
# shared/validators/registry.py — NEW shared function registry
from claim_validator.shared.validators.npi import validate_npi
# etc.

VALIDATORS: dict[str, ValidatorFunc] = {
    "npi": validate_npi,
    "date": validate_date,
    # ... all 7 shared validators
}
```

### Architecture Decision D34: Shared Validator Pure Functions

All shared validators follow the same signature pattern (established in Stories 1.1 and 1.3):

```python
def validate_npi(
    value: str | None,  # or list[str] | None for diagnosis/procedure
    field_name: str = "npi",
    code_prefix: str = "",
) -> list[Finding]:
```

Story 1.4 needs a type alias to capture this:

```python
# Two signatures exist:
# Single-value: (value, field_name, code_prefix) -> list[Finding]
# Multi-value:  (codes, field_name, code_prefix) -> list[Finding]
# Demographics is special: (name, gender, dob, field_prefix, code_prefix) -> list[Finding]
```

**Important:** Demographics has a different signature (`field_prefix` instead of `field_name`, plus 3 value params). The registry must handle this — either by using `Callable[..., list[Finding]]` or by documenting the different calling conventions.

### Existing Validator Mapping Per Domain

**What validators each domain currently uses (from `conf.py`):**

| Domain | Validators | Shared Equivalent |
|--------|-----------|-------------------|
| Claims | CompletenessValidator | *(no shared equivalent — claim-specific)* |
| Claims | NPIValidator | `validate_npi` |
| Claims | SubscriberIDValidator | `validate_member_id` |
| Claims | DemographicsValidator | `validate_demographics` |
| Claims | CodingValidator | `validate_diagnosis` + `validate_procedure` |
| Claims | MonetaryValidator | *(no shared equivalent — claim-specific)* |
| Claims | DuplicateValidator | *(no shared equivalent — claim-specific)* |
| Claims | TimelyFilingValidator | *(no shared equivalent — claim-specific)* |
| Eligibility | EligibilityDateValidator | `validate_date` |
| Eligibility | EligibilityDemographicsValidator | `validate_demographics` |
| Eligibility | MemberIDValidator | `validate_member_id` |
| Eligibility | EligibilityNPIValidator | `validate_npi` |
| Eligibility | PayerIDValidator | `validate_payer_id` |
| Eligibility | ServiceTypeValidator | *(no shared equivalent)* |
| Prior Auth | PACrossFieldValidator | *(no shared equivalent — PA-specific)* |
| Prior Auth | PADateOfBirthValidator | `validate_date` |
| Prior Auth | PADiagnosisValidator | `validate_diagnosis` |
| Prior Auth | PAMemberIDValidator | `validate_member_id` |
| Prior Auth | PANPIValidator | `validate_npi` |
| Prior Auth | PAProcedureValidator | `validate_procedure` |
| Prior Auth | PAServiceDateValidator | `validate_date` |

**Default stage configs for shared validators only:**

```python
DEFAULT_CLAIM_VALIDATORS = ("npi", "member_id", "demographics", "diagnosis", "procedure")
DEFAULT_ELIGIBILITY_VALIDATORS = ("date", "demographics", "member_id", "npi", "payer_id")
DEFAULT_PA_VALIDATORS = ("date", "diagnosis", "member_id", "npi", "procedure")
```

Note: Domain-specific validators (Completeness, Monetary, Duplicate, TimelyFiling, CrossField, ServiceType) are NOT shared validators and remain in the existing `BaseValidator` class system. The defaults above cover ONLY the shared pure function validators.

### D43: Clean Break

- Story 1.4 ONLY creates new files in `shared/validators/`
- Does NOT modify `validators/registry.py` (the existing `ValidatorRegistry`)
- Does NOT modify `conf.py` — no new settings yet (Epic 4 adds workflow settings)
- Does NOT modify existing domain validators or pipelines
- Does NOT create `shared/pipeline/` or `shared/deidentifier/` — those are Epic 2

### Implementation Guide: Registry

```python
# shared/validators/registry.py
"""Shared validator registry — maps IDs to canonical pure functions."""

from __future__ import annotations

from typing import Any, Callable

from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding

# Type alias for shared validator functions
ValidatorFunc = Callable[..., list[Finding]]

VALIDATORS: dict[str, ValidatorFunc] = {}  # populated below

def _register_all() -> None:
    """Register all shared validators. Called at module load time."""
    from claim_validator.shared.validators.date import validate_date
    from claim_validator.shared.validators.demographics import validate_demographics
    from claim_validator.shared.validators.diagnosis import validate_diagnosis
    from claim_validator.shared.validators.member_id import validate_member_id
    from claim_validator.shared.validators.npi import validate_npi
    from claim_validator.shared.validators.payer_id import validate_payer_id
    from claim_validator.shared.validators.procedure import validate_procedure

    VALIDATORS.update({
        "npi": validate_npi,
        "date": validate_date,
        "member_id": validate_member_id,
        "demographics": validate_demographics,
        "diagnosis": validate_diagnosis,
        "procedure": validate_procedure,
        "payer_id": validate_payer_id,
    })

_register_all()

def get_validator(name: str) -> ValidatorFunc:
    """Look up a shared validator by ID."""
    try:
        return VALIDATORS[name]
    except KeyError:
        raise ConfigurationError(
            f"Unknown shared validator '{name}'. "
            f"Available: {', '.join(sorted(VALIDATORS))}"
        ) from None

def list_validators() -> list[str]:
    """Return all registered validator IDs."""
    return sorted(VALIDATORS.keys())
```

### Implementation Guide: Stage Configuration

```python
# shared/validators/stage.py
"""Stage-based validator configuration — maps stages to shared validator lists."""

from __future__ import annotations

from dataclasses import dataclass

from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding
from claim_validator.shared.validators.registry import (
    ValidatorFunc,
    get_validator,
)

@dataclass(frozen=True)
class StageValidatorConfig:
    """Configuration mapping a pipeline stage to shared validator IDs."""
    validators: tuple[str, ...]

    def resolve(self) -> tuple[ValidatorFunc, ...]:
        """Resolve validator IDs to functions. Raises ConfigurationError for unknown IDs."""
        return tuple(get_validator(v) for v in self.validators)

# Domain defaults — shared validators only
DEFAULT_CLAIM_VALIDATORS: tuple[str, ...] = (
    "npi", "member_id", "demographics", "diagnosis", "procedure",
)
DEFAULT_ELIGIBILITY_VALIDATORS: tuple[str, ...] = (
    "date", "demographics", "member_id", "npi", "payer_id",
)
DEFAULT_PA_VALIDATORS: tuple[str, ...] = (
    "date", "diagnosis", "member_id", "npi", "procedure",
)

_DOMAIN_DEFAULTS: dict[str, tuple[str, ...]] = {
    "claim": DEFAULT_CLAIM_VALIDATORS,
    "eligibility": DEFAULT_ELIGIBILITY_VALIDATORS,
    "prior_auth": DEFAULT_PA_VALIDATORS,
}

def get_default_stage_config(domain: str) -> StageValidatorConfig:
    """Get the default shared validator config for a domain."""
    if domain not in _DOMAIN_DEFAULTS:
        raise ConfigurationError(
            f"Unknown domain '{domain}'. Available: {', '.join(sorted(_DOMAIN_DEFAULTS))}"
        )
    return StageValidatorConfig(validators=_DOMAIN_DEFAULTS[domain])
```

### Implementation Guide: Stage Runner

```python
def run_stage_validators(
    config: StageValidatorConfig,
    data_extractor: Callable[[str], dict[str, Any]],
    code_prefix: str = "",
) -> list[Finding]:
    """Run all validators in a stage config with domain-specific parameters.

    Args:
        config: Stage configuration with validator IDs.
        data_extractor: Callable that takes a validator ID and returns
            a dict of keyword arguments for that validator function.
            Must include at minimum the value argument(s).
            field_name and code_prefix are injected automatically if not provided.
        code_prefix: Domain prefix for finding codes (e.g. "PA_").
    """
    findings: list[Finding] = []
    validators = config.resolve()
    for vid, func in zip(config.validators, validators):
        kwargs = data_extractor(vid)
        if "code_prefix" not in kwargs:
            kwargs["code_prefix"] = code_prefix
        findings.extend(func(**kwargs))
    return findings
```

### Import Pattern

All new files must use:

```python
"""Module docstring."""

from __future__ import annotations

from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding
```

The actual import of `Finding` is only needed in type annotations. Use `TYPE_CHECKING` if Finding is only used in type hints.

**NEVER import domain models** (ClaimData, EligibilityRequest, etc.) in `shared/validators/`.

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
- `typing.cast()` needed for `load_json()` returns to satisfy mypy strict
- Thread safety tests should use `threading.Lock` for shared lists

**Story 1.3 (code-table-dependent validators):**
- Created: `diagnosis.py`, `procedure.py`, `payer_id.py` in `shared/validators/`
- ICD-10 format regex was corrected from spec to accept dotless variants
- Unknown procedure codes → WARNING (not ERROR)
- Unknown payer IDs → WARNING (not ERROR)
- Learnings:
  - All finding messages must include `field_name` reference (code review caught missing one)
  - Use dynamic `_get_valid_*()` helpers in tests, not hardcoded values
  - Use clearly impossible codes for "unknown" tests (not real codes that might be added)
  - Import ordering: `claim_validator.constants` before `claim_validator.shared.*`

### What Story 1.4 Must NOT Create/Modify

- Do NOT modify `validators/registry.py` — the existing `ValidatorRegistry` for class-based validators
- Do NOT modify `conf.py` — no new settings fields yet (Epic 4 handles workflow settings)
- Do NOT modify existing domain validators or pipelines
- Do NOT create `shared/pipeline/` or `shared/deidentifier/` — Epic 2
- Do NOT create domain wrapper validators — Epic 3
- Do NOT modify `shared/validators/npi.py`, `diagnosis.py`, etc. — Stories 1.1/1.3 output is stable

### Quality Requirements

- **mypy strict** — `python_version = "3.11"`, strict = true, pydantic plugin enabled
- **ruff** — line-length=100, rules E/F/I/N/W/UP
- **pytest** — all new + all existing tests must pass (1760+)
- **Docstrings** — module-level AND function-level on all public functions (NFR27)
- **Stateless** — no shared mutable state, thread-safe by design (NFR12)

### Testing Requirements

1. **test_registry.py**: All 7 validators registered; `get_validator("npi")` returns `validate_npi` function; `get_validator("UNKNOWN")` raises `ConfigurationError`; `list_validators()` returns sorted list of 7 IDs; each registered function is callable; registry is populated at import time
2. **test_stage.py**: `StageValidatorConfig` creation with tuple of IDs; `resolve()` returns correct functions in order; `resolve()` with invalid ID raises `ConfigurationError`; `get_default_stage_config("claim")` returns correct validators; `get_default_stage_config("eligibility")` returns correct validators; `get_default_stage_config("prior_auth")` returns correct validators; `get_default_stage_config("UNKNOWN")` raises `ConfigurationError`; `run_stage_validators()` invokes validators with correct code_prefix; `run_stage_validators()` aggregates findings from all validators; empty config returns empty findings

### References

- [Source: architecture.md — D10: Validator registry, dotted-path lazy loading]
- [Source: architecture.md — D34: Shared validator consolidation, pure functions]
- [Source: architecture.md — D36: BasePipeline parameterized by PipelineConfig]
- [Source: architecture.md — D41: Domain module refactoring with PipelineConfig]
- [Source: architecture.md — D42: Configuration extension for workflow settings]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: epics.md — Story 1.4 acceptance criteria, lines 299-319]
- [Source: epics.md — FR9: Stage registration via config]
- [Source: conf.py — DEFAULT_RULE_VALIDATORS, DEFAULT_ELIG_RULE_VALIDATORS, DEFAULT_PA_RULE_VALIDATORS]
- [Source: validators/registry.py — Existing ValidatorRegistry class]
- [Source: 1-1-shared-package-skeleton-and-core-validators.md — Previous story learnings]
- [Source: 1-3-code-table-dependent-validators.md — Previous story learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Ruff UP035: `Callable` must be imported from `collections.abc` (not `typing`) — fixed in both registry.py and stage.py
- Ruff I001: `collections.abc` must sort before `dataclasses` — fixed import order in stage.py

### Completion Notes List

- Created shared validator registry (`registry.py`) with `ValidatorFunc` type alias (`Callable[..., list[Finding]]`), `VALIDATORS` dict mapping 7 IDs to shared pure functions, `get_validator()` with `ConfigurationError`, and `list_validators()`
- Created stage configuration (`stage.py`) with frozen `StageValidatorConfig` dataclass, `resolve()` method, domain defaults for claim/eligibility/prior_auth, `get_default_stage_config()`, and `run_stage_validators()` stage runner
- Updated `__init__.py` to re-export `ValidatorFunc`, `get_validator`, `list_validators`, `StageValidatorConfig`, `get_default_stage_config`, `run_stage_validators` with updated `__all__`
- Created 21 registry tests (test_registry.py) and 24 stage tests (test_stage.py) — 45 tests total, all passing
- Quality gates: mypy strict zero errors, ruff zero warnings, 1805 tests passing (45 new + 1760 existing, zero regressions)
- D43 compliance: only new files created in `shared/validators/`, no existing code modified

### File List

- `src/claim_validator/shared/validators/registry.py` — NEW
- `src/claim_validator/shared/validators/stage.py` — NEW
- `src/claim_validator/shared/validators/__init__.py` — MODIFIED (added registry/stage re-exports)
- `tests/test_shared/test_validators/test_registry.py` — NEW
- `tests/test_shared/test_validators/test_stage.py` — NEW

## Change Log

- 2026-03-03: Implemented validator stage registration (Story 1.4) — shared function registry, stage configuration model, domain defaults, stage runner, 45 tests
