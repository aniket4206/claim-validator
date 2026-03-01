---
project_name: 'healthcare-claim-analyzer'
user_name: 'aniket'
date: '2026-02-27'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 62
optimized_for_llm: true
---

# Project Context for AI Agents

_Critical rules and patterns for AI agents implementing code in this project._

---

## Technology Stack & Versions

- **Python**: 3.11+ (target-version in ruff, mypy)
- **Build**: hatchling + hatch-vcs (version from git tags)
- **pydantic**: >=2.0,<3.0 (core dep — all models)
- **pydantic-settings**: >=2.0,<3.0 (core dep — ClaimValidatorSettings)
- **httpx**: >=0.27 (optional: AI providers, Stedi clearinghouse)
- **anthropic**: >=0.40 (optional: AI validation)
- **openai**: >=1.50 (optional: AI validation)
- **fastapi**: >=0.110, **uvicorn**: >=0.30 (optional: server)
- **django**: >=4.2 (optional: integration)
- **pytest**: >=8.0, **pytest-cov** (dev: testing)
- **ruff**: >=0.5 (dev: lint + format)
- **mypy**: >=1.10, **pydantic.mypy** plugin (dev: strict type checking)
- **factory-boy**: >=3.3 (dev: test factories)

**Package layout:** `src/claim_validator/` (src layout, wheel target)
**Optional extras:** `[ai]`, `[anthropic]`, `[openai]`, `[server]`, `[django]`, `[fastapi]`, `[stedi]` (new), `[dev]`, `[all]`

## Critical Implementation Rules

### HIPAA / PHI — NEVER Violate

- **NEVER** send raw PHI to any LLM — always de-identify first
- **NEVER** log patient names, SSNs, member IDs, DOBs, or subscriber IDs
- **NEVER** log clearinghouse request/response bodies (contain PHI)
- Claims: `ClaimDeidentifier.deidentify(claim) -> DeidentifiedClaim`
- Eligibility: `EligibilityDeidentifier.deidentify(response) -> DeidentifiedEligibilityResponse`
- Ages 90+ capped to 90 per HIPAA Safe Harbor
- Dates reduced to year-only before LLM
- PHI dual-path: clearinghouse receives raw PHI (covered entity), AI path strips PHI
- All 18 HIPAA identifiers must be stripped — verified by automated tests
- PHI must not persist in memory beyond a single `validate()` or `check_eligibility()` call

### Validation Pipeline Architecture (Claims)

- **Two-phase execution**: rule-based validators first, AI validators second
- AI validators **skipped** if rule-based fails (configurable via `skip_ai_on_rule_failure`)
- Validators are **stateless** — `BaseValidator.validate(claim) -> ValidatorOutput` must NOT modify input
- `ValidatorOutput` contains `Finding` objects: `code`, `message`, `severity`, `field_name`, `suggestion`, `context`
- `ValidatorRegistry` loads validators **lazily by dotted path** from settings
- `ValidationPipeline.run(claim) -> PipelineResult` aggregates all outputs
- Top-level API: `validate(claim_dict_or_ClaimData) -> PipelineResult`

### Eligibility Pipeline Architecture (NEW)

- **Three-phase execution**: rule-based → clearinghouse → AI interpretation
- Separate `EligibilityPipeline` class (NOT reusing `ValidationPipeline`)
- Phase 1 (rule-based): offline validators check `EligibilityRequest` fields
- Phase 2 (clearinghouse): `BaseClearinghouseClient.submit_eligibility()` → raw 271 JSON → `parse_271_response()` → `EligibilityResponse`
- Phase 3 (AI): `EligibilityDeidentifier.deidentify()` → `EligibilityInterpreterAI` → findings + summary
- Gate between phases: if rule-based fails AND `skip_clearinghouse_on_rule_failure=True` → return early
- Gate before AI: if `skip_ai=True` → return structured response without AI
- Top-level API: `check_eligibility(request_dict_or_EligibilityRequest) -> EligibilityResult`
- `EligibilityResult.passed` = zero ERROR findings from rule-based phase
- `EligibilityResult.eligible` = coverage status from 271 response (True/False/None)

