---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-18'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-18.md'
  - '_bmad-output/project-context.md'
workflowType: 'architecture'
project_name: 'healthcare-claim-analyzer'
user_name: 'aniket'
date: '2026-02-18'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
49 FRs across 8 categories driving a validation library with two execution modes (offline rules, online AI), a pluggable provider system, and extensible validator architecture.

| Category | Count | Architectural Impact |
|---|---|---|
| Claim Validation (FR1-FR6) | 6 | Defines the core public API surface — `validate()` entry point, result model |
| Rule-Based Validators (FR7-FR17) | 11 | 8 stateless validator classes, each isolated, each testable, all offline |
| AI Validation (FR18-FR22) | 5 | LLM integration layer, de-identification pipeline, probabilistic output handling |
| LLM Provider Support (FR23-FR27) | 5 | Abstract client interface, factory pattern, 3 concrete adapters with different SDK patterns |
| Pipeline & Extensibility (FR28-FR33) | 6 | Two-phase orchestrator, validator registry with lazy loading, custom validator contract |
| Data Models & Input (FR34-FR37) | 4 | Pydantic models accepting both dicts and typed instances, multi-line claim structure |
| Code Tables & Reference Data (FR38-FR42) | 5 | Bundled package data with lazy loading, in-memory lookup after first access |
| Configuration & Distribution (FR43-FR49) | 7 | Pydantic settings, optional dependency extras, PyPI packaging, py.typed marker |

**Non-Functional Requirements:**
29 NFRs across 6 categories establishing hard performance budgets, HIPAA security boundaries, and compatibility constraints.

| Category | Count | Key Constraint |
|---|---|---|
| Performance (NFR1-NFR7) | 7 | <50ms rule-based, <500ms import, <1ms code lookup, 500+ claims/sec batch |
| Security (NFR8-NFR13) | 6 | Zero PHI transmission, zero telemetry, no PHI in any output path |
| Scalability (NFR14-NFR16) | 3 | Thread-safe via statelessness, O(n) linear scaling |
| Reliability (NFR17-NFR20) | 4 | Deterministic rule-based, graceful AI degradation, input fuzzing |
| Compatibility (NFR21-NFR25) | 5 | Python 3.11-3.13, Linux/macOS/Windows, core = Pydantic only |
| Code Quality (NFR26-NFR29) | 4 | 90%+ coverage, zero lint warnings, <15MB wheel |

**Scale & Complexity:**

- Primary domain: **Python library (developer tool)**
- Complexity level: **High** — healthcare regulatory domain, brownfield extraction, multi-provider LLM abstraction, plugin architecture, strict performance budgets
- Estimated architectural components: **~12 major** — core models, validator base, 8 rule validators, 3 AI validators, LLM abstraction (base + 3 providers + factory), de-identifier, pipeline orchestrator, registry, code tables, settings, exceptions, package/distribution

### Technical Constraints & Dependencies

| Constraint | Source | Architectural Implication |
|---|---|---|
| **Pydantic 2.x only in core** | NFR23, NFR24 | No Django, Flask, FastAPI in `claim_validator` package. Framework adapters are separate extras |
| **Zero network calls (rule-based)** | NFR8 | Code tables bundled as package data. No lazy download, no CDN fetch, no telemetry |
| **<50ms per claim (rule-based)** | NFR1 | Validators must be lightweight. No I/O in rule path. Pre-loaded code tables |
| **<500ms import time** | NFR7 | Lazy loading mandatory for code tables. Validators loaded on first pipeline construction, not import |
| **<15MB wheel** | NFR29 | Code tables must be compressed. Consider binary formats (msgpack, SQLite) over raw JSON/CSV |
| **Thread-safe** | NFR14 | Stateless validators. No module-level mutable state. Pipeline instances safe for concurrent use |
| **Python 3.11+** | NFR21 | Can use `StrEnum`, `|` union syntax, `tomllib`, modern typing features |
| **Brownfield extraction** | Project context | 47 existing patterns to migrate. Django ORM → Pydantic, TextChoices → StrEnum, django-environ → Pydantic settings |
| **CPT copyright** | Domain constraint | Cannot bundle CPT descriptions. Format validation only. HCPCS Level II (public domain) can be bundled |

### Cross-Cutting Concerns Identified

| Concern | Scope | Strategy |
|---|---|---|
| **HIPAA / PHI safety** | Every output path — findings, exceptions, logs, LLM payloads | Zero PHI by design: findings reference field names not values; de-identifier strips before LLM; no logging in core |
| **Lazy loading** | Code tables, validator classes, LLM clients | Import-time cost <500ms. Tables loaded on first lookup. Validators loaded on first pipeline use. Providers instantiated on first AI call |
| **Error handling** | All validator execution, LLM calls, code table loading | Validators catch own exceptions → findings. LLM failures → graceful degradation with warning. Invalid input → clear `ValidationError` |
| **Configuration** | Pipeline composition, AI provider, validator selection, payer rules | Single `ClaimValidatorSettings` Pydantic model. Env var support. Sensible defaults for zero-config |
| **Extensibility contract** | Custom validators, custom LLM providers, future payer plugins | `BaseValidator` and `BaseLLMClient` ABCs must be stable public API from v1.0. Dotted-path registry for dynamic loading |
| **Thread safety** | Concurrent claim processing | Stateless validators (no instance state between calls). Immutable pipeline configuration. Thread-safe code table singletons |
| **Testing** | All validators, de-identifier, pipeline, providers | Test contract: known-input/known-output for every validator. PHI leak detection tests. Provider mock/stub patterns |

## Starter Template Evaluation

### Primary Technology Domain

**Python library (developer tool)** — pip-installable package distributed via PyPI. Not a web application, API server, or CLI tool. The library has no UI layer; UX requirements are not applicable.

### Technical Preferences (from Project Context)

| Dimension | Preference | Source |
|---|---|---|
| Language | Python 3.11+ (StrEnum, `|` union, tomllib) | PRD NFR21, project context |
| Core dependency | Pydantic 2.x | PRD NFR23 |
| Build system | pyproject.toml only (PEP 621) | PRD FR46 |
| Linting/Format | ruff (line-length=100, rules E/F/I/N/W/UP) | Project context |
| Type checking | mypy with py.typed marker | PRD FR49, project context |
| Testing | pytest | Project context |
| Layout | src layout (`src/claim_validator/`) | Python packaging best practices |
| Distribution | PyPI via wheel | PRD FR46 |

### Starter Options Considered

| Option | Build Backend | py.typed | pytest+ruff+mypy | CI/CD | Template Updates | Status (Feb 2026) |
|---|---|---|---|---|---|---|
| **scientific-python/cookie** (Copier) | 10 choices (hatchling recommended) | Yes | All three | Yes (GitHub Actions) | Yes (Copier pull) | Active, comprehensive |
| **hatch new** | hatchling | No | All three | No | No | Active, PyPA official |
| **uv init --lib** | uv_build (switchable) | Yes | None | No | No | Very active (Astral) |
| **cookiecutter-pypackage** | setuptools (setup.py) | No | flake8 only | Yes | No | Stagnating, outdated stack |
| **PyScaffold** | setuptools (setup.cfg) | No | No ruff | Optional ext | Yes (--update) | Stable, not modern |

