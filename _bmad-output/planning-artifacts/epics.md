---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-03-04'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/research/technical-clearinghouse-api-integration-research-2026-03-04.md'
---

# healthcare-claim-analyzer - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for healthcare-claim-analyzer v3.0 refactoring, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Shared Validators (FR1-FR9):**
- FR1: Single canonical NPI validator used by all modules
- FR2: Single canonical date validator (service date, DOB) used by all modules
- FR3: Single canonical member ID validator used by all modules
- FR4: Single canonical demographics validator (patient name, gender, DOB) used by all modules
- FR5: Single canonical diagnosis code validator (ICD-10 against bundled code table) used by all modules
- FR6: Single canonical procedure code validator (CPT/HCPCS against bundled code table) used by all modules
- FR7: Single canonical payer ID validator used by all modules
- FR8: Shared validators produce Finding objects in the same format regardless of invoking module
- FR9: Shared validators can be registered for specific pipeline stages via configuration

**Shared De-identification (FR10-FR13):**
- FR10: Single base de-identifier strips all 18 HIPAA identifiers
- FR11: Base de-identifier accepts domain-specific configuration for domain-specific fields
- FR12: De-identifier caps ages 90+ to 90 per HIPAA Safe Harbor
- FR13: De-identifier reduces dates to year-only before LLM consumption

**Shared Pipeline Engine (FR14-FR17):**
- FR14: Single configurable pipeline engine supports multi-phase execution (rule-based → clearinghouse → AI)
- FR15: Pipeline supports gating between phases (skip clearinghouse if rule-based fails)
- FR16: Pipeline produces per-phase results with execution timing
- FR17: Pipeline accepts different validator sets, clearinghouse clients, and AI interpreters per domain

**Shared Code Tables (FR18-FR20):**
- FR18: Unified code table access layer for ICD-10, HCPCS, taxonomy, payer directory, and service types
- FR19: Code tables loaded via lazy singleton with thread-safe locking
- FR20: Any module can look up any code table through the shared layer

**Unified Workflow Orchestrator (FR21-FR27):**
- FR21: process_claim(request) executes full sequential pipeline: Eligibility → PA determination → PA submission (if needed) → Claim validation
- FR22: Orchestrator accepts a single dict or typed model with all workflow data
- FR23: Orchestrator returns WorkflowResult with per-stage results (eligibility, prior_auth, claim_validation)
- FR24: Orchestrator performs PA determination from 271 response; runs PA submission only if required
- FR25: Orchestrator stops early on stage failure; reports failed stage via stopped_at
- FR26: Orchestrator tracks per-stage execution times
- FR27: Orchestrator supports validation passthrough — already-validated rules not re-run downstream

**Validation Passthrough (FR28-FR30):**
- FR28: Pipeline tracks which validators have run and their results
- FR29: Downstream stages query prior validation and skip redundant checks
- FR30: Standalone mode (not via orchestrator) runs full validator set per module

**Existing API Preservation (FR31-FR34):**
- FR31: validate(claim) standalone produces identical behavior to current implementation
- FR32: check_eligibility(request) standalone produces identical behavior to current implementation
- FR33: submit_prior_auth(request) standalone produces identical behavior to current implementation
- FR34: All 4 APIs accept both dict and typed Pydantic model input

**Result Models (FR35-FR37):**
- FR35: WorkflowResult contains: eligibility (EligibilityResult), prior_auth (PriorAuthResult | None), claim_validation (PipelineResult), stopped_at (stage name | None), stage_results (ordered list)
- FR36: WorkflowResult exposes per-stage execution time
- FR37: WorkflowResult exposes aggregate passed boolean (True only if all stages passed)

**HIPAA Compliance (FR38-FR40):**
- FR38: Shared de-identifier passes all existing HIPAA tests for claims, eligibility, and prior auth
- FR39: PHI does not persist in memory beyond a single API call
- FR40: Unified pipeline de-identifies before every LLM call — PHI-containing objects never reach AI phase

**Configuration (FR41-FR43):**
- FR41: Developers configure which shared validators run at each stage via settings
- FR42: Developers configure pipeline gating behavior via settings
- FR43: All existing CLAIM_VALIDATOR_* environment variables continue to work

**Clearinghouse Client Layer (FR44-FR55):**
- FR44: BaseClearinghouseClient ABC with submit_claim(), check_eligibility(), check_claim_status() abstract methods
- FR45: Factory function get_clearinghouse_client(provider, **config) for configuration-driven provider selection
- FR46: ClearinghouseError hierarchy — Auth, Validation, Timeout, Server subtypes under existing ClaimValidatorError
- FR47: Clearinghouse response models — SubmissionResult, ClearinghouseEligibilityResponse, ClaimStatusResponse as Pydantic models
- FR48: StediClient — JSON REST, API key auth, supports eligibility (270/271), professional claims (837P), institutional claims (837I), claim status (276/277), ERA (835)
- FR49: ClaimMDClient — REST with AccountKey auth, supports eligibility, claims upload (1-2000 per call), claim responses, ERA/835 retrieval
- FR50: WaystarClient — HMAC-SHA256 auth via HMACAuth(httpx.Auth), supports eligibility, claims submission, claim status
- FR51: Clearinghouse configuration via CLAIM_VALIDATOR_CLEARINGHOUSE_* env vars integrated into ClaimValidatorSettings
- FR52: Pipeline integration — clearinghouse clients wire into PipelineConfig.clearinghouse_client slot for multi-phase execution
- FR53: PHI flows to clearinghouse (trusted HIPAA-covered entity) but never to AI without de-identification
- FR54: Zero new pip dependencies — httpx, pydantic, hmac/hashlib already in project
- FR55: Data mapping — library Pydantic models (ClaimData, EligibilityRequest) translated to provider-specific JSON per client, responses normalized to shared models

