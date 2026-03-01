---
stepsCompleted: [1, 2, 3, 4]
completedAt: '2026-02-27'
status: 'extending'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
paExtensionStartedAt: '2026-03-01'
paExtensionScope: 'prior-authorization-module'
paExtensionStepsCompleted: [1, 2, 3, 4]
paExtensionStatus: 'complete'
paExtensionCompletedAt: '2026-03-01'
paInputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/project-context.md'
---

# Eligibility Verification Module - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the Eligibility Verification Module, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Eligibility Request Data Management (FR1-FR7)**

- FR1: Developer can create an eligibility request from a Python dict or EligibilityRequest model
- FR2: Developer can specify subscriber demographics (name, DOB, member ID, relationship to patient)
- FR3: Developer can specify provider identifiers (NPI, taxonomy code)
- FR4: Developer can specify payer identifier for the target insurance plan
- FR5: Developer can specify service type code(s) for the eligibility inquiry
- FR6: Developer can specify date of service or date range for the eligibility check
- FR7: Developer can specify patient information when patient differs from subscriber (dependent)

**Rule-Based Request Validation (FR8-FR15)**

- FR8: System can validate provider NPI using Luhn check-digit algorithm
- FR9: System can validate payer ID against a known payer directory
- FR10: System can validate subscriber demographics completeness (required fields present)
- FR11: System can validate service type codes against X12 standard code set
- FR12: System can validate date of service is present and logically valid (not future beyond reasonable range, not expired)
- FR13: System can validate member ID format against common payer patterns
- FR14: System can produce structured Finding objects for each validation failure with code, message, severity, field_name, and suggestion
- FR15: Developer can run rule-based validation without any external API keys or network access

**Clearinghouse Integration (FR16-FR22)**

- FR16: System can submit a validated eligibility request to Stedi JSON API
- FR17: System can receive and parse a 271 eligibility response from Stedi
- FR18: Developer can configure Stedi API credentials via environment variables
- FR19: Developer can switch between Stedi sandbox and production environments
- FR20: System can handle clearinghouse errors (network failures, timeouts, invalid responses) and return structured error information
- FR21: System can parse AAA rejection segments from 271 responses into structured error models
- FR22: Developer can implement a custom clearinghouse client by subclassing BaseClearinghouseClient

**Eligibility Response Parsing (FR23-FR29)**

- FR23: System can parse 271 response into structured EligibilityResponse model
- FR24: System can extract coverage status (active, inactive, unknown) from 271 response
- FR25: System can extract benefit information (copay, coinsurance, deductible) per service type
- FR26: System can extract coverage dates (effective date, termination date) from 271 response
- FR27: System can extract plan/group information from 271 response
- FR28: System can extract prior authorization requirements from 271 response
- FR29: System can provide raw Stedi JSON response alongside structured model for advanced users

**AI-Powered Response Interpretation (FR30-FR35)**

- FR30: System can de-identify eligibility response data before sending to LLM (strip all 18 HIPAA identifiers)
- FR31: System can generate a human-readable coverage summary from 271 response using configured LLM
- FR32: System can produce AI-generated findings with actionable insights about coverage, limitations, and requirements
- FR33: Developer can use any configured LLM provider (Anthropic, OpenAI, OpenAI-compatible) for interpretation
- FR34: Developer can skip AI interpretation and use only structured response parsing
- FR35: System can interpret AAA errors into human-readable explanations with suggested next steps

**Pipeline Orchestration (FR36-FR40)**

- FR36: Developer can call check_eligibility() as a single entry point for the full pipeline
- FR37: System can execute the three-phase pipeline: rule-based validation first, clearinghouse second, AI third
- FR38: System can skip the clearinghouse/AI phase if rule-based validation fails (configurable)
- FR39: Developer can configure which eligibility validators to include via settings
- FR40: System can return an EligibilityResult containing: eligible status, structured response, findings, AI summary, and raw response

**Configuration & Settings (FR41-FR44)**

- FR41: Developer can configure eligibility settings via CLAIM_VALIDATOR_ prefixed environment variables
- FR42: Developer can configure Stedi credentials (API key, environment) via settings
- FR43: Developer can configure LLM provider for eligibility interpretation (reuse existing AI config)
- FR44: Developer can enable/disable AI interpretation independently of clearinghouse submission

**Extensibility (FR45-FR47)**

- FR45: Developer can create custom eligibility validators by subclassing BaseValidator
- FR46: Developer can create custom clearinghouse clients by subclassing BaseClearinghouseClient
- FR47: Developer can register custom validators via dotted-path configuration (same pattern as claim validators)

### NonFunctional Requirements

**Performance (NFR1-NFR5)**

- NFR1: Rule-based validation phase completes in < 100ms for a single eligibility request
- NFR2: Library adds < 2 seconds overhead on top of Stedi clearinghouse round-trip latency
- NFR3: 271 response parsing (without AI) completes in < 50ms
- NFR4: Memory usage for a single eligibility check does not exceed 50MB
- NFR5: Library imports (from claim_validator import check_eligibility) complete in < 500ms

**Security & Privacy (NFR6-NFR10)**

- NFR6: All 18 HIPAA identifiers stripped from eligibility data before any LLM call — verified by automated tests
- NFR7: PHI never appears in log output, exception messages, or error tracebacks
- NFR8: Stedi API communication uses HTTPS/TLS 1.2+ exclusively
- NFR9: API keys and credentials are never hardcoded — environment variable or settings-based configuration only
- NFR10: No PHI stored in memory longer than the duration of a single check_eligibility() call

**Integration Reliability (NFR11-NFR14)**

- NFR11: Stedi integration handles HTTP 4xx/5xx errors with structured error responses (not raw exceptions)
- NFR12: Network timeout configurable with sensible default (30 seconds, matching CAQH CORE 20s + buffer)
- NFR13: LLM provider failure does not block returning structured 271 response (graceful degradation)
- NFR14: Invalid or unexpected 271 response fields handled gracefully — unparseable fields logged as warnings, not exceptions

**Code Quality (NFR15-NFR20)**

- NFR15: mypy strict mode passes with zero errors across all eligibility module code
- NFR16: ruff lint passes with zero warnings (line-length=100, py311 target)
- NFR17: Test coverage > 90% for all eligibility module code
- NFR18: All public APIs have type annotations (Pydantic models, function signatures, return types)
- NFR19: Zero breaking changes to existing validate() API or public models
- NFR20: All new dependencies are optional (rule-based eligibility works with zero additional deps)

**Documentation (NFR21-NFR23)**

- NFR21: All public classes and functions have docstrings
- NFR22: Quickstart example included that demonstrates end-to-end eligibility check
- NFR23: API reference documents all public models, their fields, and expected values

### Additional Requirements

**From Architecture — Eligibility Extension Context:**

- No starter template needed — brownfield extension of existing package
- Add `[stedi]` optional dependency extra to `pyproject.toml` with `httpx>=0.27`
- Extract NPI validation logic into shared `_npi_utils.py` utility for reuse across claim and eligibility modules
- `BaseValidator.validate()` uses `data: Any` type signature for dual-type support (ClaimData and EligibilityRequest)
- Include Stedi 271 response fixtures in `tests/test_eligibility/fixtures/` for testing

**From Architecture — Existing File Modifications:**

- `pyproject.toml` — Add `stedi` extra, update `all` extra
- `src/claim_validator/__init__.py` — Add eligibility re-exports
- `src/claim_validator/conf.py` — Add Stedi config and eligibility validator list settings
- `src/claim_validator/exceptions.py` — Add `ClearinghouseError` subclass
- `src/claim_validator/constants.py` — Add `CoverageStatus` enum

**From Architecture — Core Decisions (D14-D23):**

- D14: BaseClearinghouseClient ABC + factory — mirrors BaseLLMClient pattern
- D15: Flat EligibilityRequest, nested EligibilityResponse — frozen=True, strict=False
- D16: Separate EligibilityPipeline — three-phase (rule-based → clearinghouse → AI)
- D17: PHI dual-path — pipeline-level + type-driven enforcement (belt-and-suspenders)
- D18: StediClient — sync httpx.Client with context manager, 30s timeout
- D19: Payer directory — uncompressed JSON (~200KB), lazy singleton with threading.Lock
- D20: AAA error model — dual access (AAAError model + Finding objects)
- D21: EligibilityDeidentifier — separate class, same pattern as ClaimDeidentifier
- D22: EligibilityInterpreterAI — single AI validator for holistic 271 interpretation
- D23: Settings extension — flat fields added to ClaimValidatorSettings

**From Architecture — Implementation Patterns:**

- Finding code prefixes: ELIG_ (rule-based), CLEARINGHOUSE_ (infrastructure), AAA_REJECTION (rejections), AI_ELIG_ (AI findings)
- PHI dual-path: clearinghouse receives raw PHI (covered entity), AI path strips PHI via EligibilityDeidentifier
- Clearinghouse client contract: BaseClearinghouseClient ABC mirrors existing BaseLLMClient pattern
- Three-phase pipeline: rule-based → clearinghouse → AI (different from existing two-phase claim pipeline)
- 14-step implementation sequence defined in architecture

**From Architecture — Implementation Sequence:**

