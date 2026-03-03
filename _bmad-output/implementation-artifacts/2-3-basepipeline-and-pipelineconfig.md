# Story 2.3: BasePipeline and PipelineConfig

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want a single `BasePipeline` class parameterized by `PipelineConfig`,
so that multi-phase execution (rule-based → clearinghouse → AI) is implemented once and configured per domain.

## Acceptance Criteria

1. **AC-1: PipelineConfig specifies all pipeline parameters**
   - **Given** a `PipelineConfig` is created with validator list, clearinghouse client (optional), AI interpreter (optional), gating rules, and finding code prefix
   - **When** the config is inspected
   - **Then** it is immutable (frozen dataclass) and all fields are correctly typed
   - **And** `clearinghouse_client` and `ai_interpreter` default to `None`
   - **And** gating booleans default to `True`

2. **AC-2: Multi-phase execution order**
   - **Given** `BasePipeline(config).run(input)` is called
   - **When** all three phases are configured (validators, clearinghouse, AI)
   - **Then** phases execute in order: rule-based validators → clearinghouse → AI
   - **And** each phase produces a `PhaseResult` with its own `execution_time`

3. **AC-3: Gating — skip clearinghouse on rule failure (FR15)**
   - **Given** rule-based phase has ERROR-severity findings and `skip_clearinghouse_on_rule_failure=True` in config
   - **When** the pipeline reaches the clearinghouse phase
   - **Then** it skips clearinghouse AND AI, returning partial results with gating information

4. **AC-4: Gating — skip AI on rule failure**
   - **Given** rule-based phase has ERROR-severity findings and `skip_ai_on_rule_failure=True` in config
   - **When** the pipeline reaches the AI phase
   - **Then** it skips the AI phase, returning rule-based + clearinghouse results only

5. **AC-5: Per-phase timing (FR16)**
   - **Given** a pipeline run completes
   - **When** the result is inspected
   - **Then** `PipelineResult.execution_time` has the total wall-clock time
   - **And** each `PhaseResult.execution_time` has that phase's wall-clock time

6. **AC-6: Domain-specific config (FR17)**
   - **Given** three different `PipelineConfig` instances (claims, eligibility, prior auth configs)
   - **When** each is used to construct a `BasePipeline`
   - **Then** each pipeline uses its configured validators, clearinghouse client, and AI interpreter

7. **AC-7: Graceful skip when clearinghouse not configured**
   - **Given** no clearinghouse client is configured (`clearinghouse_client=None`)
   - **When** the pipeline runs
   - **Then** it skips the clearinghouse phase entirely (no error, no empty PhaseResult)

8. **AC-8: Graceful skip when AI not configured**
   - **Given** no AI interpreter is configured (`ai_interpreter=None`)
   - **When** the pipeline runs
   - **Then** it executes rule-based only (and clearinghouse if configured), skipping AI gracefully

9. **AC-9: `BasePipeline.run()` never subclassed (D36)**
   - **And** `BasePipeline.run()` is NOT overridden by domains — domains only provide config
   - **And** FR14, FR15, FR16, FR17 are satisfied

10. **AC-10: Backward compatibility**
    - **Given** all existing tests pass before Story 2.3
    - **When** Story 2.3 source and tests are added
    - **Then** all 1970+ existing tests still pass with zero regressions
    - **And** no existing source files are modified

11. **AC-11: Cross-cutting quality**
    - All new source files pass mypy strict and ruff clean
    - All new test files pass ruff clean
    - `shared/pipeline/__init__.py` exports `BasePipeline`, `PipelineConfig` with `__all__`
    - `from __future__ import annotations` on ALL new files

## Tasks / Subtasks

