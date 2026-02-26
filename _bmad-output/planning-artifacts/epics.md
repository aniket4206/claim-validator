---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
---

# healthcare-claim-analyzer - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for healthcare-claim-analyzer, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Claim Validation (FR1-FR6)**

FR1: Developer can validate a healthcare claim by passing a Python dict or Pydantic model and receiving a structured result indicating pass/fail with detailed findings
FR2: Developer can run rule-based validation with zero configuration, zero API keys, and zero network calls
FR3: Developer can run AI-powered validation by providing an LLM provider configuration (provider name, API key, model)
FR4: Developer can configure the validation pipeline to skip AI validation when rule-based validation fails
FR5: Developer can receive findings that include error code, human-readable message, severity level, field name, line number, and actionable fix suggestion for every issue detected
FR6: Developer can distinguish between ERROR severity (claim will be denied) and WARNING severity (claim may be denied or has quality issues)

**Rule-Based Validators (FR7-FR17)**

FR7: System can validate all required CMS-1500 fields are present and non-empty
FR8: System can validate NPI numbers using the Luhn check-digit algorithm
FR9: System can validate subscriber/insurance ID presence and format
FR10: System can validate patient demographics consistency (DOB, gender, relationship)
FR11: System can validate ICD-10-CM diagnosis code format and existence against bundled code tables
FR12: System can validate CPT/HCPCS procedure code format and modifier validity
FR13: System can validate diagnosis pointer consistency between lines and diagnosis codes
FR14: System can validate charge amounts are positive and line totals consistent
FR15: System can validate date consistency (service dates, DOB, filing date)
FR16: System can detect duplicate claim lines within a single claim
FR17: System can check service dates against configurable payer-specific timely filing deadlines

**AI Validation (FR18-FR22)**

FR18: System can assess clinical plausibility of diagnosis-procedure combinations using an LLM
FR19: System can assess likely coverage and medical necessity concerns using an LLM
FR20: System can identify services likely requiring prior authorization using an LLM
FR21: System can automatically de-identify claims before sending to any LLM, stripping all 18 HIPAA identifiers
FR22: System can send only clinically relevant, non-PHI data to LLMs (codes, charges, payer ID, NPI, age, gender, state, service year)

**LLM Provider Support (FR23-FR27)**

FR23: Developer can use Anthropic Claude models for AI validation
FR24: Developer can use OpenAI GPT models for AI validation
FR25: Developer can use any OpenAI-compatible endpoint (Ollama, vLLM, LiteLLM) for AI validation
FR26: Developer can switch LLM providers by changing configuration without modifying code
FR27: Developer can create custom LLM provider adapters by subclassing a base client interface

**Pipeline & Extensibility (FR28-FR33)**

FR28: Developer can create custom validators by subclassing a base class and implementing a validate method
FR29: Developer can register custom validators into the pipeline via configuration (dotted path strings)
FR30: Developer can construct custom pipelines with a specific subset of validators
FR31: Developer can configure pipeline behavior via a settings object
FR32: System can execute validators in two phases: rule-based first, AI second
FR33: System can aggregate results from all validators into a single pipeline result

**Data Models & Input (FR34-FR37)**

FR34: Developer can provide claim data as a plain Python dictionary
FR35: Developer can provide claim data as a typed Pydantic model with validation
FR36: System can represent claims with multiple lines (procedure codes, modifiers, diagnosis pointers, charges)
FR37: System can represent diagnosis codes with code value, pointer position, and type

**Code Tables & Reference Data (FR38-FR42)**

FR38: System can validate ICD-10-CM codes against bundled CMS tables without network calls
FR39: System can validate HCPCS Level II codes against bundled tables without network calls
FR40: System can validate Place of Service codes against bundled reference data
FR41: System can validate provider taxonomy codes against bundled NUCC data
FR42: System can provide timely filing deadline defaults for common payers

**Configuration & Distribution (FR43-FR49)**

FR43: Developer can configure the library using a Pydantic settings object with env var support
FR44: Developer can override default validator lists, AI settings, and pipeline behavior via configuration
FR45: Developer can use the library with zero configuration for basic rule-based validation
FR46: Developer can install the core library via `pip install claim-validator` with no optional dependencies
FR47: Developer can install AI support via `pip install claim-validator[ai]`
FR48: Developer can install provider-specific extras (`[anthropic]`, `[openai]`)
FR49: Library exposes type stubs (`py.typed`) for static type checking

### NonFunctional Requirements

**Performance (NFR1-NFR7)**

NFR1: Rule-based latency — `validate()` with all 8 validators, no AI — < 50ms per claim
NFR2: AI latency — Full pipeline with one LLM round-trip — < 5 seconds per claim
NFR3: Pipeline startup — First pipeline construction — < 100ms; near-zero subsequent
NFR4: Code table lookup — Single code validation — < 1ms (in-memory after first load)
NFR5: Memory footprint — Library with code tables loaded — < 100MB
NFR6: Batch throughput — Rule-based, single thread — 500+ claims/second
NFR7: Import time — `import claim_validator` — < 500ms (lazy-load tables)

**Security (NFR8-NFR13)**