### Selected Starter: Hybrid — uv init --lib + manual configuration

**Rationale for Selection:**

This is a **brownfield extraction**, not a greenfield project. The package structure, module organization, and public API are already defined by the PRD. A comprehensive template like scientific-python/cookie would scaffold structure we'd immediately override. Instead:

1. **uv init --lib** provides the correct minimal foundation: src layout, `py.typed`, modern `pyproject.toml`, and access to the fastest Python tooling (uv for resolution/installation, ruff from the same Astral ecosystem)
2. **Manual configuration** gives us precise control over: optional dependency extras (`[ai]`, `[anthropic]`, `[openai]`, `[django]`, `[fastapi]`, `[dev]`, `[all]`), bundled package data inclusion, and HIPAA-specific CI checks
3. **hatchling as build backend** (switched at init) — PyPA-maintained, excellent plugin ecosystem (`hatch-vcs` for versioning), widely adopted, well-documented for optional extras and package data inclusion
4. Build backend choice: hatchling over uv_build because hatchling is more mature for complex packaging scenarios (optional extras, package data inclusion, VCS versioning) while uv_build is newer and best for simple packages

**Initialization Command:**

```bash
uv init --lib --build-backend hatchling claim-validator
cd claim-validator
```

### Architectural Decisions Provided by Starter

**Language & Runtime:**
- Python 3.11+ (configured in `pyproject.toml` `requires-python`)
- Full type annotations with `py.typed` marker (generated by `uv init --lib`)

**Build Backend:**
- hatchling (PyPA-maintained, plugin-extensible)
- Pure `pyproject.toml` configuration (PEP 621)
- `hatch-vcs` plugin for git-tag-based versioning

**Project Layout:**
- src layout: `src/claim_validator/` (PEP 517 compliant, prevents import confusion)
- Tests outside src: `tests/`
- Package data in: `src/claim_validator/data/` (bundled code tables)

**What We Add Manually:**

| Component | Tool | Configuration |
|---|---|---|
| Linting/formatting | ruff | `[tool.ruff]` in pyproject.toml — line-length=100, target py311, rules E/F/I/N/W/UP |
| Type checking | mypy | `[tool.mypy]` in pyproject.toml — strict mode, Pydantic plugin |
| Testing | pytest | `[tool.pytest.ini_options]` in pyproject.toml — testpaths, markers |
| CI/CD | GitHub Actions | Matrix: Python 3.11/3.12/3.13, Linux/macOS/Windows, ruff+mypy+pytest |
| Pre-commit | pre-commit | ruff check, ruff format, mypy (optional) |
| Docs | mkdocs-material | API reference (mkdocstrings), quickstart, healthcare context guide |
| Optional extras | pyproject.toml | `[ai]`, `[anthropic]`, `[openai]`, `[django]`, `[fastapi]`, `[dev]`, `[all]` |
| Package data | pyproject.toml | `[tool.hatch.build.targets.wheel]` include patterns for `data/` directory |
| HIPAA CI checks | GitHub Actions | PHI leak scanning, no-network rule-based test, de-identification verification |

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- D1: Code table storage format → Compressed JSON
- D3: Pydantic model design → Frozen, lax coercion
- D4: Configuration → Pydantic BaseSettings
- D5: De-identification position → Pipeline-integrated
- D7: LLM client interface → Chat-based
- D10: Validator registry → Dotted path strings
- D13: Import/export → Subpackages + top-level re-export

**Important Decisions (Shape Architecture):**
- D2: Code table loading → Lazy singleton with lock
- D6: PHI boundary enforcement → Type-driven + runtime
- D8: Prompt management → Per-validator prompts
- D9: Response parsing → Hybrid (structured + fallback)
- D11: Pipeline composition → Settings-driven + builder
- D12: Versioning → hatch-vcs (git tags)

**Deferred Decisions (Post-MVP):**
- Framework adapter patterns (Django, FastAPI, Flask) — Phase 2
- Payer plugin package spec — Phase 2
- Batch persistence layer — Phase 3
- Hosted API architecture — Phase 3

### Data Architecture

| Decision | Choice | Version | Rationale | Affects |
|---|---|---|---|---|
| **D1: Code table storage** | Compressed JSON (.json.gz) | N/A | Lowest complexity, no extra dependencies, ~2MB for ICD-10. Adequate performance with lazy loading. Standard library `gzip` + `json` only | Code tables module, package data, wheel size |
| **D2: Code table loading** | Lazy singleton with `threading.Lock` | N/A | Transparent to user — first `validate()` call triggers load, subsequent calls use cached dict. Lock ensures thread-safe initialization. One-time ~200ms cost amortized across all calls | Code tables module, import time, thread safety |
| **D3: Pydantic models** | `frozen=True`, `strict=False` | Pydantic 2.x | Frozen models guarantee immutability → thread-safe claims. Lax coercion (`strict=False`) means `validate({"charge_amount": "150.00"})` works — critical for dict-based input DX | ClaimData, ClaimLineData, all models |
| **D4: Configuration** | Pydantic `BaseSettings` with `env_prefix="CLAIM_VALIDATOR_"` | Pydantic 2.x | Native env var support, type validation, nested model support, consistent with Pydantic core. Zero-config defaults: rule validators enabled, AI disabled, skip_ai_on_rule_failure=True | ClaimValidatorSettings, all configurable behavior |

### Security Architecture (HIPAA)

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D5: De-identification position** | Pipeline-integrated — automatic before any AI validator | Zero bypass risk. `ValidationPipeline.run()` calls `ClaimDeidentifier.deidentify()` before passing claim data to any AI validator. Custom AI validators receive pre-deidentified data. Impossible to call AI without de-id | ValidationPipeline, all AI validators, ClaimDeidentifier |
| **D6: PHI boundary enforcement** | Type-driven + runtime (belt-and-suspenders) | `DeidentifiedClaim` type created only by `ClaimDeidentifier`. `BaseLLMClient.send()` accepts only `DeidentifiedClaim` (type check). Runtime `assert claim.is_deidentified` guard as backup. Maximum HIPAA safety worth the added complexity | ClaimDeidentifier, DeidentifiedClaim type, BaseLLMClient, all AI validators |

**Security invariants enforced by architecture:**
- Rule-based validators receive `ClaimData` — never touch network
- AI validators receive `DeidentifiedClaim` — PHI already stripped
- `BaseLLMClient` type signature requires `DeidentifiedClaim` — compiler catches violations
- Finding messages reference field names, never field values — zero PHI in output
- No logging in core library — consumer controls all I/O

