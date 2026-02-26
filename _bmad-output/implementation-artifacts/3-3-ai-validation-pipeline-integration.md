# Story 3.3: AI Validation Pipeline Integration

Status: review

## Story

As a **developer**,
I want AI validators to run as the second phase of the pipeline with automatic de-identification,
so that I can get AI-powered clinical insights with zero manual PHI handling.

## Acceptance Criteria

1. **Given** a `ClaimValidatorSettings` with `ai_config` configured, **When** `validate(claim_dict, ai_config={"provider": "anthropic", "api_key": "sk-...", "model": "..."})` is called, **Then** Phase 1 (rule-based) runs first, then Phase 2 (AI) runs with de-identified claim data, **And** the `PipelineResult` contains findings from both phases.

2. **Given** `skip_ai_on_rule_failure=True` (default) and rule-based validation produced ERROR findings, **When** the pipeline reaches the AI phase gate, **Then** AI validators are skipped entirely, **And** the `PipelineResult` includes only rule-based findings.

3. **Given** `skip_ai_on_rule_failure=False` and rule-based validation produced ERROR findings, **When** the pipeline reaches the AI phase gate, **Then** AI validators still run and their findings are appended to the result.

4. **Given** the LLM provider is unreachable or returns an error, **When** AI validators attempt to call the provider, **Then** the pipeline returns rule-based results plus a `Finding(code="AI_PROVIDER_ERROR", severity=WARNING)` with the error context, **And** no exception is propagated to the caller.

5. **Given** the `BaseAIValidator` base class, **When** an AI validator is constructed by the pipeline, **Then** it receives a pre-configured `BaseLLMClient` instance via constructor injection, **And** `self._send_to_llm(messages)` helper is available for sending messages.

6. **Given** any AI validator in the pipeline, **When** it receives claim data, **Then** the data is always a `DeidentifiedClaim` (de-identification happens once in the pipeline, before all AI validators).

## Tasks / Subtasks