1. Eligibility models (D15)
2. Settings extension (D23)
3. Payer directory + service types (D19)
4. NPI utility extraction
5. Rule-based eligibility validators (5 new)
6. Clearinghouse abstraction (D14)
7. Stedi client (D18)
8. Response parser
9. Eligibility de-identifier (D21)
10. AI interpreter (D22)
11. Pipeline (D16, D17)
12. Top-level API — check_eligibility()
13. __init__.py re-exports
14. Test suite

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | Create eligibility request from dict or model |
| FR2 | Epic 1 | Specify subscriber demographics |
| FR3 | Epic 1 | Specify provider identifiers (NPI, taxonomy) |
| FR4 | Epic 1 | Specify payer identifier |
| FR5 | Epic 1 | Specify service type code(s) |
| FR6 | Epic 1 | Specify date of service or range |
| FR7 | Epic 1 | Specify patient info for dependents |
| FR8 | Epic 1 | Validate NPI via Luhn algorithm |
| FR9 | Epic 1 | Validate payer ID against directory |
| FR10 | Epic 1 | Validate subscriber demographics completeness |
| FR11 | Epic 1 | Validate service type codes (X12) |
| FR12 | Epic 1 | Validate date of service validity |
| FR13 | Epic 1 | Validate member ID format |
| FR14 | Epic 1 | Produce structured Finding objects |
| FR15 | Epic 1 | Rule-based works offline, no API keys |
| FR16 | Epic 2 | Submit request to Stedi JSON API |
| FR17 | Epic 2 | Receive and parse 271 response from Stedi |
| FR18 | Epic 2 | Configure Stedi credentials via env vars |
| FR19 | Epic 2 | Switch Stedi sandbox/production |
| FR20 | Epic 2 | Handle clearinghouse errors structurally |
| FR21 | Epic 2 | Parse AAA rejection segments |
| FR22 | Epic 2 | Custom clearinghouse via BaseClearinghouseClient |
| FR23 | Epic 2 | Parse 271 into EligibilityResponse |
| FR24 | Epic 2 | Extract coverage status |
| FR25 | Epic 2 | Extract benefit info (copay, coinsurance, deductible) |
| FR26 | Epic 2 | Extract coverage dates |
| FR27 | Epic 2 | Extract plan/group information |
| FR28 | Epic 2 | Extract prior authorization requirements |
| FR29 | Epic 2 | Provide raw JSON alongside structured model |
| FR30 | Epic 3 | De-identify response before LLM (18 HIPAA IDs) |
| FR31 | Epic 3 | Generate human-readable coverage summary via LLM |
| FR32 | Epic 3 | AI-generated findings with actionable insights |
| FR33 | Epic 3 | Use any LLM provider (Anthropic, OpenAI, compatible) |
| FR34 | Epic 3 | Skip AI, use structured parsing only |
| FR35 | Epic 3 | Interpret AAA errors into human-readable explanations |
| FR36 | Epic 1 | check_eligibility() single entry point |
| FR37 | Epic 1→2→3 | Three-phase pipeline (built progressively) |
| FR38 | Epic 1 | Skip clearinghouse on rule failure (configurable) |
| FR39 | Epic 1 | Configure which validators to include |
| FR40 | Epic 1→2 | EligibilityResult (grows with pipeline phases) |
| FR41 | Epic 1 | CLAIM_VALIDATOR_ env var configuration |
| FR42 | Epic 2 | Configure Stedi credentials via settings |
| FR43 | Epic 3 | Configure LLM provider for interpretation |
| FR44 | Epic 3 | Enable/disable AI independently |
| FR45 | Epic 1 | Custom validators via BaseValidator |
| FR46 | Epic 2 | Custom clearinghouse via BaseClearinghouseClient |
| FR47 | Epic 1 | Register custom validators via dotted-path config |

**Coverage: 47/47 FRs mapped (100%)**

## Epic List

### Epic 1: Eligibility Request Validation (Offline)
Developer can create `EligibilityRequest` models, validate them with 6 rule-based validators, and call `check_eligibility()` for offline validation. Bad NPIs, invalid payer IDs, incomplete demographics, unknown service types, invalid dates, and malformed member IDs are caught before any clearinghouse call. Zero API keys, zero network access needed.
**FRs covered:** FR1-FR15, FR36, FR38, FR39, FR40 (partial), FR41, FR45, FR47

### Epic 2: Stedi Clearinghouse Integration & 271 Response Parsing
Developer can submit validated requests to Stedi clearinghouse via `check_eligibility()` and receive structured `EligibilityResponse` with coverage status, benefits (copay, coinsurance, deductible), coverage dates, plan/group info, prior auth requirements, and AAA rejection errors. Raw JSON also available for advanced users.
**FRs covered:** FR16-FR29, FR37 (phase 2), FR40 (full result), FR42, FR46

### Epic 3: AI-Powered Eligibility Interpretation
Developer can enable AI interpretation to get human-readable coverage summaries, actionable insights, and plain-English AAA error explanations via `check_eligibility()`. PHI is automatically stripped before any LLM call. Full three-phase pipeline orchestrated with graceful degradation if LLM is unavailable.
**FRs covered:** FR30-FR35, FR37 (phase 3), FR43, FR44

---

## Epic 1: Eligibility Request Validation (Offline)

Developer can create `EligibilityRequest` models, validate them with 6 rule-based validators, and call `check_eligibility()` for offline validation. Bad NPIs, invalid payer IDs, incomplete demographics, unknown service types, invalid dates, and malformed member IDs are caught before any clearinghouse call. Zero API keys, zero network access needed.

### Story 1.1: Eligibility Data Models & Package Configuration

As a **developer**,
I want typed Pydantic models to represent eligibility requests and responses,
So that I have a validated, immutable data layer for eligibility verification that integrates with the existing claim-validator package.

**Acceptance Criteria:**

**Given** a valid eligibility request as a Python dictionary
**When** I construct `EligibilityRequest(**request_dict)` or `EligibilityRequest.model_validate(request_dict)`
**Then** a frozen, immutable instance is created with all fields validated
**And** string coercion works (e.g., `"1985-03-15"` → date)

**Given** an `EligibilityRequest` instance
**When** I access its fields
**Then** `provider_npi`, `provider_taxonomy`, `payer_id`, `subscriber_id`, `subscriber_first_name`, `subscriber_last_name`, `subscriber_dob`, `service_type_code`, and `date_of_service` are available
**And** optional dependent fields (`patient_first_name`, `patient_last_name`, `patient_dob`, `relationship_code`) are `None` when not provided

**Given** the response models
**When** I construct `EligibilityResponse`, `CoverageInfo`, `BenefitInfo`, `AAAError`
**Then** all are frozen Pydantic models with `strict=False`
**And** `EligibilityResponse` nests `CoverageInfo`, `list[BenefitInfo]`, `list[AAAError]`, and `raw_response: dict`

**Given** the `EligibilityResult` model
**When** I inspect its fields
**Then** it contains `eligible: bool | None`, `response: EligibilityResponse | None`, `findings: list[Finding]`, `ai_summary: str | None`, `passed: bool`, `raw_response: dict | None`, and `execution_time: float`
**And** `passed` returns `True` only when zero ERROR-severity findings exist

**Given** the `CoverageStatus` enum in `constants.py`
**When** I import it
**Then** it is a `StrEnum` with values `ACTIVE`, `INACTIVE`, `UNKNOWN`

**Given** the `exceptions.py` module
**When** I import `ClearinghouseError`
**Then** it is a subclass of `ClaimValidatorError`

**Given** the `ClaimValidatorSettings` in `conf.py`
**When** I inspect new fields
**Then** `stedi_api_key`, `stedi_environment`, `eligibility_rule_validators`, `skip_clearinghouse_on_rule_failure`, and `skip_ai` are available with sensible defaults
**And** all use `CLAIM_VALIDATOR_` env prefix

**Given** the `pyproject.toml`
**When** I inspect optional extras
**Then** a `stedi` extra exists with `httpx>=0.27`
**And** the `all` extra includes `stedi`

### Story 1.2: Payer Directory & Service Type Code Tables

As a **developer**,
I want to look up payer IDs and service type codes against bundled reference data,
So that eligibility validators can verify these values offline with zero network calls.

**Acceptance Criteria:**

**Given** the installed package
**When** I call `get_payer_directory()` with a valid payer ID (e.g., `"60054"`)
**Then** it confirms the payer ID exists and returns payer information
**And** the first lookup loads the JSON file; subsequent lookups return the cached in-memory dict

**Given** the payer directory data
**When** I inspect `eligibility/data/payer_directory.json`
**Then** it contains ~3,400 payer entries keyed by payer ID for O(1) lookup

**Given** the installed package
**When** I call `get_service_types()` with a valid X12 service type code (e.g., `"30"` for health benefit plan coverage)
**Then** it confirms the code exists and returns the service type description

**Given** the service types data
**When** I inspect `eligibility/data/service_types.json`
**Then** it contains the standard X12 service type code set

**Given** two threads calling `get_payer_directory()` concurrently
**When** both trigger the first load simultaneously
**Then** the data is loaded exactly once (double-check locking with `threading.Lock`)
**And** both threads receive correct results

**Given** any code table lookup with a non-existent code
**When** I query it
**Then** `None` or `False` is returned (no exception raised)

### Story 1.3: NPI Utility Extraction & First Validators (Payer ID, Demographics)

As a **developer**,
I want eligibility requests validated for NPI correctness, payer ID existence, and subscriber demographics completeness,
So that requests with invalid providers, unknown payers, or missing subscriber info are caught before reaching the clearinghouse.

**Acceptance Criteria:**

**Given** the existing `NPIValidator` in the claim validation module
**When** NPI validation logic is extracted
**Then** a shared `_validate_npi(npi: str) -> list[Finding]` utility exists in `validators/rule_based/_npi_utils.py`
**And** both the existing claim `NPIValidator` and the new eligibility pipeline call the same utility
**And** no duplication of Luhn check-digit logic

**Given** an `EligibilityRequest` with a valid NPI (passes Luhn check)
**When** rule-based validation runs
**Then** zero NPI-related findings are produced

**Given** an `EligibilityRequest` with an invalid NPI (fails Luhn check or wrong length)
**When** rule-based validation runs
**Then** a `Finding` with code `ELIG_INVALID_NPI`, severity `ERROR`, field_name `provider_npi` is produced
**And** the finding message contains no PHI — only field names and guidance

**Given** an `EligibilityRequest` with a payer ID that exists in the payer directory
**When** `PayerIDValidator.validate(request)` is called
**Then** zero payer-related findings are produced

**Given** an `EligibilityRequest` with a payer ID NOT in the payer directory
**When** `PayerIDValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_INVALID_PAYER`, severity `ERROR`, field_name `payer_id`, and suggestion to verify at Stedi payer list is produced

**Given** an `EligibilityRequest` with all required subscriber fields present (first name, last name, DOB, subscriber ID)
**When** `EligibilityDemographicsValidator.validate(request)` is called
**Then** zero demographics findings are produced

**Given** an `EligibilityRequest` missing required subscriber fields
**When** `EligibilityDemographicsValidator.validate(request)` is called
**Then** a `Finding` per missing field with code `ELIG_MISSING_FIELD`, severity `ERROR`, and the specific `field_name` is produced

**Given** an `EligibilityRequest` with `relationship_code` not `"self"` but no patient fields provided
**When** `EligibilityDemographicsValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_MISSING_DEPENDENT_INFO`, severity `ERROR` is produced

### Story 1.4: Service Type, Date & Member ID Validators

As a **developer**,
I want eligibility requests validated for service type codes, date validity, and member ID format,
So that requests with unknown service types, illogical dates, or malformed member IDs are caught offline.

**Acceptance Criteria:**

**Given** an `EligibilityRequest` with a valid X12 service type code (e.g., `"30"`)
**When** `ServiceTypeValidator.validate(request)` is called
**Then** zero service type findings are produced

**Given** an `EligibilityRequest` with an unknown service type code
**When** `ServiceTypeValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_INVALID_SERVICE_TYPE`, severity `ERROR`, field_name `service_type_code` is produced