### NonFunctional Requirements

**Performance (NFR1-NFR6):**
- NFR1: Rule-based validation <50ms per claim (no regression)
- NFR2: Import time <500ms (shared imports add no overhead)
- NFR3: Code table lookup <1ms (shared access adds zero measurable overhead)
- NFR4: process_claim() full workflow (rule-based only) <150ms (3 stages x 50ms)
- NFR5: Shared validator indirection <5ms overhead vs direct call
- NFR6: process_claim() memory footprint does not exceed sum of 3 individual calls

**Security (NFR7-NFR11):**
- NFR7: Zero PHI transmitted to any LLM
- NFR8: Zero PHI in logs, findings, exceptions, or error messages
- NFR9: PHI cleared from memory after each API call completes
- NFR10: All 18 HIPAA identifiers stripped — verified by automated tests per domain
- NFR11: No telemetry, analytics, or network calls from rule-based path

**Scalability (NFR12-NFR15):**
- NFR12: All shared validators stateless — thread-safe
- NFR13: Pipeline instances safe for concurrent use (no shared mutable state)
- NFR14: Code table singletons use threading.Lock for thread-safe initialization
- NFR15: O(n) linear scaling maintained

**Integration (NFR16-NFR20):**
- NFR16: BaseClearinghouseClient ABC unchanged — existing implementations work unmodified
- NFR17: BaseLLMClient ABC unchanged — existing providers work unmodified
- NFR18: ClaimValidatorSettings env var interface unchanged
- NFR19: Python 3.11, 3.12, 3.13 compatible
- NFR20: Linux, macOS, Windows

**Code Quality (NFR21-NFR27):**
- NFR21: Zero duplicate validation logic (measurable by grep/AST)
- NFR22: Test coverage >= current percentage
- NFR23: All existing tests pass or migrated with equivalent coverage
- NFR24: mypy strict — zero errors
- NFR25: ruff clean — zero warnings (line-length=100, rules E/F/I/N/W/UP)
- NFR26: Wheel size <15MB
- NFR27: All public classes and functions have docstrings

**Clearinghouse Integration (NFR28-NFR31):**
- NFR28: Clearinghouse clients thread-safe — stateless per request, httpx.Client connection pooling
- NFR29: Zero PHI in clearinghouse error messages, logs, or exception traces
- NFR30: Unit tests use httpx.MockTransport — no network calls, deterministic, fast
- NFR31: >90% unit test coverage per provider client

### Additional Requirements

**From Architecture (D34-D43):**
- Shared validators are pure functions with `field_name` and `code_prefix` parameters; domain validators are thin wrappers (D34)
- BaseDeidentifier with DeidentificationConfig dataclass; domain subclasses set config only (D35)
- BasePipeline parameterized by PipelineConfig; domains create config, never subclass run() (D36)
- ValidationContext dataclass carrying dict[str, ValidatorResult]; optional param on pipeline.run() (D37)
- WorkflowOrchestrator with Stage protocol (name, is_gate, should_skip, run); stages wrap domain pipelines (D38)
- All code tables consolidated in shared/code_tables/ and shared/data/ (D39)
- WorkflowResult is frozen Pydantic model with typed per-stage results (.eligibility, .prior_auth, .claim_validation) (D40)
- Domain modules become thin orchestration layers delegating to shared (D41)
- Workflow settings added flat to ClaimValidatorSettings (D42)
- Clean break at v3.0 — new internal import paths, no re-exports or deprecation shims (D43)
- No starter template needed — existing package refactoring with all tooling intact
- Implementation sequence from architecture: shared → claim refactor → eligibility refactor → PA refactor → passthrough → workflow → tests