NFR8: Zero PHI transmission (rule-based) — No network calls ever
NFR9: PHI de-identification (AI) — All 18 HIPAA identifiers stripped before LLM
NFR10: No PHI in outputs — No PHI in logs, exceptions, or findings
NFR11: No telemetry — No phone-home or undisclosed network calls
NFR12: Secrets handling — API keys never in logs or outputs
NFR13: Dependency security — No known CVEs at release

**Scalability (NFR14-NFR16)**

NFR14: Thread safety — Safe concurrent use — Zero shared mutable state. Concurrent test (100 threads)
NFR15: Stateless validation — No state between calls — Each `validate()` independent
NFR16: Linear scaling — O(n) with claim lines — No exponential patterns

**Reliability (NFR17-NFR20)**

NFR17: Deterministic results — Identical output per input (rule-based)
NFR18: Graceful AI failure — Returns rule-based results + warning if LLM down
NFR19: Invalid input handling — Clear errors, no unhandled exceptions
NFR20: Code table integrity — Match CMS official releases

**Compatibility (NFR21-NFR25)**

NFR21: Python versions — 3.11, 3.12, 3.13
NFR22: OS support — Linux, macOS, Windows
NFR23: Dependency minimalism — Core = Pydantic only
NFR24: Framework independence — Zero Django/Flask/FastAPI in core
NFR25: Type checker compatibility — `py.typed` for mypy + pyright

**Code Quality (NFR26-NFR29)**

NFR26: Test coverage — All public API paths — 90%+ lines, 100% validators + de-identifier
NFR27: Linting — ruff (E, F, I, N, W, UP) — Zero warnings
NFR28: Documentation — All public API docstrings — interrogate > 95%
NFR29: Package size — Published wheel — < 15MB with compressed tables

### Additional Requirements

**From Architecture — Starter Template (impacts Epic 1, Story 1):**
- Architecture specifies starter template: `uv init --lib --build-backend hatchling claim-validator`
- Hybrid approach: uv init --lib + manual configuration for brownfield extraction
- hatchling as build backend with hatch-vcs for git-tag-based versioning
- src layout: `src/claim_validator/`

**From Architecture — Core Design Decisions:**
- D1: Code table storage — Compressed JSON (.json.gz), standard library gzip + json only
- D2: Code table loading — Lazy singleton with `threading.Lock`, double-check locking pattern
- D3: Pydantic models — `frozen=True`, `strict=False` for immutability + lax coercion from dicts
- D4: Configuration — Pydantic `BaseSettings` with `env_prefix="CLAIM_VALIDATOR_"`
- D5: De-identification — Pipeline-integrated, automatic before any AI validator
- D6: PHI boundary — Type-driven `DeidentifiedClaim` + runtime assertion (belt-and-suspenders)
- D7: LLM client — Chat-based `send_messages(messages: list[Message]) -> str`
- D8: Prompt management — Per-validator prompts as class constants
- D9: Response parsing — Hybrid (structured JSON preferred, regex fallback)
- D10: Validator registry — Dotted path strings with `importlib.import_module()`
- D11: Pipeline composition — Both `Pipeline.from_settings()` and `Pipeline.builder().add().build()`
- D12: Versioning — hatch-vcs (git tag driven)
- D13: Import/export — Subpackages + top-level re-export via `__init__.py`

**From Architecture — Gap Resolutions:**
- Add `BaseAIValidator(BaseValidator)` in `validators/ai/base.py` with LLM client injection
- Add `data/manifest.json` for code table version metadata (version, effective date, code count)
- Use standard Python `logging.getLogger(__name__)` in all modules, never add handlers

**From Architecture — CI/CD Requirements:**
- ci.yml: Matrix Python {3.11, 3.12, 3.13} x OS {Linux, macOS, Windows}, ruff + mypy + pytest
- release.yml: Triggered by git tag `v*`, builds wheel, publishes to PyPI
- hipaa.yml: PHI leak scan, no-network rule-based test, de-identification verification on every PR

**From Architecture — Optional Dependency Extras:**
- `[ai]` = httpx + anthropic + openai
- `[anthropic]` = httpx + anthropic
- `[openai]` = httpx + openai
- `[django]` = django (Phase 2)
- `[fastapi]` = fastapi (Phase 2)
- `[dev]` = pytest + pytest-cov + ruff + mypy + factory-boy
- `[all]` = ai + django + fastapi