### LLM Provider Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D7: BaseLLMClient interface** | Chat-based: `send_messages(messages: list[Message]) -> str` | Universal — every LLM provider supports chat completions. AI validators construct prompts and parse responses; providers just transport messages. Simplest contract, easiest to implement custom providers | BaseLLMClient ABC, AnthropicClient, OpenAIClient, OpenAICompatibleClient |
| **D8: Prompt management** | Per-validator prompts — each AI validator owns its prompt templates as class constants | Encapsulated — `CodeValidationAI` contains its own system prompt, user prompt template, and parsing logic. No shared prompt infrastructure. Each validator is a self-contained, testable unit | CodeValidationAI, CoverageCheckAI, PriorAuthAI |
| **D9: Response parsing** | Hybrid — structured JSON output preferred, free-text regex fallback | Structured output (JSON mode) works well with Claude and GPT-4 but not all OpenAI-compatible endpoints (Ollama, vLLM). Fallback ensures all providers work. Each AI validator defines both parsing paths | AI validators, response parsing logic |

**LLM provider contract:**
```
BaseLLMClient (ABC)
├── send_messages(messages: list[Message]) -> str
├── model: str
├── provider_name: str
│
├── AnthropicClient — anthropic SDK, Messages API
├── OpenAIClient — openai SDK, Chat Completions API
└── OpenAICompatibleClient — httpx, OpenAI-compatible /v1/chat/completions
```

**LLM factory:**
```
get_llm_client(provider="anthropic", api_key="sk-...", model="claude-sonnet-4-5-20241022") -> BaseLLMClient
```

