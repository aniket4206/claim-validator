# Story 5.5: Pipeline Integration and Orchestrator Wiring

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer using the unified pipeline,
I want clearinghouse clients automatically wired into the pipeline's clearinghouse phase,
so that `PipelineConfig.clearinghouse_client` works with any provider and the workflow orchestrator can invoke clearinghouse calls between rule-based and AI phases.

## Acceptance Criteria

1. **AC-1: PipelineConfig accepts BaseClearinghouseClient**
   - **Given** `PipelineConfig` has `clearinghouse_client: Any | None` (from Story 2.3)
   - **When** a `BaseClearinghouseClient` instance is passed
   - **Then** the pipeline's clearinghouse phase calls the appropriate method based on domain

2. **AC-2: Clearinghouse phase uses client methods**
   - **Given** a pipeline is constructed with `clearinghouse_client=StediClient(...)`
   - **When** the pipeline domain is "eligibility"
   - **Then** the clearinghouse phase calls `client.check_eligibility()`
   - **Given** the domain is "claim"
   - **Then** the clearinghouse phase calls `client.submit_claim()`

3. **AC-3: Graceful skip when not configured**
   - **Given** `PipelineConfig.clearinghouse_client` is None (default)
   - **When** the pipeline runs
   - **Then** the clearinghouse phase is skipped — rule-based and AI phases execute as before

4. **AC-4: Gating preserved**
   - **Given** rule-based phase fails and `skip_clearinghouse_on_rule_failure=True`
   - **When** the pipeline reaches the clearinghouse phase
   - **Then** it is skipped (existing gating behavior unchanged)

5. **AC-5: Settings-driven construction**
   - **Given** `ClaimValidatorSettings.clearinghouse_config` is populated (from env vars)
   - **When** a pipeline or orchestrator is constructed from settings
   - **Then** `get_clearinghouse_client()` factory is called with the config
   - **And** the resulting client is passed to `PipelineConfig.clearinghouse_client`

6. **AC-6: ClearinghouseError → findings**
   - **Given** a clearinghouse call raises `ClearinghouseError`
   - **When** the pipeline catches it
   - **Then** it records the error as a Finding with appropriate severity and code
   - **And** continues/stops based on gating config

7. **AC-7: Orchestrator integration**
   - **Given** `process_claim()` is called with clearinghouse configured
   - **When** the orchestrator runs the eligibility stage
   - **Then** the clearinghouse client is used for the 270/271 transaction
   - **And** the response feeds into PA determination and downstream stages

8. **AC-8: Cross-cutting quality**
   - **And** all source files pass mypy strict and ruff clean
   - **And** all existing tests pass (zero regressions)
   - **And** FR52 is satisfied

## Tasks / Subtasks

