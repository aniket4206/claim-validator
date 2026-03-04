# Story 4.2: WorkflowResult Model and Stage Protocol

Status: review

## Story

As a developer consuming workflow results,
I want a typed `WorkflowResult` with per-stage results, timing, and aggregate status,
so that I can inspect exactly what happened at each stage of the pipeline.

## Acceptance Criteria

1. **AC-1: WorkflowResult structure**
   - **Given** `WorkflowResult` is a frozen Pydantic model
   - **When** inspected
   - **Then** it contains: `eligibility: EligibilityResult | None`, `pa_determination: PADeterminationResult | None`, `prior_auth: PriorAuthResult | None`, `claim_validation: PipelineResult | None`, `stopped_at: str | None`, `stage_results: list[StageResult]`, `findings: list[Finding]`, `ai_summary: str | None`, `execution_time: float` (FR35)

2. **AC-2: Per-stage execution time**
   - **Given** a completed workflow
   - **When** `result.stage_times` is accessed
   - **Then** per-stage execution time is available as `dict[str, float]` (FR36)

3. **AC-3: Aggregate passed boolean**
   - **Given** a workflow where all stages passed
   - **When** `result.passed` is accessed
   - **Then** it returns True (no ERROR findings)
   - **And** if any stage has ERROR findings, `result.passed` returns False (FR37)

4. **AC-4: StageResult model**
   - **Given** `StageResult` is a frozen Pydantic model
   - **When** constructed
   - **Then** it has: `stage_name`, `passed`, `skipped`, `skip_reason`, `findings`, `execution_time`, `detail`

5. **AC-5: Stage protocol**
   - **Given** `Stage` is a runtime-checkable Protocol with `name: str`, `is_gate: bool`, `should_skip()`, `run()`
   - **When** a class implements the Stage protocol
   - **Then** `isinstance(stage, Stage)` returns True

6. **AC-6: Four concrete stages**
   - **Given** `EligibilityStage`, `PADeterminationStage`, `PriorAuthStage`, `ClaimValidationStage` implement Stage
   - **When** each is instantiated with settings
   - **Then** `should_skip()` and `run()` dispatch to the correct domain pipeline

7. **AC-7: Cross-cutting quality**
   - **And** all source files pass ruff clean
   - **And** all existing tests pass (zero regressions)
   - **And** FR35, FR36, FR37 are satisfied

## Tasks / Subtasks

- [x] Task 1: Create workflow/models.py (AC: #1, #2, #3, #4)
  - [x] 1.1: StageResult frozen Pydantic model
  - [x] 1.2: WorkflowResult frozen Pydantic model with typed domain results
  - [x] 1.3: `passed` property (no ERROR findings) and `stage_times` property
- [x] Task 2: Create workflow/stages.py (AC: #5, #6)
  - [x] 2.1: Stage Protocol (runtime_checkable) with name, is_gate, should_skip, run
  - [x] 2.2: EligibilityStage (gate, never skips)
  - [x] 2.3: PADeterminationStage (non-gate, skips if no eligibility_response)
  - [x] 2.4: PriorAuthStage (gate, skips if PA not required)
  - [x] 2.5: ClaimValidationStage (non-gate, never skips if reached)
- [x] Task 3: Tests (AC: #1-#7)
  - [x] 3.1: WorkflowResult and StageResult model tests
  - [x] 3.2: Stage protocol and concrete stage tests
  - [x] 3.3: Full test suite regression check (2265 passed)
  - [x] 3.4: Ruff clean check

## Dev Notes

### Architecture

- D38: WorkflowOrchestrator with Stage protocol (name, is_gate, should_skip, run); stages wrap domain pipelines
- D40: WorkflowResult is frozen Pydantic model with typed per-stage results
- Each stage wraps `from_settings()` + `run()` of its domain pipeline, forwarding `validation_context`
- Stages use `workflow_context: dict` for passing state between stages (e.g., eligibility_response → PA determination)

### Files to Create

| File | Purpose |
|------|---------|
| `src/claim_validator/workflow/models.py` | StageResult, WorkflowResult |
| `src/claim_validator/workflow/stages.py` | Stage Protocol + 4 concrete stages |
| `tests/test_workflow/__init__.py` | Test package |
| `tests/test_workflow/test_models.py` | Model tests |
| `tests/test_workflow/test_stages.py` | Stage tests |

### Previous Story Intelligence

- Story 4.1 added `validation_context` param to `BasePipeline.run()` — stages must forward this
- Domain pipelines don't yet accept `validation_context` — that's Story 4.4. Stages should pass it but domain pipelines will ignore until 4.4
- `EligibilityPipeline.run(request, *, response=None)` — takes request + optional response
- `PriorAuthPipeline.run(request, *, response=None)` — same pattern
- `ValidationPipeline.run(claim)` — takes ClaimData directly

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- StageResult and WorkflowResult implemented as frozen Pydantic models with `model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)`
- WorkflowResult.passed property checks for ERROR findings across all stage results
- WorkflowResult.stage_times property returns dict[str, float] from stage_results
- Stage Protocol is runtime_checkable; all 4 concrete stages pass isinstance check
- Domain pipeline run() calls do NOT pass validation_context — deferred to Story 4.4
- Stages use deferred imports inside run() to avoid circular dependencies
- PriorAuthStage returns PA_REQUIRED warning Finding when pa_request is None
- 2265 tests passed (21 new), ruff clean

### File List

- `src/claim_validator/workflow/__init__.py` (NEW)
- `src/claim_validator/workflow/models.py` (NEW)
- `src/claim_validator/workflow/stages.py` (NEW)
- `tests/test_workflow/__init__.py` (NEW)
- `tests/test_workflow/test_models.py` (NEW)
- `tests/test_workflow/test_stages.py` (NEW)

### Change Log

- 2026-03-04: Story 4.2 implemented — WorkflowResult, StageResult, Stage protocol, 4 concrete stages, 21 new tests
