---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-02-18'
extensionStartedAt: '2026-02-27'
extensionScope: 'eligibility-verification-module'
extensionStepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
extensionStatus: 'complete'
extensionCompletedAt: '2026-02-27'
paExtensionStartedAt: '2026-03-01'
paExtensionScope: 'prior-authorization-module'
paExtensionStepsCompleted: [2, 3, 4, 5, 6, 7, 8]
paExtensionStatus: 'complete'
paExtensionCompletedAt: '2026-03-01'
refactoringExtensionStartedAt: '2026-03-02'
refactoringExtensionScope: 'v3-codebase-refactoring'
refactoringExtensionStepsCompleted: [2, 3, 4, 5, 6, 7, 8]
refactoringExtensionStatus: 'complete'
refactoringExtensionCompletedAt: '2026-03-02'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-18.md'
  - '_bmad-output/project-context.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-26.md'
  - '_bmad-output/planning-artifacts/research/domain-healthcare-eligibility-verification-research-2026-02-26.md'
  - 'docs/Claim-Eligibility-Check-Implementation-Guide.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-27.md'
  - '_bmad-output/planning-artifacts/research/domain-healthcare-prior-authorization-278-research-2026-02-27.md'
  - '_bmad-output/planning-artifacts/prd.md (v3.0 refactoring PRD - 2026-03-02)'
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

---

## Eligibility Verification Module — Context Analysis

### Requirements Overview

**Functional Requirements:**
47 FRs across 8 categories extending the library with clearinghouse connectivity, eligibility-specific models, and AI-powered 271 interpretation.

| Category | Count | Architectural Impact |
|---|---|---|
| Eligibility Request Data (FR1-FR7) | 7 | New `EligibilityRequest` model family, subscriber/patient/provider fields |
| Rule-Based Validation (FR8-FR15) | 8 | 6 new validators reusing `BaseValidator`; payer directory as new code table |
| Clearinghouse Integration (FR16-FR22) | 7 | NEW: `BaseClearinghouseClient` ABC + `StediClient`; first external service beyond LLMs |
| Response Parsing (FR23-FR29) | 7 | New `EligibilityResponse`, `BenefitInfo`, `CoverageInfo` models; 271 JSON→Pydantic |
| AI Interpretation (FR30-FR35) | 6 | Extend de-identifier for eligibility; reuse LLM providers; eligibility-specific prompts |
| Pipeline Orchestration (FR36-FR40) | 5 | `EligibilityPipeline` — three-phase (validate→clearinghouse→AI); `EligibilityResult` |
| Configuration (FR41-FR44) | 4 | Extend `ClaimValidatorSettings` with Stedi credentials and eligibility validator lists |
| Extensibility (FR45-FR47) | 3 | Custom eligibility validators + custom clearinghouse clients via subclassing |

**Non-Functional Requirements:**
23 NFRs across 5 categories, largely consistent with existing constraints.

| Category | Count | Key Constraint |
|---|---|---|
| Performance (NFR1-NFR5) | 5 | <100ms rule-based, <2s library overhead on top of Stedi RTT, <50ms response parsing |
| Security & Privacy (NFR6-NFR10) | 5 | 18 HIPAA identifiers stripped before LLM; PHI allowed to clearinghouse; no PHI in logs |
| Integration Reliability (NFR11-NFR14) | 4 | HTTP 4xx/5xx → structured errors; 30s default timeout; LLM failure → graceful degradation |
| Code Quality (NFR15-NFR20) | 6 | mypy strict, ruff clean, >90% coverage, backward compatible, optional deps |
| Documentation (NFR21-NFR23) | 3 | Docstrings, quickstart, API reference |

**Scale & Complexity:**

- Primary domain: **Python library extension** (brownfield, same package)
- Complexity level: **Medium-High** — new clearinghouse integration layer, but 60% pattern reuse from existing architecture
- New architectural components: **~8 major** — eligibility models, eligibility validators, clearinghouse abstraction, Stedi client, response parser, eligibility de-identifier extension, eligibility pipeline, `check_eligibility()` API

### New Technical Constraints & Dependencies

| Constraint | Source | Architectural Implication |
|---|---|---|
| **Stedi JSON API** | FR16-FR22 | New external HTTP dependency; requires `httpx`; sandbox + production modes; API key management |
| **PHI dual-path** | NFR6, FR30 | Clearinghouse REQUIRES PHI (covered entity). AI path STRIPS PHI. Architecture must enforce both paths correctly |
| **Backward compatibility** | NFR19 | Existing `validate()` API must remain unchanged; `check_eligibility()` is additive |
| **Optional `[stedi]` extra** | NFR20 | Rule-based eligibility validation works without httpx; clearinghouse requires it |
| **30-second timeout** | NFR12 | CAQH CORE mandates 20s clearinghouse response; library adds 10s buffer |
| **Payer directory** | FR9 | Bundled static data (~3,400 payer IDs from Stedi); same lazy-load pattern as code tables |
| **AAA error segments** | FR21 | 271 responses include structured rejection codes; need dedicated error model |

### New Cross-Cutting Concerns

| Concern | Scope | Strategy |
|---|---|---|
| **Clearinghouse abstraction** | Stedi (MVP), future providers | `BaseClearinghouseClient` ABC mirrors `BaseLLMClient` pattern: abstract interface + factory + concrete implementations |
| **PHI dual-path enforcement** | Clearinghouse path vs AI path | Pipeline enforces: raw `EligibilityRequest` → clearinghouse (PHI allowed); de-identified response → LLM (PHI stripped). Type-driven boundary |
| **Payer directory loading** | Offline payer ID validation | Reuse code tables lazy singleton pattern; new `data/payer_directory.json.gz` |
| **Eligibility settings** | Stedi config, eligibility validators | Extend `ClaimValidatorSettings` with `stedi_api_key`, `stedi_environment`, `eligibility_rule_validators`, `eligibility_ai_validators` |
| **Graceful degradation (3-tier)** | Rule-based → Clearinghouse → AI | Each phase fails independently: rule-based always works; clearinghouse down → structured error; LLM down → return structured response without AI summary |
| **Error model extension** | Clearinghouse errors, AAA rejections | New `ClearinghouseError` exception; `AAAError` model for rejection segments; integrate into `Finding` pattern |

### Reuse Analysis

| Existing Component | Reuse Strategy | Modification Needed |
|---|---|---|
| `BaseValidator` ABC | Direct reuse | None — eligibility validators subclass the same base |
| `ValidatorRegistry` | Direct reuse | None — same dotted-path loading for eligibility validators |
| `BaseLLMClient` + providers | Direct reuse | None — eligibility AI uses same LLM providers |
| `ClaimDeidentifier` | Extend | Add eligibility-specific field mappings (subscriber name, member ID, DOB) |
| `Finding`, `Severity`, `ValidatorOutput` | Direct reuse | None — eligibility validators produce same output types |
| `ClaimValidatorSettings` | Extend | Add Stedi config, eligibility validator lists, eligibility-specific settings |
| Code table loader pattern | Pattern reuse | New payer directory table using same lazy singleton pattern |
| Exception hierarchy | Extend | Add `ClearinghouseError` as new subclass of `ClaimValidatorError` |
| Test patterns | Direct reuse | Same class-based structure, PHI-leak assertions, factory pattern |
| `__init__.py` re-export pattern | Extend | Add eligibility symbols to top-level exports |

### Starter Template Evaluation (Extension)

**Primary Technology Domain:** Python library extension — adding `eligibility/` subpackage to existing `claim-validator` package.

**Starter: N/A — Existing Package Extension**

All foundational decisions from the original architecture (D1-D13) remain in effect. No new starter template needed.

**What the extension adds to `pyproject.toml`:**

```toml
[project.optional-dependencies]
stedi = ["httpx>=0.27"]  # NEW — clearinghouse connectivity
all = ["claim-validator[ai,stedi,server,django,fastapi]"]  # MODIFIED — include stedi
```

**Extension lives inside the existing package** as `src/claim_validator/eligibility/` subpackage. All existing tooling (hatchling, uv, ruff, mypy, pytest) applies unchanged.

## Eligibility Module — Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- D14: Clearinghouse client abstraction → ABC + factory
- D15: Eligibility data models → Flat request, nested response
- D16: Eligibility pipeline → Separate `EligibilityPipeline`, three-phase
- D17: PHI dual-path enforcement → Pipeline-level + type-driven

**Important Decisions (Shape Architecture):**
- D18: Stedi client → Sync `httpx.Client` with context manager
- D19: Payer directory → Uncompressed JSON, lazy singleton
- D20: AAA error model → Dual access (AAAError model + Finding objects)
- D21: Eligibility de-identification → Separate `EligibilityDeidentifier`
- D22: AI interpretation → Single `EligibilityInterpreterAI` validator
- D23: Settings → Extend `ClaimValidatorSettings` with flat fields

**Deferred Decisions (Post-MVP):**
- Batch eligibility pipeline — v1.1
- Multi-clearinghouse factory implementations — v1.2
- Async pipeline execution — v1.1
- FHIR model mapping — v2.0

### Clearinghouse Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D14: BaseClearinghouseClient** | ABC + factory — mirrors `BaseLLMClient` pattern | `BaseClearinghouseClient` ABC with `submit_eligibility(request) -> dict` method. `get_clearinghouse_client(provider, **config)` factory. `StediClient` as first concrete implementation. Consistent with D7 (LLM client) pattern | `eligibility/clearinghouse/base.py`, `eligibility/clearinghouse/factory.py`, `eligibility/clearinghouse/stedi.py` |
| **D18: HTTP client** | Sync `httpx.Client` with context manager | PRD explicitly defers async. `httpx.Client` supports session reuse, configurable timeout (30s default per NFR12), connection pooling. Context manager ensures proper cleanup | `eligibility/clearinghouse/stedi.py` |

**Clearinghouse client contract:**
```
BaseClearinghouseClient (ABC)
├── submit_eligibility(request: EligibilityRequest) -> dict  # raw 271 JSON
├── provider_name: str
├── environment: str  # "sandbox" | "production"
│
└── StediClient — httpx.Client, Stedi JSON API
```

**StediClient internals:**
```python
class StediClient(BaseClearinghouseClient):
    provider_name = "stedi"

    def __init__(self, api_key: str, environment: str = "sandbox", timeout: float = 30.0):
        self._client = httpx.Client(
            base_url=self._base_url(environment),
            headers={"Authorization": f"Key {api_key}"},
            timeout=timeout,
        )

    def submit_eligibility(self, request: EligibilityRequest) -> dict: ...
    def close(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args) -> None: ...
```

### Data Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D15: Model design** | Flat request, nested response | `EligibilityRequest` is flat (like `ClaimData`) — simple dict-compatible input. `EligibilityResponse` is nested — 271 data has inherent hierarchy (coverage status, benefit list, plan info). All frozen=True, strict=False (matches D3) | `eligibility/models/` |
| **D19: Payer directory** | Uncompressed JSON, lazy singleton | ~3,400 payer entries (~200KB). No compression needed. Same lazy singleton pattern (D2) with `threading.Lock`. JSON dict keyed by payer ID for O(1) lookup | `eligibility/data/payer_directory.json`, `eligibility/code_tables/payer_directory.py` |
| **D20: AAA errors** | Dual access — `AAAError` model + `Finding` objects | `AAAError` Pydantic model in `EligibilityResponse.errors` for programmatic access. Pipeline also creates `Finding(code="AAA_REJECTION")` for consistent pipeline output | `eligibility/models/errors.py`, `eligibility/pipeline.py` |

**Model hierarchy:**
```
EligibilityRequest (frozen, flat)
├── provider_npi, provider_taxonomy
├── payer_id
├── subscriber_id, subscriber_first_name, subscriber_last_name, subscriber_dob
├── patient_* (optional, for dependents)
├── service_type_code, date_of_service
└── relationship_code

EligibilityResponse (frozen, nested)
├── eligible: bool | None
├── coverage: CoverageInfo
│   ├── status: CoverageStatus (active/inactive/unknown)
│   ├── effective_date, termination_date
│   └── plan_name, group_number
├── benefits: list[BenefitInfo]
│   ├── service_type_code, service_type_name
│   ├── copay, coinsurance, deductible
│   ├── in_network: bool | None
│   └── prior_auth_required: bool | None
├── errors: list[AAAError]
│   ├── rejection_code, follow_up_code
│   └── message
└── raw_response: dict  # full Stedi JSON

EligibilityResult (pipeline output)
├── eligible: bool | None
├── response: EligibilityResponse | None
├── findings: list[Finding]
├── ai_summary: str | None
├── passed: bool (rule-based)
├── raw_response: dict | None
└── execution_time: float
```

### Security Architecture (HIPAA Extension)

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D17: PHI dual-path** | Both: pipeline-level + type-driven (belt-and-suspenders) | Matches existing D5+D6 pattern. Clearinghouse receives raw `EligibilityRequest` (PHI required). AI receives `DeidentifiedEligibilityResponse` (PHI stripped). Pipeline enforces ordering | `eligibility/pipeline.py`, `eligibility/deidentifier.py`, `eligibility/models/deidentified.py` |
| **D21: De-identifier** | New `EligibilityDeidentifier` — separate class | Eligibility data has different fields than claims. Separate class, same patterns as `ClaimDeidentifier`. Operates on `EligibilityResponse` → `DeidentifiedEligibilityResponse` | `eligibility/deidentifier.py` |

**PHI flow:**
```
EligibilityRequest (has PHI) ──────────→ Clearinghouse (PHI allowed)
                                              │
                                              ▼
                                     EligibilityResponse (has PHI)
                                              │
                              EligibilityDeidentifier.deidentify()
                                              │
                                              ▼
                              DeidentifiedEligibilityResponse (no PHI) → LLM
```

**Safe fields for LLM:** payer ID, service type codes, benefit amounts, copay/coinsurance values, deductible amounts, coverage dates (year only), plan type codes.
**Stripped fields:** subscriber name, DOB, member ID, address, SSN, group-specific identifiers.

### Pipeline Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D16: Pipeline design** | Separate `EligibilityPipeline` — three-phase | Eligibility has fundamentally different flow: rule-based → clearinghouse → AI. The clearinghouse step is an external API call that transforms data, not a validator. Separate class, same patterns | `eligibility/pipeline.py` |
| **D22: AI interpretation** | Single `EligibilityInterpreterAI` validator | One AI validator for eligibility (not 3 like claim validation). 271 response is one document to interpret holistically. Returns `Finding` objects + `ai_summary` string | `eligibility/validators/ai/interpreter.py` |

**Pipeline execution model:**
```
EligibilityPipeline.run(request_data)
  ├── Phase 1: Rule-based validators (sequential, offline)
  │   ├── NPIValidator (reuse existing)
  │   ├── PayerIDValidator (new)
  │   ├── DemographicsValidator (new, eligibility-specific)
  │   ├── ServiceTypeValidator (new)
  │   ├── DateValidator (new)
  │   ├── MemberIDValidator (new)
  │   └── Aggregate → partial EligibilityResult (passed, findings)
  │
  ├── Gate: if rule_phase_failed AND skip_clearinghouse_on_failure → return
  │
  ├── Phase 2: Clearinghouse (single call, network)
  │   ├── get_clearinghouse_client(config) → BaseClearinghouseClient
  │   ├── client.submit_eligibility(request) → raw 271 dict
  │   ├── Parse raw dict → EligibilityResponse
  │   └── If error → ClearinghouseError finding, return partial result
  │
  ├── Gate: if skip_ai → return with structured response
  │
  └── Phase 3: AI interpretation (optional, network)
      ├── EligibilityDeidentifier.deidentify(response) → DeidentifiedEligibilityResponse
      ├── EligibilityInterpreterAI(deidentified_response) → AI findings + summary
      └── Aggregate → complete EligibilityResult
```

### Configuration

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D23: Settings** | Extend `ClaimValidatorSettings` with flat fields | Add `stedi_api_key`, `stedi_environment`, `eligibility_rule_validators`, `eligibility_ai_validators`, `skip_clearinghouse_on_rule_failure`, `skip_ai` as flat fields. All use `CLAIM_VALIDATOR_` env prefix (FR41) | `conf.py` (modify existing) |

### Decision Impact Analysis

**Implementation Sequence (eligibility module):**
1. Eligibility models (D15) — `EligibilityRequest`, `EligibilityResponse`, `BenefitInfo`, `CoverageInfo`, `AAAError`, `EligibilityResult`
2. Settings extension (D23) — Stedi config, eligibility validator lists
3. Payer directory (D19) — bundled JSON, lazy loader
4. Rule-based eligibility validators — 6 validators (NPI reuse + 5 new)
5. Clearinghouse abstraction (D14) — `BaseClearinghouseClient` ABC, factory
6. Stedi client (D18) — `StediClient` implementation
7. Response parser — raw 271 JSON → `EligibilityResponse`
8. Eligibility de-identifier (D21) — `EligibilityDeidentifier`, `DeidentifiedEligibilityResponse`
9. AI interpreter (D22) — `EligibilityInterpreterAI`
10. Pipeline (D16, D17) — `EligibilityPipeline` with three-phase execution and PHI enforcement
11. Top-level API — `check_eligibility()` convenience function
12. `__init__.py` re-exports — add eligibility symbols

**Cross-Component Dependencies:**
- D15 (models) enables D16 (pipeline) — pipeline operates on eligibility models
- D14 (clearinghouse) + D18 (Stedi client) — StediClient implements BaseClearinghouseClient
- D16 (pipeline) requires D17 (PHI dual-path) + D21 (de-identifier) — pipeline enforces de-id before AI
- D17 (PHI dual-path) requires D15 (models) — `DeidentifiedEligibilityResponse` is a model
- D23 (settings) required by D16 (pipeline) — pipeline reads settings for config
- D19 (payer directory) required by `PayerIDValidator` — offline payer lookup

## Eligibility Module — Implementation Patterns & Consistency Rules

### Eligibility-Specific Conflict Points

**12 new conflict areas** identified for the eligibility extension, all resolved below. These extend the existing 28 conflict points from the core architecture.