- [x] Task 1: Update BasePipeline clearinghouse phase (AC: #1, #2, #6)
  - [x] 1.1: Update `_run_clearinghouse_phase()` to dispatch based on domain (eligibility → check_eligibility, claim → submit_claim)
  - [x] 1.2: Map ClearinghouseError subtypes to appropriate Finding severities (Validation→WARNING, Auth/Timeout/Server→ERROR)
  - [x] 1.3: Ensure ClearinghouseTimeoutError and ClearinghouseServerError produce ERROR findings
- [x] Task 2: Settings-driven construction (AC: #5)
  - [x] 2.1: Create `build_clearinghouse_client(config)` helper in clearinghouse `__init__.py`
  - [x] 2.2: Wire clearinghouse_config into `_api.py` validate() and `orchestrator.py` pre_claim_check()
- [x] Task 3: Orchestrator wiring (AC: #7)
  - [x] 3.1: Add `clearinghouse_config` parameter to `pre_claim_check()` — wired to settings like ai_config
  - [x] 3.2: Add `clearinghouse_config` parameter to `validate()` — same pattern
- [x] Task 4: Tests (AC: #1-#8)
  - [x] 4.1: Test clearinghouse phase dispatch by domain — 3 tests
  - [x] 4.2: Test ClearinghouseError → Finding conversion — 7 tests
  - [x] 4.3: Test settings-driven construction — 5 tests
  - [x] 4.4: Test gating still works with clearinghouse client — 2 tests
  - [x] 4.5: Test orchestrator and API accept clearinghouse_config — 3 tests
  - [x] 4.6: Test build_clearinghouse_client edge cases — 3 tests
  - [x] 4.7: Updated existing test_engine.py MockClearinghouseClient to support domain dispatch
- [x] Task 5: Quality verification (AC: #8)
  - [x] 5.1: Ruff clean, 25 new tests pass, 2202 total pass (zero regressions)

## Dev Notes

### BasePipeline.clearinghouse_client Interface

Story 2.3 created `BasePipeline._run_clearinghouse_phase()` which calls `client.submit(input_data)` via duck typing. This needs to be updated to dispatch based on domain:

```python
def _run_clearinghouse_phase(self, input_data: Any) -> PhaseResult:
    start = time.perf_counter()
    outputs: list[ValidatorOutput] = []
    try:
        client = self._config.clearinghouse_client
        if self._config.domain == "eligibility":
            result = client.check_eligibility(input_data)
        elif self._config.domain == "claim":
            result = client.submit_claim(input_data)
        else:
            result = client.check_claim_status(str(input_data))
    except ClearinghouseError as exc:
        outputs.append(ValidatorOutput(
            validator_name="clearinghouse",
            findings=[Finding(
                code=f"{self._config.code_prefix}CLEARINGHOUSE_ERROR",
                message=str(exc),  # Already PHI-scrubbed by provider
                severity=Severity.ERROR,
                field_name="",
            )],
        ))
    ...
```

### Existing Pipeline Structure

| File | Role |
|------|------|
| `shared/pipeline/engine.py` | BasePipeline with `_run_clearinghouse_phase()` |
| `shared/pipeline/config.py` | PipelineConfig with `clearinghouse_client: Any \| None` |
| `orchestrator.py` | `pre_claim_check()` — orchestrates eligibility → PA → claims |
| `conf.py` | `ClaimValidatorSettings` with `clearinghouse_config` (from Story 5.1) |

### Settings-Driven Construction Pattern

Follow existing AI config pattern in `_api.py`:

```python
from claim_validator.clearinghouse.factory import get_clearinghouse_client

def _build_clearinghouse_client(settings):
    if settings.clearinghouse_config is None:
        return None
    config = settings.clearinghouse_config
    return get_clearinghouse_client(
        provider=config["provider"],
        api_key=config.get("api_key", ""),
        secret=config.get("secret"),
        account_key=config.get("account_id"),
        base_url=config.get("base_url"),
    )
```

### Dependencies

- Story 5.1 (ABC, factory, config, exceptions) — REQUIRED
- Story 5.2 or 5.3 (at least one provider) — REQUIRED for meaningful integration tests
- Story 2.3 (BasePipeline) — already exists
- Orchestrator (`orchestrator.py`) — already exists

### What This Story Modifies

| File | Change |
|------|--------|
| `shared/pipeline/engine.py` | Update `_run_clearinghouse_phase()` dispatch |
| `orchestrator.py` | Wire clearinghouse client from settings |
| `_api.py` or equivalent | Build clearinghouse client from settings |

### References

- [Source: shared/pipeline/engine.py — BasePipeline._run_clearinghouse_phase()]
- [Source: shared/pipeline/config.py — PipelineConfig.clearinghouse_client]
- [Source: orchestrator.py — pre_claim_check() orchestrator]
- [Source: conf.py — ClaimValidatorSettings]
- [Source: epics.md — FR52: Pipeline integration]
- [Source: 2-3-basepipeline-and-pipelineconfig.md — Pipeline architecture]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- MockClearinghouseClient in test_engine.py used `submit()` — updated to support 3 dispatch methods
- EligibilityRequest field names differ from library dict keys — fixed in test

### Completion Notes List

- All 5 tasks complete, all ACs satisfied
- `_run_clearinghouse_phase()` dispatches by domain: eligibility→check_eligibility, claim→submit_claim, else→check_claim_status
- ClearinghouseError subtypes mapped to Finding severities: ValidationError→WARNING, Auth/Timeout→ERROR
- `build_clearinghouse_client(config)` convenience helper extracts provider and delegates to factory
- `pre_claim_check()` and `validate()` accept `clearinghouse_config` kwarg with same wiring pattern as ai_config
- Exported `build_clearinghouse_client` from clearinghouse and top-level packages
- 25 new tests, 2202 total pass (zero regressions)

### File List

**Modified source files (4):**
- `src/claim_validator/shared/pipeline/engine.py` — Domain-based dispatch + ClearinghouseError→Finding mapping
- `src/claim_validator/clearinghouse/__init__.py` — Added `build_clearinghouse_client()` helper
- `src/claim_validator/orchestrator.py` — Added `clearinghouse_config` parameter
- `src/claim_validator/_api.py` — Added `clearinghouse_config` parameter
- `src/claim_validator/__init__.py` — Added `build_clearinghouse_client` export

**New test files (1):**
- `tests/test_clearinghouse/test_pipeline_integration.py` — 25 tests

**Modified test files (1):**
- `tests/test_shared/test_pipeline/test_engine.py` — Updated MockClearinghouseClient for domain dispatch