**Given** an `EligibilityRequest` with a valid date of service (present, not unreasonably far in the future)
**When** `EligibilityDateValidator.validate(request)` is called
**Then** zero date findings are produced

**Given** an `EligibilityRequest` with a date of service more than 1 year in the future
**When** `EligibilityDateValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_FUTURE_DATE`, severity `WARNING`, field_name `date_of_service` is produced

**Given** an `EligibilityRequest` with a date of service in the past beyond a reasonable range
**When** `EligibilityDateValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_PAST_DATE`, severity `WARNING` is produced

**Given** an `EligibilityRequest` with a missing date of service
**When** `EligibilityDateValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_MISSING_DATE`, severity `ERROR` is produced

**Given** an `EligibilityRequest` with a well-formatted member/subscriber ID
**When** `MemberIDValidator.validate(request)` is called
**Then** zero member ID findings are produced

**Given** an `EligibilityRequest` with an empty or suspiciously short subscriber ID
**When** `MemberIDValidator.validate(request)` is called
**Then** a `Finding` with code `ELIG_INVALID_MEMBER_ID`, severity `ERROR`, field_name `subscriber_id` is produced

**Given** any finding produced by these validators
**When** I inspect the `message` field
**Then** it references field names only, never actual PHI values

### Story 1.5: Eligibility Pipeline & check_eligibility() API

As a **developer**,
I want to call `check_eligibility()` as a single entry point that runs all rule-based validators and returns a structured result,
So that I can validate eligibility requests with one function call, zero configuration, and zero network access.

**Acceptance Criteria:**

**Given** a valid eligibility request dictionary
**When** I call `check_eligibility(request_dict)`
**Then** an `EligibilityResult` is returned with `passed=True`, empty findings list, and `eligible=None` (no clearinghouse call)
**And** the call requires zero configuration, zero API keys, and zero network calls

**Given** an eligibility request with multiple validation issues
**When** I call `check_eligibility(request_dict)`
**Then** all 6 rule-based validators run (NPI, payer ID, demographics, service type, date, member ID)
**And** findings are aggregated into a single `EligibilityResult` ordered by severity

**Given** an `EligibilityRequest` Pydantic model instance
**When** I call `check_eligibility(request_model)`
**Then** it accepts both dict and Pydantic model input seamlessly

**Given** `skip_clearinghouse_on_rule_failure=True` (default) and rule-based validation failed
**When** the pipeline finishes phase 1
**Then** the pipeline returns immediately without attempting clearinghouse or AI phases

**Given** custom validator configuration
**When** I call `check_eligibility(request, settings=ClaimValidatorSettings(eligibility_rule_validators=[...]))`
**Then** only the configured validators execute

**Given** a developer importing from the package
**When** they write `from claim_validator import check_eligibility`
**Then** the import succeeds and `check_eligibility` is available at the top level
**And** `EligibilityRequest`, `EligibilityResponse`, `EligibilityResult` are also importable from `claim_validator`

**Given** rule-based validation on a typical eligibility request
**When** I measure execution time
**Then** it completes in under 100ms

**Given** a custom validator subclassing `BaseValidator`
**When** registered via dotted-path in `eligibility_rule_validators` settings
**Then** it integrates into the eligibility pipeline and receives `EligibilityRequest` data

---

## Epic 2: Stedi Clearinghouse Integration & 271 Response Parsing

Developer can submit validated requests to Stedi clearinghouse via `check_eligibility()` and receive structured `EligibilityResponse` with coverage status, benefits (copay, coinsurance, deductible), coverage dates, plan/group info, prior auth requirements, and AAA rejection errors. Raw JSON also available for advanced users.

### Story 2.1: BaseClearinghouseClient Abstraction & Stedi Client

As a **developer**,
I want a pluggable clearinghouse client with Stedi as the first implementation,
So that I can submit eligibility requests to Stedi and switch to other clearinghouses in the future without code changes.

**Acceptance Criteria:**

**Given** the `BaseClearinghouseClient` abstract base class
**When** I inspect its contract
**Then** it defines `submit_eligibility(request: EligibilityRequest) -> dict`, `provider_name: str`, `environment: str`, `close() -> None`
**And** it supports context manager protocol (`__enter__`/`__exit__`)

**Given** a `StediClient` instance with valid API key and sandbox environment
**When** I call `client.submit_eligibility(request)` with a valid `EligibilityRequest`
**Then** it submits the request to Stedi's JSON API endpoint over HTTPS
**And** returns the raw 271 response as a Python dict

**Given** Stedi API credentials
**When** I construct `StediClient(api_key="key_...", environment="sandbox")`
**Then** it creates an `httpx.Client` with base URL for sandbox, `Authorization: Key` header, and 30-second default timeout

**Given** `environment="production"`
**When** I construct `StediClient(api_key="key_...", environment="production")`
**Then** it uses the production Stedi API base URL

**Given** a `StediClient` used as a context manager
**When** the `with` block exits
**Then** the underlying `httpx.Client` is properly closed

**Given** a network timeout or HTTP 5xx error from Stedi
**When** `submit_eligibility()` is called
**Then** a `ClearinghouseError` is raised with structured error information (status code, message, provider name)

**Given** an HTTP 4xx error from Stedi (e.g., invalid request, authentication failure)
**When** `submit_eligibility()` is called
**Then** a `ClearinghouseError` is raised with the Stedi error response details

**Given** the `get_clearinghouse_client(provider, **config)` factory function
**When** I call `get_clearinghouse_client("stedi", api_key="key_...", environment="sandbox")`
**Then** a `StediClient` instance is returned

**Given** a developer subclassing `BaseClearinghouseClient`
**When** they implement `submit_eligibility()` and set `provider_name`
**Then** their custom client can be used directly with `EligibilityPipeline`

### Story 2.2: 271 Response Parser & AAA Error Handling

As a **developer**,
I want 271 responses parsed into structured Pydantic models with AAA errors clearly surfaced,
So that I can programmatically access coverage status, benefits, copays, deductibles, and rejection reasons without parsing raw JSON.

**Acceptance Criteria:**

**Given** a raw 271 JSON response from Stedi indicating active coverage
**When** `parse_271_response(raw_dict)` is called
**Then** an `EligibilityResponse` is returned with `eligible=True`, populated `coverage` (status, effective date, plan name), and `benefits` list

**Given** a 271 response with benefit information
**When** I inspect `response.benefits`
**Then** each `BenefitInfo` contains `service_type_code`, `service_type_name`, `copay`, `coinsurance`, `deductible`, `in_network`, and `prior_auth_required` fields
**And** monetary values are parsed as `float | None`

**Given** a 271 response with coverage dates
**When** I inspect `response.coverage`
**Then** `CoverageInfo` contains `status` (CoverageStatus enum), `effective_date`, `termination_date`, `plan_name`, and `group_number`

**Given** a 271 response with prior authorization requirements for specific service types
**When** I inspect the relevant `BenefitInfo`
**Then** `prior_auth_required=True` is set for those service types

**Given** a 271 response containing AAA rejection segments (subscriber not found, invalid payer, etc.)
**When** `parse_271_response(raw_dict)` is called
**Then** `response.errors` contains `AAAError` objects with `rejection_code`, `follow_up_code`, and `message`
**And** `response.eligible` is `False` or `None` depending on the rejection type

**Given** a 271 response with unexpected or unmapped fields
**When** `parse_271_response(raw_dict)` is called
**Then** unmapped fields are silently ignored (no exception)
**And** a warning-level log is emitted for unrecognized segments

**Given** any `EligibilityResponse`
**When** I access `response.raw_response`
**Then** the complete unmodified Stedi JSON dict is available for advanced users

**Given** a 271 response parser
**When** I measure execution time on a typical response
**Then** parsing completes in under 50ms

### Story 2.3: Clearinghouse Pipeline Phase & Full Integration

As a **developer**,
I want `check_eligibility()` to orchestrate rule-based validation followed by Stedi clearinghouse submission and response parsing,
So that I get a complete `EligibilityResult` with eligibility status, structured response, and all findings from a single function call.

**Acceptance Criteria:**

**Given** a valid eligibility request and Stedi credentials
**When** I call `check_eligibility(request, stedi_api_key="key_...")`
**Then** Phase 1 (rule-based) runs first, then Phase 2 (clearinghouse) submits to Stedi
**And** the 271 response is parsed into `EligibilityResponse`
**And** an `EligibilityResult` is returned with `eligible` status, `response`, `findings`, and `raw_response` populated

**Given** rule-based validation fails and `skip_clearinghouse_on_rule_failure=True` (default)
**When** the pipeline reaches the phase 2 gate
**Then** the clearinghouse phase is skipped entirely
**And** `EligibilityResult` has `response=None`, `raw_response=None`, and only rule-based findings

**Given** rule-based validation fails and `skip_clearinghouse_on_rule_failure=False`
**When** the pipeline reaches the phase 2 gate
**Then** the clearinghouse phase still runs
**And** findings from both phases are combined in the result

**Given** a clearinghouse error (network timeout, HTTP error, Stedi downtime)
**When** the pipeline catches the `ClearinghouseError`
**Then** a `Finding` with code `CLEARINGHOUSE_ERROR`, severity `ERROR` is added to the result
**And** `EligibilityResult` has `response=None` and the error details in findings
**And** no unhandled exception propagates to the caller

**Given** a 271 response with AAA rejection segments
**When** the pipeline processes the response
**Then** `AAAError` models are in `result.response.errors`
**And** corresponding `Finding` objects with code `AAA_REJECTION` are in `result.findings`
**And** both provide the rejection reason code and human-readable message

**Given** Stedi credentials configured via environment variable `CLAIM_VALIDATOR_STEDI_API_KEY`
**When** I call `check_eligibility(request)` without explicit credentials
**Then** the pipeline reads credentials from settings (env vars)

**Given** no Stedi credentials configured and no explicit credentials passed
**When** I call `check_eligibility(request)`
**Then** only rule-based validation runs (phase 1 only)
**And** `EligibilityResult` has `response=None` — no clearinghouse call attempted

**Given** the full rule-based + clearinghouse pipeline
**When** I measure library overhead (excluding Stedi network latency)
**Then** it adds less than 2 seconds on top of the Stedi round-trip

---

## Epic 3: AI-Powered Eligibility Interpretation

Developer can enable AI interpretation to get human-readable coverage summaries, actionable insights, and plain-English AAA error explanations via `check_eligibility()`. PHI is automatically stripped before any LLM call. Full three-phase pipeline orchestrated with graceful degradation if LLM is unavailable.

### Story 3.1: Eligibility De-identification Engine