### Eligibility Naming Patterns

**Module & Class Naming:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Eligibility models | `Eligibility{Name}` or `{Name}Info` for sub-models | `EligibilityRequest`, `BenefitInfo` | `EligRequest`, `Benefit`, `BenefitData` |
| Eligibility validators | `{Name}Validator` (same base convention) | `PayerIDValidator`, `ServiceTypeValidator` | `PayerValidator`, `CheckPayerID` |
| Clearinghouse clients | `{Provider}Client` (mirrors LLM) | `StediClient` | `StediAPI`, `StediProvider` |
| Clearinghouse base | `BaseClearinghouseClient` | — | `ClearinghouseBase`, `AbstractClearinghouse` |
| Eligibility AI | `EligibilityInterpreterAI` | — | `EligibilityAI`, `InterpretEligibilityAI` |
| Pipeline | `EligibilityPipeline` | — | `EligPipeline`, `EligibilityValidationPipeline` |
| De-identifier | `EligibilityDeidentifier` | — | `EligDeidentifier`, `ResponseDeidentifier` |
| Top-level API | `check_eligibility()` | — | `verify_eligibility()`, `eligibility_check()` |

**Finding Code Conventions:**

| Category | Prefix | Example | Anti-Pattern |
|---|---|---|---|
| Rule-based eligibility | `ELIG_` prefix | `ELIG_INVALID_PAYER`, `ELIG_MISSING_SUBSCRIBER` | `INVALID_PAYER` (conflicts with claim codes) |
| Clearinghouse errors | `CLEARINGHOUSE_` prefix | `CLEARINGHOUSE_TIMEOUT`, `CLEARINGHOUSE_ERROR` | `STEDI_ERROR` (vendor-specific) |
| AAA rejections | `AAA_REJECTION` | `AAA_REJECTION` with context dict containing code | `AAA_71`, `REJECTION_SUBSCRIBER_NOT_FOUND` |
| AI eligibility | `AI_ELIG_` prefix | `AI_ELIG_COVERAGE_SUMMARY`, `AI_ELIG_LIMITATION` | `AI_COVERAGE` (conflicts with claim AI codes) |

### Eligibility Communication Patterns

**Clearinghouse → Pipeline:**
- `BaseClearinghouseClient.submit_eligibility()` returns raw `dict` (JSON), never raises for business-level rejections
- HTTP errors (4xx, 5xx, timeout) → raise `ClearinghouseError` with structured info
- AAA rejections → returned in the response dict, parsed into `AAAError` models by response parser
- Pipeline catches `ClearinghouseError` → converts to `Finding(code="CLEARINGHOUSE_ERROR", severity=ERROR)`

**Response Parser → Pipeline:**
- `parse_271_response(raw: dict) -> EligibilityResponse` — pure function
- Unmapped/unexpected fields → logged as WARNING, never exceptions (NFR14)
- Missing expected fields → populate with `None`, create `Finding(code="ELIG_INCOMPLETE_RESPONSE", severity=WARNING)`

**Pipeline → User:**
- `EligibilityResult.passed` = `True` only if zero ERROR-severity findings from rule-based phase
- `EligibilityResult.eligible` = coverage status from 271 response (`True`/`False`/`None`)
- `EligibilityResult.response` = structured `EligibilityResponse` (None if clearinghouse not called)
- `EligibilityResult.ai_summary` = human-readable string (None if AI not called)
- `EligibilityResult.findings` = flat list from all phases, ordered by: phase (rule→clearinghouse→AI), then severity

### Eligibility Process Patterns

**Clearinghouse client contract:**

```python
class BaseClearinghouseClient(ABC):
    provider_name: str
    environment: str  # "sandbox" | "production"

    @abstractmethod
    def submit_eligibility(self, request: EligibilityRequest) -> dict:
        """
        MUST:
        - Return raw JSON dict from clearinghouse (271 response)
        - Raise ClearinghouseError for HTTP/network failures
        - NOT raise for business rejections (AAA segments)

        MUST NOT:
        - Parse the response into models (response_parser's job)
        - Strip or modify PHI (clearinghouse needs PHI)
        - Log PHI (no logging of request/response bodies)
        """

    def close(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(self, *args) -> None: ...
```

**Response parser contract:**

```python
def parse_271_response(raw: dict) -> EligibilityResponse:
    """
    MUST:
    - Handle missing fields gracefully (None, not exception)
    - Map Stedi JSON structure to EligibilityResponse model
    - Extract all BenefitInfo from EB segments
    - Extract AAAError from AAA segments
    - Preserve raw_response for advanced users

    MUST NOT:
    - Make network calls
    - Modify the raw response dict
    - Raise exceptions for malformed data (return partial model + warnings)
    """
```

**Eligibility validator example:**

```python
class PayerIDValidator(BaseValidator):
    name = "payer_id"

    def validate(self, claim: EligibilityRequest) -> ValidatorOutput:
        findings: list[Finding] = []
        payer_dir = get_payer_directory()
        if claim.payer_id not in payer_dir:
            findings.append(Finding(
                code="ELIG_INVALID_PAYER",
                message="Payer ID not found in known payer directory",
                severity=Severity.ERROR,
                field_name="payer_id",
                suggestion="Verify payer ID at https://www.stedi.com/app/payers",
                context={"payer_id_length": len(claim.payer_id)},
            ))
        return self._make_output(findings)
```

**BaseValidator input type:** Eligibility validators accept `EligibilityRequest` (not `ClaimData`). `BaseValidator.validate()` uses `validate(self, data: Any) -> ValidatorOutput` internally, with concrete validators type-hinting their specific input type.

### Eligibility Enforcement Guidelines

**All AI Agents MUST (eligibility-specific):**

1. Use `ELIG_` prefix for all eligibility finding codes to avoid collision with claim finding codes
2. Use `CLEARINGHOUSE_` prefix for clearinghouse infrastructure findings
3. Never log request or response bodies from clearinghouse calls (PHI)
4. Use `EligibilityDeidentifier` before passing any response data to LLM
5. Handle missing 271 fields with `None` and WARNING findings — never crash on unexpected data
6. Return `EligibilityResult` from pipeline — never return raw dicts or unstructured data
7. Follow the clearinghouse client contract — return raw dict, raise only for infrastructure errors
8. Follow the response parser contract — no exceptions for malformed data, return partial models

## Eligibility Module — Project Structure & Boundaries

### Eligibility Directory Structure

**New files added to existing package** (existing files unchanged):

```
src/claim_validator/
├── ... (all existing modules unchanged)
├── eligibility/                          # NEW subpackage
│   ├── __init__.py                       # Re-exports: check_eligibility, EligibilityRequest, etc.
│   ├── _api.py                           # check_eligibility() convenience function
│   ├── pipeline.py                       # EligibilityPipeline (three-phase)
│   ├── response_parser.py               # parse_271_response() — raw JSON → EligibilityResponse
│   ├── deidentifier.py                   # EligibilityDeidentifier
│   ├── models/
│   │   ├── __init__.py                   # Re-exports all eligibility models
│   │   ├── request.py                    # EligibilityRequest (frozen, flat)
│   │   ├── response.py                   # EligibilityResponse, CoverageInfo, BenefitInfo
│   │   ├── errors.py                     # AAAError, CoverageStatus enum
│   │   ├── result.py                     # EligibilityResult
│   │   └── deidentified.py              # DeidentifiedEligibilityResponse
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── rule_based/
│   │   │   ├── __init__.py
│   │   │   ├── payer_id.py              # PayerIDValidator (FR9)
│   │   │   ├── demographics.py          # EligibilityDemographicsValidator (FR10)
│   │   │   ├── service_type.py          # ServiceTypeValidator (FR11)
│   │   │   ├── date.py                  # EligibilityDateValidator (FR12)
│   │   │   └── member_id.py             # MemberIDValidator (FR13)
│   │   └── ai/
│   │       ├── __init__.py
│   │       └── interpreter.py           # EligibilityInterpreterAI (FR31-FR35)
│   ├── clearinghouse/
│   │   ├── __init__.py                  # Re-exports: BaseClearinghouseClient, get_clearinghouse_client
│   │   ├── base.py                      # BaseClearinghouseClient ABC
│   │   ├── factory.py                   # get_clearinghouse_client()
│   │   └── stedi.py                     # StediClient (FR16-FR22)
│   ├── code_tables/
│   │   ├── __init__.py                  # Re-exports: get_payer_directory, get_service_types
│   │   ├── payer_directory.py           # Payer ID lookup (lazy singleton)
│   │   └── service_types.py             # X12 service type code lookup (lazy singleton)
│   └── data/
│       ├── payer_directory.json         # ~3,400 payer IDs (~200KB)
│       └── service_types.json           # X12 service type codes
```

**Test structure:**

```
tests/
├── ... (all existing tests unchanged)
├── test_eligibility/
│   ├── conftest.py                      # Eligibility fixtures, request factories
│   ├── test_api.py                      # check_eligibility() top-level function
│   ├── test_pipeline.py                 # Three-phase execution, gate logic, aggregation
│   ├── test_response_parser.py          # parse_271_response() with real/mock 271 data
│   ├── test_deidentifier.py             # All 18 HIPAA identifiers stripped from response
│   ├── test_models/
│   │   ├── test_request.py              # EligibilityRequest validation, dict input, frozen
│   │   ├── test_response.py             # EligibilityResponse, BenefitInfo, CoverageInfo
│   │   ├── test_errors.py               # AAAError model
│   │   ├── test_result.py               # EligibilityResult
│   │   └── test_deidentified.py         # DeidentifiedEligibilityResponse type enforcement
│   ├── test_validators/
│   │   ├── test_rule_based/
│   │   │   ├── test_payer_id.py
│   │   │   ├── test_demographics.py
│   │   │   ├── test_service_type.py
│   │   │   ├── test_date.py
│   │   │   └── test_member_id.py
│   │   └── test_ai/
│   │       └── test_interpreter.py
│   ├── test_clearinghouse/
│   │   ├── test_base.py
│   │   ├── test_factory.py
│   │   └── test_stedi.py
│   ├── test_code_tables/
│   │   ├── test_payer_directory.py
│   │   └── test_service_types.py
│   └── test_hipaa/
│       ├── test_phi_leak.py
│       ├── test_no_network.py
│       └── test_deidentification.py
```

**Modified existing files:**

| File | Change |
|---|---|
| `pyproject.toml` | Add `stedi` extra, update `all` extra |
| `src/claim_validator/__init__.py` | Add eligibility re-exports |
| `src/claim_validator/conf.py` | Add Stedi config and eligibility validator list settings |
| `src/claim_validator/exceptions.py` | Add `ClearinghouseError` subclass |
| `src/claim_validator/constants.py` | Add `CoverageStatus` enum |

**New file count:** ~35 source files + ~25 test files = ~60 new files

### Eligibility Architectural Boundaries

**Public API Boundary (new symbols):**

| Symbol | Module | Stability |
|---|---|---|
| `check_eligibility()` | `eligibility/_api.py` | Stable from v1.0 |
| `EligibilityRequest` | `eligibility/models/request.py` | Stable from v1.0 |
| `EligibilityResponse` | `eligibility/models/response.py` | Stable from v1.0 |
| `EligibilityResult` | `eligibility/models/result.py` | Stable from v1.0 |
| `BenefitInfo`, `CoverageInfo` | `eligibility/models/response.py` | Stable from v1.0 |
| `BaseClearinghouseClient` | `eligibility/clearinghouse/base.py` | Stable from v1.0 (requires `[stedi]`) |
| `EligibilityPipeline` | `eligibility/pipeline.py` | Stable from v1.0 |

**Internal boundary:** `response_parser.py`, `stedi.py` (via factory), `code_tables/*.py`, `deidentifier.py` (via pipeline)

**Optional dependency boundary:** `clearinghouse/` requires `[stedi]` extra; `validators/ai/` requires LLM client; rule-based works with zero additional deps

### Requirements to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|---|---|---|
| **Request Data (FR1-FR7)** | `eligibility/models/request.py` | `eligibility/_api.py` |
| **Rule-Based Validation (FR8-FR15)** | `eligibility/validators/rule_based/*.py` | `eligibility/code_tables/*.py`, `eligibility/data/*` |
| **Clearinghouse (FR16-FR22)** | `eligibility/clearinghouse/stedi.py` | `eligibility/clearinghouse/base.py`, `factory.py` |
| **Response Parsing (FR23-FR29)** | `eligibility/response_parser.py`, `eligibility/models/response.py` | `eligibility/models/errors.py` |
| **AI Interpretation (FR30-FR35)** | `eligibility/validators/ai/interpreter.py`, `eligibility/deidentifier.py` | `llm/` (reuse) |
| **Pipeline (FR36-FR40)** | `eligibility/pipeline.py` | `eligibility/models/result.py` |
| **Configuration (FR41-FR44)** | `conf.py` (extend) | — |
| **Extensibility (FR45-FR47)** | `validators/base.py` (reuse), `eligibility/clearinghouse/base.py` | `validators/registry.py` (reuse) |

### Eligibility Data Flow

```
User Input (dict or EligibilityRequest)
    │
    ▼
check_eligibility() [eligibility/_api.py]
    │ Constructs EligibilityRequest if dict, builds pipeline from settings
    ▼
EligibilityPipeline.run(request) [eligibility/pipeline.py]
    │
    ├── Phase 1: Rule-Based (offline, synchronous)
    │   ├── NPIValidator(request) → reuse existing
    │   ├── PayerIDValidator(request) → payer_directory lookup
    │   ├── EligibilityDemographicsValidator(request)
    │   ├── ServiceTypeValidator(request) → service_types lookup
    │   ├── EligibilityDateValidator(request)
    │   ├── MemberIDValidator(request)
    │   └── Aggregate → partial EligibilityResult
    │
    ├── Gate: skip_clearinghouse_on_rule_failure check
    │
    ├── Phase 2: Clearinghouse (single call, network)
    │   ├── get_clearinghouse_client(settings) → StediClient
    │   ├── client.submit_eligibility(request) → raw 271 dict
    │   ├── parse_271_response(raw) → EligibilityResponse
    │   └── If ClearinghouseError → Finding, return partial result
    │
    ├── Gate: skip_ai check
    │
    └── Phase 3: AI Interpretation (optional, network)
        ├── EligibilityDeidentifier.deidentify(response) → DeidentifiedEligibilityResponse
        ├── get_llm_client(settings) → BaseLLMClient (reuse)
        ├── EligibilityInterpreterAI(deidentified) → findings + ai_summary
        └── Aggregate → complete EligibilityResult
    │
    ▼
EligibilityResult (eligible, response, findings, ai_summary, passed, raw_response)
```

## Eligibility Module — Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
All 10 new decisions (D14-D23) compatible with 13 existing decisions (D1-D13):
- D14 (clearinghouse ABC) mirrors D7 (LLM client ABC) — consistent pattern
- D15 (frozen models) matches D3 — same immutability/coercion
- D16 (separate pipeline) independent from ValidationPipeline — no conflict
- D17 (PHI dual-path) extends D5+D6 — same belt-and-suspenders
- D18 (sync httpx) uses same dep already in AI extras — no version conflict
- D19 (lazy JSON singleton) follows D1+D2 — identical pattern
- D23 (extend settings) follows D4 — consistent

**No contradictory decisions found.**

**Pattern Consistency:**
- Naming: All eligibility names follow existing conventions (ELIG_ prefix avoids collision)
- Test structure mirrors source 1:1
- One-file-per-class maintained
- Error handling follows existing pattern (validators return findings, infrastructure raises exceptions)

**Structure Alignment:**
- Eligibility subpackage cleanly nested in existing package
- Optional dependency boundary maintained (stedi extra)
- Public/internal boundary clear

### Requirements Coverage Validation

**Functional Requirements Coverage: 47/47 (100%)**

| FR Range | Category | Architectural Support | Status |
|---|---|---|---|
| FR1-FR7 | Request Data | `EligibilityRequest` model, dict + typed input | Full |
| FR8-FR15 | Rule-Based Validation | 6 validators (1 reuse + 5 new), payer directory, service types | Full |
| FR16-FR22 | Clearinghouse | `BaseClearinghouseClient` ABC + `StediClient` + factory | Full |
| FR23-FR29 | Response Parsing | `EligibilityResponse`, `BenefitInfo`, `CoverageInfo`, `AAAError`, raw response | Full |
| FR30-FR35 | AI Interpretation | `EligibilityDeidentifier` + `EligibilityInterpreterAI` + reuse LLM providers | Full |
| FR36-FR40 | Pipeline | `EligibilityPipeline` three-phase + `EligibilityResult` | Full |
| FR41-FR44 | Configuration | Extend `ClaimValidatorSettings` with Stedi config + eligibility validators | Full |
| FR45-FR47 | Extensibility | `BaseValidator` + `BaseClearinghouseClient` subclassing + dotted-path registry | Full |

**Non-Functional Requirements Coverage: 23/23 (100%)**

| NFR Range | Category | Architectural Support | Status |
|---|---|---|---|
| NFR1-NFR5 | Performance | Stateless validators, lazy loading, pure response parser, lightweight models | Full |
| NFR6-NFR10 | Security | EligibilityDeidentifier, no PHI logging, TLS via httpx, env-only keys | Full |
| NFR11-NFR14 | Reliability | ClearinghouseError, 30s timeout, LLM graceful degradation, partial model parsing | Full |
| NFR15-NFR20 | Code Quality | Same tooling (mypy/ruff/pytest), backward compat, optional deps | Full |
| NFR21-NFR23 | Documentation | Convention maintained, quickstart, API reference | Full |

### Implementation Readiness Validation

**Decision Completeness:** 23/23 decisions documented (13 base + 10 eligibility) with choices, rationale, and affected components. Implementation sequence defined with dependency chain.

**Structure Completeness:** Full eligibility directory tree with ~60 files (35 source + 25 test). Every file mapped to specific FRs. 5 modified existing files identified.

**Pattern Completeness:** 40 conflict points addressed (28 base + 12 eligibility). Code examples for clearinghouse contract, response parser contract, and eligibility validator. Anti-patterns documented via existing architecture patterns.