- [x] Task 1: Create `BaseAIValidator` ABC in `src/claim_validator/validators/ai/base.py` (AC: #5)
  - [x] `BaseAIValidator(BaseValidator)` with `llm_client: BaseLLMClient` constructor injection
  - [x] Abstract `validate_deidentified(claim: DeidentifiedClaim) -> ValidatorOutput`
  - [x] `validate(claim: ClaimData)` override raises `NotImplementedError` (AI validators use `validate_deidentified()`)
  - [x] `_send_to_llm(messages: list[Message]) -> str` helper delegating to `self._llm_client.send_messages()`
  - [x] `name` class attribute required (inherited from BaseValidator contract)
- [x] Task 2: Add `create_ai_validators()` method to `ValidatorRegistry` in `src/claim_validator/validators/registry.py` (AC: #5)
  - [x] `create_ai_validators(paths: list[str], *, llm_client: BaseLLMClient) -> list[BaseAIValidator]`
  - [x] Import classes via dotted paths (same mechanism as `create_validators()`)
  - [x] Inject `llm_client` into each AI validator constructor
  - [x] Raise `ConfigurationError` if resolved class is not a `BaseAIValidator` subclass
- [x] Task 3: Modify `ValidationPipeline` in `src/claim_validator/validators/pipeline.py` (AC: #1, #2, #3, #4, #6)
  - [x] Change `ai_validators` type hint from `list[BaseValidator]` to `list[BaseAIValidator]`
  - [x] Add `_run_ai_phase(claim: DeidentifiedClaim) -> PhaseResult` method
  - [x] In `run()`: call `ClaimDeidentifier.deidentify(claim)` once before AI phase
  - [x] In `_run_ai_phase()`: call `validator.validate_deidentified(deidentified_claim)` for each AI validator
  - [x] Catch `LLMError` specifically → `Finding(code="AI_PROVIDER_ERROR", severity=WARNING)` — no exception propagated
  - [x] Catch general `Exception` → `Finding(code="VALIDATOR_ERROR", severity=ERROR)` (same as rule-based)
  - [x] Modify `from_settings()`: create LLM client from `ai_config` via `get_llm_client()`, call `registry.create_ai_validators()` with client
  - [x] Guard: only create LLM client if both `ai_config` and `ai_validators` are non-empty
- [x] Task 4: Update `validate()` in `src/claim_validator/_api.py` (AC: #1)
  - [x] Add `ai_config: dict[str, Any] | None = None` keyword parameter
  - [x] If `ai_config` provided without `settings`: create `ClaimValidatorSettings(ai_config=ai_config)`
  - [x] If `ai_config` provided with `settings`: use `settings.model_copy(update={"ai_config": ai_config})`
  - [x] If only `settings` provided: use as-is (existing behavior)
- [x] Task 5: Update exports and re-exports (AC: all)
  - [x] `validators/ai/__init__.py` → export `BaseAIValidator`
  - [x] `validators/__init__.py` → add `BaseAIValidator` to exports
  - [x] Top-level `__init__.py` → add `BaseAIValidator` to `__all__` and imports
- [x] Task 6: Write `BaseAIValidator` tests in `tests/test_validators/test_ai/test_base_ai_validator.py` (AC: #5)
  - [x] Test `BaseAIValidator` is abstract (cannot instantiate directly)
  - [x] Test `validate_deidentified()` is abstract method
  - [x] Test `validate()` raises `NotImplementedError`
  - [x] Test `llm_client` injection via constructor
  - [x] Test `_send_to_llm()` delegates to `llm_client.send_messages()`
  - [x] Test concrete subclass with implementation works
  - [x] Test `name` attribute is required
- [x] Task 7: Write pipeline AI phase tests in `tests/test_validators/test_pipeline_ai.py` (AC: #1, #2, #3, #4, #6)
  - [x] Test two-phase execution: rule-based + AI, both in PipelineResult
  - [x] Test `skip_ai_on_rule_failure=True` + rule ERRORs → AI phase skipped
  - [x] Test `skip_ai_on_rule_failure=True` + rule WARNINGs only → AI phase runs
  - [x] Test `skip_ai_on_rule_failure=False` + rule ERRORs → AI phase still runs
  - [x] Test LLM error → `AI_PROVIDER_ERROR` WARNING finding, no exception raised
  - [x] Test de-identification called once before all AI validators
  - [x] Test AI validators receive `DeidentifiedClaim` (not `ClaimData`)
  - [x] Test `from_settings()` with `ai_config` creates LLM client and AI validators
  - [x] Test `from_settings()` without `ai_config` creates empty AI validators list
  - [x] Test no AI validators → single-phase result (existing behavior preserved)
- [x] Task 8: Write `validate()` integration tests in `tests/test_api_ai.py` (AC: #1)
  - [x] Test `validate(claim, ai_config={...})` runs both phases
  - [x] Test `validate(claim)` without `ai_config` runs rule-only (regression)
  - [x] Test `validate(claim, settings=settings, ai_config={...})` merges correctly
- [x] Task 9: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors (41 source files)
  - [x] `uv run pytest` — 626 tests pass (580 existing + 46 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### uv PATH

```bash
export PATH="$HOME/snap/code/225/.local/bin:$PATH"
```

### Previous Story Intelligence (Story 3.2)

- 580 tests pass (521 existing + 59 new), ruff clean, mypy clean (40 source files)
- `BaseLLMClient`, `Message`, `get_llm_client` all implemented and exported at top-level
- Provider tests mock SDK imports via `sys.modules` + `importlib.import_module()` to avoid requiring actual SDKs
- Line-length limit is 100 characters — wrap long strings with implicit concatenation
- Test pattern: class-based tests with `setup_method`, helper functions for test data
- ruff catches unused imports (F401), unsorted imports (I001)
- `head`, `tail`, and `tee` commands unavailable in sandbox — don't pipe to them
- Factory import-error tests required clearing `sys.modules` before patching — module caching is a real issue

### Current State of Key Files

| File | Status | Notes |
|---|---|---|
| `validators/ai/__init__.py` | **EMPTY** (0 bytes) | Needs `BaseAIValidator` export |
| `validators/ai/base.py` | **DOES NOT EXIST** | Needs `BaseAIValidator` ABC — the primary deliverable |
| `validators/pipeline.py` | **Complete** (rule-based + AI gate) | Needs AI phase with de-identification + LLM error handling |
| `validators/registry.py` | **Complete** | Needs `create_ai_validators(paths, llm_client=...)` method |
| `validators/base.py` | **Complete** | `BaseValidator` ABC — parent of `BaseAIValidator` |
| `_api.py` | **Complete** | `validate()` needs `ai_config` parameter |
| `llm/base.py` | **Complete** | `BaseLLMClient` ABC, `Message` dataclass |
| `llm/factory.py` | **Complete** | `get_llm_client()` — used by pipeline to create LLM client |
| `deidentifier/deidentifier.py` | **Complete** | `ClaimDeidentifier.deidentify(claim) -> DeidentifiedClaim` |
| `models/deidentified.py` | **Complete** | `DeidentifiedClaim` with `is_deidentified` property |
| `models/results.py` | **Complete** | `Finding`, `ValidatorOutput`, `PhaseResult`, `PipelineResult` |
| `conf.py` | **Complete** | `ai_config`, `ai_validators`, `skip_ai_on_rule_failure` already defined |
| `exceptions.py` | **Complete** | `LLMError(ClaimValidatorError)` already defined |
| `constants.py` | **Complete** | `Severity.ERROR`, `Severity.WARNING` |

### Implementation Spec

```python
# src/claim_validator/validators/ai/base.py
"""BaseAIValidator — abstract base for AI-powered validators."""

from __future__ import annotations

import abc

from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator

# Import ClaimData only for type checking (validate() override)
from claim_validator.models.claim import ClaimData


class BaseAIValidator(BaseValidator):
    """Abstract base class for AI-powered validators.

    AI validators receive a pre-configured LLM client via
    constructor injection and operate on de-identified claim data.
    The pipeline handles de-identification automatically.

    Subclass this, set ``name``, and implement ``validate_deidentified()``.
    """

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm_client = llm_client

    @abc.abstractmethod
    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Validate a de-identified claim using LLM analysis.

        Args:
            claim: HIPAA-safe de-identified claim data.

        Returns:
            ValidatorOutput with any AI-detected findings.
        """

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        """Not used directly — AI validators use validate_deidentified().

        The pipeline calls validate_deidentified() with a
        DeidentifiedClaim. This override exists for BaseValidator
        ABC compatibility.
        """
        raise NotImplementedError(
            "AI validators must be invoked via "
            "validate_deidentified(). The pipeline handles "
            "de-identification automatically."
        )

    def _send_to_llm(self, messages: list[Message]) -> str:
        """Send messages to the configured LLM provider.

        Raises:
            LLMError: If the provider returns an error.
        """
        return self._llm_client.send_messages(messages)
```

```python
# Additions to src/claim_validator/validators/registry.py

def create_ai_validators(
    self,
    paths: list[str],
    *,
    llm_client: BaseLLMClient,
) -> list[BaseAIValidator]:
    """Create AI validator instances with LLM client injection.

    Args:
        paths: Dotted class paths for AI validators.
        llm_client: Pre-configured LLM client to inject.

    Returns:
        List of instantiated AI validators.

    Raises:
        ConfigurationError: If class is not a BaseAIValidator subclass.
    """
    from claim_validator.validators.ai.base import BaseAIValidator
    validators: list[BaseAIValidator] = []
    for path in paths:
        cls = self._resolve_class(path)
        if not issubclass(cls, BaseAIValidator):
            raise ConfigurationError(
                f"{path} is not a BaseAIValidator subclass"
            )
        validators.append(cls(llm_client=llm_client))
    return validators
```

```python
# Modified run() in ValidationPipeline (pipeline.py)
# Key changes to the AI phase:

def run(self, claim: ClaimData) -> PipelineResult:
    start = time.perf_counter()
    phase_results: list[PhaseResult] = []

    # Phase 1: Rule-based
    rule_phase = self._run_phase(
        "rule_based", self._rule_validators, claim,
    )
    phase_results.append(rule_phase)

    # Phase 2: AI (conditional)
    if self._ai_validators:
        rule_has_errors = any(
            f.severity == Severity.ERROR
            for f in rule_phase.findings
        )
        if not rule_has_errors or not self._skip_ai_on_rule_failure:
            deidentified = ClaimDeidentifier.deidentify(claim)
            ai_phase = self._run_ai_phase(deidentified)
            phase_results.append(ai_phase)

    elapsed = time.perf_counter() - start
    return PipelineResult(
        phase_results=phase_results,
        execution_time=elapsed,
    )

def _run_ai_phase(
    self,
    claim: DeidentifiedClaim,
) -> PhaseResult:
    """Run AI validators with de-identified claim data."""
    start = time.perf_counter()
    outputs: list[ValidatorOutput] = []

    for validator in self._ai_validators:
        try:
            output = validator.validate_deidentified(claim)
            outputs.append(output)
        except LLMError as exc:
            # Graceful degradation: LLM errors → WARNING, not ERROR
            outputs.append(
                ValidatorOutput(
                    validator_name=validator.name,
                    findings=[
                        Finding(
                            code="AI_PROVIDER_ERROR",
                            message=(
                                "AI validation unavailable"
                            ),
                            severity=Severity.WARNING,
                            field_name="",
                            suggestion=(
                                "Rule-based results are still"
                                " valid. Retry when the AI"
                                " provider is available."
                            ),
                            context={"error": str(exc)},
                        ),
                    ],
                )
            )
        except Exception as exc:
            outputs.append(
                ValidatorOutput(
                    validator_name=getattr(
                        validator, "name",
                        type(validator).__name__,
                    ),
                    findings=[
                        Finding(
                            code="VALIDATOR_ERROR",
                            message=(
                                "Validator raised an"
                                " unexpected exception"
                            ),
                            severity=Severity.ERROR,
                            field_name="",
                            suggestion=(
                                "Check validator"
                                " implementation"
                            ),
                            context={"error": str(exc)},
                        ),
                    ],
                )
            )

    elapsed = time.perf_counter() - start
    return PhaseResult(
        phase="ai",
        validator_outputs=outputs,
        execution_time=elapsed,
    )
```

```python
# Modified from_settings() in ValidationPipeline
@classmethod
def from_settings(
    cls,
    settings: ClaimValidatorSettings | None = None,
) -> ValidationPipeline:
    """Create a pipeline from settings."""
    if settings is None:
        settings = ClaimValidatorSettings()
    registry = ValidatorRegistry()
    rule_vals = registry.create_validators(settings.rule_validators)

    ai_vals: list[BaseAIValidator] = []
    if settings.ai_config and settings.ai_validators:
        from claim_validator.llm.factory import get_llm_client
        llm_client = get_llm_client(
            settings.ai_config["provider"],
            api_key=settings.ai_config["api_key"],
            model=settings.ai_config["model"],
            **{
                k: v
                for k, v in settings.ai_config.items()
                if k not in ("provider", "api_key", "model")
            },
        )
        ai_vals = registry.create_ai_validators(
            settings.ai_validators,
            llm_client=llm_client,
        )

    return cls(
        rule_validators=rule_vals,
        ai_validators=ai_vals,
        skip_ai_on_rule_failure=settings.skip_ai_on_rule_failure,
    )
```

```python
# Modified validate() in _api.py
def validate(
    claim: dict[str, Any] | ClaimData,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
) -> PipelineResult:
    """Validate a healthcare claim and return structured results.

    Args:
        claim: Claim data as a dict or ClaimData instance.
        settings: Optional settings. Uses defaults if None.
        ai_config: Optional AI provider config dict.
            Keys: provider, api_key, model (+ provider-specific).
            Overrides settings.ai_config if both provided.

    Returns:
        PipelineResult with findings from all validators.
    """
    if isinstance(claim, dict):
        claim_data = ClaimData(**claim)
    else:
        claim_data = claim

    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(
                update={"ai_config": ai_config},
            )
        else:
            settings = ClaimValidatorSettings(
                ai_config=ai_config,
            )

    pipeline = ValidationPipeline.from_settings(settings)
    return pipeline.run(claim_data)
```

### Key Design Decisions

- **`BaseAIValidator` extends `BaseValidator`** — inherits `name`, `_make_output()`, `_make_finding()` helpers
- **`validate_deidentified()` is the abstract method** (not `validate()`) — AI validators work with `DeidentifiedClaim`, not `ClaimData`. `validate()` raises `NotImplementedError` for safety
- **Constructor injection for LLM client** — pipeline creates the client from `ai_config`, injects into each AI validator. Validators don't know about configuration
- **De-identification in pipeline, not validators** — `ClaimDeidentifier.deidentify()` called once before the AI loop. All AI validators get the same `DeidentifiedClaim` instance
- **`LLMError` caught separately from `Exception`** — LLM failures → `AI_PROVIDER_ERROR` with `WARNING` severity (graceful degradation). Other exceptions → `VALIDATOR_ERROR` with `ERROR` severity
- **Registry gets `create_ai_validators()` method** — separate from `create_validators()` because AI validators need `llm_client` injection. Validates `issubclass(cls, BaseAIValidator)`
- **`validate()` function gets `ai_config` parameter** — convenience for passing AI config without constructing full settings. Uses `model_copy(update=...)` to merge with existing frozen settings
- **Lazy LLM import in `from_settings()`** — `from claim_validator.llm.factory import get_llm_client` inside the method body to avoid importing optional dependencies at pipeline import time

### Anti-Patterns to Avoid

- **DO NOT** have AI validators call `ClaimDeidentifier` themselves — pipeline handles it
- **DO NOT** pass `ClaimData` to AI validators — always `DeidentifiedClaim`
- **DO NOT** let `LLMError` propagate to caller — catch in pipeline, convert to WARNING finding
- **DO NOT** import `get_llm_client` at module top of `pipeline.py` — it imports from `llm/` which has optional deps
- **DO NOT** create LLM client if `ai_config` is None or `ai_validators` is empty — guard both conditions
- **DO NOT** modify `BaseValidator.validate()` signature — `BaseAIValidator` adds `validate_deidentified()` alongside
- **DO NOT** store state between `validate_deidentified()` calls — AI validators must be stateless
- **DO NOT** include PHI in `AI_PROVIDER_ERROR` finding messages — the error context should only contain the exception string from the LLM provider
- **DO NOT** add retry logic in the pipeline — let consumers handle retries

### Testing Strategy

All tests use mock objects — no real LLM API calls:

```python
# Mock AI validator for pipeline tests
class MockAIValidator(BaseAIValidator):
    name = "mock_ai"

    def validate_deidentified(
        self, claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        return self._make_output([
            self._make_finding(
                code="AI_MOCK_FINDING",
                message="Mock AI finding",
                severity=Severity.WARNING,
                field_name="procedure_code",
            ),
        ])

# Mock LLM client for BaseAIValidator tests
class MockLLMClient(BaseLLMClient):
    provider_name = "mock"

    def send_messages(self, messages: list[Message]) -> str:
        return "mock response"

# For LLM error tests
class FailingLLMClient(BaseLLMClient):
    provider_name = "failing"

    def send_messages(self, messages: list[Message]) -> str:
        raise LLMError("Connection refused")

# For pipeline from_settings tests, mock get_llm_client:
@patch("claim_validator.validators.pipeline.get_llm_client")
def test_from_settings_with_ai_config(mock_factory):
    mock_client = MockLLMClient(model="m", api_key="k")
    mock_factory.return_value = mock_client
    settings = ClaimValidatorSettings(
        ai_config={
            "provider": "anthropic",
            "api_key": "sk-test",
            "model": "claude-sonnet-4-5-20241022",
        },
        ai_validators=[
            "tests.helpers.MockAIValidator",  # registered in test
        ],
    )
    pipeline = ValidationPipeline.from_settings(settings)
    # Assert LLM client was created with correct args
    mock_factory.assert_called_once_with(
        "anthropic",
        api_key="sk-test",
        model="claude-sonnet-4-5-20241022",
    )
```

**Test file structure:**

```
tests/
├── test_validators/
│   ├── test_ai/
│   │   ├── __init__.py              # already exists (empty)
│   │   └── test_base_ai_validator.py  # NEW — BaseAIValidator tests
│   └── test_pipeline_ai.py           # NEW — AI phase integration tests
└── test_api_ai.py                     # NEW — validate() with ai_config tests
```

**IMPORTANT test considerations:**
- Use `conftest.py` fixtures for shared test data (valid claim dicts, deidentified claims)
- Mock `ClaimDeidentifier.deidentify()` in pipeline tests to verify it's called exactly once
- Mock `ValidatorRegistry.create_ai_validators()` in `from_settings()` tests
- Test that existing rule-based-only pipeline behavior is NOT broken (regression)
- For `validate()` function tests, mock `ValidationPipeline.from_settings()` to avoid needing real validators

### Project Structure Notes

- `BaseAIValidator` goes in `validators/ai/base.py` — matches architecture doc's source tree
- `validators/ai/__init__.py` is empty — needs `BaseAIValidator` export
- Test directory `tests/test_validators/test_ai/` already exists as an empty package
- No new dependencies — all imports are within the `claim_validator` package

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **D5** | Pipeline-integrated de-identification — `ClaimDeidentifier.deidentify()` called once before AI phase |
| **D6** | Type-driven PHI boundary — AI validators receive `DeidentifiedClaim`, not `ClaimData` |
| **D7** | Chat-based LLM interface — `BaseLLMClient.send_messages(messages)` consumed by `_send_to_llm()` |
| **D10** | Dotted path validator registry — `create_ai_validators()` uses same import mechanism |
| **D11** | Pipeline composition — `from_settings()` handles LLM client creation from `ai_config` |
| **FR3** | AI-powered validation by providing LLM config |
| **FR4** | Configurable skip of AI on rule failure |
| **FR18-FR22** | AI validation with automatic de-identification |
| **FR28** | Custom validators via subclassing (`BaseAIValidator`) |
| **FR29** | Register custom validators via config (dotted paths in `ai_validators`) |
| **FR32** | Two-phase execution: rule-based first, AI second |
| **FR33** | Aggregate results into single PipelineResult |
| **NFR17** | Graceful AI degradation — LLM failures → WARNING, not crash |
| **NFR18** | AI findings are WARNING severity (suggestions, not blocking errors) |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3] — Acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#D5 D6] — De-identification position and PHI boundary enforcement
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline execution model] — Two-phase flow with de-identification
- [Source: _bmad-output/planning-artifacts/architecture.md#Gap Resolution] — `BaseAIValidator(BaseValidator)` in `validators/ai/base.py`
- [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns] — LLMError → graceful degradation with warning
- [Source: _bmad-output/planning-artifacts/prd.md#FR3-FR4] — AI validation configuration
- [Source: _bmad-output/planning-artifacts/prd.md#FR18-FR22] — AI validation with de-identification
- [Source: _bmad-output/planning-artifacts/prd.md#NFR17-NFR18] — Graceful degradation, AI findings as warnings
- [Source: _bmad-output/implementation-artifacts/3-2-llm-provider-abstraction-factory.md] — Previous story intelligence

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- RED phase: BaseAIValidator test initially had wrong mock response ("No issues found" contains "issue") — fixed to "All checks passed"
- RED phase: Pipeline AI tests mocked wrong path (`pipeline.get_llm_client` instead of `llm.factory.get_llm_client`) — fixed since get_llm_client is imported lazily inside from_settings()
- Ruff: 6 auto-fixed issues — F401 (unused imports: pytest, ClaimData, Finding), I001 (import sorting in 2 test files)

### Completion Notes List

- 626 tests pass (580 existing + 46 new), ruff clean, mypy clean (41 source files)
- BaseAIValidator ABC with llm_client injection and validate_deidentified() abstract method
- Pipeline AI phase: deidentify once → run all AI validators on DeidentifiedClaim
- LLMError → AI_PROVIDER_ERROR WARNING (graceful degradation), generic Exception → VALIDATOR_ERROR ERROR
- from_settings() creates LLM client from ai_config via get_llm_client() factory with lazy import
- validate() function gains ai_config parameter; uses model_copy() to merge with frozen settings
- BaseAIValidator exported at all levels: validators/ai/__init__.py, validators/__init__.py, top-level __init__.py
- Zero regressions: all 35 existing pipeline tests + 17 existing API tests pass unchanged

### File List

- `src/claim_validator/validators/ai/base.py` — NEW: BaseAIValidator ABC with llm_client injection, validate_deidentified(), _send_to_llm()
- `src/claim_validator/validators/ai/__init__.py` — MODIFIED: Export BaseAIValidator
- `src/claim_validator/validators/__init__.py` — MODIFIED: Added BaseAIValidator to exports
- `src/claim_validator/validators/pipeline.py` — MODIFIED: AI phase with de-identification, _run_ai_phase(), LLMError handling, from_settings() with ai_config
- `src/claim_validator/validators/registry.py` — MODIFIED: Added create_ai_validators() with llm_client injection
- `src/claim_validator/_api.py` — MODIFIED: Added ai_config parameter to validate()
- `src/claim_validator/__init__.py` — MODIFIED: Added BaseAIValidator to top-level exports
- `tests/test_validators/test_ai/test_base_ai_validator.py` — NEW: 16 tests for BaseAIValidator
- `tests/test_validators/test_pipeline_ai.py` — NEW: 19 tests for AI phase integration
- `tests/test_validators/test_registry.py` — MODIFIED: Added 6 tests for create_ai_validators()
- `tests/test_api_ai.py` — NEW: 5 tests for validate() with ai_config

### Change Log

| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-19 | Create-story workflow |
| Implementation complete | 2026-02-19 | All 9 tasks done, 626 tests pass |