**From PRD (Domain/Technical):**
- PHI dual-path preserved: clearinghouse receives raw PHI (covered entity), AI path strips PHI
- Zero PHI in findings — reference field names, never values
- Stateless validators — validate(input) -> output, no side effects
- Code tables remain bundled with lazy singleton + threading.Lock
- BaseClearinghouseClient ABC unchanged
- BaseLLMClient ABC unchanged
- Solo developer (aniket), existing test suite as safety net
- Incremental approach: shared → claim → eligibility → PA → workflow

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | Canonical NPI validator |
| FR2 | Epic 1 | Canonical date validator |
| FR3 | Epic 1 | Canonical member ID validator |
| FR4 | Epic 1 | Canonical demographics validator |
| FR5 | Epic 1 | Canonical diagnosis code validator |
| FR6 | Epic 1 | Canonical procedure code validator |
| FR7 | Epic 1 | Canonical payer ID validator |
| FR8 | Epic 1 | Consistent Finding format |
| FR9 | Epic 1 | Stage registration via config |
| FR10 | Epic 2 | Base de-identifier for 18 identifiers |
| FR11 | Epic 2 | Domain-specific de-id config |
| FR12 | Epic 2 | HIPAA Safe Harbor age cap |
| FR13 | Epic 2 | Year-only dates for LLM |
| FR14 | Epic 2 | Configurable multi-phase pipeline |
| FR15 | Epic 2 | Phase gating |
| FR16 | Epic 2 | Per-phase timing |
| FR17 | Epic 2 | Domain-specific pipeline config |
| FR18 | Epic 1 | Unified code table access |
| FR19 | Epic 1 | Lazy singleton loading |
| FR20 | Epic 1 | Cross-module code table access |
| FR21 | Epic 4 | process_claim() sequential pipeline |
| FR22 | Epic 4 | Dict or typed model input |
| FR23 | Epic 4 | WorkflowResult per-stage results |
| FR24 | Epic 4 | PA determination from 271 |
| FR25 | Epic 4 | Early termination + stopped_at |
| FR26 | Epic 4 | Per-stage execution times |
| FR27 | Epic 4 | Validation passthrough in orchestrator |
| FR28 | Epic 4 | Pipeline tracks validator results |
| FR29 | Epic 4 | Downstream skips redundant checks |
| FR30 | Epic 4 | Standalone mode runs full set |
| FR31 | Epic 3 | validate() identical behavior |
| FR32 | Epic 3 | check_eligibility() identical behavior |
| FR33 | Epic 3 | submit_prior_auth() identical behavior |
| FR34 | Epic 3 | All APIs accept dict + Pydantic model |
| FR35 | Epic 4 | WorkflowResult structure |
| FR36 | Epic 4 | WorkflowResult per-stage timing |
| FR37 | Epic 4 | WorkflowResult aggregate passed |
| FR38 | Epic 2 | Shared de-id passes HIPAA tests |
| FR39 | Epic 2 | No PHI persistence beyond API call |
| FR40 | Epic 2 | De-identify before every LLM call |
| FR41 | Epic 3 | Configure validators per stage |
| FR42 | Epic 3 | Configure gating behavior |
| FR43 | Epic 3 | Existing env vars work |
| FR44 | Epic 5 | BaseClearinghouseClient ABC |
| FR45 | Epic 5 | Factory function get_clearinghouse_client() |
| FR46 | Epic 5 | ClearinghouseError hierarchy |
| FR47 | Epic 5 | Clearinghouse response models |
| FR48 | Epic 5 | StediClient implementation |
| FR49 | Epic 5 | ClaimMDClient implementation |
| FR50 | Epic 5 | WaystarClient implementation |
| FR51 | Epic 5 | Clearinghouse configuration env vars |
| FR52 | Epic 5 | Pipeline integration with PipelineConfig |
| FR53 | Epic 5 | PHI security for clearinghouse calls |
| FR54 | Epic 5 | Zero new pip dependencies |
| FR55 | Epic 5 | Data mapping library models to provider JSON |

## Epic List

### Epic 1: Shared Validation & Code Tables
Developers can maintain validation rules (NPI, date, member ID, demographics, diagnosis, procedure, payer ID) in a single canonical location with unified code table access — the foundation for single-point-of-change maintenance.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR18, FR19, FR20

### Epic 2: Shared De-identification & Pipeline Engine
A single HIPAA-compliant de-identifier and configurable pipeline engine replace 3 independent implementations. HIPAA test coverage verified from one base across all domains.
**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR38, FR39, FR40

### Epic 3: Domain Module Refactoring
All 3 existing APIs (validate, check_eligibility, submit_prior_auth) use shared internals with identical external behavior. Fix a validator bug in one file — all modules benefit. Config-driven validator registration per stage.
**FRs covered:** FR31, FR32, FR33, FR34, FR41, FR42, FR43

### Epic 4: Unified Workflow Pipeline
Developers call process_claim() for the full Eligibility → PA → Claim flow with validation passthrough, early termination, per-stage results, and WorkflowResult reporting.
**FRs covered:** FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR28, FR29, FR30, FR35, FR36, FR37

### Epic 5: Clearinghouse Client Integration
Developers can submit claims, verify eligibility, check claim status, and retrieve remittance through a unified BaseClearinghouseClient interface with pluggable providers (Stedi, Claim.MD, Waystar) — zero new dependencies, JSON-first, HIPAA-compliant PHI handling.
**FRs covered:** FR44, FR45, FR46, FR47, FR48, FR49, FR50, FR51, FR52, FR53, FR54, FR55

---

## Epic 1: Shared Validation & Code Tables

Developers can maintain validation rules (NPI, date, member ID, demographics, diagnosis, procedure, payer ID) in a single canonical location with unified code table access — the foundation for single-point-of-change maintenance.

### Story 1.1: Shared Package Skeleton and Core Validators

As a library maintainer,
I want NPI, date, member ID, and demographics validation as pure functions in `shared/validators/`,
So that these rules exist in exactly one canonical location.

**Acceptance Criteria:**

**Given** the shared/ package skeleton exists with `__init__.py` files
**When** `validate_npi(npi, field_name, code_prefix)` is called with a valid Luhn NPI
**Then** an empty findings list is returned
**And** calling with an invalid NPI returns a Finding with the correct code and field_name

**Given** `validate_date(value, field_name, code_prefix)` is called
**When** the date is a valid ISO date string
**Then** an empty findings list is returned
**And** invalid/future dates return appropriate findings