**From Architecture — Implementation Sequence:**
1. Package scaffolding (D12, D13)
2. Core models (D3)
3. Configuration (D4)
4. Code tables (D1, D2)
5. Validator base + registry (D10)
6. Rule-based validators
7. Pipeline (D11)
8. De-identification (D5, D6)
9. LLM abstraction (D7, D8, D9)
10. AI validators
11. Top-level API

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 2 | Validate claim via dict or Pydantic model → structured result |
| FR2 | Epic 2 | Rule-based validation with zero config/keys/network |
| FR3 | Epic 3 | AI-powered validation with LLM provider config |
| FR4 | Epic 3 | Configure skip AI when rule-based fails |
| FR5 | Epic 2 | Findings with code, message, severity, field, line, suggestion |
| FR6 | Epic 2 | ERROR vs WARNING severity distinction |
| FR7 | Epic 2 | Validate required CMS-1500 fields present |
| FR8 | Epic 2 | Validate NPI via Luhn check-digit |
| FR9 | Epic 2 | Validate subscriber/insurance ID |
| FR10 | Epic 2 | Validate patient demographics consistency |
| FR11 | Epic 2 | Validate ICD-10-CM code format + existence |
| FR12 | Epic 2 | Validate CPT/HCPCS format + modifiers |
| FR13 | Epic 2 | Validate diagnosis pointer consistency |
| FR14 | Epic 2 | Validate charge amounts + line totals |
| FR15 | Epic 2 | Validate date consistency |
| FR16 | Epic 2 | Detect duplicate claim lines |
| FR17 | Epic 2 | Check timely filing deadlines |
| FR18 | Epic 3 | AI clinical plausibility assessment |
| FR19 | Epic 3 | AI coverage/medical necessity assessment |
| FR20 | Epic 3 | AI prior authorization identification |
| FR21 | Epic 3 | Auto de-identify claims before LLM (18 HIPAA identifiers) |
| FR22 | Epic 3 | Send only non-PHI clinically relevant data to LLMs |
| FR23 | Epic 3 | Anthropic Claude provider support |
| FR24 | Epic 3 | OpenAI GPT provider support |
| FR25 | Epic 3 | OpenAI-compatible endpoint support |
| FR26 | Epic 3 | Switch providers via config, no code changes |
| FR27 | Epic 3 | Custom LLM provider adapters via subclassing |
| FR28 | Epic 2 | Custom validators via BaseValidator subclassing |
| FR29 | Epic 2 | Register custom validators via dotted path config |
| FR30 | Epic 2 | Construct custom pipelines with validator subsets |
| FR31 | Epic 2 | Configure pipeline behavior via settings object |
| FR32 | Epic 2 | Two-phase execution: rules first, AI second |
| FR33 | Epic 2 | Aggregate all validator results into single PipelineResult |
| FR34 | Epic 1 | Claim data as plain Python dict |
| FR35 | Epic 1 | Claim data as typed Pydantic model |
| FR36 | Epic 1 | Multi-line claims (procedures, modifiers, pointers, charges) |
| FR37 | Epic 1 | Diagnosis codes with code, pointer, type |
| FR38 | Epic 1 | Bundled ICD-10-CM code tables (offline) |
| FR39 | Epic 1 | Bundled HCPCS Level II tables (offline) |
| FR40 | Epic 1 | Bundled Place of Service codes (offline) |
| FR41 | Epic 1 | Bundled provider taxonomy codes (offline) |
| FR42 | Epic 1 | Timely filing deadline defaults for common payers |
| FR43 | Epic 1 | Pydantic settings object with env var support |
| FR44 | Epic 1 | Override validator lists, AI settings, pipeline behavior |
| FR45 | Epic 1 | Zero-config for basic rule-based validation |
| FR46 | Epic 1 | Install via `pip install claim-validator` |
| FR47 | Epic 3 | Install AI support via `[ai]` extra |
| FR48 | Epic 3 | Provider-specific extras (`[anthropic]`, `[openai]`) |
| FR49 | Epic 1 | `py.typed` for static type checking |

**Coverage: 49/49 FRs mapped (100%)**

## Epic List

### Epic 1: Package Foundation & Core Data Layer
Developer can `pip install claim-validator`, import typed Pydantic models to represent claims, look up codes against bundled tables, and configure the library — the installable, typed foundation is ready.
**FRs covered:** FR34, FR35, FR36, FR37, FR38, FR39, FR40, FR41, FR42, FR43, FR44, FR45, FR46, FR49

### Epic 2: Rule-Based Claim Validation Pipeline
Developer can call `validate(claim_dict)` and get structured pass/fail results with detailed findings from all 8 rule-based validators. Zero config, zero API keys, zero network calls. Custom validators and configurable pipelines work.
**FRs covered:** FR1, FR2, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR28, FR29, FR30, FR31, FR32, FR33

### Epic 3: AI-Powered Clinical Validation
Developer can add LLM-powered clinical validation using Anthropic, OpenAI, or any compatible endpoint. Claims are automatically de-identified (all 18 HIPAA identifiers stripped). AI catches clinical edge cases that rules miss.
**FRs covered:** FR3, FR4, FR18, FR19, FR20, FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR47, FR48

---

## Epic 1: Package Foundation & Core Data Layer

Developer can `pip install claim-validator`, import typed Pydantic models to represent claims, look up codes against bundled tables, and configure the library — the installable, typed foundation is ready.

### Story 1.1: Project Initialization & Package Scaffolding

As a **developer**,
I want to install `claim-validator` via pip into my Python project,
So that I can start using healthcare claim validation with zero friction.

**Acceptance Criteria:**

**Given** a Python 3.11+ environment with pip or uv
**When** I run `pip install claim-validator`
**Then** the package installs successfully with only Pydantic as a runtime dependency
**And** `import claim_validator` completes in under 500ms

**Given** the installed package
**When** I check for type support
**Then** a `py.typed` marker file exists and mypy/pyright recognize the package as typed