### Gap Analysis Results

**Critical Gaps: 0**

**Important Gaps: 2 (resolved)**

1. **BaseValidator.validate() type signature** — Use `validate(self, data: Any) -> ValidatorOutput` in the ABC. Concrete validators type-hint their specific input. Mypy strict catches type issues in concrete implementations.

2. **NPIValidator reuse** — Extract `_validate_npi(npi: str) -> list[Finding]` utility function in `validators/rule_based/_npi_utils.py`. Both claim NPIValidator and eligibility pipeline call the same utility.

**Nice-to-Have: 1 (noted)**

1. **Stedi 271 response fixtures** — Include example 271 JSON responses in `tests/test_eligibility/fixtures/` for testing.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Eligibility PRD analyzed (47 FRs + 23 NFRs)
- [x] Scale and complexity assessed (Medium-High, 60% reuse)
- [x] Technical constraints identified (7 new)
- [x] Cross-cutting concerns mapped (6 new/modified)

**Architectural Decisions**

- [x] 10 new decisions documented with rationale (D14-D23)
- [x] Technology choices compatible with existing stack
- [x] Clearinghouse integration pattern defined
- [x] PHI dual-path enforcement designed

**Implementation Patterns**

- [x] Eligibility naming conventions established (12 conflict points)
- [x] Finding code prefixes defined (ELIG_, CLEARINGHOUSE_, AAA_, AI_ELIG_)
- [x] Clearinghouse client contract specified with code example
- [x] Response parser contract specified with code example

**Project Structure**

- [x] Complete eligibility directory structure (~35 source files)
- [x] Test mirror defined (~25 test files)
- [x] All 47 FRs mapped to specific files
- [x] Modified existing files identified (5 files)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — 47/47 FRs and 23/23 NFRs covered, zero critical gaps, 23 coherent decisions, proven pattern reuse.

**Key Strengths:**
1. **60% pattern reuse** — validators, LLM providers, de-identification, settings, pipeline all follow proven patterns
2. **PHI dual-path by architecture** — type-driven + pipeline-level enforcement prevents bypass
3. **Clean extension** — zero changes to existing `validate()` API; eligibility is purely additive
4. **Clearinghouse abstraction** — `BaseClearinghouseClient` mirrors `BaseLLMClient`; ready for future providers
5. **Graceful 3-tier degradation** — rule-based always works; clearinghouse failure → partial result; LLM failure → structured response without AI

**Areas for Future Enhancement:**
1. Async eligibility pipeline — v1.1
2. Multi-clearinghouse implementations — v1.2
3. Batch eligibility checks — v1.1
4. FHIR mapping — v2.0

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all 23 architectural decisions (D1-D13 base + D14-D23 eligibility) exactly
- Use ELIG_ prefix for all eligibility finding codes
- Follow clearinghouse client and response parser contracts
- Every eligibility validator must pass PHI-leak test
- Extract NPI logic into shared utility (`_npi_utils.py`), don't duplicate

**Eligibility Implementation Sequence:**
1. Eligibility models (D15) — `EligibilityRequest`, `EligibilityResponse`, `BenefitInfo`, `CoverageInfo`, `AAAError`, `EligibilityResult`
2. Settings extension (D23) — Stedi config, eligibility validator lists
3. Payer directory + service types (D19) — bundled JSON, lazy loaders
4. NPI utility extraction — `_npi_utils.py` shared module
5. Rule-based eligibility validators — 5 new validators
6. Clearinghouse abstraction (D14) — `BaseClearinghouseClient` ABC, factory
7. Stedi client (D18) — `StediClient` implementation
8. Response parser — `parse_271_response()` function
9. Eligibility de-identifier (D21) — `EligibilityDeidentifier`, `DeidentifiedEligibilityResponse`
10. AI interpreter (D22) — `EligibilityInterpreterAI`
11. Pipeline (D16, D17) — `EligibilityPipeline` with three-phase execution and PHI enforcement
12. Top-level API — `check_eligibility()` convenience function
13. `__init__.py` re-exports — add eligibility symbols
14. Test suite — all ~25 test files

---

## Prior Authorization Module — Context Analysis

### Requirements Overview

**Functional Requirements:**
56 FRs across 9 categories extending the library with PA-specific models, validators, 278 response parsing, and eligibility-to-PA bridge function.

| Category | Count | Architectural Impact |
|---|---|---|
| PA Determination from Eligibility (FR1-FR5) | 5 | NEW: Cross-module bridge function `determine_pa_required()` — accepts `EligibilityResponse`, returns `PADeterminationResult` |
| PA Request Data Modeling (FR6-FR10) | 5 | `PriorAuthRequest`, `ServiceLine` models; `RequestCategoryCode`, `CertificationTypeCode`, `CertificationActionCode` enums |
| Pre-Submission Rule-Based Validation (FR11-FR19) | 9 | 7 validators reusing `BaseValidator`; cross-field consistency checks (dx-supports-procedure, gender/age-procedure) |
| Clearinghouse Integration (FR20-FR24) | 5 | Extend `BaseClearinghouseClient` with `submit_prior_auth()` method — same abstract pattern |
| 278 Response Parsing (FR25-FR31) | 7 | `PriorAuthResponse`, `ServiceLineDecision` models; HCR action code mapping (7 codes); `parse_278_response()` |
| AAA Error Handling (FR32-FR35) | 4 | `PriorAuthError` model; 20+ AAA reject reason code table; `AAA_PA_REJECTION` finding codes |
| PHI De-Identification (FR36-FR40) | 5 | `PriorAuthDeidentifier` — same pattern as `EligibilityDeidentifier`; mandatory pipeline gate |
| AI Interpretation (FR41-FR46) | 6 | `PriorAuthInterpreterAI` — denial appeal strategies, pended case guidance; reuses `BaseLLMClient` |
| Pipeline Orchestration (FR47-FR51) | 5 | `PriorAuthPipeline` three-phase; `PriorAuthResult`; rule-based-only mode when no clearinghouse configured |
| Finding Code System (FR52-FR56) | 5 | `PA_`, `AI_PA_`, `AAA_PA_REJECTION`, `CLEARINGHOUSE_` prefixes |

**Non-Functional Requirements:**
36 NFRs across 5 categories, largely consistent with existing constraints.

| Category | Count | Key Constraint |
|---|---|---|
| Performance (NFR1-NFR6) | 6 | <100ms rule-based, <500ms code table first-load, <50ms response parsing, <10ms PA determination, <20ms pipeline overhead, <50MB code table memory |
| Security & Privacy (NFR7-NFR15) | 9 | 18 HIPAA identifiers stripped; mandatory de-id gate; TLS 1.2+; no PHI in logs/exceptions/memory persistence |
| Reliability & Error Handling (NFR16-NFR21) | 6 | Missing fields → None/WARNING; unmapped HCR/AAA codes → WARNING; graceful LLM degradation |
| Integration Compatibility (NFR22-NFR28) | 7 | Zero breaking changes; reuse existing LLM/finding/code table infrastructure; consistent timeouts |
| Code Quality (NFR29-NFR36) | 8 | >90% coverage; mypy strict; ruff clean; frozen models; mirror eligibility layout; HIPAA test subdirectory |

**Scale & Complexity:**

- Primary domain: **Python library extension** (brownfield, same package)
- Complexity level: **Medium** — 70%+ pattern reuse from existing architecture; clearinghouse abstraction, pipeline, de-identification all follow proven patterns
- New architectural components: **~7 major** — PA models (request + response + result + determination), PA validators (7 rule-based + 1 AI), PA code tables (3 new), PA de-identifier, PA pipeline, `determine_pa_required()` bridge, `submit_prior_auth()` API

### New Technical Constraints & Dependencies

| Constraint | Source | Architectural Implication |
|---|---|---|
| **BaseClearinghouseClient extension** | FR20-FR24 | Must add `submit_prior_auth()` to existing ABC or create PA-specific subclass — key design decision |
| **PHI dual-path (same pattern)** | NFR7-NFR15 | `PriorAuthDeidentifier` mirrors `EligibilityDeidentifier`; pipeline enforces de-id gate before AI |
| **Cross-module dependency** | FR1-FR5 | `determine_pa_required()` imports `EligibilityResponse` from eligibility module — first cross-module dependency |
| **278 per-service-line decisions** | FR29 | 278 responses have per-service decisions (unlike 271 which is holistic) — response model more complex |
| **Abstract clearinghouse (no concrete MVP)** | FR20 | Rule-based + response parsing work fully offline; concrete provider deferred to v2.1 |
| **HCR action code mapping** | FR26 | 7 action codes (A1/A2/A3/A4/A6/CT/NA) need structured enum + description table |
| **AAA reject code table** | FR33 | 20+ reject codes bundled as new `prior_auth/data/aaa_reject_codes.json` |
| **Backward compatibility** | NFR22 | Existing `validate()` and `check_eligibility()` APIs must remain unchanged |

### New Cross-Cutting Concerns

| Concern | Scope | Strategy |
|---|---|---|
| **Clearinghouse method extension** | `BaseClearinghouseClient` needs both `submit_eligibility()` and `submit_prior_auth()` | Design decision: extend existing ABC vs PA-specific subclass |
| **Cross-module imports** | `determine_pa_required()` depends on eligibility models | Loose coupling via duck typing — accept `dict \| EligibilityResponse` |
| **PA-specific code tables** | AAA reject codes, HCR action codes, service type codes | Same lazy singleton pattern; new `prior_auth/data/` directory |
| **Finding code namespace** | PA codes must not conflict with existing CLM_, AI_, ELIG_ prefixes | `PA_` (rule-based), `AI_PA_` (AI), `AAA_PA_REJECTION` (AAA) |
| **Response model complexity** | 278 has per-service-line decisions vs 271 holistic response | Nested `ServiceLineDecision` within `PriorAuthResponse` |
| **Pipeline gate behavior** | Three different gate scenarios: no clearinghouse, no AI, or full pipeline | Same EligibilityPipeline gate pattern; additional "no clearinghouse configured" gate |

### Reuse Analysis

| Existing Component | Reuse Strategy | Modification Needed |
|---|---|---|
| `BaseValidator` ABC | Direct reuse | None — PA validators subclass same base |
| `ValidatorRegistry` | Direct reuse | None — same dotted-path loading |
| `BaseLLMClient` + providers | Direct reuse | None — PA AI uses same LLM providers |
| `BaseClearinghouseClient` | **Extend** | Add `submit_prior_auth()` method to ABC (or create `BasePAClearinghouseClient`) |
| `EligibilityDeidentifier` pattern | Pattern reuse | New `PriorAuthDeidentifier` class, same approach |
| `Finding`, `Severity`, `ValidatorOutput` | Direct reuse | None — PA validators produce same output types |
| `ClaimValidatorSettings` | Extend | Add PA validator lists, PA-specific settings |
| Code table loader pattern | Pattern reuse | New PA-specific tables using same lazy singleton |
| Exception hierarchy | Direct reuse | `ClearinghouseError` already exists — reuse directly |
| Test patterns | Direct reuse | Same class-based structure, PHI-leak assertions |
| `__init__.py` re-export pattern | Extend | Add PA symbols to top-level exports |
| `EligibilityPipeline` pattern | Pattern reuse | New `PriorAuthPipeline` class, same three-phase architecture |

### Starter Template Evaluation (Extension)

**Primary Technology Domain:** Python library extension — adding `prior_auth/` subpackage to existing `claim-validator` package.

**Starter: N/A — Existing Package Extension**

All foundational decisions from the original architecture (D1-D13) and eligibility extension (D14-D23) remain in effect. No new starter template needed.

**What the extension adds to `pyproject.toml`:** No new optional extras in MVP — PA module uses existing `[ai]` extra for AI interpretation and existing `[stedi]` extra when concrete provider ships in v2.1. Rule-based PA validation works with zero additional dependencies.

**Extension lives inside the existing package** as `src/claim_validator/prior_auth/` subpackage. All existing tooling (hatchling, uv, ruff, mypy, pytest) applies unchanged.

## Prior Authorization Module — Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- D24: Clearinghouse client extension → Separate `BasePAClearinghouseClient` subclass
- D25: PA data models → Flat request, nested response with per-service-line decisions
- D26: PA pipeline → Separate `PriorAuthPipeline`, three-phase
- D27: PHI dual-path → Same pattern, `PriorAuthDeidentifier`

**Important Decisions (Shape Architecture):**
- D28: PA determination bridge → Cross-module function with duck-typed input
- D29: HCR action code mapping → Enum + JSON description table
- D30: AAA error model → `PriorAuthError` + Finding objects (mirrors D20)
- D31: PA de-identification → Separate `PriorAuthDeidentifier` class
- D32: AI interpretation → Single `PriorAuthInterpreterAI` validator
- D33: Settings extension → Extend `ClaimValidatorSettings` with PA fields

**Deferred Decisions (Post-MVP):**
- Concrete clearinghouse provider (Stedi 278 / Optum) — v2.1
- FHIR PAS model mapping — v2.1
- Status polling for pended PAs — v2.1
- 278 update/revision/extension requests — v2.1
- 275 attachment submission — v2.2
- Batch 278 submissions — v2.2

### Clearinghouse Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D24: BasePAClearinghouseClient** | Subclass of `BaseClearinghouseClient` with `submit_prior_auth()` abstract method | Non-breaking — existing `StediClient` (eligibility-only) continues working. PA-capable clients subclass the new base. Consistent with NFR22. When Stedi adds 278 in v2.1, `StediClient` inherits from `BasePAClearinghouseClient` instead | `prior_auth/clearinghouse/base.py`, `prior_auth/pipeline.py` |

**Clearinghouse client hierarchy:**
```
BaseClearinghouseClient (ABC) [existing — eligibility/clearinghouse/base.py]
├── submit_eligibility(request: EligibilityRequest) -> dict
├── provider_name: str
├── environment: str
│
├── StediClient [existing — eligibility/clearinghouse/stedi.py]
│   └── submit_eligibility() implemented
│
└── BasePAClearinghouseClient (ABC) [NEW — prior_auth/clearinghouse/base.py]
    ├── submit_prior_auth(request: PriorAuthRequest) -> dict  # NEW abstract
    │
    └── (No concrete implementation in MVP)
    └── (v2.1: StediPAClient or StediClient extends this)
```

### Data Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D25: PA model design** | Flat request, nested response with `ServiceLineDecision` list | `PriorAuthRequest` is flat (like `EligibilityRequest`) — simple dict-compatible input. `PriorAuthResponse` is nested — 278 has per-service-line authorization decisions + overall HCR action. All frozen=True, strict=False (matches D3) | `prior_auth/models/` |
| **D29: HCR action codes** | `CertificationActionCode` StrEnum + `prior_auth/data/hcr_action_codes.json` description table | Enum for type safety in code; JSON table for human-readable descriptions, suggested actions. Lazy-loaded singleton | `prior_auth/constants.py`, `prior_auth/data/hcr_action_codes.json`, `prior_auth/code_tables/hcr_actions.py` |
| **D30: AAA errors** | Dual access — `PriorAuthError` model + `Finding` objects (mirrors D20) | `PriorAuthError` Pydantic model in `PriorAuthResponse.errors` for programmatic access. Pipeline also creates `Finding(code="AAA_PA_REJECTION")` for consistent pipeline output. Same pattern as eligibility | `prior_auth/models/errors.py`, `prior_auth/pipeline.py` |

**Model hierarchy:**
```
PriorAuthRequest (frozen, flat)
├── requester_npi, requester_taxonomy
├── payer_id
├── subscriber: SubscriberInfo (member_id, first_name, last_name, dob)
├── patient: PatientInfo | None (for dependents)
├── diagnosis_codes: list[str] (ICD-10-CM)
├── service_lines: list[ServiceLine]
│   ├── cpt_code, quantity, from_date, to_date
│   └── place_of_service_code
├── request_category_code: RequestCategoryCode (AR/HS/SC/IN)
├── certification_type_code: CertificationTypeCode (I/R/S/E)
└── clinical_info: str | None (free-text clinical justification)

PriorAuthResponse (frozen, nested)
├── action_code: CertificationActionCode (A1/A2/A3/A4/A6/CT/NA)
├── is_approved: bool  # A1
├── is_denied: bool    # A3
├── is_pended: bool    # A4
├── authorization_number: str | None
├── effective_date: date | None
├── expiration_date: date | None
├── decision_reason_code: str | None
├── decision_reason_description: str | None
├── service_line_decisions: list[ServiceLineDecision]
│   ├── cpt_code, action_code, authorization_number
│   └── approved_quantity, denied_reason
├── errors: list[PriorAuthError]
│   ├── rejection_code, follow_up_code
│   └── message, suggested_fix
└── raw_response: dict  # full 278 JSON

PADeterminationResult (frozen)
├── required: bool
├── confidence: str  # "high" / "medium" / "low"
├── reason: str  # human-readable explanation
├── auth_or_cert_indicator: str | None  # raw Y/N/U
└── free_text_indicators: list[str]  # parsed free-text PA signals

PriorAuthResult (pipeline output)
├── approved: bool | None
├── response: PriorAuthResponse | None
├── findings: list[Finding]
├── ai_summary: str | None
├── passed: bool (rule-based)
├── authorization_number: str | None
├── raw_response: dict | None
└── execution_time: float
```

### Security Architecture (HIPAA Extension)

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D27: PHI dual-path** | Same pattern as D17 — pipeline-level + type-driven | `PriorAuthDeidentifier` operates on `PriorAuthResponse` → `DeidentifiedPriorAuthResponse`. Pipeline enforces ordering. Clearinghouse receives raw `PriorAuthRequest` (PHI required) | `prior_auth/pipeline.py`, `prior_auth/deidentifier.py`, `prior_auth/models/deidentified.py` |
| **D31: PA de-identifier** | Separate `PriorAuthDeidentifier` class | PA data has different sensitive fields than eligibility (clinical justification text, diagnosis descriptions). Separate class, same patterns. Strips: patient name, DOB, member ID, SSN, address, phone, clinical free-text PII. Caps age 90+. Dates to year-only | `prior_auth/deidentifier.py` |