**Given** `validate_member_id(member_id, field_name, code_prefix)` is called
**When** the member ID is None or empty
**Then** a Finding with severity ERROR is returned

**Given** `validate_demographics(name, gender, dob, field_prefix, code_prefix)` is called
**When** required demographic fields are missing
**Then** individual findings per missing field are returned

**And** all functions are stateless (no side effects), have docstrings, pass mypy strict, and return `list[Finding]`
**And** FR1, FR2, FR3, FR4, FR8 are satisfied

### Story 1.2: Shared Code Tables Consolidation

As a library maintainer,
I want all code table loaders and data files consolidated in `shared/code_tables/` and `shared/data/`,
So that any module can look up any code table through one import path.

**Acceptance Criteria:**

**Given** ICD-10, HCPCS, taxonomy, payer directory, and service type JSON files exist in `shared/data/`
**When** `get_icd10_codes()`, `get_hcpcs_codes()`, `get_taxonomy_codes()`, `get_payer_directory()`, `get_service_types()` are called
**Then** the correct code table dict/set is returned

**Given** a code table has not been loaded yet
**When** its accessor function is called for the first time
**Then** it loads lazily via singleton with `threading.Lock`
**And** subsequent calls return the cached instance without re-loading

**Given** two threads call the same code table accessor simultaneously
**When** both attempt first-time initialization
**Then** only one thread performs the load; the other gets the cached result

**And** existing code table data files are moved (not copied) from `code_tables/`, `eligibility/code_tables/`, `prior_auth/code_tables/`
**And** FR18, FR19, FR20 are satisfied

### Story 1.3: Code-Table-Dependent Validators

As a library maintainer,
I want diagnosis, procedure, and payer ID validation as pure functions in `shared/validators/`,
So that ICD-10, CPT/HCPCS, and payer lookups are maintained in one place.

**Acceptance Criteria:**

**Given** `validate_diagnosis(codes, field_name, code_prefix)` is called with valid ICD-10 codes
**When** all codes exist in the shared ICD-10 code table
**Then** an empty findings list is returned
**And** invalid codes return findings with the specific invalid code in context

**Given** `validate_procedure(code, field_name, code_prefix)` is called
**When** the CPT/HCPCS code exists in the shared code table
**Then** an empty findings list is returned
**And** unknown procedure codes return a WARNING finding

**Given** `validate_payer_id(payer_id, field_name, code_prefix)` is called
**When** the payer ID exists in the shared payer directory
**Then** an empty findings list is returned
**And** unknown payer IDs return a WARNING finding

**And** all functions use shared code table accessors from Story 1.2
**And** FR5, FR6, FR7 are satisfied

### Story 1.4: Validator Stage Registration

As a library maintainer,
I want shared validators registerable for specific pipeline stages via configuration,
So that each domain can select which validators to run without hard-coding.

**Acceptance Criteria:**

**Given** a configuration dict maps stage names to lists of validator identifiers
**When** a pipeline stage is built from settings
**Then** only the configured validators are instantiated for that stage

**Given** a validator identifier references a shared validator pure function
**When** the stage runs
**Then** the shared function is invoked with the correct field_name and code_prefix for that domain

**Given** no explicit validator configuration is provided for a stage
**When** the pipeline falls back to defaults
**Then** the default set of validators for that domain is used (backward compatible)

**And** FR9 is satisfied

---

## Epic 2: Shared De-identification & Pipeline Engine

A single HIPAA-compliant de-identifier and configurable pipeline engine replace 3 independent implementations. HIPAA test coverage verified from one base across all domains.

### Story 2.1: BaseDeidentifier and Domain Configurations

As a library maintainer,
I want a single `BaseDeidentifier` class with domain-specific `DeidentificationConfig`,
So that HIPAA de-identification logic is maintained in one place across all 3 domains.

**Acceptance Criteria:**

**Given** `DeidentificationConfig` is a frozen dataclass with `name_fields`, `date_fields`, `id_fields`, `address_fields`, `age_field`, and `output_model`
**When** `BaseDeidentifier(config).deidentify(data)` is called
**Then** all configured PHI fields are stripped/redacted in the output model

**Given** an input record has a patient age of 92
**When** de-identification runs with age cap enabled
**Then** the output age is capped to 90 per HIPAA Safe Harbor (FR12)

**Given** an input record has dates (service_date, dob)
**When** de-identification runs
**Then** dates are reduced to year-only in the output (FR13)

**Given** domain configs for claims, eligibility, and prior auth are defined
**When** each config is passed to BaseDeidentifier
**Then** the correct domain-specific fields are stripped (different PHI field sets per domain)
**And** all 18 HIPAA identifiers are covered across all 3 configs

**And** domain classes (`ClaimDeidentifier`, `EligibilityDeidentifier`, `PriorAuthDeidentifier`) are thin subclasses that only set their config
**And** FR10, FR11, FR12, FR13 are satisfied

### Story 2.2: HIPAA Compliance Verification

As a security-conscious developer,
I want automated tests verifying the shared de-identifier strips all 18 HIPAA identifiers for all 3 domains,
So that no PHI reaches LLM providers or persists beyond a single API call.

**Acceptance Criteria:**