**Given** a developer cloning the repository
**When** they run `uv sync --all-extras`
**Then** all dev dependencies (pytest, ruff, mypy, factory-boy) are installed
**And** `uv run ruff check .` passes with zero warnings
**And** `uv run mypy src/` passes with zero errors

**Given** the pyproject.toml
**When** I inspect optional extras
**Then** extras `[ai]`, `[anthropic]`, `[openai]`, `[dev]`, `[all]` are defined with correct dependencies
**And** the core package depends only on `pydantic>=2.0,<3.0`

**Given** the project structure
**When** I inspect the repository
**Then** it uses src layout (`src/claim_validator/`), has MIT LICENSE, .gitignore, .env.example, and hatchling build backend with hatch-vcs versioning

### Story 1.2: Claim Data Models

As a **developer**,
I want typed Pydantic models to represent healthcare claims,
So that I have a validated, framework-agnostic data layer for CMS-1500 claims.

**Acceptance Criteria:**

**Given** a valid claim as a Python dictionary
**When** I construct `ClaimData(**claim_dict)` or `ClaimData.model_validate(claim_dict)`
**Then** a frozen, immutable `ClaimData` instance is created with all fields validated
**And** string-to-number coercion works (e.g., `"150.00"` → `float`)

**Given** a `ClaimData` instance
**When** I access `claim.lines`
**Then** I receive a sequence of `ClaimLineData` objects, each with procedure_code, modifiers, diagnosis_pointers, and charge_amount fields

**Given** a `ClaimData` instance
**When** I access `claim.diagnosis_codes`
**Then** I receive a sequence of `DiagnosisCode` objects, each with code, pointer position, and type

**Given** a `ClaimData` instance
**When** I attempt to modify any field (e.g., `claim.billing_provider_npi = "new"`)
**Then** a `ValidationError` is raised because the model is frozen

**Given** the constants module
**When** I import `Severity`, `ClaimType`
**Then** they are `StrEnum` types with values `Severity.ERROR`, `Severity.WARNING` and `ClaimType.PROFESSIONAL`, `ClaimType.INSTITUTIONAL`

**Given** the exceptions module
**When** I import exception classes
**Then** `ClaimValidatorError` is the base, with `ValidationError`, `ConfigurationError`, `LLMError`, and `CodeTableError` as subclasses

### Story 1.3: Validation Result Models

As a **developer**,
I want structured result objects for validation outcomes,
So that I can programmatically inspect findings with error codes, messages, severity, and fix suggestions.

**Acceptance Criteria:**

**Given** a `Finding` object
**When** I inspect its fields
**Then** it has `code` (str, UPPER_SNAKE_CASE), `message` (str, human-readable), `severity` (Severity enum), `field_name` (str), `line_number` (int | None), `suggestion` (str), and `context` (dict | None)

**Given** a list of `Finding` objects
**When** I construct a `ValidatorOutput`
**Then** a `ValidatorOutput` is created containing the validator name and findings list

**Given** a `PipelineResult`
**When** I check `result.passed`
**Then** it returns `True` only if there are zero ERROR-severity findings
**And** WARNING-severity findings do not cause `passed` to be `False`

**Given** a `PipelineResult`
**When** I access `result.findings`
**Then** I receive a flat list of all `Finding` objects from all validators
**And** findings are ordered by phase (rule-based first), then severity (ERROR first), then validator order

**Given** a `PipelineResult`
**When** I access `result.phase_results` and `result.execution_time`
**Then** per-phase breakdown is available for debugging and total execution time is recorded

**Given** any `Finding` object created by any validator
**When** I inspect `message` and `suggestion`
**Then** they reference field names only, never raw PHI values (patient names, SSNs, DOBs, etc.)

### Story 1.4: Configuration System

As a **developer**,
I want to configure the library via a settings object or environment variables,
So that I can customize validation behavior without modifying code.

**Acceptance Criteria:**

**Given** no explicit configuration
**When** I call `ClaimValidatorSettings()`
**Then** sensible defaults are used: all 8 rule-based validators enabled, AI disabled, `skip_ai_on_rule_failure=True`

**Given** environment variables with `CLAIM_VALIDATOR_` prefix
**When** I construct `ClaimValidatorSettings()`
**Then** environment variables override default values (e.g., `CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE=false`)

**Given** explicit parameters
**When** I construct `ClaimValidatorSettings(rule_validators=[...], ai_validators=[...], ai_config={...})`
**Then** the settings object validates types and stores the configuration
**And** validator paths are stored as dotted path strings

**Given** a `ClaimValidatorSettings` instance
**When** I inspect configurable fields
**Then** it includes `rule_validators` (list of dotted paths), `ai_validators` (list of dotted paths), `skip_ai_on_rule_failure` (bool), and `ai_config` (optional dict with provider, api_key, model)

**Given** invalid configuration values
**When** I construct `ClaimValidatorSettings(rule_validators="not-a-list")`
**Then** a `ConfigurationError` or Pydantic `ValidationError` is raised with a clear message

### Story 1.5: Bundled Code Tables & Lookup System

As a **developer**,
I want to look up ICD-10, HCPCS, taxonomy, and Place of Service codes against bundled tables,
So that I can validate codes offline with zero network calls and zero API keys.