**PHI flow:**
```
PriorAuthRequest (has PHI) ──────────→ Clearinghouse (PHI allowed)
                                             │
                                             ▼
                                    PriorAuthResponse (has PHI)
                                             │
                             PriorAuthDeidentifier.deidentify()
                                             │
                                             ▼
                             DeidentifiedPriorAuthResponse (no PHI) → LLM
```

**Safe fields for LLM:** HCR action code, decision reason code, AAA reject codes, service type codes, CPT/HCPCS codes (without patient context), authorization status, effective date ranges (year only).
**Stripped fields:** patient name, DOB, member ID, SSN, address, phone, subscriber ID, NPI (when combined with patient), clinical justification free-text (PII scrubbed), diagnosis code descriptions (when combined with demographics).

### Pipeline Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D26: Pipeline design** | Separate `PriorAuthPipeline` — three-phase | Same rationale as D16 (eligibility pipeline). PA has same flow: rule-based → clearinghouse → AI. Separate class, same patterns. Additional gate: "no clearinghouse configured" → skip Phase 2 entirely (rule-based-only mode) | `prior_auth/pipeline.py` |
| **D32: AI interpretation** | Single `PriorAuthInterpreterAI` validator | One AI validator for PA (mirrors D22). Interprets HCR action code + decision reason + AAA errors holistically. Generates: decision summary, next-step recommendations for pended/denied, appeal strategy for denials | `prior_auth/validators/ai/interpreter.py` |

**Pipeline execution model:**
```
PriorAuthPipeline.run(request_data)
  ├── Phase 1: Rule-based validators (sequential, offline)
  │   ├── PANPIValidator (reuse NPI utility)
  │   ├── PAMemberIDValidator
  │   ├── PADateOfBirthValidator
  │   ├── PADiagnosisValidator (ICD-10 lookup)
  │   ├── PAProcedureValidator (CPT/HCPCS lookup)
  │   ├── PAServiceDateValidator
  │   ├── PACrossFieldValidator (dx-supports-procedure, gender/age)
  │   └── Aggregate → partial PriorAuthResult (passed, findings)
  │
  ├── Gate: if rule_phase_failed AND skip_clearinghouse_on_failure → return
  │
  ├── Gate: if no clearinghouse_client configured → return (rule-based-only mode)
  │
  ├── Phase 2: Clearinghouse (single call, network)
  │   ├── clearinghouse_client.submit_prior_auth(request) → raw 278 dict
  │   ├── parse_278_response(raw) → PriorAuthResponse
  │   └── If ClearinghouseError → Finding, return partial result
  │
  ├── Gate: if skip_ai → return with structured response
  │
  └── Phase 3: AI interpretation (optional, network)
      ├── PriorAuthDeidentifier.deidentify(response) → DeidentifiedPriorAuthResponse
      ├── get_llm_client(settings) → BaseLLMClient (reuse)
      ├── PriorAuthInterpreterAI(deidentified) → findings + ai_summary
      └── Aggregate → complete PriorAuthResult
```

### Cross-Module Bridge

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D28: PA determination** | Cross-module function with duck-typed input — `determine_pa_required(response: dict \| EligibilityResponse) -> PADeterminationResult` | Lives in `prior_auth/` module. Accepts both raw dict and typed `EligibilityResponse` via duck typing. Parses `authOrCertIndicator` (Y/N/U) and free-text `additionalInformation.description`. Free-text takes precedence when it indicates PA required (FR4). Loose coupling — no hard import of eligibility models at module level | `prior_auth/determination.py` |

**Determination logic:**
```
determine_pa_required(response)
  ├── Extract authOrCertIndicator from benefit info
  │   ├── "Y" → required=True, confidence="high"
  │   ├── "N" → required=False, confidence="high"
  │   └── "U" or missing → required=None, confidence="low"
  │
  ├── Scan free-text additionalInformation.description
  │   ├── Match PA indicators: "prior auth", "precertification", "preauthorization"
  │   └── If found → override indicator, confidence="medium"
  │
  ├── Conflict resolution (FR4):
  │   └── If free-text says required AND indicator says "N" → required=True (free-text wins)
  │
  └── Return PADeterminationResult(required, confidence, reason, raw_indicator, free_text_signals)
```

### Configuration

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D33: Settings** | Extend `ClaimValidatorSettings` with flat fields | Add `pa_rule_validators`, `pa_ai_validators`, `skip_clearinghouse_on_pa_failure`, `pa_skip_ai` as flat fields. All use `CLAIM_VALIDATOR_` env prefix. No new settings class — consistent with D23 | `conf.py` (modify existing) |

### Decision Impact Analysis

**Implementation Sequence (PA module):**
1. PA models (D25) — `PriorAuthRequest`, `PriorAuthResponse`, `ServiceLine`, `ServiceLineDecision`, `PriorAuthError`, `PriorAuthResult`, `PADeterminationResult`
2. PA enums/constants (D29) — `CertificationActionCode`, `RequestCategoryCode`, `CertificationTypeCode` StrEnums
3. Settings extension (D33) — PA validator lists, PA-specific config
4. PA code tables — `aaa_reject_codes.json`, `hcr_action_codes.json`, `service_type_codes.json` with lazy loaders
5. Rule-based PA validators — 7 validators (NPI utility reuse + 6 new)
6. PA determination bridge (D28) — `determine_pa_required()` function
7. 278 response parser — `parse_278_response()` function
8. PA clearinghouse abstraction (D24) — `BasePAClearinghouseClient` subclass
9. PA de-identifier (D31) — `PriorAuthDeidentifier`, `DeidentifiedPriorAuthResponse`
10. AI interpreter (D32) — `PriorAuthInterpreterAI`
11. Pipeline (D26, D27) — `PriorAuthPipeline` with three-phase execution and PHI enforcement
12. Top-level API — `submit_prior_auth()` convenience function
13. `__init__.py` re-exports — add PA symbols

**Cross-Component Dependencies:**
- D25 (models) enables D26 (pipeline) — pipeline operates on PA models
- D24 (clearinghouse subclass) — non-breaking extension of existing `BaseClearinghouseClient`
- D26 (pipeline) requires D27 (PHI dual-path) + D31 (de-identifier) — pipeline enforces de-id before AI
- D28 (PA determination) loosely depends on eligibility module — duck-typed input, no hard import
- D29 (HCR codes) required by response parser and `PriorAuthResponse` model
- D30 (AAA errors) required by response parser and pipeline Finding generation
- D33 (settings) required by D26 (pipeline) — pipeline reads settings for config

## Prior Authorization Module — Implementation Patterns & Consistency Rules

### PA-Specific Conflict Points

**10 new conflict areas** identified for the PA extension. These extend the existing 40 conflict points from the core + eligibility architecture.

### PA Naming Patterns

**Module & Class Naming:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| PA models | `PriorAuth{Name}` or `{Name}` for sub-models | `PriorAuthRequest`, `ServiceLine`, `ServiceLineDecision` | `PARequest`, `PriorAuthReq`, `AuthRequest` |
| PA validators | `PA{Name}Validator` | `PANPIValidator`, `PADiagnosisValidator` | `PriorAuthNPIValidator` (too long), `NPIValidator` (conflicts with claim) |
| PA clearinghouse base | `BasePAClearinghouseClient` | — | `PAClearinghouseClient`, `PriorAuthClearinghouse` |
| PA AI interpreter | `PriorAuthInterpreterAI` | — | `PAAI`, `InterpretPriorAuthAI` |
| PA pipeline | `PriorAuthPipeline` | — | `PAPipeline`, `PriorAuthValidationPipeline` |
| PA de-identifier | `PriorAuthDeidentifier` | — | `PADeidentifier`, `RequestDeidentifier` |
| PA determination | `determine_pa_required()` | — | `check_pa_required()`, `pa_determination()` |
| Top-level API | `submit_prior_auth()` | — | `prior_auth_submit()`, `send_prior_auth()` |
| Response parser | `parse_278_response()` | — | `parse_pa_response()`, `read_278()` |
| PA enums | `CertificationActionCode`, `RequestCategoryCode`, `CertificationTypeCode` | — | `HCRCode`, `ActionCode`, `PAActionCode` |

**Finding Code Conventions:**

| Category | Prefix | Example | Anti-Pattern |
|---|---|---|---|
| Rule-based PA | `PA_` prefix | `PA_INVALID_NPI`, `PA_MISSING_MEMBER_ID`, `PA_INVALID_DIAGNOSIS` | `INVALID_NPI` (conflicts with claim), `PRIOR_AUTH_NPI` (too long) |
| AI PA | `AI_PA_` prefix | `AI_PA_DECISION_SUMMARY`, `AI_PA_APPEAL_STRATEGY` | `AI_PRIOR_AUTH_` (too long), `PA_AI_` (inconsistent order) |
| AAA PA rejections | `AAA_PA_REJECTION` | `AAA_PA_REJECTION` with context dict containing rejection_code | `AAA_PA_04`, `PA_AAA_REJECTION` |
| Clearinghouse | `CLEARINGHOUSE_` prefix (reuse) | `CLEARINGHOUSE_TIMEOUT`, `CLEARINGHOUSE_ERROR` | `PA_CLEARINGHOUSE_` (unnecessary prefix) |
| Cross-field | `PA_CROSS_FIELD_` prefix | `PA_CROSS_FIELD_DX_PROCEDURE_MISMATCH` | `PA_MISMATCH` (unclear scope) |

### PA Communication Patterns

**Response Parser → Pipeline:**
- `parse_278_response(raw: dict) -> PriorAuthResponse` — pure function
- Unmapped HCR action codes → `Finding(code="PA_UNKNOWN_ACTION_CODE", severity=WARNING)` with raw code in context
- Unmapped AAA codes → `Finding(code="AAA_PA_REJECTION", severity=WARNING)` with raw code + generic message
- Missing fields → populate with `None`, create `Finding(code="PA_INCOMPLETE_RESPONSE", severity=WARNING)`
- Per-service-line decisions → `ServiceLineDecision` objects within `PriorAuthResponse`

**PA Determination → User:**
- `PADeterminationResult.required` = `True`/`False`/`None` (None when indeterminate)
- `PADeterminationResult.confidence` = `"high"`/`"medium"`/`"low"`
- Free-text indicators override `authOrCertIndicator` when they indicate PA required (FR4)

**Pipeline → User:**
- `PriorAuthResult.passed` = `True` only if zero ERROR-severity findings from rule-based phase
- `PriorAuthResult.approved` = authorization status from 278 response (`True`/`False`/`None`)
- `PriorAuthResult.response` = structured `PriorAuthResponse` (None if clearinghouse not called)
- `PriorAuthResult.ai_summary` = human-readable string (None if AI not called)
- `PriorAuthResult.authorization_number` = shortcut to `response.authorization_number`
- `PriorAuthResult.findings` = flat list from all phases, ordered by: phase (rule→clearinghouse→AI), then severity

### PA Process Patterns

**PA clearinghouse client contract:**

```python
class BasePAClearinghouseClient(BaseClearinghouseClient):
    @abstractmethod
    def submit_prior_auth(self, request: PriorAuthRequest) -> dict:
        """
        MUST:
        - Return raw JSON dict from clearinghouse (278 response)
        - Raise ClearinghouseError for HTTP/network failures
        - NOT raise for business rejections (AAA segments)

        MUST NOT:
        - Parse the response into models (response_parser's job)
        - Strip or modify PHI (clearinghouse needs PHI)
        - Log PHI (no logging of request/response bodies)
        """
```

**278 response parser contract:**

```python
def parse_278_response(raw: dict) -> PriorAuthResponse:
    """
    MUST:
    - Handle missing fields gracefully (None, not exception)
    - Map HCR action codes to CertificationActionCode enum
    - Extract per-service-line decisions into ServiceLineDecision objects
    - Extract PriorAuthError from AAA segments
    - Preserve raw_response for advanced users
    - Set convenience properties: is_approved, is_denied, is_pended

    MUST NOT:
    - Make network calls
    - Modify the raw response dict
    - Raise exceptions for malformed data (return partial model + warnings)
    """
```

**PA validator example:**

```python
class PADiagnosisValidator(BaseValidator):
    name = "pa_diagnosis"

    def validate(self, data: PriorAuthRequest) -> ValidatorOutput:
        findings: list[Finding] = []
        icd10_table = get_icd10_table()
        for dx_code in data.diagnosis_codes:
            if dx_code not in icd10_table:
                findings.append(Finding(
                    code="PA_INVALID_DIAGNOSIS",
                    message="ICD-10 diagnosis code not found in code tables",
                    severity=Severity.ERROR,
                    field_name="diagnosis_codes",
                    suggestion="Verify ICD-10-CM code at https://www.icd10data.com",
                    context={"code_length": len(dx_code)},
                ))
        return self._make_output(findings)
```

**BaseValidator input type:** PA validators accept `PriorAuthRequest` (not `ClaimData` or `EligibilityRequest`). Same approach as eligibility — `BaseValidator.validate(self, data: Any)` internally, concrete validators type-hint their specific input.

### PA Enforcement Guidelines

**All AI Agents MUST (PA-specific):**

1. Use `PA_` prefix for all PA rule-based finding codes to avoid collision with claim (`CLM_`) and eligibility (`ELIG_`) codes
2. Use `AI_PA_` prefix for AI interpretation findings
3. Use `AAA_PA_REJECTION` for AAA business rejection findings (with raw code in context dict)
4. Never log request or response bodies from clearinghouse calls (PHI)
5. Use `PriorAuthDeidentifier` before passing any response data to LLM
6. Handle missing 278 fields with `None` and WARNING findings — never crash on unexpected data
7. Return `PriorAuthResult` from pipeline — never return raw dicts or unstructured data
8. Follow the `BasePAClearinghouseClient` contract — return raw dict, raise only for infrastructure errors
9. Follow the `parse_278_response()` contract — no exceptions for malformed data, return partial models
10. Use `determine_pa_required()` for cross-module PA determination — never duplicate eligibility parsing logic

## Prior Authorization Module — Project Structure & Boundaries

### PA Directory Structure

**New files added to existing package** (existing files unchanged):

```
src/claim_validator/
├── ... (all existing modules unchanged)
├── prior_auth/                              # NEW subpackage
│   ├── __init__.py                          # Re-exports: submit_prior_auth, determine_pa_required, etc.
│   ├── _api.py                              # submit_prior_auth() convenience function
│   ├── determination.py                     # determine_pa_required() cross-module bridge
│   ├── pipeline.py                          # PriorAuthPipeline (three-phase)
│   ├── response_parser.py                   # parse_278_response() — raw JSON → PriorAuthResponse
│   ├── deidentifier.py                      # PriorAuthDeidentifier
│   ├── constants.py                         # CertificationActionCode, RequestCategoryCode, CertificationTypeCode
│   ├── models/
│   │   ├── __init__.py                      # Re-exports all PA models
│   │   ├── request.py                       # PriorAuthRequest, ServiceLine, SubscriberInfo, PatientInfo
│   │   ├── response.py                      # PriorAuthResponse, ServiceLineDecision
│   │   ├── errors.py                        # PriorAuthError
│   │   ├── result.py                        # PriorAuthResult
│   │   ├── determination.py                 # PADeterminationResult
│   │   └── deidentified.py                  # DeidentifiedPriorAuthResponse
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── rule_based/
│   │   │   ├── __init__.py
│   │   │   ├── npi.py                       # PANPIValidator (FR11, reuses NPI utility)
│   │   │   ├── member_id.py                 # PAMemberIDValidator (FR12)
│   │   │   ├── date_of_birth.py             # PADateOfBirthValidator (FR13)
│   │   │   ├── diagnosis.py                 # PADiagnosisValidator (FR14)
│   │   │   ├── procedure.py                 # PAProcedureValidator (FR15)
│   │   │   ├── service_date.py              # PAServiceDateValidator (FR16)
│   │   │   └── cross_field.py               # PACrossFieldValidator (FR17)
│   │   └── ai/
│   │       ├── __init__.py
│   │       └── interpreter.py               # PriorAuthInterpreterAI (FR41-FR46)
│   ├── clearinghouse/
│   │   ├── __init__.py                      # Re-exports: BasePAClearinghouseClient
│   │   └── base.py                          # BasePAClearinghouseClient ABC (extends BaseClearinghouseClient)
│   ├── code_tables/
│   │   ├── __init__.py                      # Re-exports: get_hcr_action_codes, get_aaa_reject_codes, get_pa_service_types
│   │   ├── hcr_actions.py                   # HCR action code lookup (lazy singleton)
│   │   ├── aaa_reject_codes.py              # AAA reject reason code lookup (lazy singleton)
│   │   └── service_types.py                 # PA service type codes (lazy singleton)
│   └── data/
│       ├── hcr_action_codes.json            # 7 HCR action codes with descriptions
│       ├── aaa_reject_codes.json            # 20+ AAA reject codes with messages + suggested fixes
│       └── service_type_codes.json          # PA-relevant service type codes
```

**Test structure:**