**Given** test inputs containing all 18 HIPAA identifier types for claims domain
**When** `ClaimDeidentifier.deidentify(claim)` is called
**Then** the output contains zero PHI — verified by checking every field in `DeidentifiedClaim`

**Given** test inputs containing all 18 HIPAA identifier types for eligibility domain
**When** `EligibilityDeidentifier.deidentify(response)` is called
**Then** the output contains zero PHI — verified by checking every field in `DeidentifiedEligibilityResponse`

**Given** test inputs containing all 18 HIPAA identifier types for prior auth domain
**When** `PriorAuthDeidentifier.deidentify(response)` is called
**Then** the output contains zero PHI — verified by checking every field in `DeidentifiedPriorAuthResponse`

**Given** a de-identified output object
**When** inspected for PHI leakage
**Then** findings reference field names only, never PHI values (FR40 — no PHI reaches AI phase)

**And** all existing HIPAA tests from the 3 domains pass against the shared implementation
**And** FR38, FR39, FR40 are satisfied

### Story 2.3: BasePipeline and PipelineConfig

As a library maintainer,
I want a single `BasePipeline` class parameterized by `PipelineConfig`,
So that multi-phase execution (rule-based → clearinghouse → AI) is implemented once and configured per domain.

**Acceptance Criteria:**

**Given** `PipelineConfig` specifies: validator list, clearinghouse client (optional), AI interpreter (optional), gating rules, and finding code prefix
**When** `BasePipeline(config).run(input)` is called
**Then** phases execute in order: rule-based validators → clearinghouse (if configured) → AI (if configured)

**Given** rule-based phase fails and `skip_clearinghouse_on_failure=True` in config
**When** the pipeline reaches the clearinghouse phase
**Then** it skips clearinghouse and AI, returning partial results with gating information (FR15)

**Given** a pipeline run completes
**When** the result is inspected
**Then** it contains per-phase results with execution timing in milliseconds (FR16)

**Given** three different `PipelineConfig` instances (claims, eligibility, prior auth)
**When** each is used to construct a `BasePipeline`
**Then** each pipeline uses its configured validators, clearinghouse client, and AI interpreter (FR17)

**Given** no clearinghouse client is configured
**When** the pipeline runs
**Then** it executes rule-based only (and AI if configured), gracefully skipping the clearinghouse phase

**And** `BasePipeline.run()` never subclassed by domains — domains only provide config (D36)
**And** FR14, FR15, FR16, FR17 are satisfied

---

## Epic 3: Domain Module Refactoring

All 3 existing APIs (validate, check_eligibility, submit_prior_auth) use shared internals with identical external behavior. Fix a validator bug in one file — all modules benefit. Config-driven validator registration per stage.

### Story 3.1: Refactor Claims Module

As a developer using `validate()`,
I want the claims module to use shared validators, de-identifier, and pipeline internally,
So that I get identical behavior with zero duplicate code.

**Acceptance Criteria:**

**Given** existing claim validators (NPI, date, member ID, demographics, diagnosis, procedure, payer ID)
**When** refactored to thin wrappers delegating to `shared/validators/` pure functions
**Then** each wrapper extracts the relevant field from `ClaimData`, calls the shared function, and wraps the result

**Given** `ClaimDeidentifier` is refactored to use `BaseDeidentifier` with claims config
**When** `validate(claim)` triggers AI phase
**Then** de-identification behavior is identical to current implementation

**Given** `ValidationPipeline` is replaced by `BasePipeline` with claims-specific `PipelineConfig`
**When** `validate(claim)` is called with the same input as before
**Then** the output `PipelineResult` is identical (same findings, same pass/fail)

**And** all existing claim validation tests pass without modification
**And** internal import paths change (D43) — no re-exports for old paths
**And** FR31 is satisfied

### Story 3.2: Refactor Eligibility Module

As a developer using `check_eligibility()`,
I want the eligibility module to use shared validators, de-identifier, and pipeline internally,
So that I get identical behavior with zero duplicate code.

**Acceptance Criteria:**

**Given** existing eligibility validators (payer ID, demographics, service type, date, member ID)
**When** refactored to thin wrappers delegating to `shared/validators/` pure functions
**Then** each wrapper extracts the relevant field from `EligibilityRequest`, calls the shared function with `ELIG_` code prefix, and wraps the result

**Given** `EligibilityDeidentifier` is refactored to use `BaseDeidentifier` with eligibility config
**When** `check_eligibility(request)` triggers AI phase
**Then** de-identification behavior is identical to current implementation

**Given** `EligibilityPipeline` is replaced by `BasePipeline` with eligibility-specific `PipelineConfig`
**When** `check_eligibility(request)` is called with the same input as before
**Then** the output `EligibilityResult` is identical (same findings, same eligible status, same pass/fail)

**And** all existing eligibility tests pass without modification
**And** FR32 is satisfied

### Story 3.3: Refactor Prior Auth Module

As a developer using `submit_prior_auth()`,
I want the prior auth module to use shared validators, de-identifier, and pipeline internally,
So that I get identical behavior with zero duplicate code.

**Acceptance Criteria:**

**Given** existing PA validators (NPI, member ID, DOB, diagnosis, procedure, service date, cross-field)
**When** refactored to thin wrappers delegating to `shared/validators/` pure functions
**Then** each wrapper extracts the relevant field from `PriorAuthRequest`, calls the shared function with `PA_` code prefix, and wraps the result

