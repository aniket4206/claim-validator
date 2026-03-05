# Story 4.1: ValidationContext and Pipeline Passthrough

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want pipelines to track which validators have run and skip redundant checks downstream,
so that NPI/demographics validated at eligibility are not re-run at PA or claim stages.

## Acceptance Criteria

1. **AC-1: ValidationContext records validator results**
   - **Given** `ValidationContext` is a dataclass with `_results: dict[str, ValidatorResult]`
   - **When** `context.record("NPIValidator", "npi", passed=True)` is called after NPI validation
   - **Then** `context.has_passed("npi")` returns True
   - **And** `context.get_prior_findings("npi")` returns the recorded findings

2. **AC-2: BasePipeline passthrough skips passed validators**
   - **Given** a `BasePipeline.run(input, validation_context=ctx)` call with a populated context
   - **When** the pipeline encounters a validator whose category `ctx.has_passed()` returns True
   - **Then** that validator is skipped and its prior findings are reused (FR29)
   - **And** the skipped validator output uses `"ValidatorName(passthrough)"` naming

3. **AC-3: Standalone mode runs all validators**
   - **Given** a `BasePipeline.run(input)` call with no validation_context (standalone mode)
   - **When** the pipeline runs
   - **Then** all configured validators execute — no skipping (FR30)

4. **AC-4: Passthrough findings included in results**
   - **Given** validators are skipped via passthrough
   - **When** the pipeline result is inspected
   - **Then** skipped validators' prior findings are included in the result (not silently dropped)

5. **AC-5: Category mapping covers cross-domain validators**
   - **Given** `VALIDATOR_CATEGORY_MAP` maps validator names to categories
   - **When** inspected
   - **Then** it maps: NPI validators → "npi", MemberID/SubscriberID validators → "member_id", Demographics validators → "demographics"
   - **And** unmapped validators always run regardless of context

6. **AC-6: Context records results for downstream stages**
   - **Given** a validator runs (not skipped) with a validation_context present
   - **When** the validator completes
   - **Then** its result is recorded in the context for downstream pipeline stages
   - **And** passed = True if no ERROR-severity findings

7. **AC-7: Cross-cutting quality**
   - **And** all source files pass ruff clean
   - **And** all existing tests pass (zero regressions from 2210+ baseline)
   - **And** FR28, FR29, FR30 are satisfied

## Tasks / Subtasks