```
tests/
├── ... (all existing tests unchanged)
├── test_prior_auth/
│   ├── conftest.py                          # PA fixtures, request factories
│   ├── test_api.py                          # submit_prior_auth() top-level function
│   ├── test_determination.py                # determine_pa_required() cross-module bridge
│   ├── test_pipeline.py                     # Three-phase execution, gate logic, aggregation
│   ├── test_response_parser.py              # parse_278_response() with real/mock 278 data
│   ├── test_deidentifier.py                 # All 18 HIPAA identifiers stripped from PA data
│   ├── test_models/
│   │   ├── test_request.py                  # PriorAuthRequest validation, dict input, frozen
│   │   ├── test_response.py                 # PriorAuthResponse, ServiceLineDecision, convenience props
│   │   ├── test_errors.py                   # PriorAuthError model
│   │   ├── test_result.py                   # PriorAuthResult
│   │   ├── test_determination.py            # PADeterminationResult
│   │   └── test_deidentified.py             # DeidentifiedPriorAuthResponse type enforcement
│   ├── test_validators/
│   │   ├── test_rule_based/
│   │   │   ├── test_npi.py
│   │   │   ├── test_member_id.py
│   │   │   ├── test_date_of_birth.py
│   │   │   ├── test_diagnosis.py
│   │   │   ├── test_procedure.py
│   │   │   ├── test_service_date.py
│   │   │   └── test_cross_field.py
│   │   └── test_ai/
│   │       └── test_interpreter.py
│   ├── test_clearinghouse/
│   │   └── test_base.py                     # BasePAClearinghouseClient contract tests
│   ├── test_code_tables/
│   │   ├── test_hcr_actions.py
│   │   ├── test_aaa_reject_codes.py
│   │   └── test_service_types.py
│   └── test_hipaa/
│       ├── test_phi_leak.py                 # Scan all PA Finding outputs for PHI patterns
│       ├── test_no_network.py               # Rule-based PA makes zero network calls
│       └── test_deidentification.py         # All 18 identifiers stripped before LLM
```

**Modified existing files:**

| File | Change |
|---|---|
| `src/claim_validator/__init__.py` | Add PA re-exports: `submit_prior_auth`, `determine_pa_required`, `parse_278_response` |
| `src/claim_validator/conf.py` | Add `pa_rule_validators`, `pa_ai_validators`, `skip_clearinghouse_on_pa_failure`, `pa_skip_ai` |
| `src/claim_validator/constants.py` | Add `CertificationActionCode`, `RequestCategoryCode`, `CertificationTypeCode` enums (or import from `prior_auth/constants.py`) |

**New file count:** ~30 source files + ~25 test files = ~55 new files

### PA Architectural Boundaries

**Public API Boundary (new symbols):**

| Symbol | Module | Stability |
|---|---|---|
| `submit_prior_auth()` | `prior_auth/_api.py` | Stable from v2.0 |
| `determine_pa_required()` | `prior_auth/determination.py` | Stable from v2.0 |
| `parse_278_response()` | `prior_auth/response_parser.py` | Stable from v2.0 |
| `PriorAuthRequest` | `prior_auth/models/request.py` | Stable from v2.0 |
| `PriorAuthResponse` | `prior_auth/models/response.py` | Stable from v2.0 |
| `PriorAuthResult` | `prior_auth/models/result.py` | Stable from v2.0 |
| `PADeterminationResult` | `prior_auth/models/determination.py` | Stable from v2.0 |
| `ServiceLine`, `ServiceLineDecision` | `prior_auth/models/request.py`, `response.py` | Stable from v2.0 |
| `BasePAClearinghouseClient` | `prior_auth/clearinghouse/base.py` | Stable from v2.0 |
| `PriorAuthPipeline` | `prior_auth/pipeline.py` | Stable from v2.0 |
| `CertificationActionCode` | `prior_auth/constants.py` | Stable from v2.0 |

**Internal boundary:** `response_parser.py` internals, `code_tables/*.py`, `deidentifier.py` (via pipeline), `validators/` (via registry)

**Optional dependency boundary:** `validators/ai/` requires LLM client (`[ai]` extra); clearinghouse requires future `[stedi]` extra; rule-based + response parsing works with zero additional deps

### Requirements to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|---|---|---|
| **PA Determination (FR1-FR5)** | `prior_auth/determination.py` | `prior_auth/models/determination.py` |
| **Request Data (FR6-FR10)** | `prior_auth/models/request.py` | `prior_auth/constants.py` |
| **Rule-Based Validation (FR11-FR19)** | `prior_auth/validators/rule_based/*.py` | `code_tables/*.py` (reuse), `prior_auth/code_tables/*.py` |
| **Clearinghouse (FR20-FR24)** | `prior_auth/clearinghouse/base.py` | `prior_auth/pipeline.py` |
| **Response Parsing (FR25-FR31)** | `prior_auth/response_parser.py`, `prior_auth/models/response.py` | `prior_auth/code_tables/hcr_actions.py` |
| **AAA Errors (FR32-FR35)** | `prior_auth/models/errors.py`, `prior_auth/code_tables/aaa_reject_codes.py` | `prior_auth/data/aaa_reject_codes.json` |
| **PHI De-Id (FR36-FR40)** | `prior_auth/deidentifier.py` | `prior_auth/models/deidentified.py` |
| **AI Interpretation (FR41-FR46)** | `prior_auth/validators/ai/interpreter.py` | `llm/` (reuse) |
| **Pipeline (FR47-FR51)** | `prior_auth/pipeline.py` | `prior_auth/models/result.py` |
| **Finding Codes (FR52-FR56)** | All validators, pipeline | `constants.py` (reuse `Severity`) |

### PA Data Flow

```
User Input (dict or PriorAuthRequest)
    │
    ▼
submit_prior_auth() [prior_auth/_api.py]
    │ Constructs PriorAuthRequest if dict, builds pipeline from settings
    ▼
PriorAuthPipeline.run(request) [prior_auth/pipeline.py]
    │
    ├── Phase 1: Rule-Based (offline, synchronous)
    │   ├── PANPIValidator(request) → reuse NPI utility
    │   ├── PAMemberIDValidator(request)
    │   ├── PADateOfBirthValidator(request)
    │   ├── PADiagnosisValidator(request) → ICD-10 lookup (reuse)
    │   ├── PAProcedureValidator(request) → CPT/HCPCS lookup (reuse)
    │   ├── PAServiceDateValidator(request)
    │   ├── PACrossFieldValidator(request) → dx-procedure, gender/age
    │   └── Aggregate → partial PriorAuthResult
    │
    ├── Gate: skip_clearinghouse_on_pa_failure check
    ├── Gate: no clearinghouse_client configured → return (rule-based-only)
    │
    ├── Phase 2: Clearinghouse (single call, network)
    │   ├── clearinghouse_client.submit_prior_auth(request) → raw 278 dict
    │   ├── parse_278_response(raw) → PriorAuthResponse
    │   └── If ClearinghouseError → Finding, return partial result
    │
    ├── Gate: pa_skip_ai check
    │
    └── Phase 3: AI Interpretation (optional, network)
        ├── PriorAuthDeidentifier.deidentify(response) → DeidentifiedPriorAuthResponse
        ├── get_llm_client(settings) → BaseLLMClient (reuse)
        ├── PriorAuthInterpreterAI(deidentified) → findings + ai_summary
        └── Aggregate → complete PriorAuthResult
    │
    ▼
PriorAuthResult (approved, response, findings, ai_summary, passed, authorization_number, raw_response)
```

**Cross-module flow (eligibility → PA):**

```
check_eligibility(request) → EligibilityResult
    │
    ▼
determine_pa_required(eligibility_result.response) → PADeterminationResult
    │
    ├── If required=True:
    │   └── submit_prior_auth(pa_request) → PriorAuthResult
    │       └── pa_result.authorization_number → embed in 837 claim
    │
    └── If required=False:
        └── Proceed directly to claim submission
```

## Prior Authorization Module — Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
All 10 new decisions (D24-D33) compatible with 23 existing decisions (D1-D23):
- D24 (BasePAClearinghouseClient subclass) extends D14 (BaseClearinghouseClient) — non-breaking inheritance
- D25 (frozen models) matches D3 + D15 — same immutability/coercion pattern
- D26 (separate PriorAuthPipeline) independent from ValidationPipeline and EligibilityPipeline — no conflict
- D27 (PHI dual-path) extends D5+D6+D17 — same belt-and-suspenders pattern
- D28 (cross-module bridge) uses duck typing — loose coupling, no version conflicts
- D29 (HCR enum + JSON) follows D1+D2 — same lazy singleton pattern
- D30 (AAA errors) mirrors D20 — same dual-access pattern
- D31 (PA de-identifier) follows D21 — same separate class pattern
- D32 (single AI interpreter) mirrors D22 — same approach
- D33 (extend settings) follows D4+D23 — consistent

**No contradictory decisions found.**

**Pattern Consistency:**
- Naming: All PA names follow existing conventions (PA_ prefix avoids collision with CLM_ and ELIG_)
- Test structure mirrors source 1:1
- One-file-per-class maintained
- Error handling follows existing pattern (validators return findings, infrastructure raises exceptions)

**Structure Alignment:**
- PA subpackage cleanly nested in existing package (mirrors `eligibility/` layout)
- Optional dependency boundary maintained
- Public/internal boundary clear
- Cross-module bridge uses duck typing — no tight coupling

### Requirements Coverage Validation

**Functional Requirements Coverage: 56/56 (100%)**

| FR Range | Category | Architectural Support | Status |
|---|---|---|---|
| FR1-FR5 | PA Determination | `determination.py` with duck-typed input, `PADeterminationResult` model | Full |
| FR6-FR10 | Request Data | `PriorAuthRequest`, `ServiceLine` models, PA-specific enums | Full |
| FR11-FR19 | Rule-Based Validation | 7 validators (NPI reuse + 6 new), cross-field consistency | Full |
| FR20-FR24 | Clearinghouse | `BasePAClearinghouseClient` ABC + context manager + timeout | Full |
| FR25-FR31 | Response Parsing | `parse_278_response()`, `PriorAuthResponse`, `ServiceLineDecision`, convenience properties | Full |
| FR32-FR35 | AAA Errors | `PriorAuthError` model + AAA code table (20+ codes) + Finding generation | Full |
| FR36-FR40 | PHI De-Id | `PriorAuthDeidentifier` + mandatory pipeline gate + memory lifecycle | Full |
| FR41-FR46 | AI Interpretation | `PriorAuthInterpreterAI` + reuse LLM providers + AI_PA_ findings | Full |
| FR47-FR51 | Pipeline | `PriorAuthPipeline` three-phase + `PriorAuthResult` + gate logic | Full |
| FR52-FR56 | Finding Codes | PA_, AI_PA_, AAA_PA_REJECTION, CLEARINGHOUSE_ prefixes + Severity reuse | Full |

**Non-Functional Requirements Coverage: 36/36 (100%)**

| NFR Range | Category | Architectural Support | Status |
|---|---|---|---|
| NFR1-NFR6 | Performance | Stateless validators, lazy singletons, pure response parser, lightweight models | Full |
| NFR7-NFR15 | Security | PriorAuthDeidentifier, mandatory gate, TLS via httpx, no PHI logging, memory lifecycle | Full |
| NFR16-NFR21 | Reliability | Missing fields → None/WARNING, unmapped codes → WARNING, graceful LLM degradation, ClearinghouseError | Full |
| NFR22-NFR28 | Integration | Zero breaking changes, reuse LLM/finding/code table infra, consistent 30s timeout | Full |
| NFR29-NFR36 | Code Quality | Same tooling (mypy/ruff/pytest), frozen models, mirror eligibility layout, HIPAA test subdirectory | Full |

### Implementation Readiness Validation

**Decision Completeness:** 33/33 decisions documented (13 base + 10 eligibility + 10 PA) with choices, rationale, and affected components. Implementation sequence defined with dependency chain.

**Structure Completeness:** Full PA directory tree with ~55 files (30 source + 25 test). Every file mapped to specific FRs. 3 modified existing files identified.

**Pattern Completeness:** 50 conflict points addressed (28 base + 12 eligibility + 10 PA). Code examples for clearinghouse contract, response parser contract, and PA validator. Anti-patterns documented via existing architecture patterns.

### Gap Analysis Results

**Critical Gaps: 0**

**Important Gaps: 1 (resolved)**

1. **`BasePAClearinghouseClient` location** — Define in `prior_auth/clearinghouse/base.py`, not in the existing `eligibility/clearinghouse/base.py`. This keeps the PA module self-contained. The subclass imports `BaseClearinghouseClient` from the eligibility module.

**Nice-to-Have: 1 (noted)**

1. **278 response fixtures** — Include example 278 JSON responses in `tests/test_prior_auth/fixtures/` for testing all 7 HCR action codes and common AAA rejection scenarios.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] PA PRD analyzed (56 FRs + 36 NFRs)
- [x] Scale and complexity assessed (Medium, 70%+ reuse)
- [x] Technical constraints identified (8 new)
- [x] Cross-cutting concerns mapped (6 new)

**Architectural Decisions**

- [x] 10 new decisions documented with rationale (D24-D33)
- [x] Technology choices compatible with existing stack
- [x] Clearinghouse extension pattern defined (non-breaking subclass)
- [x] PHI dual-path enforcement designed
- [x] Cross-module bridge designed (duck-typed)

**Implementation Patterns**

- [x] PA naming conventions established (10 conflict points)
- [x] Finding code prefixes defined (PA_, AI_PA_, AAA_PA_REJECTION, CLEARINGHOUSE_)
- [x] PA clearinghouse client contract specified with code example
- [x] Response parser contract specified with code example
- [x] PA validator example provided

**Project Structure**

- [x] Complete PA directory structure (~30 source files)
- [x] Test mirror defined (~25 test files)
- [x] All 56 FRs mapped to specific files
- [x] Modified existing files identified (3 files)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — 56/56 FRs and 36/36 NFRs covered, zero critical gaps, 33 coherent decisions, proven pattern reuse from two previous modules.

**Key Strengths:**
1. **70%+ pattern reuse** — pipeline, validators, de-identification, settings, code tables all follow proven patterns from claim + eligibility
2. **Non-breaking clearinghouse extension** — `BasePAClearinghouseClient` subclass preserves existing `StediClient`
3. **Cross-module bridge via duck typing** — `determine_pa_required()` loosely couples eligibility → PA without hard imports
4. **PHI dual-path by architecture** — same type-driven + pipeline-level enforcement pattern proven in eligibility
5. **Clean separation** — PA module is self-contained in `prior_auth/` subpackage, zero changes to existing claim/eligibility code paths

**Areas for Future Enhancement:**
1. Concrete clearinghouse provider (Stedi 278 / Optum) — v2.1
2. FHIR PAS model mapping — v2.1
3. Status polling for pended PAs — v2.1
4. Async PA pipeline — v2.2

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all 33 architectural decisions (D1-D13 base + D14-D23 eligibility + D24-D33 PA) exactly
- Use PA_ prefix for all PA rule-based finding codes
- Use AI_PA_ prefix for AI interpretation findings
- Follow `BasePAClearinghouseClient` and `parse_278_response()` contracts
- Every PA validator must pass PHI-leak test
- Reuse NPI utility from `_npi_utils.py` — don't duplicate
- Use `determine_pa_required()` for eligibility→PA bridge — don't reparse 271 data

**PA Implementation Sequence:**
1. PA models (D25) — `PriorAuthRequest`, `PriorAuthResponse`, `ServiceLine`, `ServiceLineDecision`, `PriorAuthError`, `PriorAuthResult`, `PADeterminationResult`
2. PA enums/constants (D29) — `CertificationActionCode`, `RequestCategoryCode`, `CertificationTypeCode`
3. Settings extension (D33) — PA validator lists, PA-specific config
4. PA code tables — `aaa_reject_codes.json`, `hcr_action_codes.json`, `service_type_codes.json` with lazy loaders
5. Rule-based PA validators — 7 validators (NPI utility reuse + 6 new)
6. PA determination bridge (D28) — `determine_pa_required()` function
7. 278 response parser — `parse_278_response()` function
8. PA clearinghouse abstraction (D24) — `BasePAClearinghouseClient` subclass
9. PA de-identifier (D31) — `PriorAuthDeidentifier`, `DeidentifiedPriorAuthResponse`
10. AI interpreter (D32) — `PriorAuthInterpreterAI`
11. Pipeline (D26, D27) — `PriorAuthPipeline` with three-phase execution and PHI enforcement
12. Top-level API — `submit_prior_auth()` convenience function
13. `__init__.py` re-exports — add PA symbols
14. Test suite — all ~25 test files

---

## v3.0 Codebase Refactoring — Context Analysis

### Requirements Overview

**Functional Requirements:**
43 FRs across 10 categories driving a full internal refactoring to eliminate duplicate code, consolidate shared logic, and build a unified sequential pipeline.

| Category | Count | Architectural Impact |
|---|---|---|
| Shared Validators (FR1-FR9) | 9 | Extract 7 canonical validators into `shared/validators/`, register per-stage via config |
| Shared De-identification (FR10-FR13) | 4 | Single base de-identifier with domain config replaces 3 independent implementations |
| Shared Pipeline Engine (FR14-FR17) | 4 | Single configurable pipeline replaces `ValidationPipeline`, `EligibilityPipeline`, `PriorAuthPipeline` |
| Shared Code Tables (FR18-FR20) | 3 | Unified access layer consolidates `code_tables/`, `eligibility/code_tables/`, `prior_auth/code_tables/` |
| Unified Workflow Orchestrator (FR21-FR27) | 7 | NEW `process_claim()` API chains Eligibility → PA → Claim with validation passthrough |
| Validation Passthrough (FR28-FR30) | 3 | Track prior validation results; downstream stages skip redundant checks |
| Existing API Preservation (FR31-FR34) | 4 | `validate()`, `check_eligibility()`, `submit_prior_auth()` unchanged externally |
| Result Models (FR35-FR37) | 3 | `WorkflowResult` with per-stage results, execution times, aggregate `passed` |
| HIPAA Compliance (FR38-FR40) | 3 | Shared de-identifier verified across all 3 domains |
| Configuration (FR41-FR43) | 3 | Configurable validator-per-stage, configurable gating, existing env vars preserved |

**Non-Functional Requirements:**
27 NFRs across 5 categories establishing hard performance budgets, zero-duplicate enforcement, and backward compatibility.

| Category | Count | Key Constraint |
|---|---|---|
| Performance (NFR1-NFR6) | 6 | <50ms rule-based, <150ms full workflow, <5ms indirection overhead, no memory bloat |
| Security (NFR7-NFR11) | 5 | Zero PHI to LLM, zero PHI in logs, PHI cleared per-call, 18 identifiers verified |
| Scalability (NFR12-NFR15) | 4 | Stateless validators, thread-safe pipeline, locked singletons, O(n) scaling |
| Integration (NFR16-NFR20) | 5 | Clearinghouse/LLM ABCs unchanged, settings unchanged, Python 3.11-3.13, cross-platform |
| Code Quality (NFR21-NFR27) | 7 | Zero duplicate validators, coverage maintained, mypy strict, ruff clean, <15MB wheel |