**Given** `PriorAuthDeidentifier` is refactored to use `BaseDeidentifier` with PA config
**When** `submit_prior_auth(request)` triggers AI phase
**Then** de-identification behavior is identical to current implementation

**Given** `PriorAuthPipeline` is replaced by `BasePipeline` with PA-specific `PipelineConfig`
**When** `submit_prior_auth(request)` is called with the same input as before
**Then** the output `PriorAuthResult` is identical (same findings, same approved status, same pass/fail)

**And** all existing prior auth tests pass without modification
**And** FR33 is satisfied

### Story 3.4: Configuration and API Finalization

As a developer configuring claim-validator,
I want per-stage validator registration, gating configuration, and dict/model input for all 4 APIs,
So that I can control pipeline behavior through settings without code changes.

**Acceptance Criteria:**

**Given** `ClaimValidatorSettings` has fields for validator lists per stage (claims, eligibility, PA)
**When** a developer sets `CLAIM_VALIDATOR_ELIGIBILITY_RULE_VALIDATORS` env var
**Then** only the specified validators run for the eligibility rule-based phase (FR41)

**Given** gating settings exist (`skip_ai_on_rule_failure`, `skip_clearinghouse_on_rule_failure`, `skip_clearinghouse_on_pa_failure`)
**When** configured via env vars
**Then** pipeline behavior changes accordingly (FR42)

**Given** all existing `CLAIM_VALIDATOR_*` environment variables
**When** used with the refactored codebase
**Then** behavior is identical to pre-refactoring (FR43)

**Given** any of the 4 APIs (`validate`, `check_eligibility`, `submit_prior_auth`, `process_claim`)
**When** called with a plain dict instead of a typed model
**Then** the dict is coerced to the appropriate Pydantic model and processed normally (FR34)

**And** FR34, FR41, FR42, FR43 are satisfied

---

## Epic 4: Unified Workflow Pipeline

Developers call process_claim() for the full Eligibility → PA → Claim flow with validation passthrough, early termination, per-stage results, and WorkflowResult reporting.

### Story 4.1: ValidationContext and Pipeline Passthrough

As a library maintainer,
I want pipelines to track which validators have run and skip redundant checks downstream,
So that NPI/demographics validated at eligibility are not re-run at PA or claim stages.

**Acceptance Criteria:**

**Given** `ValidationContext` is a dataclass with `results: dict[str, ValidatorResult]`
**When** `context.record("npi", result)` is called after NPI validation
**Then** `context.has_passed("npi")` returns True

**Given** a `BasePipeline.run(input, validation_context=ctx)` call with a populated context
**When** the pipeline encounters a validator that `ctx.has_passed()` for
**Then** that validator is skipped and its prior result is reused (FR29)

**Given** a `BasePipeline.run(input)` call with no validation_context (standalone mode)
**When** the pipeline runs
**Then** all configured validators execute — no skipping (FR30)

**Given** validators are skipped via passthrough
**When** the pipeline result is inspected
**Then** skipped validators' prior findings are included in the result (not silently dropped)

**And** FR28, FR29, FR30 are satisfied

### Story 4.2: WorkflowResult Model and Stage Protocol

As a developer consuming workflow results,
I want a typed `WorkflowResult` with per-stage results, timing, and aggregate status,
So that I can inspect exactly what happened at each stage of the pipeline.

**Acceptance Criteria:**

**Given** `WorkflowResult` is a frozen Pydantic model
**When** inspected
**Then** it contains: `eligibility: EligibilityResult`, `prior_auth: PriorAuthResult | None`, `claim_validation: PipelineResult`, `stopped_at: str | None`, `stage_results: list[StageResult]` (FR35)

**Given** a completed workflow
**When** `result.eligibility.execution_time` or `result.prior_auth.execution_time` is accessed
**Then** per-stage execution time in milliseconds is available (FR36)

**Given** a workflow where all stages passed
**When** `result.passed` is accessed
**Then** it returns True
**And** if any stage failed, `result.passed` returns False (FR37)

**Given** `Stage` is a Protocol with `name: str`, `is_gate: bool`, `should_skip()`, `run()`
**When** a class implements the Stage protocol
**Then** it can be used by the WorkflowOrchestrator

**And** FR35, FR36, FR37 are satisfied

### Story 4.3: WorkflowOrchestrator and process_claim() API

As a developer building a healthcare platform,
I want to call `process_claim(request)` for the full Eligibility → PA → Claim flow,
So that I replace 200+ lines of orchestration glue with a single API call.

**Acceptance Criteria:**

**Given** `process_claim(request)` is called with a dict or typed model containing patient, payer, and procedure data
**When** the orchestrator executes
**Then** stages run in order: Eligibility → PA Determination → PA Submission (if needed) → Claim Validation (FR21, FR22)

**Given** the orchestrator completes all stages
**When** the result is returned
**Then** it is a `WorkflowResult` with per-stage results accessible via `.eligibility`, `.prior_auth`, `.claim_validation` (FR23)

**Given** eligibility fails (e.g., inactive coverage)
**When** the orchestrator evaluates the eligibility gate
**Then** it stops early, sets `stopped_at="eligibility"`, and does not run PA or claim stages (FR25)

