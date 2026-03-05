# Story 4.4: PA Determination and Validation Passthrough Integration

Status: review

## Story

As a developer using the unified pipeline,
I want PA determined automatically from the 271 response and validation passthrough eliminating redundant checks,
so that the workflow is intelligent about what to run and what to skip.

## Acceptance Criteria

1. **AC-1: Domain pipelines accept validation_context**
   - **Given** EligibilityPipeline, PriorAuthPipeline, ValidationPipeline
   - **When** `run()` is called with `validation_context=ctx`
   - **Then** they forward it to `self._base_pipeline.run()` for passthrough (FR24)

2. **AC-2: Stages forward validation_context**
   - **Given** workflow stages receive `validation_context` from orchestrator
   - **When** each stage calls its domain pipeline
   - **Then** validation_context is forwarded to the pipeline (FR27)

3. **AC-3: End-to-end passthrough**
   - **Given** process_claim() runs the full workflow
   - **When** stages execute
   - **Then** the same ValidationContext is shared across all stages

4. **AC-4: Cross-cutting quality**
   - **And** all source files pass ruff clean
   - **And** all existing tests pass (zero regressions)

## Tasks / Subtasks

- [x] Task 1: Modify domain pipelines (AC: #1)
  - [x] 1.1: EligibilityPipeline.run() gains validation_context param
  - [x] 1.2: PriorAuthPipeline.run() gains validation_context param
  - [x] 1.3: ValidationPipeline.run() gains validation_context param
- [x] Task 2: Update workflow stages (AC: #2)
  - [x] 2.1: EligibilityStage forwards validation_context to pipeline
  - [x] 2.2: PriorAuthStage forwards validation_context to pipeline
  - [x] 2.3: ClaimValidationStage forwards validation_context to pipeline
- [x] Task 3: Update orchestrator (AC: #3)
  - [x] 3.1: WorkflowOrchestrator creates ValidationContext and passes to stages
- [x] Task 4: Tests (AC: #1-#4)
  - [x] 4.1: Passthrough integration tests (4 tests)
  - [x] 4.2: Updated stage assertion tests for new call signatures
  - [x] 4.3: Full test suite regression check (2283 passed)
  - [x] 4.4: Ruff clean check

## Dev Notes

### Architecture

- All domain pipeline `run()` methods now accept `*, validation_context: ValidationContext | None = None`
- Keyword-only arg with default None — fully backward-compatible
- Orchestrator creates a fresh `ValidationContext()` per execute() call, shared across all stages

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Completion Notes List

- EligibilityPipeline, PriorAuthPipeline, ValidationPipeline all forward validation_context to BasePipeline.run()
- All 3 stages (Eligibility, PriorAuth, ClaimValidation) forward validation_context from orchestrator to domain pipeline
- Orchestrator creates ValidationContext per-call — no thread safety concern
- 2283 tests passed (4 new passthrough integration tests), ruff clean

### File List

- `src/claim_validator/eligibility/pipeline.py` (MODIFIED)
- `src/claim_validator/prior_auth/pipeline.py` (MODIFIED)
- `src/claim_validator/validators/pipeline.py` (MODIFIED)
- `src/claim_validator/workflow/stages.py` (MODIFIED)
- `src/claim_validator/workflow/orchestrator.py` (MODIFIED)
- `tests/test_workflow/test_stages.py` (MODIFIED)
- `tests/test_workflow/test_passthrough_integration.py` (NEW)

### Change Log

- 2026-03-04: Story 4.4 implemented — validation_context forwarding through all domain pipelines