As a **developer**,
I want eligibility response data automatically de-identified before any LLM call,
So that I can use AI interpretation with zero risk of PHI leakage — guaranteed by the library.

**Acceptance Criteria:**

**Given** an `EligibilityResponse` with full PHI (subscriber name, DOB, member ID, group-specific identifiers)
**When** `EligibilityDeidentifier.deidentify(response)` is called
**Then** a `DeidentifiedEligibilityResponse` is returned with all 18 HIPAA identifiers stripped
**And** only safe data remains: payer ID, service type codes, benefit amounts, copay/coinsurance values, deductible amounts, coverage dates (year only), plan type codes

**Given** the 18 HIPAA identifier categories
**When** I run the de-identifier against test responses containing each identifier type
**Then** all are stripped: subscriber name, DOB (replaced with year only), member ID, address, SSN, account numbers, group-specific identifiers, and all other HIPAA-defined identifiers

**Given** a `DeidentifiedEligibilityResponse` instance
**When** I check its type
**Then** mypy/pyright distinguishes it from `EligibilityResponse` at the type level
**And** the type system prevents accidentally passing raw `EligibilityResponse` to LLM-facing functions

**Given** an `EligibilityResponse` with AAA errors containing subscriber-identifying information
**When** `EligibilityDeidentifier.deidentify(response)` is called
**Then** PHI in error messages is also stripped while preserving rejection codes and follow-up codes

**Given** edge cases (PHI embedded in unexpected response fields, mixed PHI/clinical data)
**When** the de-identifier processes them
**Then** it errs on the side of stripping — false positive removal is acceptable, false negative (PHI leakage) is not

**Given** a comprehensive PHI leak test suite
**When** run against `EligibilityDeidentifier`
**Then** all tests pass confirming zero PHI in the de-identified output
**And** tests cover all 18 HIPAA identifier categories

### Story 3.2: AI Eligibility Interpreter & Full Pipeline

As a **developer**,
I want AI-powered interpretation that turns cryptic 271 data into human-readable coverage summaries and actionable AAA error explanations,
So that my application can display clear eligibility information without my team learning X12 segment semantics.

**Acceptance Criteria:**

**Given** a de-identified eligibility response with active coverage and benefits
**When** `EligibilityInterpreterAI` processes it via the configured LLM
**Then** `ai_summary` contains a human-readable coverage summary (e.g., "Patient has $40 copay for office visits, $2,500 annual deductible with $1,847 remaining, prior auth required for imaging")
**And** AI-generated `Finding` objects with code prefix `AI_ELIG_` provide actionable insights about coverage limitations and requirements

**Given** a de-identified eligibility response with AAA rejection errors
**When** `EligibilityInterpreterAI` processes it
**Then** the AI interprets rejection codes into plain-English explanations with suggested next steps (e.g., "Patient's coverage under plan XYZ terminated — suggest verifying with patient for updated insurance information")

**Given** AI configuration with `provider="anthropic"` (or `"openai"` or `"openai_compatible"`)
**When** I call `check_eligibility(request, stedi_api_key="...", ai_config={"provider": "anthropic", "api_key": "sk-..."})`
**Then** the full three-phase pipeline executes: rule-based → clearinghouse → AI interpretation
**And** `EligibilityResult` contains `eligible`, `response`, `findings` (from all phases), `ai_summary`, and `raw_response`

**Given** `skip_ai=True` in settings or no `ai_config` provided
**When** I call `check_eligibility(request, stedi_api_key="...")`
**Then** the AI phase is skipped entirely
**And** `EligibilityResult` has `ai_summary=None` and only rule-based + clearinghouse findings

**Given** the LLM provider is unreachable or returns an error
**When** the AI phase attempts to call the provider
**Then** the pipeline returns the structured `EligibilityResponse` from phase 2 plus a `Finding(code="AI_ELIG_PROVIDER_ERROR", severity=WARNING)`
**And** no exception propagates to the caller — graceful degradation

**Given** the de-identification step in the pipeline
**When** the AI phase begins
**Then** `EligibilityDeidentifier.deidentify()` runs before any LLM call
**And** only `DeidentifiedEligibilityResponse` data reaches the LLM provider

**Given** AI interpretation using any configured LLM provider
**When** I switch providers via configuration (e.g., from Anthropic to OpenAI)
**Then** the pipeline works identically with the new provider — no code changes needed

**Given** AI-generated findings
**When** I inspect them
**Then** all use `AI_ELIG_` code prefix, severity is always `WARNING` (advisory, not authoritative)
**And** no PHI appears in any finding message, suggestion, or the `ai_summary`

---

# Prior Authorization Module - Epic Breakdown

## Overview

This section provides the complete epic and story breakdown for the Prior Authorization Module, decomposing the requirements from the PA PRD and Architecture PA extension into implementable stories. The PA module completes the pre-claim workflow chain: eligibility (270/271) → PA determination → PA submission (278) → claim (837).

## Requirements Inventory

### Functional Requirements

**PA Determination from Eligibility (FR1-FR5)**

- FR1: Developer can determine if prior authorization is required by passing an eligibility response (dict or `EligibilityResponse`) to `determine_pa_required()`
- FR2: System can parse `authOrCertIndicator` field (Y/N/U) from 271 benefit information to determine PA requirement
- FR3: System can parse free-text `additionalInformation.description` from 271 responses for PA indicators
- FR4: System can resolve conflicts between `authOrCertIndicator` and free-text indicators (free-text takes precedence when it indicates PA required)
- FR5: Developer can access the determination result as a `PADeterminationResult` with `required` (bool), `confidence` (high/medium/low), and `reason` (human-readable string)

**PA Request Data Modeling (FR6-FR10)**

- FR6: Developer can construct a `PriorAuthRequest` from a Python dict with subscriber, patient, requester, diagnosis, and service line data
- FR7: Developer can construct a `PriorAuthRequest` directly using typed Pydantic model with field validation
- FR8: System can validate that all Pydantic models are immutable (`frozen=True`) after creation
- FR9: Developer can represent individual services within a PA request as `ServiceLine` objects with CPT/HCPCS code, quantity, and date range
- FR10: Developer can specify request category (AR/HS/SC/IN) and certification type (I/R/S/E) via typed enums

**Pre-Submission Rule-Based Validation (FR11-FR19)**

- FR11: System can validate requester NPI using Luhn check algorithm and return `PA_INVALID_NPI` finding on failure
- FR12: System can validate that subscriber member ID is present and non-empty
- FR13: System can validate patient date of birth is present and is a valid date
- FR14: System can validate ICD-10 diagnosis codes against bundled code tables and return `PA_INVALID_DIAGNOSIS` for unknown codes
- FR15: System can validate CPT/HCPCS procedure codes against bundled code tables and return `PA_INVALID_PROCEDURE` for unknown codes
- FR16: System can validate service dates are not in the past and are within a reasonable future range
- FR17: System can perform cross-field consistency checks (diagnosis-supports-procedure, gender/age-procedure compatibility) and return WARNING-level findings
- FR18: Developer can run rule-based validation with zero API keys and zero external network calls (fully offline)
- FR19: Developer can skip specific rule-based validators via `skip_rule_validators` configuration option

**Clearinghouse Integration (FR20-FR24)**

- FR20: Developer can implement a custom clearinghouse client by subclassing `BaseClearinghouseClient` and implementing `submit_prior_auth()`
- FR21: System can submit a validated `PriorAuthRequest` to a clearinghouse via the abstract client interface and receive a raw dict response
- FR22: System can raise `ClearinghouseError` for HTTP/network failures while returning business rejections (AAA segments) as normal responses
- FR23: System can enforce a configurable timeout on clearinghouse calls (default 30 seconds)
- FR24: Clearinghouse client can be used as a context manager with `__enter__`, `__exit__`, and `close()` methods

**278 Response Parsing (FR25-FR31)**

- FR25: Developer can parse a raw 278 JSON dict into a structured `PriorAuthResponse` model via `parse_278_response()`
- FR26: System can map all 7 HCR action codes to structured decisions: A1 (approved), A2 (partial approval), A3 (denied), A4 (pended), A6 (modified), CT (contact payer), NA (not required)
- FR27: System can extract authorization number from approved/partial/modified responses
- FR28: System can extract effective date range (start/end) from authorization decisions
- FR29: System can parse per-service-line decisions into `ServiceLineDecision` objects
- FR30: Developer can access convenience properties on `PriorAuthResponse`: `is_approved`, `is_denied`, `is_pended`, `authorization_number`, `decision_reason_description`
- FR31: System can handle missing or unexpected fields in 278 response gracefully (return None, not exception)

**AAA Error Handling (FR32-FR35)**

- FR32: System can parse AAA reject segments from 278 responses into `PriorAuthError` objects
- FR33: System can map top 20+ AAA reject reason codes (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4) to human-readable error messages
- FR34: System can provide suggested fixes alongside each AAA error message
- FR35: System can generate `AAA_PA_REJECTION` finding codes for each AAA error encountered

**PHI De-Identification (FR36-FR40)**

- FR36: System can strip all 18 HIPAA identifiers from PA request/response data before any LLM call via `PriorAuthDeidentifier`
- FR37: System can cap ages 90+ to 90 per HIPAA Safe Harbor
- FR38: System can reduce dates to year-only before sending to LLM
- FR39: System can enforce de-identification as a mandatory pipeline gate — if de-identification fails, AI phase must not execute
- FR40: System can ensure PHI does not persist in memory beyond a single `submit_prior_auth()` call

**AI-Powered Interpretation (FR41-FR46)**

- FR41: Developer can enable AI-powered response interpretation via `PriorAuthInterpreterAI` using existing LLM configuration (`CLAIM_VALIDATOR_AI_CONFIG`)
- FR42: System can generate a human-readable decision summary from HCR action codes and decision reason codes
- FR43: System can generate next-step recommendations for pended cases (A4) including likely documentation needed
- FR44: System can generate appeal strategy suggestions for denied cases (A3) based on decision reason codes
- FR45: System can produce AI findings with `AI_PA_` prefix codes at WARNING severity level
- FR46: System can include raw HCR/AAA codes alongside AI interpretation for verification

**Pipeline Orchestration (FR47-FR51)**

- FR47: Developer can submit a prior authorization through the complete three-phase pipeline via `submit_prior_auth()`
- FR48: System can orchestrate rule-based validation → clearinghouse submission → AI interpretation as sequential pipeline phases
- FR49: System can skip clearinghouse and AI phases when no clearinghouse client is configured (rule-based-only mode)
- FR50: System can skip AI phase when no LLM provider is configured (clearinghouse-only mode)
- FR51: Developer can access the pipeline result as `PriorAuthResult` with `approved`, `response`, `findings`, `ai_summary`, `passed`, `authorization_number`, `raw_response`, `execution_time`

