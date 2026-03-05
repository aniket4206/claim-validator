# Story 4.3: WorkflowOrchestrator and process_claim() API

Status: review

## Story

As a developer building a healthcare platform,
I want to call `process_claim(request)` for the full Eligibility → PA → Claim flow,
so that I replace 200+ lines of orchestration glue with a single API call.

## Acceptance Criteria

1. **AC-1: Sequential stage execution**
   - **Given** `process_claim(request)` is called
   - **When** the orchestrator executes
   - **Then** stages run in order: Eligibility → PA Determination → PA Submission (if needed) → Claim Validation (FR21, FR22)

2. **AC-2: WorkflowResult returned**
   - **Given** the orchestrator completes all stages
   - **When** the result is returned
   - **Then** it is a `WorkflowResult` with per-stage results accessible via `.eligibility`, `.prior_auth`, `.claim_validation` (FR23)

3. **AC-3: Gate early termination**
   - **Given** eligibility fails (e.g., inactive coverage)
   - **When** the orchestrator evaluates the eligibility gate
   - **Then** it stops early, sets `stopped_at="eligibility"`, and does not run PA or claim stages (FR25)

4. **AC-4: Per-stage timing**
   - **Given** the orchestrator runs
   - **When** each stage completes
   - **Then** execution time per stage is recorded (FR26)

5. **AC-5: Dict coercion via ClaimRequest**
   - **Given** `process_claim()` is called with a ClaimRequest
   - **When** the request is processed
   - **Then** it builds stages with proper input_data and processes normally (FR22)

6. **AC-6: Top-level exports**
   - **And** `process_claim` is added to `workflow/__init__.py` exports
   - **And** FR21, FR22, FR23, FR25, FR26 are satisfied

7. **AC-7: Cross-cutting quality**
   - **And** all source files pass ruff clean
   - **And** all existing tests pass (zero regressions)

## Tasks / Subtasks

- [x] Task 1: Create workflow/orchestrator.py (AC: #1, #2, #3, #4)
  - [x] 1.1: WorkflowOrchestrator class with execute() method
  - [x] 1.2: Sequential stage execution with should_skip and gate logic
  - [x] 1.3: Build WorkflowResult with typed domain results
- [x] Task 2: Create workflow/_api.py (AC: #5, #6)
  - [x] 2.1: ClaimRequest container class
  - [x] 2.2: process_claim() convenience function
- [x] Task 3: Create workflow/__init__.py (AC: #6)
  - [x] 3.1: Export process_claim, ClaimRequest, WorkflowResult, StageResult, Stage
- [x] Task 4: Tests (AC: #1-#7)
  - [x] 4.1: WorkflowOrchestrator unit tests (8 tests)
  - [x] 4.2: process_claim() API tests (6 tests)
  - [x] 4.3: Full test suite regression check (2279 passed)
  - [x] 4.4: Ruff clean check

## Dev Notes

### Architecture

- D38: WorkflowOrchestrator with Stage protocol; stages wrap domain pipelines
- D40: WorkflowResult is frozen Pydantic model with typed per-stage results
- process_claim() is the public API; WorkflowOrchestrator is internal

### Previous Story Intelligence

- Story 4.2 created Stage protocol + 4 concrete stages + WorkflowResult + StageResult
- Domain pipelines don't yet accept validation_context — that's Story 4.4
- Existing orchestrator.py has pre_claim_check() — process_claim() is the new unified replacement
- EligibilityPipeline.run(request, *, response=None), PriorAuthPipeline.run(request), ValidationPipeline.run(claim)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- WorkflowOrchestrator.execute() iterates stages sequentially, checks should_skip, runs stage, and breaks on gate failure
- Findings sorted ERROR-first using severity_order dict
- Typed domain results extracted from workflow_context into WorkflowResult fields
- ClaimRequest coerces dict inputs to Pydantic models (EligibilityRequest, ClaimData, PriorAuthRequest)
- process_claim() wires ai_config/clearinghouse_config into settings, builds 4 stages, delegates to orchestrator
- workflow/__init__.py exports: process_claim, ClaimRequest, WorkflowResult, StageResult, Stage
- 2279 tests passed (14 new), ruff clean

### File List

- `src/claim_validator/workflow/__init__.py` (NEW)
- `src/claim_validator/workflow/orchestrator.py` (NEW)
- `src/claim_validator/workflow/_api.py` (NEW)
- `tests/test_workflow/test_orchestrator.py` (NEW)
- `tests/test_workflow/test_api.py` (NEW)

### Change Log

- 2026-03-04: Story 4.3 implemented — WorkflowOrchestrator, process_claim(), ClaimRequest, 14 new tests