### Prior Authorization Pipeline Architecture (NEW)

- **Three-phase execution**: rule-based → clearinghouse (278) → AI interpretation
- Separate `PriorAuthPipeline` class (like `EligibilityPipeline`)
- Phase 1 (rule-based): offline validators check `PriorAuthRequest` fields
- Phase 2 (clearinghouse): `BasePAClearinghouseClient.submit_prior_auth()` → raw 278 JSON → `parse_278_response()` → `PriorAuthResponse`
- Phase 3 (AI): `PriorAuthDeidentifier.deidentify()` → `PriorAuthInterpreterAI` → findings + summary
- Gate: if rule-based fails AND `skip_clearinghouse_on_pa_failure=True` → return early
- Gate: if `pa_skip_ai=True` → return structured response without AI
- Top-level API: `submit_prior_auth(request) -> PriorAuthResult`
- `PriorAuthResult.passed` = zero ERROR findings from rule-based phase
- `PriorAuthResult.approved` = action code from 278 response (A1=approved, A3=denied, etc.)
- PA determination: `determine_pa_required(eligibility_response) -> PADeterminationResult`

**PA models:**
- `PriorAuthRequest` — flat (like `ClaimData`), dict-compatible input
- `PriorAuthResponse` — nested: `CertificationActionCode`, `list[ServiceLineDecision]`, `list[PriorAuthError]`, `raw_response: dict`
- `PriorAuthResult` — pipeline output: `approved`, `response`, `findings`, `ai_summary`, `passed`, `authorization_number`, `raw_response`, `execution_time`
- `DeidentifiedPriorAuthResponse` — PHI-stripped version for LLM
- `PADeterminationResult` — `required: bool`, `confidence`, `reason`

### Clearinghouse Client Contract