**Finding Code System (FR52-FR56)**

- FR52: System can generate findings with `PA_` prefix for rule-based validation issues
- FR53: System can generate findings with `AI_PA_` prefix for AI interpretation results
- FR54: System can generate findings with `AAA_PA_REJECTION` prefix for AAA business rejections
- FR55: System can generate findings with `CLEARINGHOUSE_` prefix for infrastructure errors
- FR56: System can assign severity levels (ERROR, WARNING, INFO) to all findings using existing `FindingSeverity` enum

### NonFunctional Requirements

**Performance (NFR1-NFR6)**

- NFR1: Rule-based validation phase must complete in < 100ms for a single PA request (offline, no network calls)
- NFR2: Code table loading (ICD-10, CPT, AAA codes) must use lazy singleton pattern — first load < 500ms, subsequent lookups < 1ms
- NFR3: `parse_278_response()` must complete in < 50ms for a single 278 response dict
- NFR4: `determine_pa_required()` must complete in < 10ms for a single eligibility response
- NFR5: Pipeline overhead (orchestration, finding aggregation) must add < 20ms beyond individual phase execution times
- NFR6: Memory footprint of loaded code tables must not exceed 50MB

**Security & Privacy (NFR7-NFR15)**

- NFR7: All 18 HIPAA identifiers must be stripped by `PriorAuthDeidentifier` before any data reaches an LLM provider — verified by automated tests
- NFR8: De-identification must be a mandatory pipeline gate: if `PriorAuthDeidentifier` raises an exception, the AI phase must not execute under any circumstance
- NFR9: Clearinghouse communication must use TLS 1.2+ — `BaseClearinghouseClient` implementations must enforce TLS verification (no `verify=False`)
- NFR10: API keys and credentials must be sourced from environment variables only — never hardcoded, never in logs, never in exception messages
- NFR11: PHI must not appear in log output — clearinghouse request/response bodies must never be logged at any log level
- NFR12: PHI must not appear in exception messages or stack traces — error messages must reference field names, not field values
- NFR13: PHI must not persist in memory beyond a single `submit_prior_auth()` call — no module-level caching of patient data
- NFR14: Ages 90+ must be capped to 90 per HIPAA Safe Harbor before LLM path
- NFR15: Dates must be reduced to year-only before LLM path

**Reliability & Error Handling (NFR16-NFR21)**

- NFR16: Missing or unexpected fields in 278 response must return `None` or generate a WARNING finding — never raise an unhandled exception
- NFR17: Unmapped HCR action codes must generate a WARNING finding with the raw code value — never raise an exception
- NFR18: Unmapped AAA reject reason codes must generate a WARNING finding with the raw code value and a generic "Contact payer for details" message
- NFR19: Clearinghouse HTTP errors (timeout, connection refused, 5xx) must raise `ClearinghouseError` with a descriptive message — never expose raw HTTP response bodies
- NFR20: LLM provider errors (timeout, rate limit, API error) must be caught and result in AI phase skipping gracefully — rule-based and clearinghouse results must still be returned
- NFR21: Invalid input to `submit_prior_auth()` (wrong type, missing required fields) must raise `ValueError` with a clear message before any pipeline phase executes

**Integration Compatibility (NFR22-NFR28)**

- NFR22: PA module must not introduce any breaking changes to existing `validate()` or `check_eligibility()` public APIs
- NFR23: PA module must reuse existing `BaseLLMClient`, `LLMFactory`, and `CLAIM_VALIDATOR_AI_CONFIG` configuration — no parallel LLM configuration system
- NFR24: PA module must reuse existing `FindingSeverity` enum and finding model — no parallel finding system
- NFR25: PA module must reuse existing code table loading infrastructure (`claim_validator/data/`) with lazy singleton + `threading.Lock` pattern
- NFR26: New finding code prefixes (`PA_`, `AI_PA_`, `AAA_PA_REJECTION`, `CLEARINGHOUSE_`) must not conflict with existing prefixes (`CLM_`, `AI_`, `ELIG_`)
- NFR27: `PriorAuthRequest` must accept both dict and Pydantic model input (same as `validate()` and `check_eligibility()` patterns)
- NFR28: Default clearinghouse timeout must be 30 seconds (consistent with eligibility module)

**Code Quality & Maintainability (NFR29-NFR36)**

- NFR29: All `prior_auth/` module code must achieve > 90% test coverage
- NFR30: All code must pass mypy strict mode with zero errors
- NFR31: All code must pass ruff linting (line-length=100, rules E,F,I,N,W,UP) with zero warnings
- NFR32: All public classes and functions must have docstrings
- NFR33: All Pydantic models must use `frozen=True` (immutable after creation)
- NFR34: `parse_278_response()` must not modify the input dict (no side effects)
- NFR35: Module structure must mirror existing `claim_validator/eligibility/` layout for developer familiarity
- NFR36: Test structure must include dedicated `test_hipaa/` subdirectory verifying all 18 HIPAA identifier de-identification

### Additional Requirements

**From Architecture — PA Extension Context:**

- No starter template needed — brownfield extension of existing package
- ~30 source files, ~25 test files across `src/claim_validator/prior_auth/` and `tests/test_prior_auth/`
- 3 existing files modified: `__init__.py` (re-exports), `conf.py` (PA settings), `pyproject.toml` (version bump)

**From Architecture — Core Decisions (D24-D33):**

- D24: `BasePAClearinghouseClient` — subclass of existing `BaseClearinghouseClient` with `submit_prior_auth()` abstract method (non-breaking)
- D25: PA model design — flat `PriorAuthRequest`, nested `PriorAuthResponse` with `ServiceLineDecision` per-service-line
- D26: Separate `PriorAuthPipeline` — three-phase (rule-based → clearinghouse → AI), matching eligibility pattern
- D27: PHI dual-path — pipeline-level + type-driven enforcement via `PriorAuthDeidentifier` as mandatory gate
- D28: PA determination bridge — `determine_pa_required()` with duck-typed input (`dict | EligibilityResponse`), loose coupling
- D29: HCR action codes — `CertificationActionCode` StrEnum + `hcr_action_codes.json` description table, lazy singleton
- D30: AAA errors — `PriorAuthError` model + `Finding` objects (dual access, mirrors D20)
- D31: PA de-identifier — separate `PriorAuthDeidentifier` class, strips clinical justification free-text PII
- D32: AI interpretation — single `PriorAuthInterpreterAI` validator for holistic 278 interpretation
- D33: Settings — extend `ClaimValidatorSettings` with flat PA fields (`pa_rule_validators`, `pa_ai_validators`, `skip_clearinghouse_on_pa_failure`, `pa_skip_ai`)

**From Architecture — Implementation Patterns:**

- Finding code prefixes: `PA_` (rule-based), `AI_PA_` (AI), `AAA_PA_REJECTION` (rejections), `CLEARINGHOUSE_` (infrastructure)
- PHI dual-path: clearinghouse receives raw PHI (covered entity), AI path strips PHI via `PriorAuthDeidentifier`
- `BasePAClearinghouseClient` subclass of existing `BaseClearinghouseClient` — non-breaking extension
- Three-phase pipeline: rule-based → clearinghouse → AI (same as eligibility pattern)
- Cross-module bridge: `determine_pa_required()` accepts `dict | EligibilityResponse` via duck typing

**From Architecture — Implementation Sequence:**

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
14. Test suite

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR1 | Epic 1 | Determine PA required from eligibility response |
| FR2 | Epic 1 | Parse `authOrCertIndicator` (Y/N/U) |
| FR3 | Epic 1 | Parse free-text PA indicators |
| FR4 | Epic 1 | Resolve indicator vs free-text conflicts |
| FR5 | Epic 1 | `PADeterminationResult` with required, confidence, reason |
| FR6 | Epic 1 | Construct `PriorAuthRequest` from dict |
| FR7 | Epic 1 | Construct `PriorAuthRequest` from Pydantic model |
| FR8 | Epic 1 | Models immutable (`frozen=True`) |
| FR9 | Epic 1 | `ServiceLine` objects with CPT, quantity, dates |
| FR10 | Epic 1 | Request category and certification type enums |
| FR11 | Epic 1 | NPI Luhn validation → `PA_INVALID_NPI` |
| FR12 | Epic 1 | Member ID presence validation |
| FR13 | Epic 1 | DOB validation |
| FR14 | Epic 1 | ICD-10 diagnosis validation → `PA_INVALID_DIAGNOSIS` |
| FR15 | Epic 1 | CPT/HCPCS procedure validation → `PA_INVALID_PROCEDURE` |
| FR16 | Epic 1 | Service date validation |
| FR17 | Epic 1 | Cross-field consistency checks |
| FR18 | Epic 1 | Zero API keys / zero network (offline) |
| FR19 | Epic 1 | Skip validators via config |
| FR20 | Epic 3 | Custom clearinghouse via `BasePAClearinghouseClient` |
| FR21 | Epic 3 | Submit request, receive raw dict |
| FR22 | Epic 3 | `ClearinghouseError` for HTTP, AAA as normal responses |
| FR23 | Epic 3 | Configurable timeout (30s default) |
| FR24 | Epic 3 | Context manager support |
| FR25 | Epic 2 | Parse 278 JSON → `PriorAuthResponse` |
| FR26 | Epic 2 | Map all 7 HCR action codes |
| FR27 | Epic 2 | Extract authorization number |
| FR28 | Epic 2 | Extract effective date range |
| FR29 | Epic 2 | Parse per-service-line decisions |
| FR30 | Epic 2 | Convenience properties (`is_approved`, `is_denied`, etc.) |
| FR31 | Epic 2 | Handle missing/unexpected fields gracefully |
| FR32 | Epic 2 | Parse AAA segments → `PriorAuthError` |
| FR33 | Epic 2 | Map 20+ AAA codes to human-readable messages |
| FR34 | Epic 2 | Suggested fixes per AAA error |
| FR35 | Epic 2 | `AAA_PA_REJECTION` finding codes |
| FR36 | Epic 4 | Strip 18 HIPAA identifiers via `PriorAuthDeidentifier` |
| FR37 | Epic 4 | Cap ages 90+ to 90 |
| FR38 | Epic 4 | Dates to year-only before LLM |
| FR39 | Epic 4 | De-id as mandatory pipeline gate |
| FR40 | Epic 4 | PHI not persisted beyond single call |
| FR41 | Epic 4 | AI via existing LLM config |
| FR42 | Epic 4 | Human-readable decision summary |
| FR43 | Epic 4 | Next-step recommendations for pended (A4) |
| FR44 | Epic 4 | Appeal strategies for denied (A3) |
| FR45 | Epic 4 | `AI_PA_` prefix findings |
| FR46 | Epic 4 | Raw codes alongside AI interpretation |
| FR47 | Epic 1→3 | Full pipeline via `submit_prior_auth()` (built progressively) |
| FR48 | Epic 3 | Sequential phase orchestration |
| FR49 | Epic 1 | Skip clearinghouse/AI when unconfigured |
| FR50 | Epic 3 | Skip AI when no LLM configured |
| FR51 | Epic 1→3 | `PriorAuthResult` (grows with pipeline phases) |
| FR52 | Epic 1 | `PA_` prefix findings |
| FR53 | Epic 4 | `AI_PA_` prefix findings |
| FR54 | Epic 2 | `AAA_PA_REJECTION` findings |
| FR55 | Epic 3 | `CLEARINGHOUSE_` prefix findings |
| FR56 | Epic 1 | Severity levels from existing enum |