**Scale & Complexity:**

- Primary domain: **Python library internal refactoring** (brownfield, same package)
- Complexity level: **High** — touching all 3 existing modules, creating 2 new top-level subpackages (`shared/`, `workflow/`), changing all internal import paths
- Estimated new architectural components: **~8 major** — shared validator module, shared de-identifier base, shared pipeline engine, shared code tables layer, workflow orchestrator, WorkflowResult models, validation passthrough mechanism, stage abstraction

### New Technical Constraints & Dependencies

| Constraint | Source | Architectural Implication |
|---|---|---|
| **Zero duplicate validation code** | NFR21 | Every validator function must exist in exactly one file — `shared/validators/` |
| **<5ms indirection overhead** | NFR5 | Shared module indirection (import + dispatch) adds negligible cost vs direct call |
| **<150ms full workflow (rule-based)** | NFR4 | 3 stages × 50ms budget; validation passthrough must skip, not add overhead |
| **Existing APIs unchanged** | FR31-FR34 | `validate()`, `check_eligibility()`, `submit_prior_auth()` produce identical behavior |
| **Clean break at v3.0** | PRD | New internal paths; no re-exports or deprecation shims for old paths |
| **Validation passthrough** | FR28-FR30 | Pipeline must track validation history and skip redundant checks downstream |
| **Cross-module orchestration** | FR21-FR27 | `process_claim()` depends on eligibility, PA, and claim modules sequentially |
| **PHI isolation between stages** | FR39 | Unified pipeline must not leak PHI between stages; fresh de-id per AI phase |

### New Cross-Cutting Concerns

| Concern | Scope | Strategy |
|---|---|---|
| **Shared validator registration** | All 3 pipelines reference shared validators by config | Registry maps validator IDs to shared implementations; domain pipelines configure which validators to run |
| **Base de-identifier with domain config** | 3 domains have different PHI field sets | Single base class with domain-specific field mapping; each domain provides its config |
| **Configurable pipeline engine** | 3 pipelines have identical phase logic | Single base pipeline class parameterized by: validator set, clearinghouse client, AI interpreter, gating rules |
| **Validation passthrough data structure** | Workflow orchestrator → downstream pipelines | Lightweight `ValidationContext` carrying validator name → result pairs; optional parameter on pipeline.run() |
| **Unified code table access** | Code tables split across 3 module directories | Single `shared/code_tables/` with all tables; domain modules import from shared |
| **Workflow stage abstraction** | Orchestrator chains 3 domain pipelines | `Stage` protocol/ABC with `run(request, context) -> StageResult`; orchestrator iterates stages |

### Reuse Analysis

| Existing Component | Refactoring Strategy | Change |
|---|---|---|
| `validators/rule_based/npi.py` + eligibility NPI + `prior_auth/validators/rule_based/npi.py` | **Consolidate** → `shared/validators/npi.py` | 3 files → 1 |
| `validators/rule_based/demographics.py` + eligibility + PA variants | **Consolidate** → `shared/validators/demographics.py` | 3 files → 1 |
| `ClaimDeidentifier` + `EligibilityDeidentifier` + `PriorAuthDeidentifier` | **Consolidate** → `shared/deidentifier/base.py` + domain config | 3 classes → 1 base + 3 configs |
| `ValidationPipeline` + `EligibilityPipeline` + `PriorAuthPipeline` | **Consolidate** → `shared/pipeline/engine.py` + domain config | 3 classes → 1 base + 3 configs |
| `code_tables/` + `eligibility/code_tables/` + `prior_auth/code_tables/` | **Consolidate** → `shared/code_tables/` | 3 directories → 1 |
| `BaseClearinghouseClient` ABC | **Direct reuse** | Unchanged |
| `BaseLLMClient` ABC + providers | **Direct reuse** | Unchanged |
| `Finding`, `Severity`, `ValidatorOutput` | **Direct reuse** | Unchanged |
| `ClaimValidatorSettings` | **Extend** | Add workflow-specific settings |
| Exception hierarchy | **Extend** | May add workflow-specific exceptions |
| All existing models (`ClaimData`, `EligibilityRequest`, `PriorAuthRequest`, results) | **Direct reuse** | Unchanged |
| `BaseValidator` ABC | **Direct reuse** (validators continue subclassing it) | Unchanged |

### Relationship to Existing Architectural Decisions

All 33 existing decisions (D1-D33) remain valid. The refactoring does NOT change:
- D1-D4: Data architecture (compressed JSON, lazy singletons, frozen models, Pydantic settings)
- D5-D6: HIPAA security architecture (pipeline-integrated de-id, type-driven PHI boundary)
- D7-D9: LLM provider architecture (chat-based, per-validator prompts, hybrid parsing)
- D10-D13: Pipeline/registry/versioning/import architecture (dotted paths, settings-driven)
- D14-D23: Eligibility-specific decisions
- D24-D33: PA-specific decisions

What changes is the **internal organization** — shared logic moves to `shared/`, domain modules delegate to shared, and a new `workflow/` module orchestrates the full flow. Public API signatures are preserved.

### Starter Template Evaluation (v3.0 Refactoring)

**Primary Technology Domain:** Python library internal refactoring — restructuring `claim-validator` package internals.

**Starter: N/A — Existing Package Refactoring**

All foundational decisions from the original architecture (D1-D13) and both extensions (D14-D33) remain in effect. The project already exists with its full tooling chain:

- **Build:** hatchling + hatch-vcs (D12)
- **Runtime:** Python 3.11+ (NFR19)
- **Core dep:** Pydantic 2.x (D3)
- **Linting:** ruff (line-length=100, E/F/I/N/W/UP)
- **Type checking:** mypy strict + Pydantic plugin
- **Testing:** pytest
- **Layout:** src layout (`src/claim_validator/`)

No new starter template, CLI scaffolding, or tooling changes are needed. The refactoring adds `shared/` and `workflow/` subpackages inside the existing package and restructures internal imports.

**What the refactoring adds to `pyproject.toml`:** No new optional extras in MVP. The `process_claim()` API uses existing extras (`[ai]`, `[stedi]`) when AI/clearinghouse features are enabled. Rule-based unified workflow works with zero additional dependencies.

## v3.0 Refactoring — Core Architectural Decisions

### Decision Priority Analysis

**Already Decided (from D1-D33):**
Data formats, model patterns, settings, LLM/clearinghouse ABCs, exception hierarchy, naming conventions, test patterns — all unchanged.

**Critical Decisions (Block Implementation):**
- D34: Shared validator consolidation — how shared validators serve all 3 domains
- D35: Shared de-identifier base — base class with domain config
- D36: Shared pipeline engine — parameterized base pipeline
- D37: Validation passthrough mechanism — tracking and skipping
- D38: Workflow orchestrator — `process_claim()` and stage abstraction

**Important Decisions (Shape Architecture):**
- D39: Shared code tables consolidation — unified access layer
- D40: WorkflowResult model design — per-stage results
- D41: Domain module refactoring pattern — how existing modules delegate to shared
- D42: Configuration extension — workflow-specific settings
- D43: Import path migration — clean break v3.0 strategy

**Deferred Decisions (Post-MVP):**
- Smart validation skipping configuration — Phase 2
- Workflow state object (rich context between stages) — Phase 2
- Configurable stage ordering — Phase 2
- Async pipeline support — Phase 3

### Shared Module Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D34: Shared validator consolidation** | Canonical implementations in `shared/validators/`, domain validators import and delegate | Each shared validator (NPI, date, member ID, demographics, diagnosis, procedure, payer ID) lives in one file in `shared/validators/`. Domain-specific validators (e.g., `PANPIValidator`) become thin wrappers that call the shared function and wrap results with domain-specific finding codes. This achieves FR1-FR7 (single canonical implementation) while preserving domain-specific finding code prefixes (FR8) | `shared/validators/*.py`, `validators/rule_based/`, `eligibility/validators/`, `prior_auth/validators/` |
| **D35: Shared de-identifier** | Base class `BaseDeidentifier` with domain config dict | `BaseDeidentifier` implements the core 18-identifier stripping logic. Each domain provides a `DeidentificationConfig` specifying: field mappings (which model fields contain which PHI types), age cap behavior, date reduction strategy. Domain classes (`ClaimDeidentifier`, `EligibilityDeidentifier`, `PriorAuthDeidentifier`) become thin subclasses that set their config. Achieves FR10-FR13 | `shared/deidentifier/base.py`, `shared/deidentifier/config.py` |
| **D36: Shared pipeline engine** | `BasePipeline` class parameterized by `PipelineConfig` dataclass | Single `BasePipeline.run(input, context?) -> PipelineResult` handles: phase sequencing, gating logic, timing, error aggregation. Each domain provides `PipelineConfig`: validator list, clearinghouse client (optional), AI interpreter (optional), gating rules, finding code prefix. Achieves FR14-FR17 | `shared/pipeline/engine.py`, `shared/pipeline/config.py` |

**Shared validator pattern:**
```python
# shared/validators/npi.py — THE canonical NPI validation
class NPIValidatorBase(BaseValidator):
    """Canonical NPI Luhn check. All domains delegate to this."""
    name = "shared_npi"

    def validate(self, data: Any) -> ValidatorOutput:
        npi = self._extract_npi(data)  # duck-typed extraction
        findings = validate_npi(npi)   # pure function
        return self._make_output(findings)

def validate_npi(npi: str | None, field_name: str = "npi",
                 code_prefix: str = "") -> list[Finding]:
    """Pure function: validates NPI, returns findings with configurable code prefix."""
    # Single implementation of Luhn check + format validation
```

```python
# validators/rule_based/npi.py — claim domain wrapper (thin)
from claim_validator.shared.validators.npi import validate_npi

class NPIValidator(BaseValidator):
    name = "npi"
    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings = validate_npi(claim.billing_provider_npi, "billing_provider_npi")
        return self._make_output(findings)

# prior_auth/validators/rule_based/npi.py — PA domain wrapper (thin)
class PANPIValidator(BaseValidator):
    name = "pa_npi"
    def validate(self, data: PriorAuthRequest) -> ValidatorOutput:
        findings = validate_npi(data.requester_npi, "requester_npi", code_prefix="PA_")
        return self._make_output(findings)
```

**Shared de-identifier pattern:**
```python
# shared/deidentifier/base.py
class BaseDeidentifier:
    """Base de-identifier — strips 18 HIPAA identifiers per domain config."""

    def __init__(self, config: DeidentificationConfig):
        self._config = config

    def deidentify(self, data: Any) -> Any:
        """Strip PHI fields per config. Cap ages 90+. Dates to year-only."""
        # Single implementation of 18-identifier stripping
        # Config tells us which fields to strip and what type they are

# shared/deidentifier/config.py
@dataclass(frozen=True)
class DeidentificationConfig:
    name_fields: tuple[str, ...]      # ("subscriber_first_name", "subscriber_last_name")
    date_fields: tuple[str, ...]      # ("date_of_birth", "service_date")
    id_fields: tuple[str, ...]        # ("subscriber_id", "member_id", "ssn")
    address_fields: tuple[str, ...]   # ("address", "city", "state", "zip")
    age_field: str | None             # "patient_age" — for 90+ cap
    output_model: type                # DeidentifiedClaim / DeidentifiedEligibilityResponse / etc.
```

**Shared pipeline pattern:**
```python
# shared/pipeline/engine.py
class BasePipeline:
    """Configurable multi-phase pipeline engine."""

    def __init__(self, config: PipelineConfig):
        self._config = config

    def run(self, input_data: Any, validation_context: ValidationContext | None = None) -> Any:
        # Phase 1: Rule-based validators (respects validation_context for passthrough)
        # Gate: configurable skip behavior
        # Phase 2: Clearinghouse (if client provided)
        # Gate: configurable skip behavior
        # Phase 3: AI interpretation (if interpreter provided)
        # Returns domain-specific result model

# shared/pipeline/config.py
@dataclass(frozen=True)
class PipelineConfig:
    domain: str                              # "claim", "eligibility", "prior_auth"
    rule_validators: tuple[str, ...]         # dotted paths
    clearinghouse_client: Any | None         # BaseClearinghouseClient instance
    ai_interpreter: Any | None               # AI validator instance
    deidentifier: BaseDeidentifier | None    # domain-configured de-identifier
    skip_next_on_rule_failure: bool          # gate behavior
    skip_ai: bool                            # skip AI phase
    result_factory: Callable                 # builds domain-specific result model
```

### Workflow Architecture

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D37: Validation passthrough** | `ValidationContext` frozen dataclass carrying `dict[str, ValidatorResult]` | Lightweight object passed from orchestrator to downstream pipelines. Maps validator name → pass/fail + findings. `BasePipeline.run()` accepts optional `validation_context` parameter. When present, pipeline skips validators whose name appears in context with a passing result. In standalone mode (no context), runs all validators. Achieves FR28-FR30 | `shared/pipeline/context.py`, `shared/pipeline/engine.py`, `workflow/orchestrator.py` |
| **D38: Workflow orchestrator** | `WorkflowOrchestrator` class with `Stage` protocol | Orchestrator iterates `Stage` objects sequentially. Each stage wraps a domain pipeline. Stages: `EligibilityStage`, `PADeterminationStage`, `PAStage` (conditional), `ClaimValidationStage`. Orchestrator passes `ValidationContext` between stages. Stops on first stage failure (configurable). Returns `WorkflowResult`. Achieves FR21-FR27 | `workflow/orchestrator.py`, `workflow/stages.py`, `workflow/models.py` |

**Validation passthrough pattern:**
```python
# shared/pipeline/context.py
@dataclass(frozen=True)
class ValidatorResult:
    passed: bool
    findings: tuple[Finding, ...]

@dataclass
class ValidationContext:
    """Carries validation results between pipeline stages."""
    results: dict[str, ValidatorResult] = field(default_factory=dict)

    def has_passed(self, validator_name: str) -> bool:
        """Check if a validator already ran and passed."""
        return validator_name in self.results and self.results[validator_name].passed

    def record(self, validator_name: str, result: ValidatorResult) -> None:
        """Record a validator's result for downstream stages."""
        self.results[validator_name] = result
```

**Workflow orchestrator pattern:**
```python
# workflow/orchestrator.py
class WorkflowOrchestrator:
    def __init__(self, stages: list[Stage], settings: ClaimValidatorSettings):
        self._stages = stages
        self._settings = settings

    def run(self, request: dict | WorkflowRequest) -> WorkflowResult:
        context = ValidationContext()
        stage_results: list[StageResult] = []

        for stage in self._stages:
            if stage.should_skip(context, stage_results):
                continue
            result = stage.run(request, context)
            stage_results.append(result)
            if not result.passed and stage.is_gate:
                return WorkflowResult(
                    stage_results=stage_results,
                    stopped_at=stage.name,
                    ...
                )
        return WorkflowResult(stage_results=stage_results, stopped_at=None, ...)

# workflow/stages.py
class Stage(Protocol):
    name: str
    is_gate: bool
    def should_skip(self, ctx: ValidationContext, prior: list[StageResult]) -> bool: ...
    def run(self, request: Any, ctx: ValidationContext) -> StageResult: ...
```

### Supporting Decisions

| Decision | Choice | Rationale | Affects |
|---|---|---|---|
| **D39: Shared code tables** | Move all code table loaders + data to `shared/code_tables/` | Single directory with: `icd10.py`, `hcpcs.py`, `taxonomy.py`, `pos.py`, `payer_directory.py`, `service_types.py`, `hcr_actions.py`, `aaa_reject_codes.py`, `timely_filing.py`. All `data/*.json(.gz)` files move to `shared/data/`. Domain modules import from `shared.code_tables`. Achieves FR18-FR20 | `shared/code_tables/`, `shared/data/` |
| **D40: WorkflowResult model** | Frozen Pydantic model with per-stage typed results | `WorkflowResult.eligibility: EligibilityResult`, `.prior_auth: PriorAuthResult | None`, `.claim_validation: PipelineResult`, `.stopped_at: str | None`, `.passed: bool` (aggregate), `.execution_time: float`, `.stage_results: list[StageResult]`. Achieves FR35-FR37 | `workflow/models.py` |
| **D41: Domain module refactoring** | Domain modules become thin orchestration layers delegating to shared | `validators/pipeline.py` → creates `BasePipeline` with claim-specific `PipelineConfig`. `eligibility/pipeline.py` → creates `BasePipeline` with eligibility-specific config. Domain validators become thin wrappers calling shared functions. Domain de-identifiers subclass `BaseDeidentifier` with domain config | All domain modules |
| **D42: Configuration extension** | Add workflow settings to `ClaimValidatorSettings` | New flat fields: `workflow_stages` (list of stage dotted paths), `workflow_stop_on_failure` (bool), `workflow_skip_pa_when_not_required` (bool). All use `CLAIM_VALIDATOR_` prefix. Achieves FR41-FR43 | `conf.py` |
| **D43: Import path migration** | Clean break — new internal paths, no compatibility shims | `shared/validators/npi.py` is the canonical path. Old paths (`validators/rule_based/npi.py`) still exist but contain thin wrappers. No `__getattr__` re-export hacks for old internal paths. Public API paths (`from claim_validator import validate`) unchanged. Achieves PRD clean break requirement | All `__init__.py` files |

### Decision Impact Analysis

**Implementation Sequence:**
1. `shared/` scaffolding — `__init__.py`, `validators/`, `deidentifier/`, `pipeline/`, `code_tables/`
2. Shared code tables (D39) — move all loaders + data
3. Shared validators (D34) — extract pure functions, create canonical validators
4. Shared de-identifier (D35) — `BaseDeidentifier` + `DeidentificationConfig`
5. Shared pipeline engine (D36) — `BasePipeline` + `PipelineConfig`
6. Validation passthrough (D37) — `ValidationContext`
7. Refactor claim module (D41) — delegate to shared
8. Refactor eligibility module (D41) — delegate to shared
9. Refactor PA module (D41) — delegate to shared
10. WorkflowResult model (D40)
11. Workflow orchestrator + stages (D38)
12. Configuration extension (D42)
13. `process_claim()` top-level API
14. Import path cleanup (D43)