- [x] Task 1: Create ValidationContext and ValidatorResult (AC: #1, #5)
  - [x] 1.1: Create `src/claim_validator/shared/pipeline/context.py` with `ValidatorResult` dataclass (validator_name, category, passed, findings)
  - [x] 1.2: Implement `ValidationContext` dataclass with `record()`, `has_passed()`, `get_prior_findings()` methods
  - [x] 1.3: Define `VALIDATOR_CATEGORY_MAP` dict mapping all 8 cross-domain validators to 3 categories (npi, member_id, demographics)
- [x] Task 2: Modify BasePipeline for passthrough (AC: #2, #3, #4, #6)
  - [x] 2.1: Add `*, validation_context: ValidationContext | None = None` keyword-only param to `BasePipeline.run()`
  - [x] 2.2: Add same param to `_run_rule_phase()` and forward from `run()`
  - [x] 2.3: In `_run_rule_phase()`, for each validator: lookup category in `VALIDATOR_CATEGORY_MAP`, if context has_passed → skip with passthrough output, else run normally and record result
  - [x] 2.4: Ensure unmapped validators always execute regardless of context
- [x] Task 3: Update pipeline exports (AC: #7)
  - [x] 3.1: Export `ValidationContext` from `src/claim_validator/shared/pipeline/__init__.py`
- [x] Task 4: Tests (AC: #1-#7)
  - [x] 4.1: Unit tests for `ValidationContext` — record, has_passed, get_prior_findings, overwrite, multiple categories
  - [x] 4.2: Unit tests for `VALIDATOR_CATEGORY_MAP` — all 8 validators mapped, unmapped validators absent
  - [x] 4.3: Engine passthrough tests — skip on passed, no skip on failed, no skip without context, unmapped always runs, backward compatibility
  - [x] 4.4: Run full test suite — verify zero regressions (2244 passed, 34 new)
  - [x] 4.5: Run ruff check — all checks passed

## Dev Notes

### Architecture Requirements

- **D37:** ValidationContext dataclass carrying `dict[str, ValidatorResult]`; optional param on `pipeline.run()` [Source: architecture.md#D37]
- **D36:** BasePipeline parameterized by PipelineConfig; domains create config, never subclass `run()` [Source: architecture.md#D36]
- **FR28:** Pipeline tracks which validators have run and their results
- **FR29:** Downstream stages query prior validation and skip redundant checks
- **FR30:** Standalone mode (not via orchestrator) runs full validator set per module

### Validator Category Mapping

| Category | Eligibility Validator | PA Validator | Claims Validator |
|----------|----------------------|--------------|------------------|
| `npi` | EligibilityNPIValidator | PANPIValidator | NPIValidator |
| `member_id` | MemberIDValidator | PAMemberIDValidator | SubscriberIDValidator |
| `demographics` | EligibilityDemographicsValidator | — | DemographicsValidator |

### Key Implementation Details

- `BasePipeline.run()` signature change: `run(self, input_data: Any, *, validation_context: ValidationContext | None = None)` — backward-compatible keyword-only arg
- `_run_rule_phase()` gets same param, forwarded from `run()`
- Passthrough output uses `ValidatorOutput(validator_name="NPIValidator(passthrough)", findings=prior_findings)` — clearly marked
- Context records results only when context is not None AND validator has a category mapping
- `passed` = True when validator has zero ERROR-severity findings (WARNINGs are OK)
- `get_prior_findings()` returns a copy to prevent mutation

### Files to Create

| File | Purpose |
|------|---------|
| `src/claim_validator/shared/pipeline/context.py` | ValidationContext, ValidatorResult, VALIDATOR_CATEGORY_MAP |
| `tests/test_shared/test_pipeline/test_context.py` | Unit tests for context module |
| `tests/test_shared/test_pipeline/test_engine_passthrough.py` | Passthrough integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/claim_validator/shared/pipeline/engine.py` | Add validation_context param to run() and _run_rule_phase(), passthrough logic |
| `src/claim_validator/shared/pipeline/__init__.py` | Export ValidationContext |

### Testing Standards

- Test framework: pytest (existing)
- Mock validators using `BaseValidator` subclasses with configurable `name` attribute
- Run `python -m pytest tests/ -x -q` for full suite
- Run `ruff check src/ tests/` for linting
- Baseline: 2210+ tests must all pass

### Previous Story Intelligence

- Epic 3 established the pattern of domain pipelines delegating to `BasePipeline` via `PipelineConfig`
- Epic 5 (Story 5.5) wired clearinghouse clients into the pipeline — same `PipelineConfig` slot pattern
- `BasePipeline._run_rule_phase()` iterates validators with exception wrapping — passthrough inserts before the try/except
- Existing `run()` has no keyword args — new param is keyword-only for backward compatibility
- `ValidatorOutput` is frozen Pydantic model — can construct with prior findings

### Git Intelligence

- Last commit `4939bbe`: Epic 3 refactor — all domain modules delegate to shared infrastructure
- Domain pipelines (`EligibilityPipeline`, `PriorAuthPipeline`, `ValidationPipeline`) all call `self._base_pipeline.run(request)` — will need `validation_context` forwarding in Story 4.4
- `pre_claim_check()` orchestrator exists but doesn't use passthrough — Story 4.3 replaces it with `process_claim()`

### Project Structure Notes

- All shared infrastructure lives under `src/claim_validator/shared/pipeline/`
- Test mirror: `tests/test_shared/test_pipeline/`
- Existing test files: `test_config.py`, `test_engine.py` — new files follow same pattern
- venv at `.venv/` — run tests via `.venv/bin/python -m pytest`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic-4-Story-4.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#D37]
- [Source: src/claim_validator/shared/pipeline/engine.py — BasePipeline.run(), _run_rule_phase()]
- [Source: src/claim_validator/shared/pipeline/__init__.py — current exports]
- [Source: src/claim_validator/shared/pipeline/config.py — PipelineConfig frozen dataclass]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- ValidationContext dataclass with record/has_passed/get_prior_findings implemented as pure dataclass (not Pydantic) for simplicity
- VALIDATOR_CATEGORY_MAP maps 8 validators across 3 domains to 3 categories (npi, member_id, demographics)
- BasePipeline.run() and _run_rule_phase() gained keyword-only `validation_context` param — fully backward-compatible
- Passthrough outputs use `"ValidatorName(passthrough)"` naming to clearly distinguish skipped validators
- Context records results only for validators with category mapping — unmapped validators always run
- passed = no ERROR findings (WARNINGs don't fail)
- 2244 tests passed (34 new), ruff clean

### File List

- `src/claim_validator/shared/pipeline/context.py` (NEW)
- `src/claim_validator/shared/pipeline/engine.py` (MODIFIED)
- `src/claim_validator/shared/pipeline/__init__.py` (MODIFIED)
- `tests/test_shared/test_pipeline/test_context.py` (NEW)
- `tests/test_shared/test_pipeline/test_engine_passthrough.py` (NEW)

### Change Log

- 2026-03-04: Story 4.1 implemented — ValidationContext, BasePipeline passthrough, 34 new tests