**Acceptance Criteria:**

**Given** the installed package
**When** I call the ICD-10-CM lookup with a valid code (e.g., `"J06.9"`)
**Then** it returns confirmation the code exists and the code description
**And** the first lookup loads the compressed table; subsequent lookups use the cached in-memory dict

**Given** the installed package
**When** I call the HCPCS lookup with a valid code (e.g., `"99213"`)
**Then** it confirms the code exists in the bundled HCPCS table

**Given** the installed package
**When** I call the taxonomy lookup with a valid taxonomy code
**Then** it confirms the code exists in the bundled NUCC taxonomy table

**Given** the installed package
**When** I call the Place of Service lookup with a valid POS code (e.g., `"11"`)
**Then** it confirms the code exists in the bundled POS table

**Given** the timely filing reference data
**When** I query filing deadlines for a common payer
**Then** default timely filing limits are returned (e.g., Medicare = 365 days)

**Given** two threads calling code table lookups concurrently
**When** both trigger the first load simultaneously
**Then** the table is loaded exactly once (double-check locking with `threading.Lock`)
**And** both threads receive correct results

**Given** a `data/manifest.json` file
**When** I inspect code table metadata
**Then** each table has version, effective_date, and code_count fields
**And** the loader emits a WARNING-level log if tables are older than 12 months

**Given** the full set of bundled data files
**When** I measure the compressed size
**Then** the total package data is under 15MB

---

## Epic 2: Rule-Based Claim Validation Pipeline

Developer can call `validate(claim_dict)` and get structured pass/fail results with detailed findings from all 8 rule-based validators. Zero config, zero API keys, zero network calls. Custom validators and configurable pipelines work.

### Story 2.1: BaseValidator & Validator Registry

As a **developer**,
I want a base validator class and a registry system,
So that I can create custom validators and register them into the pipeline via configuration.

**Acceptance Criteria:**

**Given** the `BaseValidator` abstract base class
**When** I subclass it and implement `validate(self, claim: ClaimData) -> ValidatorOutput`
**Then** my custom validator integrates with the pipeline
**And** `_make_output(findings)` produces a correctly structured `ValidatorOutput`

**Given** a custom validator class at a dotted path (e.g., `"my_app.validators.CustomValidator"`)
**When** I add this path to `ClaimValidatorSettings.rule_validators`
**Then** `ValidatorRegistry` lazily imports and instantiates the validator on first pipeline construction

**Given** an invalid dotted path in the validator list
**When** the registry attempts to load it
**Then** a `ConfigurationError` is raised with a clear message identifying the bad path

**Given** the `BaseValidator` contract
**When** a validator's `validate()` method is called
**Then** it is stateless (no instance state between calls), does not modify the claim (frozen model), and returns `ValidatorOutput` (never raises for validation failures)

**Given** a validator that raises an unexpected exception during `validate()`
**When** the pipeline catches it
**Then** it converts the exception to a `Finding(code="VALIDATOR_ERROR", severity=ERROR)` and continues

### Story 2.2: Completeness Validator

As a **developer**,
I want claims validated for required CMS-1500 field presence,
So that claims with missing mandatory fields are caught before submission.

**Acceptance Criteria:**

**Given** a claim with all required CMS-1500 fields populated
**When** `CompletenessValidator.validate(claim)` is called
**Then** the output contains zero findings

**Given** a claim missing required fields (e.g., no `billing_provider_npi`, no `diagnosis_codes`, no `lines`)
**When** `CompletenessValidator.validate(claim)` is called
**Then** the output contains one `Finding` per missing field with code `MISSING_FIELD`, severity `ERROR`, the specific `field_name`, and a suggestion to provide the field

**Given** a claim with empty string values for required fields
**When** `CompletenessValidator.validate(claim)` is called
**Then** empty strings are treated as missing and flagged

**Given** a claim with lines that have missing required line-level fields (e.g., no `procedure_code`)
**When** `CompletenessValidator.validate(claim)` is called
**Then** the finding includes the `line_number` identifying which line is incomplete

**Given** any finding produced by this validator
**When** I inspect the `message` field
**Then** it contains no PHI values — only field names and guidance

### Story 2.3: NPI Validator

As a **developer**,
I want NPI numbers validated using the Luhn check-digit algorithm,
So that claims with invalid provider identifiers are caught before submission.

**Acceptance Criteria:**

**Given** a claim with a valid NPI (e.g., `"1234567893"` — passes Luhn check)
**When** `NPIValidator.validate(claim)` is called
**Then** the output contains zero NPI-related findings

**Given** a claim with an invalid NPI (e.g., `"1234567890"` — fails Luhn check)
**When** `NPIValidator.validate(claim)` is called
**Then** the output contains a `Finding` with code `INVALID_NPI`, severity `ERROR`, field_name `billing_provider_npi`, and a suggestion to verify at `https://npiregistry.cms.hhs.gov`

**Given** a claim with an NPI that is not exactly 10 digits
**When** `NPIValidator.validate(claim)` is called
**Then** the output contains a finding about invalid NPI format

