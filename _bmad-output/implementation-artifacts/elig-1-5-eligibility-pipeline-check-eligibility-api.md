# Story ELIG-1.5: Eligibility Pipeline & check_eligibility() API

Status: done

## Story

As a **developer**,
I want to call `check_eligibility()` as a single entry point that runs all rule-based validators and returns a structured result,
so that I can validate eligibility requests with one function call, zero configuration, and zero network access.

## Acceptance Criteria

1. **Given** a valid eligibility request dictionary, **when** I call `check_eligibility(request_dict)`, **then** an `EligibilityResult` is returned with `passed=True`, empty findings list, and `eligible=None` (no clearinghouse call), and the call requires zero configuration, zero API keys, and zero network calls.
2. **Given** an eligibility request with multiple validation issues, **when** I call `check_eligibility(request_dict)`, **then** all 6 rule-based validators run (NPI, payer ID, demographics, service type, date, member ID) and findings are aggregated into a single `EligibilityResult` ordered by severity.
3. **Given** an `EligibilityRequest` Pydantic model instance, **when** I call `check_eligibility(request_model)`, **then** it accepts both dict and Pydantic model input seamlessly.
4. **Given** `skip_clearinghouse_on_eligibility_failure=True` (default) and rule-based validation failed, **when** the pipeline finishes phase 1, **then** the pipeline returns immediately without attempting clearinghouse or AI phases.
5. **Given** custom validator configuration, **when** I call `check_eligibility(request, settings=ClaimValidatorSettings(eligibility_rule_validators=[...]))`, **then** only the configured validators execute.
6. **Given** a developer importing from the package, **when** they write `from claim_validator import check_eligibility`, **then** the import succeeds and `check_eligibility` is available at the top level, and `EligibilityRequest`, `EligibilityResponse`, `EligibilityResult` are also importable from `claim_validator`.
7. **Given** rule-based validation on a typical eligibility request, **when** I measure execution time, **then** it completes in under 100ms.
8. **Given** a custom validator subclassing `BaseValidator`, **when** registered via dotted-path in `eligibility_rule_validators` settings, **then** it integrates into the eligibility pipeline and receives `EligibilityRequest` data.

## Tasks / Subtasks