**Coverage: 56/56 FRs mapped (100%)**

## Epic List

### Epic 1: PA Request Validation & Determination (Offline)
Developer can create `PriorAuthRequest` models, determine if PA is required from eligibility responses via `determine_pa_required()`, validate PA requests with 7 rule-based validators, and call `submit_prior_auth()` for offline validation. Invalid NPIs, missing member IDs, invalid diagnosis/procedure codes, date issues, and cross-field inconsistencies are caught before any clearinghouse call. Zero API keys, zero network access needed.
**FRs covered:** FR1-FR19, FR47 (offline mode), FR49, FR51 (partial), FR52, FR56

### Epic 2: 278 Response Parsing & AAA Error Handling
Developer can parse raw 278 JSON responses into structured `PriorAuthResponse` models via `parse_278_response()`, with all 7 HCR action codes mapped to human-readable decisions, per-service-line authorization decisions extracted, and AAA reject errors mapped to human-readable messages with suggested fixes. Authorization numbers and effective date ranges extracted automatically.
**FRs covered:** FR25-FR35, FR54

### Epic 3: Clearinghouse Integration & Full Pipeline
Developer can implement custom clearinghouse clients by subclassing `BasePAClearinghouseClient`, submit PA requests through the complete three-phase pipeline via `submit_prior_auth()`, and get structured `PriorAuthResult` with approval status, authorization number, findings from all phases, and execution time. Pipeline orchestrates rule-based → clearinghouse → response parsing automatically.
**FRs covered:** FR20-FR24, FR47-FR48 (full pipeline), FR50-FR51, FR55

### Epic 4: AI-Powered PA Interpretation
Developer can enable AI-powered response interpretation with automatic PHI de-identification. `PriorAuthDeidentifier` strips all 18 HIPAA identifiers before any LLM call. `PriorAuthInterpreterAI` generates decision summaries, next-step recommendations for pended cases (A4), and appeal strategies for denied cases (A3). Full three-phase pipeline complete.
**FRs covered:** FR36-FR46, FR53

---

## Epic 1: PA Request Validation & Determination (Offline)

Developer can create `PriorAuthRequest` models, determine if PA is required from eligibility responses via `determine_pa_required()`, validate PA requests with 7 rule-based validators, and call `submit_prior_auth()` for offline validation. Invalid NPIs, missing member IDs, invalid diagnosis/procedure codes, date issues, and cross-field inconsistencies are caught before any clearinghouse call. Zero API keys, zero network access needed.

### Story 1.1: PA Data Models, Enums & Package Configuration

As a **developer**,
I want typed Pydantic models and enums to represent prior authorization requests, responses, and results,
So that I have a validated, immutable data layer for the PA module that integrates with the existing claim-validator package.

**Acceptance Criteria:**

**Given** a valid PA request as a Python dictionary with subscriber, diagnosis, and service line data
**When** I construct `PriorAuthRequest(**request_dict)` or `PriorAuthRequest.model_validate(request_dict)`
**Then** a frozen, immutable instance is created with all fields validated
**And** string coercion works (e.g., `"2026-04-01"` → date)

**Given** a `PriorAuthRequest` instance
**When** I access its fields
**Then** `requester_npi`, `requester_taxonomy`, `payer_id`, `subscriber` (SubscriberInfo), `patient` (PatientInfo | None), `diagnosis_codes` (list[str]), `service_lines` (list[ServiceLine]), `request_category_code`, `certification_type_code`, and `clinical_info` are available
**And** `subscriber` contains `member_id`, `first_name`, `last_name`, `dob`

**Given** a `ServiceLine` model
**When** I construct it
**Then** it contains `cpt_code`, `quantity`, `from_date`, `to_date` (optional), and `place_of_service_code` (optional)
**And** it is frozen (immutable)

**Given** the PA response models
**When** I construct `PriorAuthResponse`, `ServiceLineDecision`, `PriorAuthError`
**Then** all are frozen Pydantic models with `strict=False`
**And** `PriorAuthResponse` contains `action_code` (CertificationActionCode), `is_approved`, `is_denied`, `is_pended`, `authorization_number`, `effective_date`, `expiration_date`, `decision_reason_code`, `decision_reason_description`, `service_line_decisions`, `errors`, and `raw_response`

**Given** the `PriorAuthResult` model
**When** I inspect its fields
**Then** it contains `approved: bool | None`, `response: PriorAuthResponse | None`, `findings: list[Finding]`, `ai_summary: str | None`, `passed: bool`, `authorization_number: str | None`, `raw_response: dict | None`, and `execution_time: float`
**And** `passed` returns `True` only when zero ERROR-severity findings exist

**Given** the `PADeterminationResult` model
**When** I inspect its fields
**Then** it contains `required: bool`, `confidence: str` (high/medium/low), `reason: str`, `auth_or_cert_indicator: str | None`, and `free_text_indicators: list[str]`

**Given** the PA enums in `prior_auth/constants.py`
**When** I import them
**Then** `CertificationActionCode` is a StrEnum with values A1, A2, A3, A4, A6, CT, NA
**And** `RequestCategoryCode` is a StrEnum with values AR, HS, SC, IN
**And** `CertificationTypeCode` is a StrEnum with values I, R, S, E

**Given** the `ClaimValidatorSettings` in `conf.py`
**When** I inspect new PA fields
**Then** `pa_rule_validators`, `pa_ai_validators`, `skip_clearinghouse_on_pa_failure`, and `pa_skip_ai` are available with sensible defaults
**And** all use `CLAIM_VALIDATOR_` env prefix

**Given** a developer importing PA models
**When** they write `from claim_validator import PriorAuthRequest, PriorAuthResponse, PriorAuthResult`
**Then** the import succeeds and models are available at the top level via `__init__.py` re-exports

**Given** the existing `validate()` and `check_eligibility()` APIs
**When** the PA module is installed
**Then** zero breaking changes — all existing APIs continue to work identically

### Story 1.2: PA Code Tables (HCR Action Codes, AAA Reject Codes, Service Types)

As a **developer**,
I want bundled reference data for HCR action codes, AAA reject reason codes, and service type codes,
So that the PA module can map X12 278 codes to human-readable descriptions offline.

**Acceptance Criteria:**

**Given** the installed package
**When** I call `get_hcr_action_codes()` with a valid action code (e.g., `"A1"`)
**Then** it returns the human-readable description ("Certified in Total") and suggested action
**And** all 7 HCR codes are mapped: A1, A2, A3, A4, A6, CT, NA

**Given** the HCR action code data
**When** I inspect `prior_auth/data/hcr_action_codes.json`
**Then** it contains all 7 action codes with descriptions, categories (approved/denied/pended/other), and suggested actions

**Given** the installed package
**When** I call `get_aaa_reject_codes()` with a valid reject code (e.g., `"04"`)
**Then** it returns the human-readable message and suggested fix
**And** top 20+ codes are mapped (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4)

**Given** the AAA reject code data
**When** I inspect `prior_auth/data/aaa_reject_codes.json`
**Then** it contains reject codes with human-readable messages and suggested corrective actions

**Given** the installed package
**When** I call `get_pa_service_types()` with a valid service type code
**Then** it returns the service type description

**Given** two threads calling `get_hcr_action_codes()` concurrently
**When** both trigger the first load simultaneously
**Then** the data is loaded exactly once (double-check locking with `threading.Lock`)
**And** both threads receive correct results

**Given** any code table lookup with a non-existent code
**When** I query it
**Then** `None` is returned (no exception raised)

**Given** code table loading
**When** I measure the first load time
**Then** it completes in under 500ms
**And** subsequent lookups complete in under 1ms

### Story 1.3: PA Determination from Eligibility Response

As a **developer**,
I want to determine if prior authorization is required based on an eligibility response,
So that I can programmatically bridge the eligibility → PA workflow without manually interpreting 271 data.

**Acceptance Criteria:**

**Given** an `EligibilityResponse` (or dict) with `authOrCertIndicator: "Y"` in benefit information
**When** I call `determine_pa_required(response)`
**Then** a `PADeterminationResult` is returned with `required=True`, `confidence="high"`, and `reason` containing "authOrCertIndicator=Y"
**And** `auth_or_cert_indicator` is `"Y"`

**Given** an eligibility response with `authOrCertIndicator: "N"`
**When** I call `determine_pa_required(response)`
**Then** `required=False`, `confidence="high"`, and `reason` indicates PA not required

**Given** an eligibility response with `authOrCertIndicator: "U"` or missing
**When** I call `determine_pa_required(response)`
**Then** `confidence="low"` and `reason` indicates the indicator is unknown/missing

**Given** an eligibility response with free-text `additionalInformation.description` containing "prior auth" or "precertification" or "preauthorization"
**When** I call `determine_pa_required(response)`
**Then** `required=True` with `confidence="medium"` and `free_text_indicators` contains the matched phrases

**Given** an eligibility response where `authOrCertIndicator="N"` but free-text says "prior authorization required"
**When** I call `determine_pa_required(response)`
**Then** `required=True` (free-text takes precedence per FR4)
**And** `reason` explains the conflict resolution

**Given** a plain Python dict instead of an `EligibilityResponse` object
**When** I call `determine_pa_required(dict_response)`
**Then** it works via duck typing — no hard import of eligibility models required

**Given** `determine_pa_required()` execution
**When** I measure performance
**Then** it completes in under 10ms (NFR4)

**Given** a developer importing from the package
**When** they write `from claim_validator import determine_pa_required`
**Then** the import succeeds and the function is available at the top level

### Story 1.4: Pre-Submission Validators (NPI, Member ID, DOB, Diagnosis, Procedure)