**Given** the orchestrator runs
**When** each stage completes
**Then** execution time per stage is recorded (FR26)

**Given** `process_claim()` is called with a plain dict
**When** the dict is processed
**Then** it is coerced to the appropriate model and processed normally (FR22)

**And** `process_claim` is added to top-level `__init__.py` exports
**And** FR21, FR22, FR23, FR25, FR26 are satisfied

### Story 4.4: PA Determination and Validation Passthrough Integration

As a developer using the unified pipeline,
I want PA determined automatically from the 271 response and validation passthrough eliminating redundant checks,
So that the workflow is intelligent about what to run and what to skip.

**Acceptance Criteria:**

**Given** the eligibility stage returns an `EligibilityResult` with a 271 response
**When** the orchestrator evaluates PA determination
**Then** `determine_pa_required(eligibility_response)` is called and returns `PADeterminationResult` (FR24)

**Given** PA determination returns `required=False`
**When** the orchestrator processes the PA stage
**Then** the PA stage is skipped and `result.prior_auth` is None (FR24)

**Given** NPI and demographics were validated at the eligibility stage
**When** the PA stage runs
**Then** those validators are skipped via `ValidationContext` passthrough (FR27)

**Given** NPI, demographics, and member ID were validated at eligibility and PA stages
**When** the claim validation stage runs
**Then** those validators are skipped — only claim-specific validators execute (FR27)

**Given** the full pipeline runs with passthrough
**When** compared to running all 3 standalone APIs separately
**Then** total validator executions are fewer (no duplicates) while producing equivalent findings

**And** FR24, FR27 are satisfied

---

## Epic 5: Clearinghouse Client Integration

Developers can submit claims, verify eligibility, check claim status, and retrieve remittance through a unified BaseClearinghouseClient interface with pluggable providers (Stedi, Claim.MD, Waystar) — zero new dependencies, JSON-first, HIPAA-compliant PHI handling.

### Story 5.1: BaseClearinghouseClient ABC, Factory, Config, Exceptions, and Models

As a library maintainer,
I want an abstract clearinghouse client with factory, configuration, exception hierarchy, and shared response models,
So that all provider implementations follow a consistent contract and new providers can be added without modifying existing code.

**Acceptance Criteria:**

**Given** `BaseClearinghouseClient` is an ABC in `clearinghouse/base.py`
**When** inspected
**Then** it declares abstract methods: `submit_claim(claim_data: dict) -> SubmissionResult`, `check_eligibility(request: dict) -> ClearinghouseEligibilityResponse`, `check_claim_status(claim_ref: str) -> ClaimStatusResponse`, and abstract property `provider_name: str`

**Given** `get_clearinghouse_client(provider, **config)` is called with `provider="stedi"`
**When** the factory resolves the provider
**Then** it returns a `StediClient` instance configured with the provided credentials
**And** calling with an unknown provider raises `ClearinghouseError`

**Given** `ClearinghouseError` is defined in `clearinghouse/exceptions.py`
**When** inspected
**Then** it is a subclass of existing `ClaimValidatorError` with subtypes: `ClearinghouseAuthError` (401/403), `ClearinghouseValidationError` (4xx), `ClearinghouseTimeoutError`, `ClearinghouseServerError` (5xx)

**Given** response models `SubmissionResult`, `ClearinghouseEligibilityResponse`, `ClaimStatusResponse` exist in `clearinghouse/models/`
**When** constructed
**Then** they are frozen Pydantic models with provider-agnostic fields (status, reference_id, raw_response, errors)

**Given** `ClaimValidatorSettings` is extended with `clearinghouse_config: dict | None`
**When** env vars `CLAIM_VALIDATOR_CLEARINGHOUSE_PROVIDER`, `CLAIM_VALIDATOR_CLEARINGHOUSE_API_KEY`, etc. are set
**Then** `settings.clearinghouse_config` returns the assembled config dict

**And** zero new pip dependencies — only httpx, pydantic, hmac/hashlib (already available)
**And** the module structure matches: `clearinghouse/{__init__, base, factory, auth, exceptions}.py` + `models/` + `providers/`
**And** FR44, FR45, FR46, FR47, FR51, FR54 are satisfied

### Story 5.2: StediClient — JSON REST Integration

As a developer integrating with Stedi,
I want a `StediClient` implementing `BaseClearinghouseClient` with full Stedi API coverage,
So that I can submit claims, verify eligibility, check claim status, and retrieve ERA through the unified interface.

**Acceptance Criteria:**

**Given** `StediClient` is instantiated with an API key
**When** `client.check_eligibility(request)` is called with patient/payer/provider data
**Then** it translates the library's `EligibilityRequest` fields to Stedi's JSON format and POSTs to `https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3`
**And** the response is normalized to `ClearinghouseEligibilityResponse`

**Given** `StediClient.submit_claim(claim_data)` is called
**When** the claim data contains professional claim fields
**Then** it translates to Stedi's 837P JSON format and POSTs to the professional claims endpoint
**And** returns a `SubmissionResult` with acknowledgment status and reference ID
**And** includes `Idempotency-Key` header for safe retries

**Given** `StediClient.check_claim_status(claim_ref)` is called
**When** a valid claim reference is provided
**Then** it queries Stedi's claim status endpoint (276/277) and returns a `ClaimStatusResponse`