- [x] Task 1: Add `DEFAULT_ELIG_RULE_VALIDATORS` constant to `conf.py` and wire it into `ClaimValidatorSettings` (AC: #1, #5, #8)
  - [x] 1.1: Define `DEFAULT_ELIG_RULE_VALIDATORS` list with all 6 validator dotted paths (NPI, payer ID, demographics, service type, date, member ID)
  - [x] 1.2: Update `eligibility_rule_validators` field default from `[]` to `DEFAULT_ELIG_RULE_VALIDATORS`

- [x] Task 2: Create `EligibilityPipeline` class in `eligibility/pipeline.py` (AC: #1, #2, #4, #7, #8)
  - [x] 2.1: `__init__(*, rule_validators: list[BaseValidator])` — stores validator list
  - [x] 2.2: `from_settings(settings=None) -> EligibilityPipeline` — factory using `ValidatorRegistry` and `settings.eligibility_rule_validators`
  - [x] 2.3: `run(request: EligibilityRequest) -> EligibilityResult` — iterate validators, collect findings, wrap in `EligibilityResult` with `execution_time`
  - [x] 2.4: Exception handling per validator — catch exceptions, emit `VALIDATOR_ERROR` finding

- [x] Task 3: Create `check_eligibility()` function in `eligibility/_api.py` (AC: #1, #3, #5)
  - [x] 3.1: Accept `dict[str, Any] | EligibilityRequest` input with `settings` kwarg
  - [x] 3.2: Dict → `EligibilityRequest(**request)`, model → pass through, else `ValueError`
  - [x] 3.3: Create pipeline via `EligibilityPipeline.from_settings(settings)`, call `run()`

- [x] Task 4: Update exports (AC: #6)
  - [x] 4.1: Add `EligibilityPipeline` and `check_eligibility` to `eligibility/__init__.py` and `__all__`
  - [x] 4.2: Add `check_eligibility` and `EligibilityPipeline` to top-level `claim_validator/__init__.py` and `__all__`

- [x] Task 5: Write tests in `tests/test_eligibility/test_pipeline.py` (AC: #1–#8)
  - [x] 5.1: Valid request → `passed=True`, zero findings, `eligible=None`
  - [x] 5.2: Dict input accepted
  - [x] 5.3: Pydantic model input accepted
  - [x] 5.4: Invalid input type → `ValueError`
  - [x] 5.5: Request with validation errors → all 6 validators run, findings aggregated
  - [x] 5.6: Custom settings with subset of validators
  - [x] 5.7: Custom settings with empty validators list
  - [x] 5.8: `execution_time > 0`
  - [x] 5.9: Performance test: < 100ms
  - [x] 5.10: Validator exception → `VALIDATOR_ERROR` finding (not crash)
  - [x] 5.11: Top-level import works: `from claim_validator import check_eligibility`
  - [x] 5.12: `EligibilityPipeline` importable from `claim_validator.eligibility`

- [x] Task 6: Run full test suite and linting (AC: all)
  - [x] 6.1: `pytest tests/test_eligibility/test_pipeline.py` — all pass (23/23)
  - [x] 6.2: Full regression `pytest` — no regressions (1377/1377)
  - [x] 6.3: `ruff check` — clean (0 errors on changed files)

## Dev Notes

### Architecture — Direct Analog: `PriorAuthPipeline`

The `EligibilityPipeline` follows the **exact same pattern** as `PriorAuthPipeline` (Phase 1 only for this story). Key structural parallels:

| Component | Prior Auth (reference) | Eligibility (to build) |
|---|---|---|
| Pipeline | `prior_auth/pipeline.py` → `PriorAuthPipeline` | `eligibility/pipeline.py` → `EligibilityPipeline` |
| API function | `prior_auth/_api.py` → `submit_prior_auth()` | `eligibility/_api.py` → `check_eligibility()` |
| Request model | `PriorAuthRequest` | `EligibilityRequest` (exists) |
| Result model | `PriorAuthResult` | `EligibilityResult` (exists) |
| Settings field | `pa_rule_validators` | `eligibility_rule_validators` (exists, needs default) |
| Default validators | `DEFAULT_PA_RULE_VALIDATORS` (7 validators) | `DEFAULT_ELIG_RULE_VALIDATORS` (6 validators, to create) |

### The 6 Default Eligibility Validators (dotted paths)

```python
DEFAULT_ELIG_RULE_VALIDATORS: list[str] = [
    "claim_validator.eligibility.validators.rule_based.date.EligibilityDateValidator",
    "claim_validator.eligibility.validators.rule_based.demographics.EligibilityDemographicsValidator",
    "claim_validator.eligibility.validators.rule_based.member_id.MemberIDValidator",
    "claim_validator.eligibility.validators.rule_based.npi.EligibilityNPIValidator",
    "claim_validator.eligibility.validators.rule_based.payer_id.PayerIDValidator",
    "claim_validator.eligibility.validators.rule_based.service_type.ServiceTypeValidator",
]
```

### Pipeline Pattern

```python
# From PriorAuthPipeline — follow this exactly
class EligibilityPipeline:
    def __init__(self, *, rule_validators: list[BaseValidator]) -> None: ...
    @classmethod
    def from_settings(cls, settings=None) -> EligibilityPipeline: ...
    def run(self, request: EligibilityRequest) -> EligibilityResult: ...
```

Key implementation details from PA pipeline:
- Use `time.perf_counter()` for `execution_time`
- Wrap each validator in try/except, emit `VALIDATOR_ERROR` finding on exception
- `from_settings()` uses `ValidatorRegistry().create_validators(settings.eligibility_rule_validators)`
- Phase 1 only — docstring notes Phases 2 (clearinghouse) and 3 (AI) as future

### API Function Pattern

```python
# From submit_prior_auth() — follow this exactly
def check_eligibility(
    request: dict[str, Any] | EligibilityRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
) -> EligibilityResult:
    if isinstance(request, dict):
        request_model = EligibilityRequest(**request)
    elif isinstance(request, EligibilityRequest):
        request_model = request
    else:
        raise ValueError(...)
    pipeline = EligibilityPipeline.from_settings(settings)
    return pipeline.run(request_model)
```

### Test Fixtures

The existing `tests/test_eligibility/test_validators/conftest.py` has `valid_request` and `valid_request_dict` fixtures. The pipeline tests need a **fully valid request** (with `date_of_service` and `service_type_code`) since `valid_request` fixture omits `date_of_service` (triggers `ELIG_MISSING_DATE`). Create pipeline-specific fixtures in `tests/test_eligibility/test_pipeline.py` or a new conftest.

```python
# Fully valid request — no findings expected
{
    "provider_npi": "1234567893",
    "payer_id": "60054",
    "subscriber_id": "XYZ123456",
    "subscriber_first_name": "Jane",
    "subscriber_last_name": "Doe",
    "subscriber_dob": "1985-03-15",
    "date_of_service": datetime.date.today(),
    "service_type_code": "30",
}
```

### Learnings from Previous Stories

- All eligibility validators use `# type: ignore[override]` on `validate()` since they accept `EligibilityRequest` instead of `ClaimData`
- Finding `context` dicts are required — established pattern (ELIG-1.4 code review)
- Finding code prefix: `ELIG_` for rule-based, `VALIDATOR_ERROR` for pipeline-level errors
- `EligibilityResult` is frozen (`ConfigDict(frozen=True)`) — no mutation after creation
- All line lengths must stay ≤100 chars (ruff E501)

### Project Structure Notes

- New files follow `eligibility/` module layout matching `prior_auth/` structure
- `EligibilityPipeline` in `eligibility/pipeline.py` (mirrors `prior_auth/pipeline.py`)
- `check_eligibility()` in `eligibility/_api.py` (mirrors `prior_auth/_api.py`)
- Tests in `tests/test_eligibility/test_pipeline.py`
- No new test conftest needed if pipeline test creates its own fixtures

### References

- [Source: src/claim_validator/prior_auth/pipeline.py] — PriorAuthPipeline (direct structural analog)
- [Source: src/claim_validator/prior_auth/_api.py] — submit_prior_auth() (direct API analog)
- [Source: src/claim_validator/conf.py] — ClaimValidatorSettings, DEFAULT_PA_RULE_VALIDATORS pattern
- [Source: src/claim_validator/eligibility/models/result.py] — EligibilityResult (exists, no changes needed)
- [Source: src/claim_validator/eligibility/models/request.py] — EligibilityRequest (exists, no changes needed)
- [Source: src/claim_validator/validators/registry.py] — ValidatorRegistry.create_validators()
- [Source: src/claim_validator/eligibility/validators/rule_based/__init__.py] — All 6 validators
- [Source: src/claim_validator/eligibility/__init__.py] — Current exports (needs EligibilityPipeline, check_eligibility)
- [Source: src/claim_validator/__init__.py] — Top-level exports (needs check_eligibility, EligibilityPipeline)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5] — Acceptance criteria

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Pre-existing test `test_eligibility_rule_validators_default_empty` expected empty default; updated to `test_eligibility_rule_validators_default_six` to reflect new `DEFAULT_ELIG_RULE_VALIDATORS`
- Demographics validator uses `ELIG_MISSING_FIELD` code (not `ELIG_DEMO*`); adjusted test assertion accordingly
- Ruff auto-fixed import sorting in `__init__.py` and test file; removed unused `Finding`/`ValidatorOutput` imports
- Code review: findings now sorted by severity (ERROR > WARNING) per AC #2
- Code review: VALIDATOR_ERROR context now includes `"validator"` key with class name for debugging
- Code review: added `test_findings_ordered_by_severity` test and validator name assertion
- Code review: fixed stale docstring "AC 7" in test_conf.py

### Completion Notes List

- `EligibilityPipeline` mirrors `PriorAuthPipeline` exactly: `__init__`, `from_settings()`, `run()` with `time.perf_counter()` timing and per-validator exception handling
- `check_eligibility()` mirrors `submit_prior_auth()`: accepts `dict | EligibilityRequest`, optional `settings` kwarg
- `DEFAULT_ELIG_RULE_VALIDATORS` constant added to `conf.py` with all 6 validator dotted paths, wired as default for `eligibility_rule_validators`
- Exports added to `eligibility/__init__.py` (2 new: `check_eligibility`, `EligibilityPipeline`) and `claim_validator/__init__.py` (2 new)
- 23 tests covering all 8 ACs: valid/invalid requests, dict/model input, custom settings, performance <100ms, exception handling, imports
- Full regression: 1377/1377 passed, ruff clean

### File List

- `claim-validator/src/claim_validator/conf.py` (modified — added `DEFAULT_ELIG_RULE_VALIDATORS`, updated default)
- `claim-validator/src/claim_validator/eligibility/pipeline.py` (new — `EligibilityPipeline` class)
- `claim-validator/src/claim_validator/eligibility/_api.py` (new — `check_eligibility()` function)
- `claim-validator/src/claim_validator/eligibility/__init__.py` (modified — added exports)
- `claim-validator/src/claim_validator/__init__.py` (modified — added top-level exports)
- `claim-validator/tests/test_eligibility/test_pipeline.py` (new — 23 tests)
- `claim-validator/tests/test_eligibility/test_conf.py` (modified — updated default validator count test)