- `BaseClearinghouseClient` ABC mirrors `BaseLLMClient` pattern
- `submit_eligibility(request: EligibilityRequest) -> dict` — returns raw 271 JSON
- **MUST** raise `ClearinghouseError` for HTTP/network failures
- **MUST NOT** raise for business rejections (AAA segments — returned in response)
- **MUST NOT** parse response into models (response parser's job)
- **MUST NOT** log request/response bodies (PHI)
- Context manager support: `__enter__`, `__exit__`, `close()`
- `StediClient`: `httpx.Client`, 30s default timeout (NFR12), `Authorization: Key {api_key}`

### Response Parser Contract

- `parse_271_response(raw: dict) -> EligibilityResponse` — pure function
- Handle missing fields gracefully — `None`, not exception (NFR14)
- Unmapped/unexpected fields → WARNING finding, never exception
- Extract `BenefitInfo` from EB segments, `AAAError` from AAA segments
- Preserve `raw_response` dict for advanced users
- **MUST NOT** make network calls or modify the raw dict

### Adding a New Claim Validator

1. Subclass `BaseValidator` from `claim_validator/validators/base.py`
2. Set `name` class attribute
3. Implement `validate(claim: ClaimData) -> ValidatorOutput`
4. Use `self._make_output(findings)` and `self._make_finding(...)` helpers
5. Add dotted class path to `CLAIM_VALIDATOR_RULE_VALIDATORS` or `CLAIM_VALIDATOR_AI_VALIDATORS` in settings

### Adding a New Eligibility Validator

1. Subclass `BaseValidator` from `claim_validator/validators/base.py` (same base)
2. Set `name` class attribute
3. Implement `validate(request: EligibilityRequest) -> ValidatorOutput`
4. Use `ELIG_` prefix for all finding codes
5. Add dotted class path to `CLAIM_VALIDATOR_ELIGIBILITY_RULE_VALIDATORS` in settings
6. Place in `claim_validator/eligibility/validators/rule_based/{name}.py`

### Model Patterns

- All Pydantic models use `ConfigDict(frozen=True, strict=False)`
- One model file per domain, re-exported from `__init__.py`
- Enums use `StrEnum` in `constants.py`

**Claim models:** `ClaimData` (flat), `ClaimLineData`, `DiagnosisCode`, `DeidentifiedClaim`
**Result models:** `Finding`, `ValidatorOutput`, `PhaseResult`, `PipelineResult`

**Eligibility models (NEW):**
- `EligibilityRequest` — flat (like `ClaimData`), dict-compatible input
- `EligibilityResponse` — nested: `CoverageInfo`, `list[BenefitInfo]`, `list[AAAError]`, `raw_response: dict`
- `EligibilityResult` — pipeline output: `eligible`, `response`, `findings`, `ai_summary`, `passed`, `raw_response`, `execution_time`
- `DeidentifiedEligibilityResponse` — PHI-stripped version for LLM
- `CoverageStatus` enum: `ACTIVE`, `INACTIVE`, `UNKNOWN`

### Finding Code Prefixes

| Domain | Prefix | Example |
|---|---|---|
| Claim rule-based | (none — legacy) | `INVALID_NPI`, `MISSING_SUBSCRIBER_ID` |
| Claim AI | `AI_` | `AI_COVERAGE_CONCERN`, `AI_PRIOR_AUTH` |
| Eligibility rule-based | `ELIG_` | `ELIG_INVALID_PAYER`, `ELIG_MISSING_SUBSCRIBER` |
| Clearinghouse infra | `CLEARINGHOUSE_` | `CLEARINGHOUSE_TIMEOUT`, `CLEARINGHOUSE_ERROR` |
| AAA rejections | `AAA_REJECTION` | `AAA_REJECTION` (with context dict) |
| Eligibility AI | `AI_ELIG_` | `AI_ELIG_COVERAGE_SUMMARY`, `AI_ELIG_LIMITATION` |
| PA rule-based | `PA_` | `PA_INVALID_NPI`, `PA_MISSING_MEMBER_ID` |
| PA clearinghouse | `CLEARINGHOUSE_` | `CLEARINGHOUSE_PA_TIMEOUT` |
| AAA PA rejections | `AAA_PA_REJECTION` | `AAA_PA_REJECTION` (with context dict) |
| PA AI | `AI_PA_` | `AI_PA_INTERPRETATION`, `AI_PA_RECOMMENDATION` |
| Internal errors | `VALIDATOR_ERROR` | `VALIDATOR_ERROR`, `AI_PROVIDER_ERROR` |

### Naming Conventions

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Models | `PascalCase` | `EligibilityRequest`, `BenefitInfo` | `EligRequest`, `Benefit` |
| Validators | `{Name}Validator` | `PayerIDValidator` | `PayerValidator` |
| Clearinghouse clients | `{Provider}Client` | `StediClient` | `StediAPI` |
| Clearinghouse base | `BaseClearinghouseClient` | — | `ClearinghouseBase` |
| LLM base | `BaseLLMClient` | — | `LLMBase` |
| De-identifiers | `{Domain}Deidentifier` | `EligibilityDeidentifier` | `ResponseDeidentifier` |
| Pipeline | `{Domain}Pipeline` | `EligibilityPipeline` | `EligPipeline` |
| Top-level API | `check_{domain}()` / `submit_{domain}()` | `check_eligibility()`, `submit_prior_auth()` | `verify_eligibility()` |
| PA models | `PriorAuth{Type}` | `PriorAuthRequest`, `PriorAuthResponse` | `PARequest`, `AuthResponse` |
| PA sub-models | `{Concept}Info` / `{Concept}Decision` | `SubscriberInfo`, `ServiceLineDecision` | `Subscriber`, `LineDecision` |
| PA enums | `{Concept}Code` | `CertificationActionCode` | `HCRCode`, `ActionCode` |
| PA module dir | `prior_auth/` | — | `pa/`, `prior_authorization/` |
| Files | `snake_case.py` | `payer_id.py`, `service_type.py` | `payerId.py` |
| Tests | `test_{module}/test_{name}.py` | `test_eligibility/test_pipeline.py` | `test_elig_pipe.py` |

### Settings Pattern

- `ClaimValidatorSettings` in `claim_validator/conf.py` — `pydantic_settings.BaseSettings`
- Reads `CLAIM_VALIDATOR_` prefixed env vars
- `model_config = SettingsConfigDict(env_prefix="CLAIM_VALIDATOR_", frozen=True)`
- Eligibility fields added flat: `stedi_api_key`, `stedi_environment`, `eligibility_rule_validators`, `skip_clearinghouse_on_rule_failure`, `skip_ai`

### Exception Hierarchy

- `ClaimValidatorError` (base)
  - `ValidationError` — invalid input data
  - `ConfigurationError` — bad config (validator path, missing provider)
  - `LLMError` — LLM provider failure
  - `CodeTableError` — code table load/lookup failure
  - `ClearinghouseError` (NEW) — clearinghouse HTTP/network failure

### Code Tables (Lazy Singletons)

- Bundled JSON files in `claim_validator/data/` and `claim_validator/eligibility/data/`
- Loaded via lazy singleton with `threading.Lock` — loaded once, cached in module global
- Existing: ICD-10, HCPCS, taxonomy, POS, timely filing
- New: payer directory (~3,400 entries, ~200KB), X12 service type codes

### Testing Conventions

- `pytest` with `testpaths = ["tests"]`
- Test structure mirrors source: `tests/test_{module}/test_{name}.py`
- Fixtures in `conftest.py` per test directory
- Valid Luhn NPI for tests: `1234567893`; invalid: `1234567890`
- Assertions: `result.passed`, `len(result.findings)`, `any(f.code == "..." for f in result.findings)`
- Eligibility tests: `tests/test_eligibility/` (mirrors `src/claim_validator/eligibility/`)
- HIPAA tests: `tests/test_eligibility/test_hipaa/` — verify all 18 identifiers stripped
- Coverage target: >90% for all eligibility module code (NFR17)

### Code Style

- ruff: `line-length = 100`, target Python 3.11, rules `E, F, I, N, W, UP`
- mypy: `strict = true`, `pydantic.mypy` plugin, `init_forbid_extra = true`
- `from __future__ import annotations` at top of every file
- Private methods prefixed with `_`
- All public classes and functions must have docstrings (NFR21)

### Project Structure

**Existing (claim validation):**
```
src/claim_validator/
├── __init__.py, _api.py, conf.py, constants.py, exceptions.py
├── models/ (claim.py, results.py, deidentified.py)
├── validators/ (base.py, registry.py, pipeline.py)
│   ├── rule_based/ (8 validators)
│   └── ai/ (base.py, 3 AI validators)
├── deidentifier/
├── llm/ (base.py, factory.py, providers/)
├── code_tables/ (icd10, hcpcs, taxonomy, pos, timely_filing)
└── data/ (bundled JSON files)
```

**New (eligibility module):**
```
src/claim_validator/eligibility/
├── __init__.py, _api.py, pipeline.py, response_parser.py, deidentifier.py
├── models/ (request.py, response.py, errors.py, result.py, deidentified.py)
├── validators/
│   ├── rule_based/ (payer_id, demographics, service_type, date, member_id)
│   └── ai/ (interpreter.py)
├── clearinghouse/ (base.py, factory.py, stedi.py)
├── code_tables/ (payer_directory.py, service_types.py)
└── data/ (payer_directory.json, service_types.json)
```

**New (prior authorization module):**
```
src/claim_validator/prior_auth/
├── __init__.py, constants.py
├── models/ (request.py, response.py, result.py, deidentified.py)
├── validators/
│   ├── rule_based/ (npi, member_id, diagnosis, procedure, dates, cross_field)
│   └── ai/ (interpreter.py)
├── clearinghouse/ (base.py, factory.py)
├── code_tables/ (hcr_action_codes.py, aaa_reject_codes.py, service_types.py)
└── data/ (hcr_action_codes.json, aaa_reject_codes.json, service_types.json)
```

### Environment Setup

- Rule-based validation works with zero API keys
- AI validation requires LLM provider key (`CLAIM_VALIDATOR_AI_CONFIG`)
- Stedi clearinghouse requires `CLAIM_VALIDATOR_STEDI_API_KEY`
- Stedi environment: `CLAIM_VALIDATOR_STEDI_ENVIRONMENT` (sandbox/production)

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Use `ELIG_` prefix for all eligibility finding codes — never reuse claim prefixes
- Always de-identify before LLM calls — no exceptions

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack or architecture changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-02-27