**Given** a claim with both billing and rendering provider NPIs
**When** `NPIValidator.validate(claim)` is called
**Then** both NPIs are validated independently with appropriate field_name on each finding

**Given** the NPI value `"1234567890"` in the finding
**When** I inspect the `message` field
**Then** it does NOT contain the actual NPI value (no PHI in messages)

### Story 2.4: Subscriber ID & Demographics Validators

As a **developer**,
I want subscriber IDs and patient demographics validated for consistency,
So that claims with missing insurance info or contradictory demographics are caught.

**Acceptance Criteria:**

**Given** a claim with a valid subscriber/insurance ID
**When** `SubscriberIDValidator.validate(claim)` is called
**Then** the output contains zero subscriber-related findings

**Given** a claim with a missing or empty subscriber ID
**When** `SubscriberIDValidator.validate(claim)` is called
**Then** the output contains a `Finding` with code `MISSING_SUBSCRIBER_ID`, severity `ERROR`

**Given** a claim with consistent demographics (valid DOB, gender, patient relationship)
**When** `DemographicsValidator.validate(claim)` is called
**Then** the output contains zero demographics-related findings

**Given** a claim with a date of birth in the future
**When** `DemographicsValidator.validate(claim)` is called
**Then** the output contains a finding with code `INVALID_DOB` and severity `ERROR`

**Given** a claim where patient relationship is "self" but subscriber and patient details differ
**When** `DemographicsValidator.validate(claim)` is called
**Then** the output contains a finding flagging the inconsistency with severity `WARNING`

**Given** any demographics finding
**When** I inspect the `message`
**Then** it references field names (e.g., "patient_dob") but never actual DOB values

### Story 2.5: Coding Validator

As a **developer**,
I want diagnosis and procedure codes validated against bundled code tables,
So that claims with invalid ICD-10, CPT/HCPCS codes, or inconsistent pointers are caught.

**Acceptance Criteria:**

**Given** a claim with valid ICD-10-CM diagnosis codes that exist in the bundled table
**When** `CodingValidator.validate(claim)` is called
**Then** zero diagnosis code findings are produced

**Given** a claim with an ICD-10 code not in the bundled table (e.g., `"Z99.99"`)
**When** `CodingValidator.validate(claim)` is called
**Then** a `Finding` with code `INVALID_DIAGNOSIS_CODE`, severity `ERROR`, and the specific `field_name` is produced

**Given** a claim with an ICD-10 code in wrong format (e.g., missing decimal, too short)
**When** `CodingValidator.validate(claim)` is called
**Then** a `Finding` about invalid code format is produced

**Given** a claim line with a CPT/HCPCS procedure code
**When** `CodingValidator.validate(claim)` is called
**Then** the code format is validated (5 characters for CPT, alphanumeric for HCPCS)
**And** modifier format is validated if modifiers are present

**Given** a claim line with diagnosis pointers referencing non-existent diagnosis positions
**When** `CodingValidator.validate(claim)` is called
**Then** a `Finding` with code `INVALID_DIAGNOSIS_POINTER`, severity `ERROR`, and the `line_number` is produced

**Given** a claim where a diagnosis code exists but no line references it
**When** `CodingValidator.validate(claim)` is called
**Then** a `Finding` with code `UNREFERENCED_DIAGNOSIS`, severity `WARNING` is produced

### Story 2.6: Monetary & Duplicate Validators

As a **developer**,
I want charge amounts validated and duplicate lines detected,
So that claims with financial errors or redundant lines are caught.

**Acceptance Criteria:**

**Given** a claim where all line charge amounts are positive
**When** `MonetaryValidator.validate(claim)` is called
**Then** the output contains zero monetary findings

**Given** a claim with a line that has zero or negative charge amount
**When** `MonetaryValidator.validate(claim)` is called
**Then** a `Finding` with code `INVALID_CHARGE_AMOUNT`, severity `ERROR`, and `line_number` is produced

**Given** a claim where line charges do not sum to the total charge (if total is provided)
**When** `MonetaryValidator.validate(claim)` is called
**Then** a `Finding` with code `CHARGE_TOTAL_MISMATCH`, severity `ERROR` is produced

**Given** a claim with no duplicate lines
**When** `DuplicateValidator.validate(claim)` is called
**Then** the output contains zero duplicate findings

**Given** a claim with two lines having the same procedure code, modifiers, and service date
**When** `DuplicateValidator.validate(claim)` is called
**Then** a `Finding` with code `DUPLICATE_LINE`, severity `WARNING`, and `line_number` identifying both lines is produced

### Story 2.7: Timely Filing Validator

As a **developer**,
I want service dates validated for consistency and timely filing deadlines checked,
So that claims with date errors or past-deadline submissions are caught.

**Acceptance Criteria:**

**Given** a claim with consistent dates (service date before filing date, service date after DOB)
**When** `TimelyFilingValidator.validate(claim)` is called
**Then** the output contains zero date-related findings

**Given** a claim with a service date in the future
**When** `TimelyFilingValidator.validate(claim)` is called
**Then** a `Finding` with code `FUTURE_SERVICE_DATE`, severity `ERROR` is produced