As a **developer**,
I want PA requests validated for NPI correctness, member ID presence, DOB validity, and diagnosis/procedure code accuracy,
So that requests with invalid data are caught offline before clearinghouse submission.

**Acceptance Criteria:**

**Given** a `PriorAuthRequest` with a valid NPI (passes Luhn check, e.g., `"1234567893"`)
**When** rule-based validation runs
**Then** zero NPI-related findings are produced

**Given** a `PriorAuthRequest` with an invalid NPI (fails Luhn check or wrong length)
**When** rule-based validation runs
**Then** a `Finding` with code `PA_INVALID_NPI`, severity `ERROR`, field_name `requester_npi` is produced
**And** the NPI validation reuses the shared `_validate_npi()` utility from the eligibility module

**Given** a `PriorAuthRequest` with a non-empty subscriber member ID
**When** `PAMemberIDValidator.validate(request)` is called
**Then** zero member ID findings are produced

**Given** a `PriorAuthRequest` with an empty or missing subscriber member ID
**When** `PAMemberIDValidator.validate(request)` is called
**Then** a `Finding` with code `PA_MISSING_MEMBER_ID`, severity `ERROR`, field_name `subscriber.member_id` is produced

**Given** a `PriorAuthRequest` with a valid patient DOB
**When** `PADateOfBirthValidator.validate(request)` is called
**Then** zero DOB findings are produced

**Given** a `PriorAuthRequest` with a missing or invalid DOB
**When** `PADateOfBirthValidator.validate(request)` is called
**Then** a `Finding` with code `PA_INVALID_DOB`, severity `ERROR` is produced

**Given** a `PriorAuthRequest` with valid ICD-10 diagnosis codes (present in bundled code tables)
**When** `PADiagnosisValidator.validate(request)` is called
**Then** zero diagnosis findings are produced

**Given** a `PriorAuthRequest` with an unknown ICD-10 code
**When** `PADiagnosisValidator.validate(request)` is called
**Then** a `Finding` with code `PA_INVALID_DIAGNOSIS`, severity `ERROR`, and the invalid code in the message is produced

**Given** a `PriorAuthRequest` with valid CPT/HCPCS procedure codes in service lines
**When** `PAProcedureValidator.validate(request)` is called
**Then** zero procedure findings are produced

**Given** a `PriorAuthRequest` with an unknown CPT/HCPCS code
**When** `PAProcedureValidator.validate(request)` is called
**Then** a `Finding` with code `PA_INVALID_PROCEDURE`, severity `ERROR` is produced

**Given** any finding produced by these validators
**When** I inspect the `message` field
**Then** it references field names only, never actual PHI values (NFR12)

### Story 1.5: Service Date, Cross-Field Validators & Pipeline

As a **developer**,
I want PA requests validated for service date logic and cross-field consistency, and I want to call `submit_prior_auth()` as a single entry point that runs all rule-based validators,
So that I can validate PA requests with one function call, zero configuration, and zero network access.

**Acceptance Criteria:**

**Given** a `PriorAuthRequest` with service dates in the future (within reasonable range)
**When** `PAServiceDateValidator.validate(request)` is called
**Then** zero date findings are produced

**Given** a `PriorAuthRequest` with a service date in the past
**When** `PAServiceDateValidator.validate(request)` is called
**Then** a `Finding` with code `PA_SERVICE_DATE_PAST`, severity `ERROR` is produced

**Given** a `PriorAuthRequest` with a service date unreasonably far in the future (> 365 days)
**When** `PAServiceDateValidator.validate(request)` is called
**Then** a `Finding` with code `PA_SERVICE_DATE_FUTURE`, severity `WARNING` is produced

**Given** a `PriorAuthRequest` where the diagnosis codes do not clinically support the requested procedure
**When** `PACrossFieldValidator.validate(request)` is called
**Then** a `Finding` with code `PA_DX_PROCEDURE_MISMATCH`, severity `WARNING` is produced
**And** the finding includes a suggestion about verifying clinical appropriateness

**Given** a `PriorAuthRequest` where gender/age is incompatible with the procedure
**When** `PACrossFieldValidator.validate(request)` is called
**Then** a `Finding` with code `PA_DEMOGRAPHIC_PROCEDURE_MISMATCH`, severity `WARNING` is produced

**Given** a valid PA request dictionary
**When** I call `submit_prior_auth(request_dict)` with no clearinghouse or AI configured
**Then** a `PriorAuthResult` is returned with `passed=True`, empty findings list, and `approved=None` (no clearinghouse call)
**And** the call requires zero configuration, zero API keys, and zero network calls

**Given** a PA request with multiple validation issues
**When** I call `submit_prior_auth(request_dict)`
**Then** all 7 rule-based validators run (NPI, member ID, DOB, diagnosis, procedure, date, cross-field)
**And** findings are aggregated into a single `PriorAuthResult` ordered by severity

**Given** a `PriorAuthRequest` Pydantic model instance
**When** I call `submit_prior_auth(request_model)`
**Then** it accepts both dict and Pydantic model input seamlessly (NFR27)

**Given** no clearinghouse client configured and no AI configured
**When** the pipeline finishes phase 1
**Then** the pipeline returns immediately with rule-based-only results (FR49)

**Given** custom validator configuration via `skip_rule_validators`
**When** I call `submit_prior_auth(request)` with specific validators disabled
**Then** only the remaining validators execute (FR19)

**Given** invalid input to `submit_prior_auth()` (wrong type, missing required fields)
**When** the function is called
**Then** a `ValueError` is raised with a clear message before any pipeline phase executes (NFR21)

**Given** rule-based validation on a typical PA request
**When** I measure execution time
**Then** it completes in under 100ms (NFR1)

**Given** a developer importing from the package
**When** they write `from claim_validator import submit_prior_auth`
**Then** the import succeeds and `submit_prior_auth` is available at the top level

**Given** all findings produced by PA validators
**When** I inspect their codes
**Then** all use the `PA_` prefix (FR52)
**And** severity levels use the existing `FindingSeverity` enum (FR56)

---

## Epic 2: 278 Response Parsing & AAA Error Handling

Developer can parse raw 278 JSON responses into structured `PriorAuthResponse` models via `parse_278_response()`, with all 7 HCR action codes mapped to human-readable decisions, per-service-line authorization decisions extracted, and AAA reject errors mapped to human-readable messages with suggested fixes. Authorization numbers and effective date ranges extracted automatically.

### Story 2.1: 278 Response Parser & HCR Action Code Mapping

As a **developer**,
I want to parse raw 278 JSON responses into structured Pydantic models with HCR action codes mapped to human-readable decisions,
So that I can programmatically determine authorization status without reading the X12 278 specification.

**Acceptance Criteria:**

**Given** a raw 278 JSON dict from a clearinghouse with HCR01=A1 (approved)
**When** `parse_278_response(raw_dict)` is called
**Then** a `PriorAuthResponse` is returned with `action_code=CertificationActionCode.A1`, `is_approved=True`, `is_denied=False`, `is_pended=False`
**And** `authorization_number` contains the extracted auth number
**And** `effective_date` and `expiration_date` are populated

**Given** a 278 response with HCR01=A3 (denied)
**When** `parse_278_response(raw_dict)` is called
**Then** `is_denied=True`, `is_approved=False`
**And** `decision_reason_code` and `decision_reason_description` are populated

**Given** a 278 response with HCR01=A4 (pended)
**When** `parse_278_response(raw_dict)` is called
**Then** `is_pended=True`, `is_approved=False`, `is_denied=False`

**Given** a 278 response with HCR01=A2 (partial approval)
**When** `parse_278_response(raw_dict)` is called
**Then** `action_code=CertificationActionCode.A2`
**And** per-service-line decisions show which services were approved vs denied

**Given** a 278 response with per-service-line authorization decisions
**When** I inspect `response.service_line_decisions`
**Then** each `ServiceLineDecision` contains `cpt_code`, `action_code`, `authorization_number`, `approved_quantity`, and `denied_reason`

**Given** all 7 HCR action codes (A1, A2, A3, A4, A6, CT, NA)
**When** each is processed by `parse_278_response()`
**Then** the correct `CertificationActionCode` enum value is set
**And** the correct convenience property returns `True` (`is_approved` for A1, `is_denied` for A3, etc.)

**Given** a 278 response with missing or unexpected fields
**When** `parse_278_response(raw_dict)` is called
**Then** missing fields return `None` (not exception) (FR31, NFR16)
**And** unexpected fields are silently ignored

**Given** an unmapped HCR action code (future code not in enum)
**When** `parse_278_response()` encounters it
**Then** a WARNING finding is generated with the raw code value (NFR17)
**And** no exception is raised

**Given** any `PriorAuthResponse`
**When** I access `response.raw_response`
**Then** the complete unmodified 278 JSON dict is available

**Given** the response parser
**When** I verify it does not modify the input dict
**Then** the original `raw_dict` is unchanged after parsing (NFR34)

**Given** `parse_278_response()` execution on a typical response
**When** I measure performance
**Then** it completes in under 50ms (NFR3)

**Given** a developer importing from the package
**When** they write `from claim_validator import parse_278_response`
**Then** the import succeeds and the function is available at the top level

### Story 2.2: AAA Error Parsing & Human-Readable Messages

As a **developer**,
I want AAA reject errors from 278 responses parsed into structured models with human-readable messages and suggested fixes,
So that my application can display actionable error information instead of cryptic X12 reject codes.

**Acceptance Criteria:**

**Given** a 278 response containing AAA reject segments
**When** `parse_278_response(raw_dict)` is called
**Then** `response.errors` contains `PriorAuthError` objects for each AAA segment
**And** each `PriorAuthError` has `rejection_code`, `follow_up_code`, `message`, and `suggested_fix`

**Given** AAA reject code `"04"` (Authorized Quantity Exceeded)
**When** the code is mapped
**Then** `message` is a human-readable description (e.g., "Authorized quantity exceeded")
**And** `suggested_fix` provides actionable guidance (e.g., "Verify requested quantity against payer limits")

**Given** the top 20+ AAA reject codes (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4)
**When** each is encountered in a 278 response
**Then** all have human-readable messages and suggested fixes from the bundled code table

**Given** an unmapped AAA reject code (not in the code table)
**When** it is encountered
**Then** a WARNING finding is generated with the raw code value and a generic "Contact payer for details" message (NFR18)
**And** no exception is raised

**Given** AAA errors in a 278 response
**When** the pipeline processes the response
**Then** corresponding `Finding` objects with code `AAA_PA_REJECTION` are generated (FR35, FR54)
**And** each finding includes the rejection code, human-readable message, and suggested fix in the `context` dict