### Pipeline Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D10: Validator registry** | Dotted path strings with `importlib.import_module()` | Matches existing Django codebase pattern (lowest migration friction). Config-driven — validators listed in `ClaimValidatorSettings.rule_validators` and `ai_validators`. Lazy import — classes loaded on first pipeline construction, not at import time | ValidatorRegistry, ClaimValidatorSettings, pipeline construction |
| **D11: Pipeline composition** | Both: `Pipeline.from_settings(settings)` + `Pipeline.builder().add(...).build()` | `from_settings()` covers 90% of users (zero-code pipeline from config). `builder()` covers power users constructing custom pipelines programmatically (Raj's Journey J4). Both return identical `ValidationPipeline` instance | ValidationPipeline, ValidatorRegistry, public API |

**Pipeline execution model:**
```
ValidationPipeline.run(claim_data)
  ├── Phase 1: Rule-based validators (sequential, offline)
  │   ├── CompletenessValidator
  │   ├── NPIValidator
  │   ├── ... (all rule validators from config)
  │   └── Aggregate → PipelineResult (partial)
  │
  ├── Gate: if rule_phase_failed AND skip_ai_on_rule_failure → return
  │
  ├── Phase 2: AI validators (sequential, network)
  │   ├── ClaimDeidentifier.deidentify(claim) → DeidentifiedClaim
  │   ├── CodeValidationAI(deidentified_claim)
  │   ├── CoverageCheckAI(deidentified_claim)
  │   ├── PriorAuthAI(deidentified_claim)
  │   └── Aggregate → PipelineResult (complete)
  │
  └── Return PipelineResult (passed, findings, execution_time, phase_results)
```

### Package & Distribution

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D12: Versioning** | hatch-vcs (git tag driven) | `git tag v1.0.0` → version auto-populated in built wheel. Zero manual version management. Consistent with hatchling build backend. Follows Python packaging best practices | pyproject.toml, release process, CI/CD |
| **D13: Import/export** | Subpackages internally + re-export key symbols at top level | Clean internal organization (`claim_validator.validators.npi`, `claim_validator.llm.anthropic`). Simple top-level DX (`from claim_validator import validate, ClaimData, BaseValidator`). `__init__.py` re-exports ~15 key symbols. `__all__` controls public API | Package structure, __init__.py, py.typed, all imports |

**Optional extras design:**
```toml
[project.optional-dependencies]
ai = ["httpx>=0.27", "anthropic>=0.40", "openai>=1.50"]
anthropic = ["httpx>=0.27", "anthropic>=0.40"]
openai = ["httpx>=0.27", "openai>=1.50"]
django = ["django>=4.2"]
fastapi = ["fastapi>=0.110"]
dev = ["pytest>=8.0", "pytest-cov", "ruff>=0.5", "mypy>=1.10", "factory-boy>=3.3"]
all = ["claim-validator[ai,django,fastapi]"]
```

### Decision Impact Analysis

**Implementation Sequence:**
1. Package scaffolding (D12, D13) — `uv init`, pyproject.toml, src layout
2. Core models (D3) — `ClaimData`, `ClaimLineData`, `Finding`, `ValidatorOutput`, `PipelineResult`
3. Configuration (D4) — `ClaimValidatorSettings` with Pydantic BaseSettings
4. Code tables (D1, D2) — compressed JSON, lazy singleton loader
5. Validator base + registry (D10) — `BaseValidator` ABC, `ValidatorRegistry`
6. Rule-based validators — 8 validators extracted from Django codebase
7. Pipeline (D11) — `ValidationPipeline` with two-phase execution
8. De-identification (D5, D6) — `ClaimDeidentifier`, `DeidentifiedClaim` type
9. LLM abstraction (D7, D8, D9) — `BaseLLMClient`, 3 providers, factory
10. AI validators — 3 validators with per-validator prompts
11. Top-level API — `validate()` convenience function, `__init__.py` re-exports

**Cross-Component Dependencies:**
- D3 (frozen models) enables D6 (type-driven PHI boundary) — immutable claims can't be modified after de-identification
- D1+D2 (code tables) blocks rule-based validators — validators need code lookups
- D5 (pipeline-integrated de-id) requires D6 (DeidentifiedClaim type) — pipeline creates the type
- D10 (dotted paths) requires D4 (settings) — settings store the validator path lists
- D7 (chat-based LLM) simplifies D9 (response parsing) — all providers return strings

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 28 areas where AI agents could make different choices, organized into 6 categories below.

### Naming Patterns

**Module & File Naming:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Package | `snake_case` | `claim_validator` | `claimValidator`, `ClaimValidator` |
| Module files | `snake_case.py` | `npi_validator.py` | `NPIValidator.py`, `npi-validator.py` |
| Test files | `test_{module}.py` | `test_npi_validator.py` | `npi_validator_test.py`, `test_npi.py` |
| Test directories | `tests/test_{subpackage}/` | `tests/test_validators/` | `tests/validators/` |

**Class Naming:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Validators | `{Name}Validator` | `NPIValidator`, `CodingValidator` | `NPI`, `ValidateNPI`, `NPICheck` |
| AI validators | `{Name}AI` | `CodeValidationAI`, `CoverageCheckAI` | `AICodeValidator`, `CodeValidatorAI` |
| LLM clients | `{Provider}Client` | `AnthropicClient`, `OpenAIClient` | `AnthropicLLM`, `ClaudeClient` |
| Models | `{Name}Data` (domain) or `{Name}` (results) | `ClaimData`, `Finding`, `PipelineResult` | `ClaimModel`, `ClaimDTO` |
| Settings | `ClaimValidatorSettings` | — | `Config`, `Settings`, `Preferences` |
| Exceptions | `{Name}Error` | `ClaimValidatorError`, `ConfigurationError` | `ClaimValidatorException`, `InvalidConfig` |

**Function & Method Naming:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Public methods | `snake_case`, verb-first | `validate()`, `deidentify()`, `run()` | `doValidation()`, `process()` |
| Private methods | `_snake_case` | `_check_luhn()`, `_load_table()` | `__check_luhn()`, `checkLuhn()` |
| Factory functions | `get_{thing}` or `create_{thing}` | `get_llm_client()` | `llm_client_factory()`, `make_client()` |
| Predicates | `is_` or `has_` prefix | `is_deidentified`, `has_findings` | `deidentified()`, `check_findings()` |

**Constants & Error Codes:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Finding codes | `UPPER_SNAKE_CASE` | `INVALID_NPI`, `MISSING_FIELD`, `AI_CLINICAL_IMPLAUSIBILITY` | `invalidNpi`, `E001`, `npi-invalid` |
| Code prefixes | Rule: no prefix. AI: `AI_` prefix | `INVALID_NPI` (rule), `AI_COVERAGE_CONCERN` (AI) | Mixing prefixed/unprefixed |
| Severity enum | `StrEnum` | `Severity.ERROR`, `Severity.WARNING` | String literals "error", "ERROR" |
| Claim types | `StrEnum` | `ClaimType.PROFESSIONAL`, `ClaimType.INSTITUTIONAL` | String literals |

### Structure Patterns

**Source Organization:**

```
src/claim_validator/
├── __init__.py              # Re-exports ~15 key symbols
├── py.typed                 # PEP 561 marker
├── _version.py              # Auto-generated by hatch-vcs
├── models/                  # Pydantic data models
│   ├── __init__.py          # Re-exports all models
│   ├── claim.py             # ClaimData, ClaimLineData, DiagnosisCode
│   ├── results.py           # Finding, ValidatorOutput, PipelineResult
│   └── deidentified.py      # DeidentifiedClaim
├── validators/              # All validators
│   ├── __init__.py          # Re-exports BaseValidator
│   ├── base.py              # BaseValidator ABC
│   ├── registry.py          # ValidatorRegistry
│   ├── pipeline.py          # ValidationPipeline
│   ├── rule_based/          # Rule-based validators
│   │   ├── __init__.py
│   │   ├── completeness.py  # CompletenessValidator
│   │   ├── npi.py           # NPIValidator
│   │   ├── subscriber_id.py # SubscriberIDValidator
│   │   ├── demographics.py  # DemographicsValidator
│   │   ├── coding.py        # CodingValidator
│   │   ├── monetary.py      # MonetaryValidator
│   │   ├── duplicate.py     # DuplicateValidator
│   │   └── timely_filing.py # TimelyFilingValidator
│   └── ai/                  # AI-powered validators
│       ├── __init__.py
│       ├── code_validation.py   # CodeValidationAI
│       ├── coverage_check.py    # CoverageCheckAI
│       └── prior_auth.py        # PriorAuthAI
├── llm/                     # LLM provider abstraction
│   ├── __init__.py          # Re-exports BaseLLMClient, factory
│   ├── base.py              # BaseLLMClient ABC, Message dataclass
│   ├── factory.py           # get_llm_client()
│   └── providers/
│       ├── __init__.py
│       ├── anthropic.py     # AnthropicClient
│       ├── openai.py        # OpenAIClient
│       └── openai_compatible.py  # OpenAICompatibleClient
├── deidentifier/            # HIPAA de-identification
│   ├── __init__.py
│   └── deidentifier.py      # ClaimDeidentifier
├── code_tables/             # Reference data loading
│   ├── __init__.py          # Re-exports lookup functions
│   ├── loader.py            # Lazy singleton loader
│   ├── icd10.py             # ICD-10-CM lookup
│   ├── hcpcs.py             # HCPCS lookup
│   ├── taxonomy.py          # Provider taxonomy lookup
│   └── pos.py               # Place of service lookup
├── data/                    # Bundled compressed tables (package data)
│   ├── icd10_cm.json.gz
│   ├── hcpcs.json.gz
│   ├── taxonomy.json.gz
│   ├── pos_codes.json.gz
│   └── timely_filing.json   # Payer defaults (small, uncompressed)
├── conf.py                  # ClaimValidatorSettings
├── constants.py             # Enums: Severity, ClaimType, ClaimStatus
├── exceptions.py            # Exception hierarchy
└── _api.py                  # validate() convenience function
```

**Test Organization:**

```
tests/
├── conftest.py              # Shared fixtures, claim factories
├── test_models/
│   ├── test_claim.py
│   ├── test_results.py
│   └── test_deidentified.py
├── test_validators/
│   ├── test_base.py
│   ├── test_pipeline.py
│   ├── test_registry.py
│   ├── test_rule_based/
│   │   ├── test_completeness.py
│   │   ├── test_npi.py
│   │   └── ... (one per validator)
│   └── test_ai/
│       ├── test_code_validation.py
│       └── ...
├── test_llm/
│   ├── test_base.py
│   ├── test_factory.py
│   └── test_providers/
│       ├── test_anthropic.py
│       └── ...
├── test_deidentifier/
│   └── test_deidentifier.py
├── test_code_tables/
│   └── test_loader.py
├── test_conf.py
├── test_api.py              # Tests for validate()
└── test_hipaa/              # HIPAA-specific compliance tests
    ├── test_phi_leak.py     # Grep outputs for PHI patterns
    ├── test_no_network.py   # Rule-based makes zero network calls
    └── test_deidentification.py  # All 18 identifiers stripped
```

**One file per class rule:** Each validator, provider, and model gets its own file. No multi-class files except `__init__.py` re-exports.

### Format Patterns

**Validator Output Format:**

Every validator (rule-based and AI) MUST return `ValidatorOutput` via `self._make_output(findings)`:

```python
# CORRECT — all fields populated
Finding(
    code="INVALID_NPI",
    message="NPI fails Luhn check-digit validation",
    severity=Severity.ERROR,
    field_name="billing_provider_npi",
    line_number=None,  # None for claim-level, int for line-level
    suggestion="Verify NPI at https://npiregistry.cms.hhs.gov",
    context={"expected_check_digit": 3, "actual_check_digit": 0},
)

# WRONG — missing fields, PHI in message
Finding(
    code="NPI_ERR",           # Non-standard code format
    message="Bad NPI",         # Not actionable
    severity="error",          # String literal, not enum
    # Missing: field_name, suggestion
)
```

**PHI rule in findings:** `message` and `suggestion` MUST reference field names, not field values. Context dict MAY include non-PHI computed values (check digits, code lookups) but NEVER raw patient data.

**Exception Format:**

```python
# All exceptions inherit from ClaimValidatorError
class ClaimValidatorError(Exception):
    """Base exception for claim-validator library."""

class ValidationError(ClaimValidatorError):
    """Invalid input data (malformed claim, missing required fields)."""

class ConfigurationError(ClaimValidatorError):
    """Invalid library configuration (bad validator path, missing provider)."""

class LLMError(ClaimValidatorError):
    """LLM provider communication failure."""

class CodeTableError(ClaimValidatorError):
    """Code table loading or lookup failure."""
```

**Configuration Format:**

```python
# Settings always use explicit fields, never **kwargs
settings = ClaimValidatorSettings(
    rule_validators=[
        "claim_validator.validators.rule_based.npi.NPIValidator",
        "claim_validator.validators.rule_based.coding.CodingValidator",
    ],
    ai_validators=[
        "claim_validator.validators.ai.code_validation.CodeValidationAI",
    ],
    skip_ai_on_rule_failure=True,
    ai_config={"provider": "anthropic", "api_key": "sk-...", "model": "claude-sonnet-4-5-20241022"},
)
```

### Communication Patterns

**Validator → Pipeline communication:**
- Validators return `ValidatorOutput`, never raise exceptions for validation failures
- Validation failures = `Finding` objects in output. Exceptions = infrastructure failures only
- Pipeline catches validator exceptions → converts to `Finding(code="VALIDATOR_ERROR", severity=ERROR)`

**Pipeline → User communication:**
- `PipelineResult.passed` = `True` only if zero ERROR-severity findings
- `PipelineResult.findings` = flat list from all validators, ordered by: phase (rule first), then severity (ERROR first), then validator order
- `PipelineResult.phase_results` = per-phase breakdown for debugging

**Error propagation:**
- `ValidationError` — raised on invalid input BEFORE validation runs (malformed dict, missing required claim fields)
- `ConfigurationError` — raised on pipeline construction (bad validator path, missing AI config)
- `LLMError` — caught by pipeline, converted to WARNING finding, rule-based results still returned
- Individual validator exceptions — caught by pipeline, logged as VALIDATOR_ERROR finding

### Process Patterns

**Validator implementation contract:**

```python
class BaseValidator(ABC):
    name: str  # Class attribute, UPPER_SNAKE not required but must be unique

    @abstractmethod
    def validate(self, claim: ClaimData) -> ValidatorOutput:
        """
        MUST:
        - Return ValidatorOutput (never raise for validation failures)
        - Be stateless (no self.state between calls)
        - Not modify claim (ClaimData is frozen)
        - Not make network calls (rule-based) or only via BaseLLMClient (AI)

        MUST NOT:
        - Include PHI in Finding messages
        - Have side effects (logging, file I/O, network)
        - Store state between validate() calls
        """

    def _make_output(self, findings: list[Finding]) -> ValidatorOutput:
        """Standard output builder — always use this, never construct ValidatorOutput directly."""
```

**Lazy loading contract:**

```python
# CORRECT — lazy singleton with lock
_TABLE_LOCK = threading.Lock()
_icd10_table: dict[str, str] | None = None

def get_icd10_table() -> dict[str, str]:
    global _icd10_table
    if _icd10_table is None:
        with _TABLE_LOCK:
            if _icd10_table is None:  # Double-check
                _icd10_table = _load_compressed_json("icd10_cm.json.gz")
    return _icd10_table

# WRONG — loading at import time
ICD10_TABLE = _load_compressed_json("icd10_cm.json.gz")  # Violates NFR7
```

**Import pattern at `__init__.py`:**

```python
# Top-level __init__.py — lazy imports for heavy modules
from claim_validator._api import validate
from claim_validator.models import (
    ClaimData, ClaimLineData, Finding, ValidatorOutput, PipelineResult,
)
from claim_validator.validators.base import BaseValidator
from claim_validator.constants import Severity, ClaimType
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.exceptions import (
    ClaimValidatorError, ValidationError, ConfigurationError,
)

# These are conditional — only available when extras installed
def __getattr__(name: str):
    if name == "BaseLLMClient":
        from claim_validator.llm.base import BaseLLMClient
        return BaseLLMClient
    if name == "ClaimDeidentifier":
        from claim_validator.deidentifier import ClaimDeidentifier
        return ClaimDeidentifier
    raise AttributeError(f"module 'claim_validator' has no attribute {name}")

__all__ = [
    "validate", "ValidationPipeline", "ValidatorRegistry",
    "ClaimData", "ClaimLineData", "Finding", "ValidatorOutput", "PipelineResult",
    "BaseValidator", "BaseLLMClient",
    "Severity", "ClaimType",
    "ClaimValidatorSettings",
    "ClaimDeidentifier",
    "ClaimValidatorError", "ValidationError", "ConfigurationError",
]
```

**Test pattern:**

```python
# Every test file follows this structure
import pytest
from claim_validator import validate, ClaimData, Finding, Severity

class TestNPIValidator:
    """Tests for NPIValidator."""

    def setup_method(self):
        """Fresh state per test."""
        self.valid_claim = {
            "billing_provider_npi": "1234567893",  # Valid Luhn
            # ... minimal valid claim
        }

    def test_valid_npi_passes(self):
        result = validate(self.valid_claim)
        npi_findings = [f for f in result.findings if f.code == "INVALID_NPI"]
        assert len(npi_findings) == 0

    def test_invalid_npi_fails(self):
        claim = {**self.valid_claim, "billing_provider_npi": "1234567890"}
        result = validate(claim)
        assert any(f.code == "INVALID_NPI" for f in result.findings)
        finding = next(f for f in result.findings if f.code == "INVALID_NPI")
        assert finding.severity == Severity.ERROR
        assert finding.field_name == "billing_provider_npi"
        assert finding.suggestion  # Must have a suggestion
        assert "1234567890" not in finding.message  # No PHI in message
```

### Enforcement Guidelines

**All AI Agents MUST:**

1. Follow the one-file-per-class rule for validators, providers, and models
2. Use `self._make_output(findings)` to build validator output — never construct `ValidatorOutput` directly
3. Never include PHI (field values) in Finding messages — only field names
4. Use `Severity` enum, never string literals for severity
5. Return `ValidatorOutput` from `validate()` — never raise exceptions for validation failures
6. Use the lazy singleton pattern (with `threading.Lock`) for code table loading
7. Follow the naming conventions exactly: `{Name}Validator`, `{Name}AI`, `{Provider}Client`, `UPPER_SNAKE_CASE` finding codes
8. Write tests in `tests/test_{subpackage}/test_{module}.py` structure
9. Include a PHI-leak assertion in every validator test (assert no patient values in finding messages)
10. Use type annotations on all public API functions and methods

**Pattern Enforcement:**
- ruff rules catch naming violations (N convention rules)
- mypy strict mode catches type annotation gaps
- Custom pytest fixture asserts zero PHI in all Finding outputs
- CI HIPAA test suite (`tests/test_hipaa/`) runs on every PR

## Project Structure & Boundaries

### Complete Project Directory Structure

```
claim-validator/
├── .github/
│   └── workflows/
│       ├── ci.yml                # Lint + type-check + test matrix (3.11/3.12/3.13 × Linux/macOS/Win)
│       ├── release.yml           # Build wheel + publish to PyPI on git tag
│       └── hipaa.yml             # HIPAA compliance: PHI leak scan, no-network test, de-id verification
├── docs/
│   ├── mkdocs.yml               # mkdocs-material config
│   ├── index.md                 # Landing page
│   ├── quickstart.md            # 5-minute install → validate → AI → custom
│   ├── api/                     # Auto-generated API reference (mkdocstrings)
│   ├── guides/
│   │   ├── healthcare-context.md    # CMS-1500, denial reasons, CARC/RARC codes
│   │   ├── custom-validators.md     # BaseValidator subclassing guide
│   │   ├── llm-providers.md         # BaseLLMClient, adding custom providers
│   │   └── migration.md            # Django → library, custom code → library
│   └── contributing.md          # Validator contribution, payer rule contribution
├── src/
│   └── claim_validator/
│       ├── __init__.py              # Re-exports ~15 key symbols + __getattr__ for optional imports
│       ├── py.typed                 # PEP 561 marker
│       ├── _version.py              # Auto-generated by hatch-vcs
│       ├── _api.py                  # validate() convenience function
│       ├── conf.py                  # ClaimValidatorSettings (Pydantic BaseSettings)
│       ├── constants.py             # StrEnums: Severity, ClaimType, ClaimStatus
│       ├── exceptions.py            # ClaimValidatorError hierarchy
│       ├── models/
│       │   ├── __init__.py          # Re-exports: ClaimData, ClaimLineData, Finding, etc.
│       │   ├── claim.py             # ClaimData, ClaimLineData, DiagnosisCode (frozen Pydantic)
│       │   ├── results.py           # Finding, ValidatorOutput, PipelineResult
│       │   └── deidentified.py      # DeidentifiedClaim (type-driven PHI boundary)
│       ├── validators/
│       │   ├── __init__.py          # Re-exports: BaseValidator
│       │   ├── base.py              # BaseValidator ABC, _make_output()
│       │   ├── registry.py          # ValidatorRegistry (dotted-path lazy loading)
│       │   ├── pipeline.py          # ValidationPipeline (two-phase, from_settings, builder)
│       │   ├── rule_based/
│       │   │   ├── __init__.py
│       │   │   ├── completeness.py      # CompletenessValidator (FR7)
│       │   │   ├── npi.py               # NPIValidator (FR8)
│       │   │   ├── subscriber_id.py     # SubscriberIDValidator (FR9)
│       │   │   ├── demographics.py      # DemographicsValidator (FR10)
│       │   │   ├── coding.py            # CodingValidator (FR11-FR13)
│       │   │   ├── monetary.py          # MonetaryValidator (FR14)
│       │   │   ├── duplicate.py         # DuplicateValidator (FR16)
│       │   │   └── timely_filing.py     # TimelyFilingValidator (FR15, FR17)
│       │   └── ai/
│       │       ├── __init__.py
│       │       ├── code_validation.py   # CodeValidationAI (FR18)
│       │       ├── coverage_check.py    # CoverageCheckAI (FR19)
│       │       └── prior_auth.py        # PriorAuthAI (FR20)
│       ├── llm/
│       │   ├── __init__.py          # Re-exports: BaseLLMClient, get_llm_client
│       │   ├── base.py              # BaseLLMClient ABC, Message dataclass (FR27)
│       │   ├── factory.py           # get_llm_client() factory (FR26)
│       │   └── providers/
│       │       ├── __init__.py
│       │       ├── anthropic.py         # AnthropicClient (FR23)
│       │       ├── openai.py            # OpenAIClient (FR24)
│       │       └── openai_compatible.py # OpenAICompatibleClient (FR25)
│       ├── deidentifier/
│       │   ├── __init__.py
│       │   └── deidentifier.py      # ClaimDeidentifier (FR21, FR22)
│       ├── code_tables/
│       │   ├── __init__.py          # Re-exports: lookup functions
│       │   ├── loader.py            # Lazy singleton loader with threading.Lock
│       │   ├── icd10.py             # ICD-10-CM lookup (FR38)
│       │   ├── hcpcs.py             # HCPCS lookup (FR39)
│       │   ├── taxonomy.py          # Provider taxonomy lookup (FR41)
│       │   └── pos.py               # Place of service lookup (FR40)
│       └── data/                    # Package data (bundled compressed tables)
│           ├── icd10_cm.json.gz         # ~72K codes, ~2MB compressed
│           ├── hcpcs.json.gz            # ~8K codes
│           ├── taxonomy.json.gz         # ~900 codes
│           ├── pos_codes.json.gz        # ~100 codes
│           └── timely_filing.json       # Payer filing deadlines (small, uncompressed)
├── tests/
│   ├── conftest.py                  # Shared fixtures: valid_claim_dict, claim_factory, etc.
│   ├── test_api.py                  # Tests for validate() top-level function
│   ├── test_conf.py                 # Tests for ClaimValidatorSettings
│   ├── test_models/
│   │   ├── test_claim.py            # ClaimData, ClaimLineData validation, frozen behavior
│   │   ├── test_results.py          # Finding, ValidatorOutput, PipelineResult
│   │   └── test_deidentified.py     # DeidentifiedClaim type enforcement
│   ├── test_validators/
│   │   ├── test_base.py             # BaseValidator contract tests
│   │   ├── test_pipeline.py         # Two-phase execution, gate logic, aggregation
│   │   ├── test_registry.py         # Dotted-path loading, lazy import, error handling
│   │   ├── test_rule_based/
│   │   │   ├── test_completeness.py
│   │   │   ├── test_npi.py
│   │   │   ├── test_subscriber_id.py
│   │   │   ├── test_demographics.py
│   │   │   ├── test_coding.py
│   │   │   ├── test_monetary.py
│   │   │   ├── test_duplicate.py
│   │   │   └── test_timely_filing.py
│   │   └── test_ai/
│   │       ├── test_code_validation.py
│   │       ├── test_coverage_check.py
│   │       └── test_prior_auth.py
│   ├── test_llm/
│   │   ├── test_base.py             # BaseLLMClient contract
│   │   ├── test_factory.py          # get_llm_client() factory
│   │   └── test_providers/
│   │       ├── test_anthropic.py
│   │       ├── test_openai.py
│   │       └── test_openai_compatible.py
│   ├── test_deidentifier/
│   │   └── test_deidentifier.py     # All 18 HIPAA identifiers stripped
│   ├── test_code_tables/
│   │   └── test_loader.py           # Lazy loading, thread safety, compressed JSON
│   └── test_hipaa/                  # HIPAA compliance test suite
│       ├── test_phi_leak.py         # Scan all Finding outputs for PHI patterns
│       ├── test_no_network.py       # Rule-based validation makes zero network calls
│       └── test_deidentification.py # Verify all 18 identifiers stripped before LLM
├── pyproject.toml               # PEP 621 metadata, hatchling backend, tool configs
├── uv.lock                      # uv lockfile
├── README.md                    # Quickstart, badges, 3-line example
├── LICENSE                      # MIT
├── CHANGELOG.md                 # Keep-a-changelog format
├── .gitignore
├── .pre-commit-config.yaml      # ruff check, ruff format
└── .env.example                 # CLAIM_VALIDATOR_* env vars documented
```

### Architectural Boundaries

**Public API Boundary (what users import):**

| Symbol | Module | Stability |
|---|---|---|
| `validate()` | `_api.py` | Stable from v1.0 |
| `ClaimData`, `ClaimLineData` | `models/claim.py` | Stable from v1.0 |
| `Finding`, `ValidatorOutput`, `PipelineResult` | `models/results.py` | Stable from v1.0 |
| `BaseValidator` | `validators/base.py` | Stable from v1.0 |
| `ValidationPipeline` | `validators/pipeline.py` | Stable from v1.0 |
| `ValidatorRegistry` | `validators/registry.py` | Stable from v1.0 |
| `BaseLLMClient` | `llm/base.py` | Stable from v1.0 (requires `[ai]` extra) |
| `ClaimDeidentifier` | `deidentifier/deidentifier.py` | Stable from v1.0 |
| `ClaimValidatorSettings` | `conf.py` | Stable from v1.0 |
| `Severity`, `ClaimType` | `constants.py` | Stable from v1.0 |
| Exception hierarchy | `exceptions.py` | Stable from v1.0 |

**Internal boundary (not part of public API):**
- `_api.py` — underscore prefix signals internal
- `_version.py` — auto-generated
- `code_tables/loader.py` — internal loading mechanism
- `validators/registry.py` internals — only `ValidatorRegistry` class is public
- All `providers/*.py` — accessed via `get_llm_client()` factory, not directly

**Optional dependency boundary:**
- `claim_validator.llm` — imports fail gracefully if `[ai]` extra not installed
- `claim_validator.deidentifier` — available in core but only useful with AI
- `claim_validator.validators.ai` — requires LLM client, guarded by import check

### Requirements to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|---|---|---|
| **Claim Validation (FR1-FR6)** | `_api.py`, `models/results.py` | `validators/pipeline.py`, `conf.py` |
| **Rule-Based Validators (FR7-FR17)** | `validators/rule_based/*.py` | `code_tables/*.py`, `data/*.json.gz` |
| **AI Validation (FR18-FR22)** | `validators/ai/*.py`, `deidentifier/` | `llm/base.py`, `models/deidentified.py` |
| **LLM Provider Support (FR23-FR27)** | `llm/providers/*.py`, `llm/factory.py` | `llm/base.py` |
| **Pipeline & Extensibility (FR28-FR33)** | `validators/base.py`, `validators/pipeline.py`, `validators/registry.py` | `conf.py` |
| **Data Models & Input (FR34-FR37)** | `models/claim.py` | `constants.py` |
| **Code Tables (FR38-FR42)** | `code_tables/*.py`, `data/*.json.gz` | `code_tables/loader.py` |
| **Configuration & Distribution (FR43-FR49)** | `conf.py`, `pyproject.toml`, `__init__.py` | `.github/workflows/release.yml` |

### Data Flow

```
User Input (dict or ClaimData)
    │
    ▼
validate() [_api.py]
    │ Constructs ClaimData if dict, builds pipeline from settings
    ▼
ValidationPipeline.run(claim) [validators/pipeline.py]
    │
    ├── Phase 1: Rule-Based (offline, synchronous)
    │   ├── ValidatorRegistry loads validators [validators/registry.py]
    │   ├── Each validator.validate(claim) → ValidatorOutput
    │   │   └── Code table lookups [code_tables/*.py] → lazy-loaded from [data/*.json.gz]
    │   └── Aggregate findings → partial PipelineResult
    │
    ├── Gate: skip_ai_on_rule_failure check
    │
    └── Phase 2: AI (network, async-friendly)
        ├── ClaimDeidentifier.deidentify(claim) → DeidentifiedClaim [deidentifier/]
        ├── get_llm_client(config) → BaseLLMClient [llm/factory.py]
        ├── Each ai_validator.validate(deidentified_claim) → ValidatorOutput
        │   ├── Construct prompt (per-validator)
        │   ├── client.send_messages() → str [llm/providers/*.py]
        │   └── Parse response → Finding objects
        └── Aggregate all findings → complete PipelineResult
    │
    ▼
PipelineResult (passed, findings, phase_results, execution_time)
    │
    ▼
User receives structured result
```

### Development Workflow

**Local development:**
```bash
uv sync --all-extras           # Install all deps including dev
uv run pytest                  # Run tests
uv run ruff check .            # Lint
uv run ruff format .           # Format
uv run mypy src/               # Type check
```

**CI pipeline (ci.yml):**
- Matrix: Python {3.11, 3.12, 3.13} × OS {ubuntu, macos, windows}
- Steps: checkout → uv sync → ruff check → mypy → pytest --cov
- Fail on: any lint error, type error, test failure, coverage <90%

**Release pipeline (release.yml):**
- Trigger: git tag `v*`
- Steps: checkout → uv build → twine check → publish to PyPI
- Version from git tag via hatch-vcs

**HIPAA pipeline (hipaa.yml):**
- Trigger: every PR
- Steps: PHI leak scan (grep Finding outputs for SSN/DOB patterns), no-network test (run rule-based in sandboxed env), de-identification verification (all 18 identifiers)

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
All technology choices are compatible and conflict-free:
- Python 3.11+ ↔ Pydantic 2.x: Native support, full typing compatibility
- hatchling ↔ uv: hatchling is a supported build backend in uv ecosystem
- ruff ↔ Python 3.11: Target version alignment confirmed
- Compressed JSON ↔ hatchling: Package data inclusion via `[tool.hatch.build]`
- Frozen Pydantic models ↔ thread-safe validators: Immutability guarantees enable safe concurrent use
- Lazy singleton loading ↔ <500ms import time: Loading deferred past import, meets NFR7
- Pipeline-integrated de-id ↔ type-driven PHI boundary: `DeidentifiedClaim` created by pipeline, consumed by AI validators — no bypass path

**No contradictory decisions found.**

**Pattern Consistency:**
- Naming: All patterns use consistent Python conventions (snake_case modules, PascalCase classes, UPPER_SNAKE constants)
- Error handling: Consistent pattern across all components — validators return findings, infrastructure raises typed exceptions, pipeline catches and converts
- Lazy loading: Uniform double-check locking pattern for all code tables
- Testing: Uniform test structure (class-based, setup_method, PHI leak assertions) across all modules

**Structure Alignment:**
- src layout enables clean packaging boundaries (public vs internal)
- One-file-per-class supports independent development of validators/providers by different agents
- Test mirror of source structure ensures no test gaps
- `data/` directory co-located with `code_tables/` module for clear data ownership

### Requirements Coverage Validation

**Functional Requirements Coverage: 49/49 (100%)**

| FR Range | Category | Architectural Support | Status |
|---|---|---|---|
| FR1-FR6 | Claim Validation | `_api.py` → `ValidationPipeline` → `PipelineResult` with `Finding` objects | Full |
| FR7-FR17 | Rule-Based Validators | 8 validators in `validators/rule_based/`, each mapped to specific FRs | Full |
| FR18-FR22 | AI Validation | 3 AI validators + `ClaimDeidentifier` + `DeidentifiedClaim` type | Full |
| FR23-FR27 | LLM Providers | `BaseLLMClient` ABC + 3 concrete providers + `get_llm_client()` factory | Full |
| FR28-FR33 | Pipeline & Extensibility | `BaseValidator` ABC + `ValidatorRegistry` + `ValidationPipeline` (from_settings + builder) | Full |
| FR34-FR37 | Data Models | `ClaimData`, `ClaimLineData`, `DiagnosisCode` — frozen Pydantic, dict + typed input | Full |
| FR38-FR42 | Code Tables | Lazy singleton loaders + compressed JSON in `data/` + `timely_filing.json` defaults | Full |
| FR43-FR49 | Config & Distribution | `ClaimValidatorSettings` (BaseSettings) + `pyproject.toml` extras + `py.typed` | Full |

**Non-Functional Requirements Coverage: 29/29 (100%)**

| NFR Range | Category | Architectural Support | Status |
|---|---|---|---|
| NFR1-NFR7 | Performance | Lazy loading (NFR7), compressed JSON <15MB (NFR5/29), stateless validators (NFR1/6), in-memory dict lookups (NFR4) | Full |
| NFR8-NFR13 | Security | Pipeline-integrated de-id (NFR8/9), zero PHI in findings/exceptions (NFR10), no telemetry (NFR11), API keys never in output (NFR12), `uv` lockfile + CI audit (NFR13) | Full |
| NFR14-NFR16 | Scalability | Stateless validators + `threading.Lock` singletons (NFR14), no state between calls (NFR15), O(n) linear with lines (NFR16) | Full |
| NFR17-NFR20 | Reliability | Deterministic rule-based (NFR17), `LLMError` → WARNING finding (NFR18), `ValidationError` for bad input (NFR19), code table checksums (NFR20) | Full |
| NFR21-NFR25 | Compatibility | CI matrix 3.11/3.12/3.13 x 3 OS (NFR21/22), Pydantic-only core (NFR23/24), `py.typed` marker (NFR25) | Full |
| NFR26-NFR29 | Quality | Test structure + HIPAA suite (NFR26), ruff config (NFR27), mkdocs + mkdocstrings (NFR28), compressed tables <15MB (NFR29) | Full |

### Implementation Readiness Validation

**Decision Completeness:** 13/13 decisions documented with choices, rationale, and affected components. Versions specified where applicable. Implementation sequence defined with dependency chain.

**Structure Completeness:** Full directory tree with ~70 files/directories specified. Every file mapped to specific FRs. Test mirrors source 1:1. CI/CD workflows defined.

**Pattern Completeness:** 28 conflict points addressed. Naming conventions cover all elements (modules, classes, functions, constants, error codes). Code examples provided for: validator implementation, lazy loading, `__init__.py` re-export, test structure, Finding construction, configuration. Anti-patterns documented alongside correct patterns.

### Gap Analysis Results

**Critical Gaps: 0** — No missing decisions that block implementation.

**Important Gaps: 2 (resolved)**

1. **Code table version metadata** — Add `data/manifest.json` containing version, effective date, and code count per table. Code table loader checks manifest age, emits WARNING finding if >12 months old. Addresses NFR20 and PRD stale-table risk mitigation.

2. **AI validator base class** — Add `BaseAIValidator(BaseValidator)` in `validators/ai/base.py` that accepts `llm_client: BaseLLMClient` in constructor and provides `self._send_to_llm(messages)` helper. Pipeline constructs AI validators with the LLM client injected. Cleaner separation between rule-based and AI validator contracts.

**Nice-to-Have Gaps: 1 (noted)**

1. **Logging strategy** — Use standard Python `logging.getLogger(__name__)` in all modules. Never add handlers — let consumers configure. Not blocking for implementation.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed (47 existing patterns mapped)
- [x] Scale and complexity assessed (High — healthcare, brownfield, multi-provider)
- [x] Technical constraints identified (9 constraints with architectural implications)
- [x] Cross-cutting concerns mapped (7 concerns with strategies)

**Architectural Decisions**

- [x] Critical decisions documented with versions (13 decisions, all with rationale)
- [x] Technology stack fully specified (Python 3.11+, Pydantic 2.x, hatchling, uv, ruff, mypy, pytest)
- [x] Integration patterns defined (LLM providers, code tables, validator registry)
- [x] Performance considerations addressed (lazy loading, compressed tables, stateless validators)

**Implementation Patterns**

- [x] Naming conventions established (modules, classes, functions, constants, error codes)
- [x] Structure patterns defined (one-file-per-class, src layout, test mirror)
- [x] Communication patterns specified (validator → pipeline → user, error propagation)
- [x] Process patterns documented (validator contract, lazy loading, import, test)

**Project Structure**

- [x] Complete directory structure defined (~70 files/directories)
- [x] Component boundaries established (public API, internal, optional dependency)
- [x] Integration points mapped (data flow diagram, pipeline phases)
- [x] Requirements to structure mapping complete (all 8 FR categories → specific files)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — all 49 FRs and 29 NFRs architecturally covered, zero critical gaps, coherent decision set with no contradictions.

**Key Strengths:**
1. **Zero-ambiguity public API** — 15 symbols, all stable from v1.0, clear import paths
2. **HIPAA safety by architecture** — type-driven PHI boundary + pipeline-integrated de-id = impossible to bypass
3. **Comprehensive patterns** — AI agents have concrete examples for every pattern, with anti-patterns documented
4. **Clean extraction path** — brownfield patterns mapped to library equivalents (Django ORM → Pydantic, TextChoices → StrEnum, etc.)
5. **Performance by design** — lazy loading, compressed tables, stateless validators all address NFR budgets architecturally

**Areas for Future Enhancement:**
1. Async pipeline execution (asyncio-based AI validators) — Phase 2
2. Plugin discovery via entry_points (payer rule packages) — Phase 2
3. Caching layer for LLM responses (avoid redundant calls) — Phase 2
4. Batch optimization (parallel validator execution) — Phase 3

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all 13 architectural decisions exactly as documented
- Use implementation patterns consistently — refer to pattern examples, not improvisation
- Respect the one-file-per-class rule and project structure boundaries
- Every validator must pass the PHI-leak test before merge
- Use `self._make_output(findings)` — never construct `ValidatorOutput` directly

**First Implementation Priority:**
```bash
uv init --lib --build-backend hatchling claim-validator
```
Then: pyproject.toml configuration → core models → constants → exceptions → configuration → code tables → validator base + registry → pipeline → rule-based validators → de-identifier → LLM abstraction → AI validators → `validate()` API → `__init__.py` re-exports