**Cross-Component Dependencies:**
- D34 (shared validators) enables D41 (domain refactoring) — domains delegate to shared
- D35 (shared de-identifier) enables D36 (shared pipeline) — pipeline uses de-identifier
- D36 (shared pipeline) requires D37 (passthrough) — pipeline accepts `ValidationContext`
- D37 (passthrough) enables D38 (orchestrator) — orchestrator passes context between stages
- D39 (shared code tables) enables D34 (shared validators) — validators look up shared tables
- D38 (orchestrator) requires D40 (WorkflowResult) — orchestrator builds result
- D42 (settings) required by D38 (orchestrator) — orchestrator reads workflow config

## v3.0 Refactoring — Implementation Patterns & Consistency Rules

### Refactoring-Specific Conflict Points

**10 new conflict areas** identified for the v3.0 refactoring extension. These extend the existing 50 conflict points from core + eligibility + PA.

### Shared Validator Patterns

**Pure function signature pattern:**

```python
# CORRECT — shared pure function with configurable code prefix and field name
def validate_npi(
    npi: str | None,
    field_name: str = "npi",
    code_prefix: str = "",
) -> list[Finding]:
    """Canonical NPI validation. Returns findings with configurable prefix."""
    findings: list[Finding] = []
    if npi is None:
        findings.append(Finding(
            code=f"{code_prefix}MISSING_NPI",
            message="NPI is required",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Provide a valid 10-digit NPI",
        ))
        return findings
    if not _luhn_check(npi):
        findings.append(Finding(
            code=f"{code_prefix}INVALID_NPI",
            message="NPI fails Luhn check-digit validation",
            severity=Severity.ERROR,
            field_name=field_name,
            suggestion="Verify NPI at https://npiregistry.cms.hhs.gov",
            context={"npi_length": len(npi)},
        ))
    return findings

# WRONG — hardcoded domain specifics in shared function
def validate_npi(claim: ClaimData) -> list[Finding]:  # Tied to ClaimData
    ...  # Can't reuse for EligibilityRequest or PriorAuthRequest
```

**Domain wrapper pattern:**

```python
# CORRECT — thin wrapper: extract field, delegate, wrap
class NPIValidator(BaseValidator):
    name = "npi"
    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings = validate_npi(
            claim.billing_provider_npi,
            field_name="billing_provider_npi",
        )
        return self._make_output(findings)

# CORRECT — PA wrapper with prefix
class PANPIValidator(BaseValidator):
    name = "pa_npi"
    def validate(self, data: PriorAuthRequest) -> ValidatorOutput:
        findings = validate_npi(
            data.requester_npi,
            field_name="requester_npi",
            code_prefix="PA_",
        )
        return self._make_output(findings)

# WRONG — duplicating logic in wrapper
class PANPIValidator(BaseValidator):
    name = "pa_npi"
    def validate(self, data: PriorAuthRequest) -> ValidatorOutput:
        # BAD: reimplements Luhn check instead of calling validate_npi()
        if not _check_luhn(data.requester_npi):
            ...

# WRONG — wrapper adds behavior beyond field extraction + delegation
class PANPIValidator(BaseValidator):
    name = "pa_npi"
    def validate(self, data: PriorAuthRequest) -> ValidatorOutput:
        findings = validate_npi(data.requester_npi, ...)
        # BAD: wrapper adds extra validation not in shared function
        if data.requester_npi and len(data.requester_npi) > 10:
            findings.append(...)  # Should be in shared function
        return self._make_output(findings)
```

**Shared validator naming convention:**

| Element | Convention | Example | Anti-Pattern |
|---|---|---|---|
| Shared pure function | `validate_{concept}()` | `validate_npi()`, `validate_date()` | `check_npi()`, `npi_validation()` |
| Shared module file | `shared/validators/{concept}.py` | `shared/validators/npi.py` | `shared/validators/npi_validator.py` |
| Domain wrapper class | Domain convention unchanged | `NPIValidator`, `PANPIValidator` | `SharedNPIValidator` |
| Private helpers | `_{verb}_{noun}()` | `_luhn_check()`, `_format_npi()` | `luhn()`, `checkLuhn()` |

### Shared De-identifier Patterns

**Domain config pattern:**

```python
# CORRECT — domain provides config, base does the work
CLAIM_DEID_CONFIG = DeidentificationConfig(
    name_fields=("patient_first_name", "patient_last_name"),
    date_fields=("date_of_birth", "service_date"),
    id_fields=("subscriber_id", "member_id"),
    address_fields=("patient_address", "patient_city", "patient_state", "patient_zip"),
    age_field="patient_age",
    output_model=DeidentifiedClaim,
)

class ClaimDeidentifier(BaseDeidentifier):
    """Claim-specific de-identifier. Thin subclass with config."""
    def __init__(self) -> None:
        super().__init__(CLAIM_DEID_CONFIG)

# WRONG — overriding deidentify() in subclass
class ClaimDeidentifier(BaseDeidentifier):
    def deidentify(self, data: ClaimData) -> DeidentifiedClaim:
        # BAD: reimplements stripping logic
        ...
```

### Shared Pipeline Patterns

**Pipeline config pattern:**

```python
# CORRECT — domain creates BasePipeline with domain-specific config
def build_claim_pipeline(settings: ClaimValidatorSettings) -> BasePipeline:
    config = PipelineConfig(
        domain="claim",
        rule_validators=settings.rule_validators,
        clearinghouse_client=None,  # claims don't use clearinghouse
        ai_interpreter=None,  # loaded lazily if AI enabled
        deidentifier=ClaimDeidentifier(),
        skip_next_on_rule_failure=settings.skip_ai_on_rule_failure,
        skip_ai=not settings.ai_config,
        result_factory=build_pipeline_result,
    )
    return BasePipeline(config)

# WRONG — subclassing BasePipeline for domain behavior
class ClaimPipeline(BasePipeline):
    def run(self, claim: ClaimData) -> PipelineResult:
        # BAD: overrides run() — defeats shared engine purpose
        ...
```

**Pipeline `run()` with passthrough:**

```python
# CORRECT — pipeline respects ValidationContext
def run(self, input_data: Any, validation_context: ValidationContext | None = None) -> Any:
    for validator in self._rule_validators:
        if validation_context and validation_context.has_passed(validator.name):
            continue  # Skip — already validated upstream
        output = validator.validate(input_data)
        if validation_context:
            validation_context.record(validator.name, ValidatorResult(
                passed=not any(f.severity == Severity.ERROR for f in output.findings),
                findings=tuple(output.findings),
            ))
        all_findings.extend(output.findings)

# WRONG — ignoring validation_context
def run(self, input_data: Any, validation_context: ValidationContext | None = None) -> Any:
    for validator in self._rule_validators:
        output = validator.validate(input_data)  # Always runs, even if already validated
        ...
```

### Workflow Patterns

**Stage implementation pattern:**

```python
# CORRECT — stage wraps a domain pipeline
class EligibilityStage:
    name = "eligibility"
    is_gate = True

    def should_skip(self, ctx: ValidationContext, prior: list[StageResult]) -> bool:
        return False  # Eligibility always runs first

    def run(self, request: Any, ctx: ValidationContext) -> StageResult:
        pipeline = build_eligibility_pipeline(self._settings)
        result = pipeline.run(request, validation_context=ctx)
        return StageResult(
            stage=self.name,
            result=result,
            passed=result.passed,
            execution_time=result.execution_time,
        )

# CORRECT — conditional stage
class PAStage:
    name = "prior_auth"
    is_gate = True

    def should_skip(self, ctx: ValidationContext, prior: list[StageResult]) -> bool:
        # Skip PA if determination says not required
        elig_result = next((s for s in prior if s.stage == "eligibility"), None)
        if elig_result is None:
            return True
        determination = determine_pa_required(elig_result.result.response)
        return not determination.required

# WRONG — stage does its own validation instead of delegating to pipeline
class EligibilityStage:
    def run(self, request: Any, ctx: ValidationContext) -> StageResult:
        # BAD: reimplements pipeline logic in stage
        for validator in validators:
            validator.validate(request)
```

**WorkflowResult access pattern:**

```python
# CORRECT — typed per-stage access
result = process_claim(request)
result.eligibility        # EligibilityResult (always present)
result.prior_auth         # PriorAuthResult | None (None if skipped)
result.claim_validation   # PipelineResult (None if stopped early)
result.stopped_at         # "eligibility" | "prior_auth" | None
result.passed             # True only if ALL stages passed
result.execution_time     # Total wall-clock time
result.stage_results      # list[StageResult] — ordered, for iteration

# WRONG — index-based access
result.stages[0]          # Don't force users to know stage order
result.results["eligibility"]  # Don't use string dict keys
```

### Shared Code Table Patterns

**Import pattern:**

```python
# CORRECT — all code table access through shared module
from claim_validator.shared.code_tables import get_icd10_table, get_payer_directory

# CORRECT — domain code uses shared tables
class CodingValidator(BaseValidator):
    def validate(self, claim: ClaimData) -> ValidatorOutput:
        icd10 = get_icd10_table()  # From shared, not from local code_tables/
        ...

# WRONG — importing from old domain-specific location
from claim_validator.code_tables import get_icd10_table          # Old claim path
from claim_validator.eligibility.code_tables import get_payer_directory  # Old elig path
```

### Test Patterns for Shared Modules

```python
# Shared validator tests — test the pure function directly
# tests/test_shared/test_validators/test_npi.py
class TestValidateNPI:
    def test_valid_npi(self):
        findings = validate_npi("1234567893", "billing_provider_npi")
        assert len(findings) == 0

    def test_invalid_npi(self):
        findings = validate_npi("1234567890", "billing_provider_npi")
        assert any(f.code == "INVALID_NPI" for f in findings)

    def test_custom_prefix(self):
        findings = validate_npi("1234567890", "requester_npi", code_prefix="PA_")
        assert any(f.code == "PA_INVALID_NPI" for f in findings)

    def test_no_phi_in_findings(self):
        findings = validate_npi("1234567890", "billing_provider_npi")
        for f in findings:
            assert "1234567890" not in f.message  # PHI leak check

# Domain wrapper tests — verify delegation, not re-test logic
# tests/test_validators/test_rule_based/test_npi.py
class TestNPIValidator:
    def test_delegates_to_shared(self):
        """Verify wrapper extracts correct field and delegates."""
        claim = ClaimData(billing_provider_npi="1234567890", ...)
        result = NPIValidator().validate(claim)
        assert any(f.code == "INVALID_NPI" for f in result.findings)
        assert result.findings[0].field_name == "billing_provider_npi"
```

### Enforcement Guidelines

**All AI Agents MUST (v3.0 refactoring-specific):**

1. **Never duplicate validation logic** — all validation functions exist only in `shared/validators/`. Domain validators are thin wrappers that extract fields and delegate
2. **Use `validate_{concept}()` pure functions** — shared validators expose pure functions with `field_name` and `code_prefix` parameters
3. **Keep domain wrappers thin** — extract field, call shared function, wrap output. No additional logic in wrappers
4. **Provide `DeidentificationConfig`** — domain de-identifiers set config in `__init__`, never override `deidentify()`
5. **Use `PipelineConfig`** — domain pipelines create `BasePipeline` with config, never subclass `BasePipeline.run()`
6. **Respect `ValidationContext`** — pipeline `run()` must skip validators that have already passed in context
7. **Stages delegate to pipelines** — workflow stages wrap domain pipelines, never reimplement pipeline logic
8. **Import code tables from `shared.code_tables`** — never from old domain-specific paths
9. **Test shared functions directly** — test pure functions in `test_shared/`. Domain wrapper tests verify delegation only
10. **No re-export shims** — old internal import paths are not re-exported. Clean break at v3.0

## v3.0 Refactoring — Project Structure & Boundaries

### Complete v3.0 Directory Structure

**New and modified files** (existing unchanged files omitted for clarity):

```
src/claim_validator/
├── __init__.py                          # MODIFIED — add process_claim, WorkflowResult exports
├── _api.py                              # MODIFIED — validate() delegates to shared pipeline
├── conf.py                              # MODIFIED — add workflow settings (D42)
├── shared/                              # NEW — all shared utilities
│   ├── __init__.py
│   ├── validators/                      # NEW — canonical validator implementations (D34)
│   │   ├── __init__.py                  # Re-exports: validate_npi, validate_date, etc.
│   │   ├── npi.py                       # validate_npi() pure function
│   │   ├── date.py                      # validate_date() — service date, DOB
│   │   ├── member_id.py                 # validate_member_id()
│   │   ├── demographics.py              # validate_demographics() — name, gender, DOB
│   │   ├── diagnosis.py                 # validate_diagnosis() — ICD-10 code table lookup
│   │   ├── procedure.py                 # validate_procedure() — CPT/HCPCS lookup
│   │   └── payer_id.py                  # validate_payer_id() — payer directory lookup
│   ├── deidentifier/                    # NEW — base de-identifier engine (D35)
│   │   ├── __init__.py                  # Re-exports: BaseDeidentifier, DeidentificationConfig
│   │   ├── base.py                      # BaseDeidentifier class
│   │   └── config.py                    # DeidentificationConfig dataclass
│   ├── pipeline/                        # NEW — shared pipeline engine (D36, D37)
│   │   ├── __init__.py                  # Re-exports: BasePipeline, PipelineConfig, ValidationContext
│   │   ├── engine.py                    # BasePipeline — multi-phase execution
│   │   ├── config.py                    # PipelineConfig dataclass
│   │   └── context.py                   # ValidationContext, ValidatorResult
│   ├── code_tables/                     # NEW — unified code table access (D39)
│   │   ├── __init__.py                  # Re-exports: all get_*_table() functions
│   │   ├── loader.py                    # Lazy singleton loader with threading.Lock
│   │   ├── icd10.py                     # get_icd10_table()
│   │   ├── hcpcs.py                     # get_hcpcs_table()
│   │   ├── taxonomy.py                  # get_taxonomy_table()
│   │   ├── pos.py                       # get_pos_table()
│   │   ├── payer_directory.py           # get_payer_directory()
│   │   ├── service_types.py             # get_service_types()
│   │   ├── hcr_actions.py               # get_hcr_action_codes()
│   │   ├── aaa_reject_codes.py          # get_aaa_reject_codes()
│   │   └── timely_filing.py             # get_timely_filing_rules()
│   └── data/                            # NEW — all bundled data files (moved here)
│       ├── icd10_cm.json.gz
│       ├── hcpcs.json.gz
│       ├── taxonomy.json.gz
│       ├── pos_codes.json.gz
│       ├── timely_filing.json
│       ├── payer_directory.json
│       ├── service_types.json
│       ├── hcr_action_codes.json
│       └── aaa_reject_codes.json
├── workflow/                            # NEW — unified sequential pipeline (D38, D40)
│   ├── __init__.py                      # Re-exports: process_claim, WorkflowResult
│   ├── _api.py                          # process_claim() convenience function
│   ├── orchestrator.py                  # WorkflowOrchestrator class
│   ├── stages.py                        # Stage protocol + EligibilityStage, PAStage, ClaimStage
│   └── models.py                        # WorkflowResult, WorkflowRequest, StageResult
├── validators/                          # MODIFIED — delegates to shared (D41)
│   ├── pipeline.py                      # MODIFIED — builds BasePipeline with claim config
│   └── rule_based/                      # MODIFIED — thin wrappers calling shared
│       ├── npi.py                       # NPIValidator → calls validate_npi()
│       ├── demographics.py              # DemographicsValidator → calls validate_demographics()
│       ├── coding.py                    # CodingValidator → calls validate_diagnosis/procedure()
│       └── ...                          # Other validators → delegate to shared
├── deidentifier/                        # MODIFIED — subclasses BaseDeidentifier
│   └── deidentifier.py                  # ClaimDeidentifier(BaseDeidentifier) with claim config
├── eligibility/                         # MODIFIED — delegates to shared (D41)
│   ├── pipeline.py                      # MODIFIED — builds BasePipeline with eligibility config
│   ├── deidentifier.py                  # MODIFIED — EligibilityDeidentifier(BaseDeidentifier)
│   ├── validators/rule_based/           # MODIFIED — thin wrappers calling shared
│   │   ├── payer_id.py                  # PayerIDValidator → calls validate_payer_id()
│   │   ├── demographics.py              # EligDemographicsValidator → calls validate_demographics()
│   │   └── ...                          # Other validators → delegate to shared
│   ├── code_tables/                     # REMOVED — imports from shared/code_tables/
│   └── data/                            # REMOVED — data moved to shared/data/
├── prior_auth/                          # MODIFIED — delegates to shared (D41)
│   ├── pipeline.py                      # MODIFIED — builds BasePipeline with PA config
│   ├── deidentifier.py                  # MODIFIED — PriorAuthDeidentifier(BaseDeidentifier)
│   ├── validators/rule_based/           # MODIFIED — thin wrappers calling shared
│   │   ├── npi.py                       # PANPIValidator → calls validate_npi()
│   │   ├── diagnosis.py                 # PADiagnosisValidator → calls validate_diagnosis()
│   │   └── ...                          # Other validators → delegate to shared
│   ├── code_tables/                     # REMOVED — imports from shared/code_tables/
│   └── data/                            # REMOVED — data moved to shared/data/
└── ...                                  # Unchanged: models/, llm/, constants.py, exceptions.py
```

**Test structure:**