**Given** multiple AAA errors in a single 278 response
**When** they are parsed
**Then** all errors are captured in `response.errors` and corresponding findings are generated for each

**Given** a 278 response with both HCR action code and AAA errors
**When** processed together
**Then** both the `PriorAuthResponse` model and the findings list reflect the complete error picture

---

## Epic 3: Clearinghouse Integration & Full Pipeline

Developer can implement custom clearinghouse clients by subclassing `BasePAClearinghouseClient`, submit PA requests through the complete three-phase pipeline via `submit_prior_auth()`, and get structured `PriorAuthResult` with approval status, authorization number, findings from all phases, and execution time. Pipeline orchestrates rule-based → clearinghouse → response parsing automatically.

### Story 3.1: BasePAClearinghouseClient Abstraction

As a **developer**,
I want a pluggable clearinghouse client interface for 278 PA submissions,
So that I can implement my own clearinghouse integration by subclassing an abstract base class.

**Acceptance Criteria:**

**Given** the `BasePAClearinghouseClient` abstract base class
**When** I inspect its contract
**Then** it defines `submit_prior_auth(request: PriorAuthRequest) -> dict` as an abstract method
**And** it inherits from `BaseClearinghouseClient` (existing base class) (D24)
**And** it has `provider_name: str`, `environment: str`, `close() -> None`
**And** it supports context manager protocol (`__enter__`/`__exit__`)

**Given** a developer subclassing `BasePAClearinghouseClient`
**When** they implement `submit_prior_auth()` and set `provider_name`
**Then** their custom client can be used directly with `PriorAuthPipeline`

**Given** a custom clearinghouse client that returns a raw 278 JSON dict
**When** `submit_prior_auth(request)` is called
**Then** it returns the raw response dict for downstream parsing

**Given** a clearinghouse client encountering an HTTP/network failure
**When** `submit_prior_auth()` is called
**Then** it raises `ClearinghouseError` with a descriptive message (FR22)
**And** the error message contains no PHI (NFR12)

**Given** a clearinghouse client receiving an AAA business rejection
**When** `submit_prior_auth()` is called
**Then** it returns the response normally (does NOT raise — FR22)
**And** AAA errors are in the response dict for downstream parsing

**Given** a clearinghouse client with a configurable timeout
**When** no timeout is explicitly set
**Then** the default timeout is 30 seconds (FR23, NFR28)

**Given** a clearinghouse client used as a context manager
**When** the `with` block exits
**Then** the client is properly closed (FR24)

**Given** the existing `BaseClearinghouseClient` (eligibility)
**When** the PA subclass is added
**Then** zero breaking changes to the existing `StediClient` or eligibility pipeline (NFR22)

### Story 3.2: Full Pipeline Orchestration & submit_prior_auth() API

As a **developer**,
I want `submit_prior_auth()` to orchestrate the full three-phase pipeline (rule-based → clearinghouse → AI) and return a complete `PriorAuthResult`,
So that I get end-to-end PA submission with a single function call.

**Acceptance Criteria:**

**Given** a valid PA request and a configured clearinghouse client
**When** I call `submit_prior_auth(request, clearinghouse_client=client)`
**Then** Phase 1 (rule-based) runs first, then Phase 2 (clearinghouse) submits to the clearinghouse
**And** the 278 response is parsed into `PriorAuthResponse`
**And** a `PriorAuthResult` is returned with `approved`, `response`, `findings`, `authorization_number`, and `raw_response` populated

**Given** rule-based validation fails and `skip_clearinghouse_on_pa_failure=True` (default)
**When** the pipeline reaches the phase 2 gate
**Then** the clearinghouse phase is skipped entirely
**And** `PriorAuthResult` has `response=None`, `raw_response=None`, and only rule-based findings

**Given** rule-based validation fails and `skip_clearinghouse_on_pa_failure=False`
**When** the pipeline reaches the phase 2 gate
**Then** the clearinghouse phase still runs
**And** findings from both phases are combined in the result

**Given** a clearinghouse error (network timeout, HTTP error)
**When** the pipeline catches the `ClearinghouseError`
**Then** a `Finding` with code `CLEARINGHOUSE_ERROR`, severity `ERROR` is added to the result (FR55)
**And** `PriorAuthResult` has `response=None` and the error details in findings
**And** no unhandled exception propagates to the caller

**Given** no AI/LLM provider configured
**When** the pipeline reaches the phase 3 gate
**Then** the AI phase is skipped entirely (FR50)
**And** `PriorAuthResult` has `ai_summary=None` and only rule-based + clearinghouse findings

**Given** the pipeline producing a `PriorAuthResult`
**When** the response has HCR01=A1 (approved)
**Then** `result.approved=True` and `result.authorization_number` contains the auth number

**Given** the pipeline producing a `PriorAuthResult`
**When** the response has HCR01=A3 (denied)
**Then** `result.approved=False`

**Given** `PriorAuthResult`
**When** I inspect `execution_time`
**Then** it contains the total pipeline execution time in seconds

**Given** the pipeline overhead (orchestration, finding aggregation)
**When** measured separately from phase execution
**Then** it adds less than 20ms (NFR5)

---

## Epic 4: AI-Powered PA Interpretation

Developer can enable AI-powered response interpretation with automatic PHI de-identification. `PriorAuthDeidentifier` strips all 18 HIPAA identifiers before any LLM call. `PriorAuthInterpreterAI` generates decision summaries, next-step recommendations for pended cases (A4), and appeal strategies for denied cases (A3). Full three-phase pipeline complete.

### Story 4.1: PA De-identification Engine

As a **developer**,
I want PA response data automatically de-identified before any LLM call,
So that I can use AI interpretation with zero risk of PHI leakage — guaranteed by the library.

**Acceptance Criteria:**

**Given** a `PriorAuthResponse` with full PHI (patient name, DOB, member ID, clinical justification text)
**When** `PriorAuthDeidentifier.deidentify(response)` is called
**Then** a `DeidentifiedPriorAuthResponse` is returned with all 18 HIPAA identifiers stripped
**And** only safe data remains: HCR action codes, decision reason codes, AAA reject codes, CPT/HCPCS codes (without patient context), authorization status, effective dates (year only)

**Given** the 18 HIPAA identifier categories
**When** I run the de-identifier against test responses containing each identifier type
**Then** all are stripped: patient name, DOB (replaced with year only), member ID, address, SSN, phone, email, subscriber ID, NPI (when combined with patient data), and all other HIPAA-defined identifiers

**Given** clinical justification free-text containing PII
**When** the de-identifier processes it
**Then** PII is scrubbed from the clinical text while preserving medical terminology

**Given** ages 90+
**When** the de-identifier processes them
**Then** age is capped to 90 per HIPAA Safe Harbor (FR37)

**Given** dates in the response
**When** the de-identifier processes them
**Then** dates are reduced to year-only (FR38)

**Given** a `DeidentifiedPriorAuthResponse` instance
**When** I check its type
**Then** mypy/pyright distinguishes it from `PriorAuthResponse` at the type level
**And** the type system prevents accidentally passing raw `PriorAuthResponse` to LLM-facing functions

**Given** the de-identifier failing (exception during de-identification)
**When** the pipeline reaches the AI phase
**Then** the AI phase must NOT execute under any circumstance (FR39, NFR8)

**Given** PHI in the PA request/response
**When** the `submit_prior_auth()` call completes
**Then** PHI does not persist in memory beyond that single call (FR40, NFR13)

**Given** a comprehensive PHI leak test suite in `tests/test_prior_auth/test_hipaa/`
**When** run against `PriorAuthDeidentifier`
**Then** all tests pass confirming zero PHI in de-identified output
**And** tests cover all 18 HIPAA identifier categories (NFR36)

### Story 4.2: AI PA Interpreter & Full Pipeline

As a **developer**,
I want AI-powered interpretation that turns cryptic HCR action codes and AAA errors into actionable decision summaries, next-step recommendations, and appeal strategies,
So that my application can display clear PA guidance without my team learning X12 278 semantics.

**Acceptance Criteria:**

**Given** a de-identified PA response with HCR01=A1 (approved)
**When** `PriorAuthInterpreterAI` processes it via the configured LLM
**Then** `ai_summary` contains a human-readable approval summary (e.g., "All requested services approved. Include authorization number AUTH123 on the 837 claim. Authorization valid through 2026-04-01.")

**Given** a de-identified PA response with HCR01=A3 (denied)
**When** `PriorAuthInterpreterAI` processes it
**Then** `ai_summary` includes denial reason interpretation, appeal strategy suggestions, and recommended documentation to gather (FR44)
**And** AI findings with `AI_PA_` prefix are generated

**Given** a de-identified PA response with HCR01=A4 (pended)
**When** `PriorAuthInterpreterAI` processes it
**Then** `ai_summary` includes likely documentation needed and recommended follow-up timeline (FR43)

**Given** AI interpretation with raw HCR/AAA codes
**When** the AI generates its summary
**Then** raw codes are included alongside the interpretation for verification (FR46)

**Given** AI configuration with any supported LLM provider (Anthropic, OpenAI)
**When** I call `submit_prior_auth(request, clearinghouse_client=client, ai_config={...})`
**Then** the full three-phase pipeline executes: rule-based → clearinghouse → AI interpretation
**And** `PriorAuthResult` contains `approved`, `response`, `findings` (from all phases), `ai_summary`, and `raw_response`

**Given** `pa_skip_ai=True` in settings or no `ai_config` provided
**When** I call `submit_prior_auth(request, clearinghouse_client=client)`
**Then** the AI phase is skipped entirely
**And** `PriorAuthResult` has `ai_summary=None` and only rule-based + clearinghouse findings

**Given** the LLM provider is unreachable or returns an error
**When** the AI phase attempts to call the provider
**Then** the pipeline returns the structured `PriorAuthResponse` from phase 2 plus a `Finding(code="AI_PA_PROVIDER_ERROR", severity=WARNING)` (NFR20)
**And** no exception propagates to the caller — graceful degradation

**Given** the de-identification step in the pipeline
**When** the AI phase begins
**Then** `PriorAuthDeidentifier.deidentify()` runs before any LLM call
**And** only `DeidentifiedPriorAuthResponse` data reaches the LLM provider

**Given** AI-generated findings
**When** I inspect them
**Then** all use `AI_PA_` code prefix (FR45, FR53), severity is always `WARNING` (advisory, not authoritative)
**And** no PHI appears in any finding message, suggestion, or the `ai_summary`

**Given** AI interpretation using the existing LLM configuration
**When** I verify LLM setup
**Then** it reuses `BaseLLMClient`, `LLMFactory`, and `CLAIM_VALIDATOR_AI_CONFIG` — no parallel LLM configuration system (NFR23)