**Given** a Stedi API call returns HTTP 5xx
**When** the error is handled
**Then** one retry with 1s backoff is attempted before raising `ClearinghouseServerError`
**And** no PHI appears in the error message (NFR29)

**Given** unit tests use `httpx.MockTransport`
**When** all Stedi client tests run
**Then** zero network calls are made and all tests are deterministic (NFR30)

**And** auth uses API key in `Authorization` header
**And** FR48, FR53, FR55 are satisfied

### Story 5.3: ClaimMDClient — REST with AccountKey Auth

As a developer integrating with Claim.MD,
I want a `ClaimMDClient` implementing `BaseClearinghouseClient` with Claim.MD API coverage,
So that I can verify eligibility, upload claims, retrieve responses, and download ERA/835 reports.

**Acceptance Criteria:**

**Given** `ClaimMDClient` is instantiated with an AccountKey
**When** `client.check_eligibility(request)` is called
**Then** it translates to Claim.MD's form data format (PayerID, ProviderNPI, InsuredFirstName, etc.) and POSTs to `https://svc.claim.md/services/eligdata/`
**And** `AccountKey` is included in every request
**And** the response is normalized to `ClearinghouseEligibilityResponse`

**Given** `ClaimMDClient.submit_claim(claim_data)` is called
**When** the claim data contains one or more claims
**Then** it translates to Claim.MD's upload format and POSTs to `/services/upload/`
**And** returns a `SubmissionResult` with batch reference

**Given** `ClaimMDClient.check_claim_status(claim_ref)` is called
**When** a valid claim reference (ResponseID) is provided
**Then** it queries `/services/response/` with the reference and returns a `ClaimStatusResponse`

**Given** a Claim.MD API call returns an authentication error
**When** the error is handled
**Then** `ClearinghouseAuthError` is raised immediately (no retry)
**And** the error message contains no PHI

**Given** unit tests use `httpx.MockTransport`
**When** all Claim.MD client tests run
**Then** zero network calls are made and all tests are deterministic

**And** FR49, FR53, FR55 are satisfied

### Story 5.4: WaystarClient — HMAC-SHA256 Auth Integration

As a developer integrating with Waystar,
I want a `WaystarClient` implementing `BaseClearinghouseClient` with HMAC-SHA256 authentication,
So that I can submit claims, verify eligibility, and check claim status through the enterprise Waystar platform.

**Acceptance Criteria:**

**Given** `WaystarClient` is instantiated with API key and secret
**When** any API call is made
**Then** requests are signed using `HMACAuth(httpx.Auth)` — computing HMAC-SHA256 over `method\npath\ntimestamp\nbody_hash` and setting `Authorization: HMAC {api_key}:{signature}` + `X-Timestamp` headers

**Given** `WaystarClient.check_eligibility(request)` is called
**When** the request contains patient/payer/provider data
**Then** it translates to Waystar's JSON format and POSTs to the eligibility endpoint
**And** the response is normalized to `ClearinghouseEligibilityResponse`

**Given** `WaystarClient.submit_claim(claim_data)` is called
**When** the claim data is valid
**Then** it translates to Waystar's format, signs with HMAC, and submits
**And** returns a `SubmissionResult`

**Given** Waystar API documentation becomes available (requires portal access)
**When** exact endpoint URLs and request schemas are known
**Then** the client is updated with production-ready endpoint paths and field mappings

**Given** unit tests use `httpx.MockTransport`
**When** HMAC signing is tested
**Then** the signature matches expected output for known inputs (deterministic)

**And** `HMACAuth` is implemented in `clearinghouse/auth.py` as `httpx.Auth` subclass
**And** FR50, FR53, FR55 are satisfied
**And** NOTE: Full implementation depends on Waystar portal docs from aniket

### Story 5.5: Pipeline Integration and Orchestrator Wiring

As a developer using the unified pipeline,
I want clearinghouse clients automatically wired into the pipeline's clearinghouse phase,
So that `PipelineConfig.clearinghouse_client` works with any provider and the workflow orchestrator can invoke clearinghouse calls between rule-based and AI phases.

**Acceptance Criteria:**

**Given** `PipelineConfig` has a `clearinghouse_client: BaseClearinghouseClient | None` field
**When** a pipeline is constructed with `clearinghouse_client=StediClient(...)`
**Then** the clearinghouse phase calls `client.check_eligibility()` or `client.submit_claim()` depending on the pipeline domain

**Given** `PipelineConfig.clearinghouse_client` is None (default)
**When** the pipeline runs
**Then** the clearinghouse phase is gracefully skipped — rule-based and AI phases execute as before

**Given** the rule-based phase fails and `skip_clearinghouse_on_rule_failure=True`
**When** the pipeline reaches the clearinghouse phase
**Then** it is skipped (existing gating behavior preserved)

**Given** `process_claim()` is called with clearinghouse configured
**When** the workflow orchestrator runs the eligibility stage
**Then** the clearinghouse client is used for the actual 270/271 transaction
**And** the response feeds into PA determination and downstream stages

**Given** a clearinghouse call raises `ClearinghouseError`
**When** the pipeline catches it
**Then** it records the error as a finding and continues/stops based on gating config

**And** clearinghouse client is constructed from `settings.clearinghouse_config` via the factory
**And** FR52 is satisfied
