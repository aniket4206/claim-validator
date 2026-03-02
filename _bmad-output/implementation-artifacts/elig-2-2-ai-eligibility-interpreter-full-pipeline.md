# Story ELIG-2.2: AI Eligibility Interpreter & Full Pipeline

Status: review

## Story

As a **developer**,
I want AI-powered interpretation that turns cryptic eligibility data into human-readable coverage summaries and actionable AAA error explanations,
so that my application can display clear eligibility information without my team learning X12 segment semantics.

## Acceptance Criteria

1. **Given** a de-identified eligibility response with active coverage and benefits, **when** `EligibilityInterpreterAI` processes it via the configured LLM, **then** `ai_summary` contains a human-readable coverage summary (e.g., "Patient has $40 copay for office visits, $2,500 annual deductible with $1,847 remaining, prior auth required for imaging") **and** AI-generated `Finding` objects with code prefix `AI_ELIG_` provide actionable insights about coverage limitations and requirements.

2. **Given** a de-identified eligibility response with AAA rejection errors, **when** `EligibilityInterpreterAI` processes it, **then** the AI interprets rejection codes into plain-English explanations with suggested next steps (e.g., "Patient's coverage under plan terminated — suggest verifying with patient for updated insurance information").

3. **Given** AI configuration with `provider="anthropic"` (or `"openai"` or `"openai_compatible"`), **when** I call `check_eligibility(request, ai_config={"provider": "anthropic", "api_key": "sk-..."}, response=eligibility_response)`, **then** the full pipeline executes: rule-based validation → de-identification → AI interpretation **and** `EligibilityResult` contains `eligible`, `response`, `findings` (from all phases), `ai_summary`, and `raw_response` populated.

4. **Given** `eligibility_skip_ai=True` in settings or no `ai_config` provided, **when** I call `check_eligibility(request)`, **then** the AI phase is skipped entirely **and** `EligibilityResult` has `ai_summary=None` and only rule-based findings.

5. **Given** the LLM provider is unreachable or returns an error, **when** the AI phase attempts to call the provider, **then** the pipeline returns the rule-based results plus a `Finding(code="AI_ELIG_PROVIDER_ERROR", severity=WARNING)` **and** no exception propagates to the caller — graceful degradation.

6. **Given** the de-identification step in the pipeline, **when** the AI phase begins, **then** `EligibilityDeidentifier.deidentify()` runs before any LLM call **and** only `DeidentifiedEligibilityResponse` data reaches the LLM provider.

7. **Given** AI interpretation using any configured LLM provider, **when** I switch providers via configuration (e.g., from Anthropic to OpenAI), **then** the pipeline works identically with the new provider — no code changes needed.

8. **Given** AI-generated findings, **when** I inspect them, **then** all use `AI_ELIG_` code prefix, severity is always `WARNING` (advisory, not authoritative) **and** no PHI appears in any finding message, suggestion, or the `ai_summary`.

## Tasks / Subtasks