**Given** a claim with a service date before the patient's DOB
**When** `TimelyFilingValidator.validate(claim)` is called
**Then** a `Finding` with code `SERVICE_BEFORE_DOB`, severity `ERROR` is produced

**Given** a claim filed beyond the payer's timely filing deadline (e.g., Medicare 365 days)
**When** `TimelyFilingValidator.validate(claim)` is called
**Then** a `Finding` with code `TIMELY_FILING_EXCEEDED`, severity `ERROR`, and a suggestion with the payer's deadline is produced

**Given** a claim with a payer that has a custom timely filing limit configured
**When** the validator checks the deadline
**Then** it uses the configured limit instead of the default
**And** falls back to the bundled `timely_filing.json` defaults if no custom limit is set

**Given** a claim with `service_date_from` after `service_date_to` on a line
**When** `TimelyFilingValidator.validate(claim)` is called
**Then** a `Finding` with code `INVALID_DATE_RANGE`, severity `ERROR`, and `line_number` is produced

### Story 2.8: Validation Pipeline & Top-Level API

As a **developer**,
I want to call `validate(claim_dict)` and get a complete pipeline result,
So that I can validate claims with a single function call using zero configuration.

**Acceptance Criteria:**

**Given** a valid claim dictionary
**When** I call `validate(claim_dict)`
**Then** a `PipelineResult` is returned with `passed=True` and an empty findings list
**And** the call requires zero configuration, zero API keys, and zero network calls

**Given** a claim dictionary with multiple validation issues
**When** I call `validate(claim_dict)`
**Then** all 8 rule-based validators run and findings are aggregated into a single `PipelineResult`
**And** findings are ordered by severity (ERROR first) then validator order

**Given** a `ClaimData` Pydantic model instance
**When** I call `validate(claim_data)`
**Then** it accepts both dict and Pydantic model input seamlessly

**Given** a `ClaimValidatorSettings` with a custom validator list
**When** I call `ValidationPipeline.from_settings(settings)` then `pipeline.run(claim)`
**Then** only the configured validators execute

**Given** a developer wanting programmatic pipeline construction
**When** they use `ValidationPipeline.builder().add(NPIValidator).add(CodingValidator).build()`
**Then** a pipeline with only those validators is created and functional

**Given** the two-phase pipeline design
**When** rule-based validation runs
**Then** Phase 1 (rule-based) completes with all findings aggregated
**And** Phase 2 (AI) is skipped when no AI config is provided (rule-based-only mode)

**Given** `validate()` is called with zero configuration
**When** I inspect the pipeline
**Then** all 8 default rule-based validators are loaded from `ClaimValidatorSettings` defaults

**Given** rule-based validation on a typical claim
**When** I measure execution time
**Then** it completes in under 50ms per claim

---

## Epic 3: AI-Powered Clinical Validation

Developer can add LLM-powered clinical validation using Anthropic, OpenAI, or any compatible endpoint. Claims are automatically de-identified (all 18 HIPAA identifiers stripped). AI catches clinical edge cases that rules miss.

### Story 3.1: HIPAA De-identification Engine

As a **developer**,
I want claims automatically de-identified before any LLM call,
So that I can use AI validation with zero risk of PHI leakage — guaranteed by the library.

**Acceptance Criteria:**

**Given** a `ClaimData` instance with full PHI (patient name, SSN, DOB, address, member ID, phone, email, etc.)
**When** `ClaimDeidentifier.deidentify(claim)` is called
**Then** a `DeidentifiedClaim` is returned with all 18 HIPAA identifiers stripped
**And** only clinically relevant, non-PHI data remains: codes, charges, payer ID, NPI, patient age, gender, state, service year

**Given** the 18 HIPAA identifier categories
**When** I run the de-identifier against test claims containing each identifier type
**Then** all 18 types are removed: names, geographic data (below state), dates (except year), phone/fax, email, SSN, medical record numbers, health plan beneficiary numbers, account numbers, certificate/license numbers, vehicle identifiers, device identifiers, URLs, IP addresses, biometric identifiers, full-face photos, any other unique number

**Given** a `DeidentifiedClaim` instance
**When** I check `claim.is_deidentified`
**Then** it returns `True`
**And** the type system (mypy/pyright) distinguishes `DeidentifiedClaim` from `ClaimData`

**Given** any code path that calls an LLM
**When** I trace the data flow
**Then** `BaseLLMClient.send_messages()` accepts only `DeidentifiedClaim` at the type level
**And** a runtime assertion `assert claim.is_deidentified` provides belt-and-suspenders protection

**Given** a claim with edge cases (PHI in unexpected fields, mixed PHI/clinical data)
**When** the de-identifier processes it
**Then** it errs on the side of stripping — false positive removal is acceptable, false negative (PHI leakage) is not

### Story 3.2: LLM Provider Abstraction & Factory

As a **developer**,
I want to use any supported LLM provider for AI validation by changing configuration only,
So that I can switch between Anthropic, OpenAI, or self-hosted models without code changes.

**Acceptance Criteria:**

**Given** AI configuration with `provider="anthropic"`, `api_key`, and `model`
**When** I call `get_llm_client(provider="anthropic", api_key="sk-...", model="claude-sonnet-4-5-20241022")`
**Then** an `AnthropicClient` instance is returned using the Anthropic SDK's Messages API