- [x] Task 1: Create shared pipeline package (AC: #11)
  - [x] 1.1: Create `src/claim_validator/shared/pipeline/__init__.py` with re-exports and `__all__`
  - [x] 1.2: Create `src/claim_validator/shared/pipeline/config.py`
  - [x] 1.3: Create `src/claim_validator/shared/pipeline/engine.py`
- [x] Task 2: Implement PipelineConfig (AC: #1)
  - [x] 2.1: Define frozen dataclass with `domain`, `validators`, `clearinghouse_client`, `ai_interpreter`, `deidentifier`, `skip_ai_on_rule_failure`, `skip_clearinghouse_on_rule_failure`, `code_prefix`
  - [x] 2.2: All fields correctly typed with sensible defaults
  - [x] 2.3: Validate config constraints in `__post_init__` if needed (e.g., AI without deidentifier)
- [x] Task 3: Implement BasePipeline rule-based phase (AC: #2, #5)
  - [x] 3.1: Implement `__init__(self, config: PipelineConfig)` storing config
  - [x] 3.2: Implement `run(self, input_data: Any) -> PipelineResult` — orchestrate all phases
  - [x] 3.3: Implement `_run_rule_phase(input_data)` — iterate validators, collect ValidatorOutput, wrap in PhaseResult with timing
  - [x] 3.4: Exception handling: validator exception → ValidatorOutput with VALIDATOR_ERROR finding
- [x] Task 4: Implement BasePipeline clearinghouse phase (AC: #2, #3, #7)
  - [x] 4.1: Implement `_run_clearinghouse_phase(input_data)` — call clearinghouse client, wrap result in PhaseResult
  - [x] 4.2: Gating: skip if `skip_clearinghouse_on_rule_failure=True` and rule phase has errors
  - [x] 4.3: Skip entirely when `clearinghouse_client is None`
  - [x] 4.4: Exception handling: clearinghouse error → PhaseResult with error finding
- [x] Task 5: Implement BasePipeline AI phase (AC: #2, #4, #8)
  - [x] 5.1: Implement `_run_ai_phase(input_data)` — de-identify via config.deidentifier, then call AI interpreter
  - [x] 5.2: Gating: skip if `skip_ai_on_rule_failure=True` and rule phase has errors
  - [x] 5.3: Gating: skip if clearinghouse was skipped due to rule failure (cascade gating per AC-3)
  - [x] 5.4: Skip entirely when `ai_interpreter is None`
  - [x] 5.5: Exception handling: LLMError → WARNING finding, generic exception → ERROR finding
- [x] Task 6: Create tests (AC: #1-#11)
  - [x] 6.1: Create `tests/test_shared/test_pipeline/__init__.py`
  - [x] 6.2: Create `tests/test_shared/test_pipeline/test_config.py` — PipelineConfig creation, immutability, defaults, field types
  - [x] 6.3: Create `tests/test_shared/test_pipeline/test_engine.py` — phase execution, gating, timing, error handling, graceful skip
- [x] Task 7: Quality verification (AC: #10, #11)
  - [x] 7.1: Run `ruff check` on ALL new files (source AND test)
  - [x] 7.2: Run `pytest tests/test_shared/test_pipeline/` — all pass
  - [x] 7.3: Run full `pytest` — all 1970+ existing tests still pass, zero regressions

## Dev Notes

### Architecture Decision D36: Shared Pipeline Engine (MANDATORY)

`BasePipeline` parameterized by `PipelineConfig` dataclass. Single `BasePipeline.run(input) -> PipelineResult` handles: phase sequencing, gating logic, timing, error aggregation. Each domain provides `PipelineConfig`: validator list, clearinghouse client (optional), AI interpreter (optional), gating rules, finding code prefix.

**Enforcement Guideline #5:** Domain pipelines create `BasePipeline` with config, never subclass `BasePipeline.run()`.

Files: `shared/pipeline/engine.py`, `shared/pipeline/config.py`

### Design: PipelineConfig

```python
# shared/pipeline/config.py
"""Pipeline configuration — specifies phases, validators, and gating rules per domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.validators.base import BaseValidator


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable configuration for a multi-phase pipeline.

    Each domain creates one PipelineConfig with its specific validators,
    clearinghouse client, AI interpreter, and gating rules. The BasePipeline
    executes phases in order using this config.

    Attributes:
        domain: Domain identifier ("claim", "eligibility", "prior_auth").
        validators: Pre-constructed rule-based validators for phase 1.
        clearinghouse_client: Optional clearinghouse client for phase 2.
            Must have a callable interface (duck-typed).
        ai_interpreter: Optional AI interpreter/validator for phase 3.
            Must have a callable interface (duck-typed).
        deidentifier: De-identifier for stripping PHI before AI phase.
            Required if ai_interpreter is configured.
        skip_ai_on_rule_failure: If True, skip AI when rule phase has ERRORs.
        skip_clearinghouse_on_rule_failure: If True, skip clearinghouse
            (and AI) when rule phase has ERRORs.
        code_prefix: Finding code prefix for this domain (e.g., "ELIG_", "PA_").
    """

    domain: str
    validators: tuple[BaseValidator, ...] = ()
    clearinghouse_client: Any | None = None
    ai_interpreter: Any | None = None
    deidentifier: BaseDeidentifier | None = None
    skip_ai_on_rule_failure: bool = True
    skip_clearinghouse_on_rule_failure: bool = True
    code_prefix: str = ""
```

**Key typing decision:** `clearinghouse_client` and `ai_interpreter` are `Any | None` because the specific ABCs are not defined in the shared package. Each domain's client/interpreter conforms to a duck-typed interface:
- Clearinghouse: must be callable with `submit(input_data)` or equivalent
- AI interpreter: must have `validate_deidentified(data) -> ValidatorOutput` or `interpret(data) -> tuple[str, list[Finding]]`

The BasePipeline uses **duck typing** to call these — it does NOT import domain-specific types.

### Design: BasePipeline Engine

```python
# shared/pipeline/engine.py
"""BasePipeline — configurable multi-phase pipeline engine."""

from __future__ import annotations

import time
from typing import Any

from claim_validator.constants import Severity
from claim_validator.exceptions import LLMError
from claim_validator.models.results import (
    Finding,
    PhaseResult,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.shared.pipeline.config import PipelineConfig


class BasePipeline:
    """Configurable multi-phase pipeline engine.

    Executes up to 3 phases:
      1. Rule-based validators (always runs if validators configured)
      2. Clearinghouse (optional, gated by rule results)
      3. AI interpretation (optional, gated by rule results)

    Domains provide PipelineConfig, never subclass run().
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    @property
    def config(self) -> PipelineConfig:
        """The pipeline configuration."""
        return self._config

    def run(self, input_data: Any) -> PipelineResult:
        """Execute the full multi-phase pipeline."""
        start = time.perf_counter()
        phase_results: list[PhaseResult] = []

        # Phase 1: Rule-based validators
        rule_phase = self._run_rule_phase(input_data)
        phase_results.append(rule_phase)

        rule_has_errors = any(
            f.severity == Severity.ERROR for f in rule_phase.findings
        )

        # Phase 2: Clearinghouse (optional, gated)
        clearinghouse_skipped = False
        if self._config.clearinghouse_client is not None:
            if rule_has_errors and self._config.skip_clearinghouse_on_rule_failure:
                clearinghouse_skipped = True
            else:
                ch_phase = self._run_clearinghouse_phase(input_data)
                phase_results.append(ch_phase)

        # Phase 3: AI (optional, gated)
        if self._config.ai_interpreter is not None:
            should_skip = (
                clearinghouse_skipped  # cascade: clearinghouse skipped → AI skipped
                or (rule_has_errors and self._config.skip_ai_on_rule_failure)
            )
            if not should_skip:
                ai_phase = self._run_ai_phase(input_data)
                phase_results.append(ai_phase)

        elapsed = time.perf_counter() - start
        return PipelineResult(
            phase_results=phase_results,
            execution_time=elapsed,
        )
```

### Phase Implementation Details

**Rule-based phase** — follows `ValidationPipeline._run_phase()` pattern exactly:
```python
def _run_rule_phase(self, input_data: Any) -> PhaseResult:
    start = time.perf_counter()
    outputs: list[ValidatorOutput] = []
    for validator in self._config.validators:
        try:
            output = validator.validate(input_data)
            outputs.append(output)
        except Exception as exc:
            outputs.append(ValidatorOutput(
                validator_name=getattr(validator, "name", type(validator).__name__),
                findings=[Finding(
                    code=f"{self._config.code_prefix}VALIDATOR_ERROR",
                    message="Validator raised an unexpected exception",
                    severity=Severity.ERROR,
                    field_name="",
                    suggestion="Check validator implementation",
                    context={"validator": type(validator).__name__, "error": str(exc)},
                )],
            ))
    elapsed = time.perf_counter() - start
    return PhaseResult(phase="rule_based", validator_outputs=outputs, execution_time=elapsed)
```

**Clearinghouse phase** — wraps the clearinghouse client call:
```python
def _run_clearinghouse_phase(self, input_data: Any) -> PhaseResult:
    start = time.perf_counter()
    outputs: list[ValidatorOutput] = []
    try:
        self._config.clearinghouse_client.submit(input_data)
        # Clearinghouse success produces no findings (it's a transport phase)
    except Exception as exc:
        outputs.append(ValidatorOutput(
            validator_name="clearinghouse",
            findings=[Finding(
                code=f"{self._config.code_prefix}CLEARINGHOUSE_ERROR",
                message="Clearinghouse submission failed",
                severity=Severity.ERROR,
                field_name="",
                suggestion="Check clearinghouse client configuration",
                context={"error": str(exc)},
            )],
        ))
    elapsed = time.perf_counter() - start
    return PhaseResult(phase="clearinghouse", validator_outputs=outputs, execution_time=elapsed)
```

**AI phase** — de-identifies first, then calls AI interpreter:
```python
def _run_ai_phase(self, input_data: Any) -> PhaseResult:
    start = time.perf_counter()
    outputs: list[ValidatorOutput] = []
    try:
        # De-identify before AI consumption (FR40)
        deidentified = input_data
        if self._config.deidentifier is not None:
            deidentified = self._config.deidentifier.deidentify(input_data)

        # Call AI interpreter — duck-typed interface
        output = self._config.ai_interpreter.validate_deidentified(deidentified)
        outputs.append(output)
    except LLMError as exc:
        outputs.append(ValidatorOutput(
            validator_name=getattr(self._config.ai_interpreter, "name", "ai"),
            findings=[Finding(
                code=f"{self._config.code_prefix}AI_PROVIDER_ERROR",
                message="AI validation unavailable",
                severity=Severity.WARNING,
                field_name="",
                suggestion="Rule-based results are still valid. Retry when AI provider is available.",
                context={"error": str(exc)},
            )],
        ))
    except Exception as exc:
        outputs.append(ValidatorOutput(
            validator_name=getattr(self._config.ai_interpreter, "name", "ai"),
            findings=[Finding(
                code=f"{self._config.code_prefix}VALIDATOR_ERROR",
                message="AI interpreter raised an unexpected exception",
                severity=Severity.ERROR,
                field_name="",
                suggestion="Check AI interpreter implementation",
                context={"error": str(exc)},
            )],
        ))
    elapsed = time.perf_counter() - start
    return PhaseResult(phase="ai", validator_outputs=outputs, execution_time=elapsed)
```

### Clearinghouse Phase: Duck-Typed Interface

There is NO `BaseClearinghouseClient` ABC in the codebase yet. The architecture describes it as a planned component. For Story 2.3, the `clearinghouse_client` in `PipelineConfig` is typed `Any | None`. The BasePipeline calls `client.submit(input_data)` via duck typing.

For tests, use a simple mock object with a `submit()` method.

**IMPORTANT:** Do NOT create a BaseClearinghouseClient ABC — that's a domain concern for Epic 3 / eligibility module. The shared pipeline just calls whatever interface the domain provides.

### AI Phase: Duck-Typed Interface

The existing codebase has TWO AI patterns:
1. **Claims**: `BaseAIValidator.validate_deidentified(deidentified) -> ValidatorOutput`
2. **Eligibility/PA**: `Interpreter.interpret(deidentified) -> tuple[str, list[Finding]]`

For Story 2.3, the BasePipeline uses the `validate_deidentified()` interface (claims pattern) since `BaseAIValidator` already exists. In Epic 3, eligibility/PA interpreters will be adapted to conform to this interface (or an adapter will wrap them).

The `ai_interpreter` config field is typed `Any` to allow either pattern. For Story 2.3 tests, use mock objects that implement `validate_deidentified()`.

### Existing Models to Reuse (DO NOT RECREATE)

| Model | File | Usage in BasePipeline |
|-------|------|----------------------|
| `Finding` | `models/results.py` | Individual validation finding |
| `ValidatorOutput` | `models/results.py` | Output from a single validator |
| `PhaseResult` | `models/results.py` | Result from one phase (rule/clearinghouse/AI) |
| `PipelineResult` | `models/results.py` | Aggregated result from full pipeline |
| `Severity` | `constants.py` | ERROR/WARNING enum |
| `LLMError` | `exceptions.py` | LLM provider failure exception |
| `BaseValidator` | `validators/base.py` | ABC for rule-based validators |
| `BaseDeidentifier` | `shared/deidentifier/base.py` | De-identification engine |

All of these already exist and MUST be imported, NOT recreated.

### Existing Pipeline Comparison (Context Only)

| Aspect | Claims `ValidationPipeline` | Eligibility/PA Pipelines |
|--------|---------------------------|--------------------------|
| **Phases** | rule_based → ai | rule_based → ai |
| **Rule result** | `PhaseResult` (structured) | Flat `list[Finding]` |
| **AI component** | `list[BaseAIValidator]` | Single interpreter |
| **AI return** | `ValidatorOutput` | `tuple[str, list[Finding]]` |
| **Result type** | `PipelineResult` | `EligibilityResult` / `PriorAuthResult` |
| **Clearinghouse** | None (N/A for claims) | Called OUTSIDE pipeline in `_api.py` |
| **Deidentifier** | `ClaimDeidentifier.deidentify(claim)` | `EligibilityDeidentifier.deidentify(response)` |

The BasePipeline uses `PipelineResult` (structured PhaseResult approach) for ALL domains. In Epic 3, domain APIs will convert `PipelineResult` to domain-specific results as needed.

### Gating Logic (AC-3, AC-4)

Two gating rules, each independent:
1. **`skip_clearinghouse_on_rule_failure`**: If rule phase has ERRORs, skip clearinghouse phase. When clearinghouse is skipped, AI is ALSO skipped (cascade).
2. **`skip_ai_on_rule_failure`**: If rule phase has ERRORs, skip AI phase (even if clearinghouse ran successfully).

Cascade behavior: If clearinghouse is skipped due to gating, AI is always skipped too (per AC-3: "it skips clearinghouse AND AI").

### D43: Clean Break

- Story 2.3 ONLY creates new files in `shared/pipeline/`
- Does NOT modify existing domain pipelines (`validators/pipeline.py`, `eligibility/pipeline.py`, `prior_auth/pipeline.py`)
- Does NOT modify existing result models (`models/results.py`)
- Does NOT modify existing validators
- Does NOT modify `conf.py`
- Does NOT create `shared/pipeline/context.py` — that's Story 4.1 (ValidationContext)

### What Story 2.3 Must NOT Create/Modify

- Do NOT modify existing domain pipelines — Epic 3 refactors them
- Do NOT modify `models/results.py` — reuse existing models as-is
- Do NOT modify `validators/base.py` or `validators/ai/base.py`
- Do NOT modify `conf.py` — Epic 4
- Do NOT create `shared/pipeline/context.py` — Story 4.1 (ValidationContext)
- Do NOT create domain pipeline builders (e.g., `build_claim_pipeline()`) — Epic 3
- Do NOT import domain models (`ClaimData`, `EligibilityRequest`, etc.) in shared/pipeline/

### ValidationContext — NOT IN SCOPE

`ValidationContext` (D37) is Story 4.1. The `run()` method in Story 2.3 does NOT accept a `validation_context` parameter. That parameter will be added in Story 4.1 when passthrough logic is implemented.

### Previous Story Intelligence

**Story 2.1 (BaseDeidentifier and domain configurations):**
- Pattern: `__init__(config)` with frozen dataclass config → single `deidentify()` method
- `BaseDeidentifier.deidentify()` operates on `dict[str, Any]` — shallow copy via `{**data}`
- Import: `from claim_validator.shared.deidentifier.base import BaseDeidentifier`
- Import: `from claim_validator.shared.deidentifier.config import DeidentificationConfig`
- Code review fix: added `__post_init__` validation to prevent config overlap
- Learnings: `from __future__ import annotations` on ALL new files, run ruff on ALL files including tests

**Story 2.2 (HIPAA compliance verification):**
- Tests-only story, no impact on 2.3 source code
- Total test count after 2.2: 1970 tests (baseline for regression check)
- Learnings: PHI-safe error messages — reference field names only, never values (FR40)

**Story 1.1-1.4 Learnings (accumulated):**
- Use `.venv/bin/python -m pytest` (NOT `.venv/bin/pytest` — stale shebang)
- Run ruff on ALL files including test files
- `Callable` must be from `collections.abc` not `typing` (ruff UP035)
- Defensive dict copy: `{**data}` to avoid mutating caller's dict
- `collections.abc` sorts before `dataclasses` in imports
- D43 compliance: create new files only, leave existing code untouched

### Quality Requirements

- **ruff** — run on ALL new files (source + test); line-length=100, rules E/F/I/N/W/UP
- **pytest** — all new + all existing tests must pass (1970+ baseline)
- **Docstrings** — module-level AND class/function-level on all public APIs (NFR27)
- **`from __future__ import annotations`** — on ALL new files
- **Stateless pipeline** — `run()` never mutates `input_data` or config (NFR12, NFR13)
- **Thread-safe** — no shared mutable state; `PipelineConfig` is frozen (NFR12)

### Testing Strategy

**Test file structure:**
- `tests/test_shared/test_pipeline/__init__.py`
- `tests/test_shared/test_pipeline/test_config.py` — PipelineConfig creation, immutability, defaults
- `tests/test_shared/test_pipeline/test_engine.py` — BasePipeline phase execution, gating, timing, error handling

**Test fixtures — mock validators:**
```python
class PassingValidator(BaseValidator):
    name = "passing"
    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[])

class FailingValidator(BaseValidator):
    name = "failing"
    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[
            Finding(code="TEST_ERROR", message="Test failure", severity=Severity.ERROR, field_name="test_field"),
        ])

class WarningValidator(BaseValidator):
    name = "warning"
    def validate(self, data: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[
            Finding(code="TEST_WARNING", message="Test warning", severity=Severity.WARNING, field_name="test_field"),
        ])

class ExplodingValidator(BaseValidator):
    name = "exploding"
    def validate(self, data: Any) -> ValidatorOutput:
        raise RuntimeError("boom")
```

**Mock clearinghouse client:**
```python
class MockClearinghouseClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.called = False
        self._should_fail = should_fail

    def submit(self, data: Any) -> Any:
        self.called = True
        if self._should_fail:
            raise RuntimeError("Clearinghouse error")
        return {"status": "ok"}
```

**Mock AI interpreter:**
```python
class MockAIInterpreter:
    name = "mock_ai"
    def __init__(self, should_fail: bool = False, fail_with_llm_error: bool = False) -> None:
        self.called = False
        self._should_fail = should_fail
        self._fail_with_llm_error = fail_with_llm_error

    def validate_deidentified(self, data: Any) -> ValidatorOutput:
        self.called = True
        if self._fail_with_llm_error:
            raise LLMError("LLM unavailable")
        if self._should_fail:
            raise RuntimeError("AI error")
        return ValidatorOutput(validator_name=self.name, findings=[])
```

**Test classes:**

1. **TestPipelineConfigCreation** — creation with all fields, defaults, immutability, field types
2. **TestPipelineConfigDefaults** — default values for optional fields
3. **TestBasePipelineRulePhase** — passing validators, failing validators, mixed, exception handling, timing
4. **TestBasePipelineClearinghousePhase** — clearinghouse called when configured, skipped when None, error handling
5. **TestBasePipelineAIPhase** — AI called when configured, skipped when None, de-identification invoked, LLMError → WARNING, generic error → ERROR
6. **TestBasePipelineGating** — skip clearinghouse on rule failure, skip AI on rule failure, cascade (clearinghouse skipped → AI skipped), no gating when rules pass, no gating when gating disabled
7. **TestBasePipelineTiming** — total execution_time > 0, per-phase execution_time > 0, total >= sum of phases
8. **TestBasePipelineResultStructure** — PipelineResult has correct phase names, passed property reflects findings, findings flat list correct
9. **TestBasePipelineEdgeCases** — empty validators tuple, no phases configured (validators empty + no clearinghouse + no AI), input data not mutated

### References

- [Source: architecture.md — D36: Shared pipeline engine, BasePipeline + PipelineConfig]
- [Source: architecture.md — D37: ValidationContext (Story 4.1, NOT this story)]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: architecture.md — Enforcement Guideline #5: domain pipelines create BasePipeline with config, never subclass run()]
- [Source: architecture.md — v3.0 Directory Structure: shared/pipeline/]
- [Source: epics.md — Epic 2, Story 2.3 acceptance criteria]
- [Source: epics.md — FR14: Configurable multi-phase pipeline]
- [Source: epics.md — FR15: Phase gating]
- [Source: epics.md — FR16: Per-phase timing]
- [Source: epics.md — FR17: Domain-specific pipeline config]
- [Source: validators/pipeline.py — Existing ValidationPipeline (claims) implementation]
- [Source: eligibility/pipeline.py — Existing EligibilityPipeline implementation]
- [Source: prior_auth/pipeline.py — Existing PriorAuthPipeline implementation]
- [Source: models/results.py — Finding, ValidatorOutput, PhaseResult, PipelineResult models]
- [Source: constants.py — Severity enum (ERROR, WARNING)]
- [Source: exceptions.py — LLMError exception class]
- [Source: validators/base.py — BaseValidator ABC]
- [Source: validators/ai/base.py — BaseAIValidator ABC]
- [Source: 2-1-basedeidentifier-and-domain-configurations.md — Previous story learnings]
- [Source: 2-2-hipaa-compliance-verification.md — Previous story learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Ruff check: All checks passed on source and test files (after auto-fix for import sorting)
- New tests: 64 passed in 0.88s (pre-review)
- Full regression: 2034 passed in 7.10s (pre-review)
- Code review: 3 MEDIUM + 3 LOW issues found, 3 MEDIUM fixed
- Post-review tests: 69 passed in 0.87s (64 original + 5 review fixes)
- Post-review regression: 2039 passed in 6.93s (1970 existing + 69 new, zero regressions)

### Completion Notes List

- Created `shared/pipeline/` package with 3 source files: `__init__.py`, `config.py`, `engine.py`
- `PipelineConfig`: frozen dataclass with 8 fields — `domain`, `validators`, `clearinghouse_client`, `ai_interpreter`, `deidentifier`, `skip_ai_on_rule_failure`, `skip_clearinghouse_on_rule_failure`, `code_prefix`
- `BasePipeline`: 3-phase engine (rule-based → clearinghouse → AI) with gating, timing, and error handling
- Gating logic: two independent gates + cascade (clearinghouse skip → AI skip per AC-3)
- Exception handling: validator exception → ERROR finding, LLMError → WARNING finding, generic AI error → ERROR finding
- Duck-typed interfaces for clearinghouse (`submit()`) and AI (`validate_deidentified()`)
- De-identification before AI call (FR40) — input data never mutated
- Reuses all existing models: Finding, ValidatorOutput, PhaseResult, PipelineResult, Severity, LLMError, BaseValidator, BaseDeidentifier
- No existing files modified (D43 clean break)
- `__post_init__` validation: raises ValueError when ai_interpreter set without deidentifier (FR40 enforcement)
- 69 tests across 10 test classes covering all 11 ACs (64 original + 5 code review additions)
- All 11 ACs satisfied
- Code review fixes: `__post_init__` PHI safety (#1), deidentifier error attribution (#2), AI findings propagation test (#3)

### Change Log

- 2026-03-03: Story 2.3 implemented — BasePipeline and PipelineConfig (3 source files, 64 tests)
- 2026-03-03: Code review fixes — 3 MEDIUM issues resolved (69 tests after adding __post_init__ validation, deidentifier error separation, AI findings propagation test)

### File List

- `src/claim_validator/shared/pipeline/__init__.py` — NEW (re-exports BasePipeline, PipelineConfig)
- `src/claim_validator/shared/pipeline/config.py` — NEW (PipelineConfig frozen dataclass)
- `src/claim_validator/shared/pipeline/engine.py` — NEW (BasePipeline 3-phase engine)
- `tests/test_shared/test_pipeline/__init__.py` — NEW (empty)
- `tests/test_shared/test_pipeline/test_config.py` — NEW (23 tests)
- `tests/test_shared/test_pipeline/test_engine.py` — NEW (41 tests)