- [x] Task 1: Create `EligibilityInterpreterAI` in `eligibility/validators/ai/interpreter.py` (AC: #1, #2, #7, #8)
  - [x] 1.1: Subclass `BaseAIValidator` — set `name = "EligibilityInterpreterAI"`
  - [x] 1.2: Implement `validate_deidentified` raising `NotImplementedError` (ABC requirement)
  - [x] 1.3: Implement `interpret(response: DeidentifiedEligibilityResponse) -> tuple[str, list[Finding]]` — returns `(ai_summary, findings)`
  - [x] 1.4: `SYSTEM_PROMPT` — instruct LLM to produce JSON `{"summary": ..., "findings": [...]}` from eligibility data
  - [x] 1.5: `_build_user_prompt(response)` — format de-identified coverage, benefits, errors into text
  - [x] 1.6: `_parse_response(text)` — JSON parse with free-text fallback (mirrors `CoverageCheckAI`)
  - [x] 1.7: All findings use `AI_ELIG_` prefix codes, `Severity.WARNING` only, no PHI in messages

- [x] Task 2: Extend `EligibilityPipeline` to support AI phase (AC: #3, #4, #5, #6)
  - [x] 2.1: Add `ai_interpreter: EligibilityInterpreterAI | None = None` and `skip_ai_on_rule_failure: bool = True` to `__init__`
  - [x] 2.2: Update `from_settings()` — create LLM client and AI interpreter when `ai_config` present and `eligibility_skip_ai` is False
  - [x] 2.3: Add `response: EligibilityResponse | None = None` parameter to `run()`
  - [x] 2.4: Phase 2 gate: if AI interpreter and response exist and (rules passed OR not skip_ai_on_rule_failure) → de-identify → interpret
  - [x] 2.5: Exception handling: `LLMError` → `AI_ELIG_PROVIDER_ERROR` WARNING finding (graceful degradation), generic `Exception` → `VALIDATOR_ERROR` ERROR
  - [x] 2.6: Merge AI findings into result, set `ai_summary`, set `eligible` and `response` from provided data

- [x] Task 3: Update `check_eligibility()` API (AC: #3, #4, #7)
  - [x] 3.1: Add `ai_config: dict[str, Any] | None = None` kwarg
  - [x] 3.2: Add `response: EligibilityResponse | None = None` kwarg (for pre-fetched 271 data)
  - [x] 3.3: Wire `ai_config` into settings (same pattern as `_api.py` in claims module)
  - [x] 3.4: Pass `response` to `pipeline.run(request_model, response=response)`

- [x] Task 4: Add default AI validator path to `conf.py` (AC: #3, #7)
  - [x] 4.1: Add `DEFAULT_ELIG_AI_VALIDATORS` constant with `EligibilityInterpreterAI` dotted path
  - [x] 4.2: Wire `eligibility_ai_validators` default to `DEFAULT_ELIG_AI_VALIDATORS`

- [x] Task 5: Update exports (AC: #3)
  - [x] 5.1: Add `EligibilityInterpreterAI` to `eligibility/validators/ai/__init__.py`
  - [x] 5.2: Add to `eligibility/__init__.py` and `__all__`

- [x] Task 6: Write tests in `tests/test_eligibility/test_ai_interpreter.py` (AC: #1–#8)
  - [x] 6.1: Fixture: `mock_llm_client` — mock `BaseLLMClient` with `send_messages` returning JSON
  - [x] 6.2: Fixture: `deidentified_active_response` — `DeidentifiedEligibilityResponse` with coverage + benefits
  - [x] 6.3: Fixture: `deidentified_error_response` — `DeidentifiedEligibilityResponse` with AAA errors
  - [x] 6.4: TestInterpreterDirect — active coverage → summary + `AI_ELIG_*` findings (AC #1)
  - [x] 6.5: TestInterpreterErrors — AAA rejection → plain-English explanation (AC #2)
  - [x] 6.6: TestPipelineAIPhase — full pipeline with mock LLM → ai_summary populated (AC #3)
  - [x] 6.7: TestSkipAI — no ai_config → ai_summary=None (AC #4)
  - [x] 6.8: TestGracefulDegradation — `LLMError` → `AI_ELIG_PROVIDER_ERROR` WARNING, no crash (AC #5)
  - [x] 6.9: TestDeidentificationGate — verify only `DeidentifiedEligibilityResponse` reaches interpreter (AC #6)
  - [x] 6.10: TestProviderAgnostic — mock different providers work identically (AC #7)
  - [x] 6.11: TestFindingConventions — all `AI_ELIG_` prefix, all WARNING severity (AC #8)
  - [x] 6.12: TestNoPHILeakage — ai_summary and findings contain no PHI values (AC #8)
  - [x] 6.13: TestFreeTextFallback — non-JSON LLM response → parsed correctly
  - [x] 6.14: TestImports — importable from `claim_validator.eligibility`

- [x] Task 7: Run full test suite and linting (AC: all)
  - [x] 7.1: `pytest tests/test_eligibility/test_ai_interpreter.py` — 28/28 pass
  - [x] 7.2: Full regression `pytest` — 1445/1445 pass, no regressions
  - [x] 7.3: `ruff check` — clean (0 errors on changed files)

## Dev Notes

### Architecture — Direct Analog: `ValidationPipeline` AI Phase + `CoverageCheckAI`

The `EligibilityInterpreterAI` follows the **exact same pattern** as `CoverageCheckAI` (for LLM interaction) and the AI phase from `ValidationPipeline` (for pipeline integration). Key structural parallels:

| Component | Claims (reference) | Eligibility (to build) |
|---|---|---|
| AI validator | `validators/ai/coverage_check.py` → `CoverageCheckAI` | `eligibility/validators/ai/interpreter.py` → `EligibilityInterpreterAI` |
| Base class | `validators/ai/base.py` → `BaseAIValidator` | Same — reuse existing |
| Pipeline AI phase | `validators/pipeline.py` → `_run_ai_phase()` | `eligibility/pipeline.py` → new AI phase |
| De-identifier | `deidentifier/deidentifier.py` → `ClaimDeidentifier` | `eligibility/deidentifier.py` → `EligibilityDeidentifier` (exists, ELIG-2.1) |
| De-identified model | `models/deidentified.py` → `DeidentifiedClaim` | `eligibility/models/deidentified.py` → `DeidentifiedEligibilityResponse` (exists) |
| API function | `_api.py` → `validate(ai_config=...)` | `eligibility/_api.py` → `check_eligibility(ai_config=...)` |

### Key Difference from Claims Module

The claims AI validators operate on `DeidentifiedClaim` (request data). The eligibility AI interpreter operates on `DeidentifiedEligibilityResponse` (response data). This means:
- The interpreter does NOT extend `validate_deidentified(claim: DeidentifiedClaim)` — it uses a custom `interpret()` method
- The pipeline integration is slightly different: it de-identifies the `EligibilityResponse`, not the request
- `BaseAIValidator` is subclassed for constructor pattern (`__init__(llm_client)`) but the main method is `interpret()`, not `validate_deidentified()`

### EligibilityInterpreterAI Pattern

```python
class EligibilityInterpreterAI(BaseAIValidator):
    """AI-powered eligibility response interpreter.

    Takes de-identified eligibility data and generates human-readable
    coverage summaries and actionable findings via LLM.
    """

    name = "EligibilityInterpreterAI"

    SYSTEM_PROMPT = (
        "You are a healthcare eligibility analyst. Interpret "
        "this eligibility response data and provide:\n\n"
        "1. A clear summary of coverage status and benefits\n"
        "2. Any coverage concerns or limitations\n"
        "3. Plain-English explanations of any errors\n\n"
        "Respond in JSON format:\n"
        '{"summary": "<coverage summary>", "findings": [\n'
        '  {"code": "AI_ELIG_<TYPE>", "message": "<str>", '
        '"suggestion": "<str>"}\n'
        "]}\n\n"
        "Finding codes: AI_ELIG_COVERAGE_CONCERN, AI_ELIG_LIMITATION, "
        "AI_ELIG_REJECTION_EXPLAINED, AI_ELIG_PRIOR_AUTH_NEEDED, "
        "AI_ELIG_BENEFIT_NOTE"
    )

    def interpret(
        self,
        response: DeidentifiedEligibilityResponse,
    ) -> tuple[str, list[Finding]]:
        """Interpret de-identified eligibility response.

        Returns:
            Tuple of (ai_summary, findings).
        """
        prompt = self._build_user_prompt(response)
        llm_response = self._send_to_llm([
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ])
        return self._parse_response(llm_response)

    def validate_deidentified(self, claim):
        """Not used — interpreter uses interpret() instead."""
        raise NotImplementedError(
            "Use interpret() with DeidentifiedEligibilityResponse"
        )
```

### Pipeline Integration Pattern

Mirror `ValidationPipeline._run_ai_phase()` but adapted for eligibility:

```python
class EligibilityPipeline:
    def __init__(
        self,
        *,
        rule_validators: list[BaseValidator],
        ai_interpreter: EligibilityInterpreterAI | None = None,
        skip_ai_on_rule_failure: bool = True,
    ) -> None:
        self._rule_validators = rule_validators
        self._ai_interpreter = ai_interpreter
        self._skip_ai_on_rule_failure = skip_ai_on_rule_failure

    @classmethod
    def from_settings(cls, settings=None) -> EligibilityPipeline:
        settings = settings or ClaimValidatorSettings()
        registry = ValidatorRegistry()
        rule_vals = registry.create_validators(settings.eligibility_rule_validators)

        ai_interpreter = None
        if settings.ai_config and not settings.eligibility_skip_ai:
            from claim_validator.llm.factory import get_llm_client
            ai_config = settings.ai_config
            extra = {k: v for k, v in ai_config.items()
                     if k not in ("provider", "api_key", "model")}
            llm_client = get_llm_client(
                ai_config["provider"],
                api_key=ai_config["api_key"],
                model=ai_config["model"],
                **extra,
            )
            ai_interpreter = EligibilityInterpreterAI(llm_client=llm_client)

        return cls(
            rule_validators=rule_vals,
            ai_interpreter=ai_interpreter,
            skip_ai_on_rule_failure=settings.eligibility_skip_ai is False,
        )

    def run(
        self,
        request: EligibilityRequest,
        *,
        response: EligibilityResponse | None = None,
    ) -> EligibilityResult:
        start = time.perf_counter()
        findings: list[Finding] = []
        ai_summary: str | None = None

        # Phase 1: Rule-based validators
        for validator in self._rule_validators:
            # ... existing code ...

        # Phase 2: AI interpretation (if configured + response available)
        if self._ai_interpreter and response:
            rule_has_errors = any(
                f.severity == Severity.ERROR for f in findings
            )
            if not rule_has_errors or not self._skip_ai_on_rule_failure:
                try:
                    deidentified = EligibilityDeidentifier.deidentify(response)
                    ai_summary, ai_findings = self._ai_interpreter.interpret(deidentified)
                    findings.extend(ai_findings)
                except LLMError as exc:
                    findings.append(Finding(
                        code="AI_ELIG_PROVIDER_ERROR",
                        message="AI interpretation unavailable",
                        severity=Severity.WARNING,
                        ...
                    ))

        findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
        elapsed = time.perf_counter() - start
        return EligibilityResult(
            eligible=response.eligible if response else None,
            response=response,
            findings=findings,
            ai_summary=ai_summary,
            execution_time=elapsed,
        )
```

### check_eligibility() API Update

```python
def check_eligibility(
    request: dict[str, Any] | EligibilityRequest,
    *,
    settings: ClaimValidatorSettings | None = None,
    ai_config: dict[str, Any] | None = None,
    response: EligibilityResponse | None = None,
) -> EligibilityResult:
    # ... existing request validation ...

    # Wire ai_config into settings (mirror claims module _api.py pattern)
    if ai_config is not None:
        if settings is not None:
            settings = settings.model_copy(update={"ai_config": ai_config})
        else:
            settings = ClaimValidatorSettings(ai_config=ai_config)

    pipeline = EligibilityPipeline.from_settings(settings)
    return pipeline.run(request_model, response=response)
```

### LLM Response Parsing

Follow `CoverageCheckAI._parse_response()` pattern:
1. Try JSON parse: `{"summary": "...", "findings": [...]}`
2. Free-text fallback: extract summary from response text, generate generic finding

### Finding Codes

| Code | Description |
|---|---|
| `AI_ELIG_COVERAGE_CONCERN` | Coverage gap or limitation detected |
| `AI_ELIG_LIMITATION` | Specific benefit limitation |
| `AI_ELIG_REJECTION_EXPLAINED` | AAA rejection code explained in plain English |
| `AI_ELIG_PRIOR_AUTH_NEEDED` | Prior auth requirement detected for service |
| `AI_ELIG_BENEFIT_NOTE` | General benefit information note |
| `AI_ELIG_PROVIDER_ERROR` | LLM provider unreachable (graceful degradation) |

### Test Fixtures

```python
@pytest.fixture
def mock_llm_client():
    """Mock BaseLLMClient that returns structured JSON."""
    client = Mock(spec=BaseLLMClient)
    client.send_messages.return_value = json.dumps({
        "summary": "Patient has active coverage with $40 copay.",
        "findings": [
            {
                "code": "AI_ELIG_BENEFIT_NOTE",
                "message": "Annual deductible: $2,500",
                "suggestion": "Verify remaining deductible before procedure",
            }
        ],
    })
    return client

@pytest.fixture
def deidentified_active_response():
    return DeidentifiedEligibilityResponse(
        eligible=True,
        coverage=DeidentifiedCoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_year=2023,
            termination_year=None,
        ),
        benefits=[
            BenefitInfo(
                service_type_code="30",
                service_type_name="Health Benefit Plan Coverage",
                copay=40.0,
                coinsurance=0.20,
                deductible=2500.0,
                in_network=True,
                prior_auth_required=False,
            ),
        ],
        errors=[],
    )

@pytest.fixture
def deidentified_error_response():
    return DeidentifiedEligibilityResponse(
        eligible=None,
        coverage=None,
        benefits=[],
        errors=[
            DeidentifiedAAAError(
                rejection_code="72",
                follow_up_code="C",
            ),
        ],
    )
```

### Learnings from Previous Stories

- `EligibilityDeidentifier.deidentify()` is a `@classmethod` — call directly, no instance needed
- `DeidentifiedEligibilityResponse` has `is_deidentified` property (`Literal[True]`) for type distinction
- `BenefitInfo` passes through unchanged in de-identification — no PHI in benefit fields
- `EligibilityResult` is frozen (`ConfigDict(frozen=True)`) — set all fields at construction time
- Finding `context` dicts are required — established pattern
- Findings must be sorted by severity (ERROR=0, WARNING=1) before returning — `_SEVERITY_ORDER` already in pipeline
- `LLMError` is the exception for LLM failures — catch specifically for `AI_ELIG_PROVIDER_ERROR`
- `BaseLLMClient.send_messages(messages: list[Message]) -> str` — the LLM interface
- `ValidatorRegistry.create_ai_validators()` takes `llm_client` kwarg — but we build interpreter directly instead
- ruff line length ≤100 chars
- Use `.venv/bin/python -m pytest` (not bare `pytest`)
- All models use `ConfigDict(frozen=True, strict=False)`
- Import `Message` from `claim_validator.llm.base` for LLM messages

### Settings That Already Exist

```python
# In ClaimValidatorSettings (conf.py) — already present:
eligibility_ai_validators: list[str] = []          # Will set default
eligibility_skip_ai: bool = False                   # Already exists
ai_config: dict[str, Any] | None = None             # Already exists (shared)
```

### Project Structure Notes

- `eligibility/validators/ai/interpreter.py` — new file (AI interpreter class)
- `eligibility/validators/ai/__init__.py` — currently empty stub, add exports
- `eligibility/pipeline.py` — modify to add AI phase
- `eligibility/_api.py` — modify to accept `ai_config` and `response` kwargs
- `conf.py` — add `DEFAULT_ELIG_AI_VALIDATORS` constant, wire default
- `eligibility/__init__.py` — add `EligibilityInterpreterAI` export
- `tests/test_eligibility/test_ai_interpreter.py` — new test file

### References

- [Source: src/claim_validator/validators/ai/coverage_check.py] — CoverageCheckAI (LLM interaction pattern)
- [Source: src/claim_validator/validators/ai/base.py] — BaseAIValidator (base class)
- [Source: src/claim_validator/validators/pipeline.py] — ValidationPipeline (AI phase integration pattern)
- [Source: src/claim_validator/eligibility/pipeline.py] — EligibilityPipeline (to modify)
- [Source: src/claim_validator/eligibility/_api.py] — check_eligibility() (to modify)
- [Source: src/claim_validator/eligibility/deidentifier.py] — EligibilityDeidentifier (exists, ELIG-2.1)
- [Source: src/claim_validator/eligibility/models/deidentified.py] — DeidentifiedEligibilityResponse (exists)
- [Source: src/claim_validator/eligibility/models/result.py] — EligibilityResult (ai_summary field exists)
- [Source: src/claim_validator/eligibility/models/response.py] — EligibilityResponse (input for de-identification)
- [Source: src/claim_validator/llm/base.py] — BaseLLMClient, Message
- [Source: src/claim_validator/llm/factory.py] — get_llm_client() factory
- [Source: src/claim_validator/conf.py] — ClaimValidatorSettings (ai_config, eligibility_skip_ai exist)
- [Source: src/claim_validator/exceptions.py] — LLMError, ClearinghouseError
- [Source: src/claim_validator/_api.py] — validate() ai_config wiring pattern
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] — Original ACs (Epic 3 → renumbered to Epic 2)
- [Source: _bmad-output/implementation-artifacts/elig-2-1-eligibility-de-identification-engine.md] — Previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- `BaseAIValidator.validate_deidentified` is abstract — must provide concrete implementation (raises `NotImplementedError` since eligibility uses `interpret()` instead)
- Pre-existing `test_eligibility_ai_validators_default_empty` expected `== []` — updated to `test_eligibility_ai_validators_default_one` after wiring `DEFAULT_ELIG_AI_VALIDATORS`
- Ruff I001 (import sorting) auto-fixed in test file
- Ruff N813 (CamelCase alias) — removed `as cls` aliases in import tests, used full class name instead

### Completion Notes List

- `EligibilityInterpreterAI` subclasses `BaseAIValidator` with `interpret()` method for eligibility-specific interpretation (not `validate_deidentified()` which is for claims)
- LLM prompt instructs JSON `{"summary": ..., "findings": [...]}` with valid `AI_ELIG_*` codes; free-text fallback with keyword detection
- Invalid LLM finding codes sanitized to `AI_ELIG_BENEFIT_NOTE`; all findings forced to `Severity.WARNING`
- `EligibilityPipeline` extended with `ai_interpreter` and `skip_ai_on_rule_failure` params; `_run_ai_phase()` handles de-identification + interpretation
- `LLMError` → `AI_ELIG_PROVIDER_ERROR` WARNING (graceful degradation); generic `Exception` → `VALIDATOR_ERROR` ERROR
- `check_eligibility()` gains `ai_config` and `response` kwargs; `ai_config` wires into settings via `model_copy()` pattern from claims module
- `DEFAULT_ELIG_AI_VALIDATORS` constant added to `conf.py` with single interpreter path
- 28 tests across 10 test classes covering all 8 ACs + edge cases
- Full regression: 1445/1445 passed, ruff clean

### File List

- `claim-validator/src/claim_validator/eligibility/validators/ai/interpreter.py` (NEW) — `EligibilityInterpreterAI` class
- `claim-validator/src/claim_validator/eligibility/validators/ai/__init__.py` (MODIFIED) — added `EligibilityInterpreterAI` export
- `claim-validator/src/claim_validator/eligibility/pipeline.py` (MODIFIED) — added AI phase: `ai_interpreter`, `_run_ai_phase()`, `response` param
- `claim-validator/src/claim_validator/eligibility/_api.py` (MODIFIED) — added `ai_config` and `response` kwargs
- `claim-validator/src/claim_validator/conf.py` (MODIFIED) — added `DEFAULT_ELIG_AI_VALIDATORS`, wired default
- `claim-validator/src/claim_validator/eligibility/__init__.py` (MODIFIED) — added `EligibilityInterpreterAI` export
- `claim-validator/tests/test_eligibility/test_ai_interpreter.py` (NEW) — 28 tests across 10 classes
- `claim-validator/tests/test_eligibility/test_conf.py` (MODIFIED) — updated AI validator default count test