```
tests/
├── test_shared/                         # NEW — shared module tests
│   ├── conftest.py                      # Shared test fixtures
│   ├── test_validators/
│   │   ├── test_npi.py                  # validate_npi() pure function tests
│   │   ├── test_date.py                 # validate_date() tests
│   │   ├── test_member_id.py            # validate_member_id() tests
│   │   ├── test_demographics.py         # validate_demographics() tests
│   │   ├── test_diagnosis.py            # validate_diagnosis() tests
│   │   ├── test_procedure.py            # validate_procedure() tests
│   │   └── test_payer_id.py             # validate_payer_id() tests
│   ├── test_deidentifier/
│   │   ├── test_base.py                 # BaseDeidentifier core logic tests
│   │   └── test_config.py               # DeidentificationConfig tests
│   ├── test_pipeline/
│   │   ├── test_engine.py               # BasePipeline phase execution, gating, timing
│   │   ├── test_config.py               # PipelineConfig tests
│   │   └── test_context.py              # ValidationContext passthrough tests
│   └── test_code_tables/
│       └── test_loader.py               # Unified lazy loading, thread safety
├── test_workflow/                       # NEW — workflow orchestrator tests
│   ├── conftest.py                      # Workflow test fixtures
│   ├── test_api.py                      # process_claim() top-level function
│   ├── test_orchestrator.py             # WorkflowOrchestrator sequential execution
│   ├── test_stages.py                   # Stage implementations, skip logic
│   └── test_models.py                   # WorkflowResult, StageResult
├── test_validators/                     # MODIFIED — wrapper delegation tests
│   └── test_rule_based/
│       ├── test_npi.py                  # NPIValidator delegates to validate_npi()
│       └── ...
├── test_eligibility/                    # MODIFIED — delegation tests
│   └── ...
├── test_prior_auth/                     # MODIFIED — delegation tests
│   └── ...
└── test_hipaa/                          # EXISTING — verify shared de-identifier
    ├── test_phi_leak.py                 # Scan all 3 domains
    ├── test_no_network.py               # Rule-based zero network calls
    └── test_deidentification.py         # All 18 identifiers stripped (claims, elig, PA)
```

**Modified existing files summary:**

| File | Change | Reason |
|---|---|---|
| `__init__.py` | Add `process_claim`, `WorkflowResult`, `WorkflowRequest` exports | FR21, new public API |
| `_api.py` | `validate()` builds `BasePipeline` with claim config | D41 delegation |
| `conf.py` | Add workflow settings fields | D42 |
| `validators/pipeline.py` | Replace `ValidationPipeline` with `BasePipeline` construction | D36, D41 |
| `validators/rule_based/*.py` | Thin wrappers calling `shared/validators/` functions | D34 |
| `deidentifier/deidentifier.py` | `ClaimDeidentifier` subclasses `BaseDeidentifier` | D35 |
| `eligibility/pipeline.py` | Replace `EligibilityPipeline` with `BasePipeline` construction | D36, D41 |
| `eligibility/deidentifier.py` | `EligibilityDeidentifier` subclasses `BaseDeidentifier` | D35 |
| `eligibility/validators/rule_based/*.py` | Thin wrappers calling shared functions | D34 |
| `prior_auth/pipeline.py` | Replace `PriorAuthPipeline` with `BasePipeline` construction | D36, D41 |
| `prior_auth/deidentifier.py` | `PriorAuthDeidentifier` subclasses `BaseDeidentifier` | D35 |
| `prior_auth/validators/rule_based/*.py` | Thin wrappers calling shared functions | D34 |

**Removed directories** (data/code_tables moved to shared):

| Removed | Replaced By |
|---|---|
| `data/` (claim data dir) | `shared/data/` |
| `code_tables/` (claim code tables) | `shared/code_tables/` |
| `eligibility/data/` | `shared/data/` |
| `eligibility/code_tables/` | `shared/code_tables/` |
| `prior_auth/data/` | `shared/data/` |
| `prior_auth/code_tables/` | `shared/code_tables/` |

**New file count:** ~25 new source files (`shared/` + `workflow/`) + ~20 new test files = ~45 new files
**Modified file count:** ~15 existing files refactored
**Removed directories:** 6 (replaced by `shared/`)

### v3.0 Architectural Boundaries

**Public API Boundary (new symbols):**

| Symbol | Module | Stability |
|---|---|---|
| `process_claim()` | `workflow/_api.py` | Stable from v3.0 |
| `WorkflowResult` | `workflow/models.py` | Stable from v3.0 |
| `WorkflowRequest` | `workflow/models.py` | Stable from v3.0 |

**Internal boundary (shared module):**
- `shared/validators/*.py` — internal; domain wrappers are the public interface
- `shared/deidentifier/` — internal; domain de-identifiers are the public interface
- `shared/pipeline/engine.py` — internal; domain `build_*_pipeline()` functions are the interface
- `shared/pipeline/context.py` — `ValidationContext` is semi-public (used by workflow, not by end users)
- `shared/code_tables/` — public (any code can look up any table via `get_*_table()`)
- `shared/data/` — package data, not importable

**Workflow boundary:**
- `workflow/orchestrator.py` — internal; `process_claim()` in `workflow/_api.py` is the public interface
- `workflow/stages.py` — internal; stage implementations are not user-facing
- `workflow/models.py` — public; `WorkflowResult`, `StageResult` returned to users

### v3.0 Requirements to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|---|---|---|
| **Shared Validators (FR1-FR9)** | `shared/validators/*.py` | Domain `validators/rule_based/*.py` (thin wrappers) |
| **Shared De-identification (FR10-FR13)** | `shared/deidentifier/base.py`, `config.py` | Domain `deidentifier.py` files (thin subclasses) |
| **Shared Pipeline Engine (FR14-FR17)** | `shared/pipeline/engine.py`, `config.py` | Domain `pipeline.py` files (config + construction) |
| **Shared Code Tables (FR18-FR20)** | `shared/code_tables/*.py`, `shared/data/` | — |
| **Unified Workflow (FR21-FR27)** | `workflow/orchestrator.py`, `workflow/stages.py` | `workflow/_api.py`, `workflow/models.py` |
| **Validation Passthrough (FR28-FR30)** | `shared/pipeline/context.py`, `shared/pipeline/engine.py` | `workflow/orchestrator.py` |
| **API Preservation (FR31-FR34)** | `_api.py`, `eligibility/_api.py`, `prior_auth/_api.py` | Domain pipeline construction |
| **Result Models (FR35-FR37)** | `workflow/models.py` | — |
| **HIPAA Compliance (FR38-FR40)** | `shared/deidentifier/base.py` | `tests/test_hipaa/` |
| **Configuration (FR41-FR43)** | `conf.py` | — |

### v3.0 Data Flow — Unified Workflow

```
User Input (dict or WorkflowRequest)
    │
    ▼
process_claim() [workflow/_api.py]
    │ Constructs WorkflowRequest if dict, builds orchestrator from settings
    ▼
WorkflowOrchestrator.run(request) [workflow/orchestrator.py]
    │ Creates ValidationContext()
    │
    ├── Stage 1: EligibilityStage
    │   ├── build_eligibility_pipeline(settings) → BasePipeline [eligibility/pipeline.py]
    │   ├── pipeline.run(request, validation_context=ctx)
    │   │   ├── Phase 1: Shared validators (via thin wrappers)
    │   │   │   ├── validate_npi() [shared/validators/npi.py]
    │   │   │   ├── validate_payer_id() [shared/validators/payer_id.py]
    │   │   │   ├── validate_demographics() [shared/validators/demographics.py]
    │   │   │   └── ... → records results in ValidationContext
    │   │   ├── Phase 2: Clearinghouse → EligibilityResponse
    │   │   └── Phase 3: AI → EligibilityDeidentifier(BaseDeidentifier) → LLM
    │   └── StageResult(eligibility_result, ctx updated)
    │
    ├── Gate: if eligibility failed → stopped_at="eligibility", return
    │
    ├── Stage 2: PA Determination
    │   ├── determine_pa_required(eligibility_response) → PADeterminationResult
    │   └── If not required → skip PA stage
    │
    ├── Stage 3: PAStage (conditional)
    │   ├── build_pa_pipeline(settings) → BasePipeline [prior_auth/pipeline.py]
    │   ├── pipeline.run(request, validation_context=ctx)
    │   │   ├── Phase 1: Shared validators (SKIPS already-validated: NPI, demographics)
    │   │   ├── Phase 2: Clearinghouse → PriorAuthResponse
    │   │   └── Phase 3: AI → PriorAuthDeidentifier(BaseDeidentifier) → LLM
    │   └── StageResult(pa_result, ctx updated)
    │
    ├── Gate: if PA failed → stopped_at="prior_auth", return
    │
    └── Stage 4: ClaimValidationStage
        ├── build_claim_pipeline(settings) → BasePipeline [validators/pipeline.py]
        ├── pipeline.run(request, validation_context=ctx)
        │   ├── Phase 1: Shared validators (SKIPS already-validated)
        │   └── Phase 2: AI → ClaimDeidentifier(BaseDeidentifier) → LLM
        └── StageResult(claim_result)
    │
    ▼
WorkflowResult(eligibility, prior_auth, claim_validation, stopped_at, passed, execution_time)
```

---

## v3.0 Refactoring — Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

All 43 decisions (D1-D43) are compatible. The v3.0 refactoring decisions (D34-D43) are additive — they introduce shared infrastructure that existing domain decisions delegate to, without contradicting any prior decision. Key compatibility points:

- D34 (shared validators) provides the implementations that D5-D6 (claim validators), D16-D17 (eligibility validators), and D26-D27 (PA validators) delegate to
- D35 (shared de-identifier) unifies D8 (claim de-id), D19 (eligibility de-id), and D29 (PA de-id) under a single base with config-driven behavior
- D36 (shared pipeline) generalizes D7 (claim pipeline), D14 (eligibility pipeline), and D24 (PA pipeline) into a config-parameterized engine
- D42 (configuration extension) adds flat fields to D10/D20/D30 settings — no conflicts with existing env var patterns
- D43 (clean break) explicitly acknowledges that internal import paths change, which is consistent with D41 (domain refactoring)

No version conflicts — all technology choices remain unchanged (Python 3.11+, Pydantic 2.x, hatchling).

**Pattern Consistency:**

All 10 new conflict points (from step 5) align with existing patterns:
- Shared validator pure functions follow the same `Finding`-based return pattern as existing validators
- Domain wrappers maintain `BaseValidator.validate()` interface unchanged
- `BaseDeidentifier` follows the same ABC pattern as `BaseLLMClient` and `BaseClearinghouseClient`
- `BasePipeline` with `PipelineConfig` mirrors the settings-driven configuration pattern used throughout
- Naming conventions are consistent: `validate_{concept}()`, `{Domain}Deidentifier`, `{Domain}Pipeline`

**Structure Alignment:**

The v3.0 directory structure (step 6) properly supports all decisions:
- `shared/` subpackage is cleanly isolated with no circular dependencies
- Domain modules (`validators/`, `eligibility/`, `prior_auth/`) become thin orchestration layers
- `workflow/` subpackage is separate from domain logic
- Test structure mirrors source structure exactly

### Requirements Coverage Validation ✅

**Functional Requirements Coverage (43/43 — 100%):**

| FR Group | FRs | Architectural Support |
|---|---|---|
| Shared Validators | FR1-FR9 | D34 shared validators, `shared/validators/` directory |
| Shared De-identification | FR10-FR13 | D35 BaseDeidentifier, `shared/deidentifier/` directory |
| Shared Pipeline Engine | FR14-FR17 | D36 BasePipeline + PipelineConfig, `shared/pipeline/` directory |
| Shared Code Tables | FR18-FR20 | D39 unified code tables, `shared/code_tables/` + `shared/data/` |
| Unified Workflow Orchestrator | FR21-FR27 | D38 WorkflowOrchestrator + Stage protocol, `workflow/` directory |
| Validation Passthrough | FR28-FR30 | D37 ValidationContext, pipeline skip logic |
| Existing API Preservation | FR31-FR34 | D41 domain refactoring (thin wrappers), D43 clean break |
| Result Models | FR35-FR37 | D40 WorkflowResult model |
| HIPAA Compliance | FR38-FR40 | D35 shared de-id inherits all existing HIPAA tests |
| Configuration | FR41-FR43 | D42 configuration extension, flat settings pattern |

**Non-Functional Requirements Coverage (27/27 — 100%):**

| NFR Group | NFRs | Architectural Support |
|---|---|---|
| Performance | NFR1-NFR6 | D34 pure functions (<50ms), D36 no overhead (<5ms indirection), D39 lazy singletons (<1ms lookup) |
| Security | NFR7-NFR11 | D35 BaseDeidentifier enforces de-id before every LLM call, PHI cleared per-call |
| Scalability | NFR12-NFR15 | D34 stateless validators, D36 thread-safe pipeline, D39 locked singletons |
| Integration | NFR16-NFR20 | D41 existing APIs unchanged, D43 internal paths change only, Python 3.11-3.13 |
| Code Quality | NFR21-NFR27 | D34 eliminates duplication, D41 thin wrappers reduce complexity, test patterns maintained |

### Implementation Readiness Validation ✅

**Decision Completeness:**

- All 10 refactoring decisions (D34-D43) include version/rationale, code examples, and migration notes
- Implementation patterns cover all major shared module interfaces with concrete code samples
- Enforcement guidelines provide 10 clear rules for AI agent consistency
- Examples provided for: shared validator, domain wrapper, de-identifier config, pipeline config, stage implementation, WorkflowResult access, code table import, and test patterns

**Structure Completeness:**

- Complete v3.0 directory structure with ~45 new files and ~15 modified files
- All files and directories defined with purpose annotations
- Integration points clearly specified (shared → domain delegation, workflow → pipeline composition)
- Component boundaries well-defined (shared = pure logic, domain = orchestration, workflow = sequencing)

**Pattern Completeness:**

- All 10 conflict points addressed with code examples
- Naming conventions comprehensive and consistent with existing codebase
- Error handling follows existing exception hierarchy (no new exception classes needed)
- Test patterns cover shared modules, domain wrappers, passthrough logic, and workflow integration

### Gap Analysis Results

**Critical Gaps: 0**

No blocking gaps identified.

**Important Gaps: 2 (both resolved during validation)**

1. **FR31-33 "identical behavior" specification** — Resolved: existing test suites serve as the formal specification. Domain wrappers must pass all existing tests unchanged. Added to enforcement guidelines.

2. **ValidationContext thread safety** — Resolved: `ValidationContext` is created per-call (not shared across threads). The `WorkflowOrchestrator.process_claim()` creates a fresh context for each invocation. No thread-safety concern.

**Nice-to-Have Gaps: 2**

1. **Migration script** — A script to verify that all existing tests pass after refactoring would be helpful but is not architecturally blocking. Can be created during implementation.

2. **Performance benchmark suite** — A benchmark comparing v2 vs v3 performance for all NFR thresholds would validate the <5ms indirection overhead claim. Can be created post-implementation.

### Validation Issues Addressed

No critical or blocking issues found. The two important gaps were resolved inline during validation (see above).

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context thoroughly analyzed (43 FRs, 27 NFRs, existing codebase)
- [x] Scale and complexity assessed (refactoring 3 modules, ~45 new files)
- [x] Technical constraints identified (Python 3.11+, Pydantic 2.x, HIPAA)
- [x] Cross-cutting concerns mapped (PHI, validation passthrough, configuration)

**✅ Architectural Decisions**

- [x] Critical decisions documented with versions (D34-D43)
- [x] Technology stack fully specified (unchanged from existing)
- [x] Integration patterns defined (shared→domain delegation, workflow→pipeline composition)
- [x] Performance considerations addressed (pure functions, lazy singletons, no overhead)

**✅ Implementation Patterns**

- [x] Naming conventions established (10 conflict points)
- [x] Structure patterns defined (shared module, domain wrapper, workflow stage)
- [x] Communication patterns specified (ValidationContext, StageResult, WorkflowResult)
- [x] Process patterns documented (enforcement guidelines, test patterns)

**✅ Project Structure**

- [x] Complete directory structure defined (~45 new + ~15 modified files)
- [x] Component boundaries established (shared/domain/workflow)
- [x] Integration points mapped (FR-to-structure table)
- [x] Requirements to structure mapping complete (43/43 FRs, 27/27 NFRs)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — based on 100% FR/NFR coverage, zero critical gaps, and complete implementation patterns with code examples.

**Key Strengths:**

1. Clean separation between shared logic (pure functions) and domain orchestration (thin wrappers)
2. Config-driven de-identification and pipeline behavior — domains differ only in configuration
3. Validation passthrough eliminates redundant work without coupling stages
4. WorkflowOrchestrator with Stage protocol enables clean sequencing with gate logic
5. All existing APIs preserved — refactoring is purely internal

**Areas for Future Enhancement:**

1. Performance benchmark suite to validate NFR thresholds empirically
2. Migration verification script for test suite continuity
3. Potential async pipeline support (not in v3.0 scope)

### Implementation Handoff

**AI Agent Guidelines:**

- Follow all architectural decisions (D34-D43) exactly as documented
- Use implementation patterns consistently — especially the thin domain wrapper pattern
- Respect the shared/domain/workflow boundary: shared = pure logic, domain = orchestration, workflow = sequencing
- Refer to this document for all architectural questions
- Run existing test suites after every refactoring step to verify "identical behavior" (FR31-33)

**Implementation Sequence (15 steps):**

1. Create `shared/` package skeleton with `__init__.py` files
2. Implement `shared/validators/` — extract pure functions from existing validators
3. Implement `shared/deidentifier/` — `BaseDeidentifier` + `DeidentificationConfig`
4. Implement `shared/pipeline/` — `BasePipeline` + `PipelineConfig`
5. Implement `shared/code_tables/` — consolidate all loaders + data
6. Write tests for all shared modules
7. Refactor `validators/` (claims) — thin wrappers delegating to shared
8. Refactor `eligibility/` — thin wrappers delegating to shared
9. Refactor `prior_auth/` — thin wrappers delegating to shared
10. Verify all existing tests pass after domain refactoring
11. Implement `ValidationContext` and passthrough logic in `BasePipeline`
12. Implement `workflow/` — `WorkflowOrchestrator`, stages, `WorkflowResult`
13. Implement `process_claim()` top-level API
14. Write workflow integration tests
15. Final validation: all tests green, mypy strict, ruff clean, coverage maintained