**Given** AI configuration with `provider="openai"`
**When** I call `get_llm_client(provider="openai", api_key="sk-...", model="gpt-4o")`
**Then** an `OpenAIClient` instance is returned using the OpenAI SDK's Chat Completions API

**Given** AI configuration with `provider="openai_compatible"` and a custom `base_url`
**When** I call `get_llm_client(provider="openai_compatible", api_key="...", model="llama3", base_url="http://localhost:11434/v1")`
**Then** an `OpenAICompatibleClient` instance is returned using httpx to call the OpenAI-compatible endpoint

**Given** the `BaseLLMClient` abstract base class
**When** a developer subclasses it and implements `send_messages(messages: list[Message]) -> str`
**Then** their custom provider integrates with the AI validation pipeline
**And** the factory can be extended to instantiate it

**Given** the `[ai]` extra is not installed
**When** I attempt to import LLM classes
**Then** a clear `ImportError` is raised explaining which extra to install (`pip install claim-validator[ai]`)

**Given** provider-specific extras (`[anthropic]`, `[openai]`)
**When** I install only `claim-validator[anthropic]`
**Then** only the Anthropic SDK is installed, and `AnthropicClient` works while `OpenAIClient` raises a clear import error

### Story 3.3: AI Validation Pipeline Integration

As a **developer**,
I want AI validators to run as the second phase of the pipeline with automatic de-identification,
So that I can get AI-powered clinical insights with zero manual PHI handling.

**Acceptance Criteria:**

**Given** a `ClaimValidatorSettings` with `ai_config` configured
**When** `validate(claim_dict, ai_config={"provider": "anthropic", "api_key": "sk-...", "model": "..."})` is called
**Then** Phase 1 (rule-based) runs first, then Phase 2 (AI) runs with de-identified claim data
**And** the `PipelineResult` contains findings from both phases

**Given** `skip_ai_on_rule_failure=True` (default) and rule-based validation produced ERROR findings
**When** the pipeline reaches the AI phase gate
**Then** AI validators are skipped entirely
**And** the `PipelineResult` includes only rule-based findings

**Given** `skip_ai_on_rule_failure=False` and rule-based validation produced ERROR findings
**When** the pipeline reaches the AI phase gate
**Then** AI validators still run and their findings are appended to the result

**Given** the LLM provider is unreachable or returns an error
**When** AI validators attempt to call the provider
**Then** the pipeline returns rule-based results plus a `Finding(code="AI_PROVIDER_ERROR", severity=WARNING)` with the error context
**And** no exception is propagated to the caller

**Given** the `BaseAIValidator` base class
**When** an AI validator is constructed by the pipeline
**Then** it receives a pre-configured `BaseLLMClient` instance via constructor injection
**And** `self._send_to_llm(messages)` helper is available for sending messages

**Given** any AI validator in the pipeline
**When** it receives claim data
**Then** the data is always a `DeidentifiedClaim` (de-identification happens once in the pipeline, before all AI validators)

### Story 3.4: AI Clinical Validators

As a **developer**,
I want AI validators that catch clinical edge cases rules miss — implausible diagnosis-procedure pairs, coverage concerns, and prior auth requirements,
So that I can reduce denials caused by clinical issues that deterministic rules can't detect.

**Acceptance Criteria:**

**Given** a de-identified claim with a clinically implausible diagnosis-procedure combination (e.g., CPT 59400 obstetric package for a male patient)
**When** `CodeValidationAI.validate(claim)` is called
**Then** a `Finding` with code `AI_CLINICAL_IMPLAUSIBILITY`, severity `WARNING`, specific `field_name`, and `line_number` is produced
**And** the suggestion explains why the combination is implausible

**Given** a de-identified claim with valid clinical coding
**When** `CodeValidationAI.validate(claim)` is called
**Then** zero AI clinical findings are produced

**Given** a de-identified claim with a service likely to be denied for medical necessity
**When** `CoverageCheckAI.validate(claim)` is called
**Then** a `Finding` with code `AI_COVERAGE_CONCERN`, severity `WARNING` is produced
**And** the suggestion describes the coverage concern and recommended documentation

**Given** a de-identified claim with a service likely requiring prior authorization
**When** `PriorAuthAI.validate(claim)` is called
**Then** a `Finding` with code `AI_PRIOR_AUTH_LIKELY`, severity `WARNING` is produced
**And** the suggestion recommends checking prior auth status before submission

**Given** each AI validator
**When** I inspect its implementation
**Then** it has per-validator prompt templates as class constants (system prompt, user prompt template)
**And** uses hybrid response parsing (structured JSON preferred, free-text regex fallback)

**Given** AI findings from any AI validator
**When** I inspect the findings
**Then** all AI finding codes are prefixed with `AI_` (e.g., `AI_CLINICAL_IMPLAUSIBILITY`, `AI_COVERAGE_CONCERN`, `AI_PRIOR_AUTH_LIKELY`)
**And** severity is always `WARNING` (AI findings are advisory, never authoritative ERROR)
**And** no PHI appears in any finding message or suggestion
