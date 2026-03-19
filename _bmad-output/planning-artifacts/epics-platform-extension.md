---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-03-19'
inputDocuments:
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/prd.md'
workflowType: 'epics'
project_name: 'healthcare-claim-analyzer'
user_name: 'aniket'
date: '2026-03-19'
scope: 'platform-extension-D44-D63'
---

# healthcare-claim-analyzer — Platform Extension Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the healthcare-claim-analyzer **Platform Extension**, decomposing the platform architecture decisions (D44-D63) and requirements (PFR1-PFR50) into implementable stories across two repositories (open-source core + proprietary platform).

## Requirements Inventory

### Functional Requirements

**Payer Routing Engine (PFR1-PFR5):**
- PFR1: PayerRouter resolves payer ID to clearinghouse provider via bundled mapping table
- PFR2: PayerRouter returns fallback clearinghouse list when primary is unavailable
- PFR3: Payer routing mapping loaded from gzipped JSON (payer_routing.json.gz), lazy, thread-safe
- PFR4: Users override default payer mappings via ClaimValidatorSettings.payer_routing_overrides
- PFR5: ClearinghouseClientPool manages multiple BaseClearinghouseClient instances, lazy-instantiated, cached

**New Clearinghouse Integrations (PFR6-PFR12):**
- PFR6: ChangeHealthcareClient authenticates via OAuth2 client_credentials with token caching
- PFR7: ChangeHealthcareClient supports eligibility (270/271), professional claims (837P), institutional claims (837I), claim status (276/277)
- PFR8: ChangeHealthcareClient respects Retry-After headers for rate limiting
- PFR9: AvailityClient authenticates via OAuth2 client_credentials with token caching
- PFR10: AvailityClient supports eligibility, claims, claim status with payer-specific API variations
- PFR11: AvailityClient handles async response pattern (submit → poll for result) for some payers
- PFR12: WaystarClient extended with submit_claim() and check_claim_status() (currently missing)

**New Claim Types (PFR13-PFR19):**
- PFR13: InstitutionalClaimData (837I) frozen Pydantic model with UB-04 fields (bill type, revenue codes, attending physician, admission/discharge, occurrence/condition/value codes)
- PFR14: InstitutionalServiceLine model with revenue_code, HCPCS, rate, units
- PFR15: BillTypeValidator validates 3-digit bill type code structure
- PFR16: RevenueCodeValidator validates revenue codes against bundled revenue_codes.json.gz
- PFR17: AdmissionValidator validates admission/discharge dates, type/source codes, patient status
- PFR18: InstitutionalCompletenessValidator checks UB-04 required fields per bill type
- PFR19: ClaimType StrEnum ("837P", "837I", "837D") with pipeline claim type detection and routing

**Async Processing (PFR20-PFR25) — Platform Only:**
- PFR20: API accepts claim submission, creates DB record (status=pending), enqueues Celery task, returns job_id (HTTP 202)
- PFR21: Worker picks up job, runs 7-stage pipeline, updates DB (status=completed|failed)
- PFR22: GET /api/v1/jobs/{job_id} returns current status and result when complete
- PFR23: Job states: pending → processing → completed | failed | timeout
- PFR24: Configurable job timeout (default 120s single claim, 600s batch)
- PFR25: Celery Beat periodic task polls clearinghouses for async responses (835, 277CA)

**Persistence Layer (PFR26-PFR32) — Platform Only:**
- PFR26: PostgreSQL schema with tables: tenants, claims, transactions, findings, audit_log, payer_mappings
- PFR27: audit_log is append-only — no UPDATE or DELETE
- PFR28: transactions stores raw clearinghouse payloads encrypted at rest
- PFR29: Row-level security on claims, transactions, findings enforced at DB level
- PFR30: HIPAA 6-year retention policy on claims and transactions
- PFR31: Alembic migrations with reversible schema changes
- PFR32: All tables include tenant_id and created_at columns

**Multi-Tenancy (PFR33-PFR37) — Platform Only:**
- PFR33: Tenant resolved from API key (Bearer cv_live_xxx or cv_test_xxx) via FastAPI middleware
- PFR34: Per-tenant clearinghouse credentials stored encrypted (AES-256-GCM) in tenants.clearinghouse_configs
- PFR35: Per-tenant settings overrides for validator selection, AI config, payer routing
- PFR36: Rate limiting per tenant (configurable, default 100 req/min)
- PFR37: API key rotation: tenants regenerate keys, old key invalidated immediately

**Remittance Processing (PFR38-PFR41) — Platform Only (Deferred to P2):**
- PFR38: 835 ERA response parsing into structured model
- PFR39: Payment reconciliation matching 835 to original 837 submission
- PFR40: Denial tracking and categorization
- PFR41: Webhook notification when matched 835 response received

**Observability (PFR42-PFR45) — Platform Only:**
- PFR42: Structured JSON logging via structlog with tenant_id and claim_id context binding
- PFR43: Prometheus metrics: claims_processed_total, pipeline_duration_seconds, queue_depth gauge
- PFR44: Health endpoints: GET /health (liveness), GET /ready (DB + Redis checks)
- PFR45: Distributed tracing via OpenTelemetry (deferred to post-MVP)

**API Gateway (PFR46-PFR50) — Platform Only:**
- PFR46: POST /api/v1/claims — submit claim (async, returns job_id)
- PFR47: GET /api/v1/claims/{id} — get claim result
- PFR48: POST /api/v1/eligibility — check eligibility (async)
- PFR49: GET /api/v1/tenants/me — current tenant info
- PFR50: Usage metering per tenant (validations, submissions, API calls) for billing

### Non-Functional Requirements

- PNFR1: Performance — <200ms API response for job_id return, >5,000 claims/hour throughput per worker
- PNFR2: Availability — 99.9% uptime SLA for SaaS tier
- PNFR3: Security — HIPAA BAA for SaaS, tenant data isolation, encrypted at rest + in transit
- PNFR4: Scalability — Horizontal worker scaling, connection pooling per clearinghouse
- PNFR5: Compliance — 6-year audit trail retention (HIPAA), SOC 2 Type II pathway
- PNFR6: Resilience — Circuit breakers per clearinghouse, retry with exponential backoff, fallback routing

### Additional Requirements (from Architecture)

- Open-source core must work standalone without platform installed (D44)
- Platform imports library, never reverse (D44)
- No premium stubs, feature flags, or telemetry in open-source core (D44)
- New extras in pyproject.toml: [change], [availity], [resilience], [all-clearinghouses] (D45)
- Backward compatible: single CLEARINGHOUSE_PROVIDER env var still works (D47)
- tenacity >=8.2 is the only new open-source dependency (D59)
- Platform deps: celery >=5.3, redis >=5.0, sqlalchemy >=2.0, alembic >=1.13, asyncpg >=0.29, structlog >=24.0, prometheus-client >=0.20 (D54, D57)
- SQLAlchemy Core only, never ORM (D57)
- Tenant context passed explicitly as parameter, never thread-local (D62)
- Circuit breaker per-instance, not global singleton (D60)
- Resilience order: circuit breaker → retry → HTTP call (D59, D60)
- 837I needs new code table: revenue_codes.json.gz (D52)
- 837I needs new code table: payer_routing.json.gz (D46)

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| PFR1 | Epic 1 | PayerRouter resolves payer ID → clearinghouse |
| PFR2 | Epic 1 | Fallback clearinghouse list |
| PFR3 | Epic 1 | Payer mapping from gzipped JSON |
| PFR4 | Epic 1 | User override for payer mappings |
| PFR5 | Epic 1 | ClearinghouseClientPool manages multiple clients |
| PFR6 | Epic 2 | Change Healthcare OAuth2 auth |
| PFR7 | Epic 2 | Change Healthcare eligibility, claims, status |
| PFR8 | Epic 2 | Change Healthcare rate limit handling |
| PFR9 | Epic 3 | Availity OAuth2 auth |
| PFR10 | Epic 3 | Availity eligibility, claims, status |
| PFR11 | Epic 3 | Availity async response pattern |
| PFR12 | Epic 4 | Waystar submit_claim + check_claim_status |
| PFR13 | Epic 5 | InstitutionalClaimData model |
| PFR14 | Epic 5 | InstitutionalServiceLine model |
| PFR15 | Epic 5 | BillTypeValidator |
| PFR16 | Epic 5 | RevenueCodeValidator |
| PFR17 | Epic 5 | AdmissionValidator |
| PFR18 | Epic 5 | InstitutionalCompletenessValidator |
| PFR19 | Epic 5 | ClaimType routing |
| PFR20 | Epic 7 | Async claim submission → job_id |
| PFR21 | Epic 7 | Worker runs pipeline, updates DB |
| PFR22 | Epic 7 | GET /jobs/{id} status query |
| PFR23 | Epic 7 | Job state machine |
| PFR24 | Epic 7 | Configurable job timeout |
| PFR25 | Epic 9 | Celery Beat polls for async responses |
| PFR26 | Epic 7 | PostgreSQL schema |
| PFR27 | Epic 7 | Append-only audit_log |
| PFR28 | Epic 7 | Encrypted transaction payloads |
| PFR29 | Epic 7 | Row-level security |
| PFR30 | Epic 7 | HIPAA 6-year retention |
| PFR31 | Epic 7 | Alembic migrations |
| PFR32 | Epic 7 | tenant_id + created_at on all tables |
| PFR33 | Epic 8 | Tenant from API key middleware |
| PFR34 | Epic 8 | Encrypted per-tenant credentials |
| PFR35 | Epic 8 | Per-tenant settings overrides |
| PFR36 | Epic 8 | Per-tenant rate limiting |
| PFR37 | Epic 8 | API key rotation |
| PFR38-41 | Deferred | 835 remittance (P2) |
| PFR42 | Epic 9 | Structured JSON logging |
| PFR43 | Epic 9 | Prometheus metrics |
| PFR44 | Epic 9 | Health endpoints |
| PFR45 | Deferred | OpenTelemetry tracing (P2) |
| PFR46 | Epic 8 | POST /api/v1/claims |
| PFR47 | Epic 8 | GET /api/v1/claims/{id} |
| PFR48 | Epic 8 | POST /api/v1/eligibility |
| PFR49 | Epic 8 | GET /api/v1/tenants/me |
| PFR50 | Epic 8 | Usage metering |

**Coverage: 45/50 FRs mapped (5 deferred to P2), 6/6 PNFRs addressed**

## Epic List

### Epic 1: Route Claims to the Right Clearinghouse
Developers can configure multiple clearinghouses and the library automatically routes claims to the correct one based on payer ID — with fallback options if primary is unavailable.
**FRs covered:** PFR1, PFR2, PFR3, PFR4, PFR5
**Decisions:** D44, D45, D46, D47
**Repo:** Open-source

### Epic 2: Reach 40% More of the US Market via Change Healthcare
Developers can submit claims, check eligibility, and query claim status through Change Healthcare (Optum) — the largest clearinghouse in the US.
**FRs covered:** PFR6, PFR7, PFR8
**Decisions:** D48
**Repo:** Open-source

### Epic 3: Reach BCBS/Humana/Cigna via Availity
Developers can route claims through Availity to reach BCBS affiliates, Humana, and Cigna — including handling Availity's async response pattern for select payers.
**FRs covered:** PFR9, PFR10, PFR11
**Decisions:** D49
**Repo:** Open-source

### Epic 4: Complete Waystar Claim Submission
The Waystar integration is fully functional — developers can submit claims and check claim status, not just run eligibility and prior auth.
**FRs covered:** PFR12
**Decisions:** D50
**Repo:** Open-source

### Epic 5: Validate Institutional (Hospital) Claims
Developers can validate 837I institutional claims (UB-04) — enabling hospital, SNF, and outpatient facility billing alongside existing professional claims. Opens ~40% more claim volume.
**FRs covered:** PFR13, PFR14, PFR15, PFR16, PFR17, PFR18, PFR19
**Decisions:** D51, D52, D53
**Repo:** Open-source

### Epic 6: Resilient Clearinghouse Communication
All clearinghouse calls automatically retry on transient failures, circuit-break when a provider is down, and fall back to alternate clearinghouses — so developers never lose claims to temporary outages.
**FRs covered:** PNFR6 (resilience)
**Decisions:** D59, D60, D61
**Repo:** Open-source

### Epic 7: Platform — Async Claim Processing Engine
The platform accepts claims via REST API, processes them asynchronously in background workers, persists all results to PostgreSQL, and serves job status queries — the foundation for the SaaS tier.
**FRs covered:** PFR20, PFR21, PFR22, PFR23, PFR24, PFR26, PFR27, PFR28, PFR29, PFR30, PFR31, PFR32
**Decisions:** D54, D57, D58
**Repo:** Platform

### Epic 8: Platform — Multi-Tenant API with Isolation
Multiple customers can use the platform simultaneously with full data isolation, their own clearinghouse credentials, API key authentication, and per-tenant rate limiting.
**FRs covered:** PFR33, PFR34, PFR35, PFR36, PFR37, PFR46, PFR47, PFR48, PFR49, PFR50
**Decisions:** D62, D63
**Repo:** Platform

### Epic 9: Platform — Webhooks & Monitoring
Tenants receive automatic webhook notifications when claims complete, operators can monitor system health via structured logs and Prometheus metrics, and the platform polls for delayed clearinghouse responses.
**FRs covered:** PFR25, PFR42, PFR43, PFR44
**Decisions:** D55, D56
**Repo:** Platform

### Deferred (P2): Remittance & Dental
- PFR38-41: 835 remittance reconciliation
- PFR45: OpenTelemetry distributed tracing
- 837D dental claim support

---

## Epic 1: Route Claims to the Right Clearinghouse

Developers can configure multiple clearinghouses and the library automatically routes claims to the correct one based on payer ID — with fallback options if primary is unavailable.

### Story 1.1: Payer Route Model and Default Mapping Data

As a developer,
I want a bundled payer-to-clearinghouse mapping table loaded from compressed JSON,
So that the library knows which clearinghouse handles each payer without manual configuration.

**Acceptance Criteria:**

**Given** the library is installed with default data
**When** `load_default_mapping()` is called
**Then** it returns a dict of ~2,000 payer ID → `PayerRoute` mappings loaded from `payer_routing.json.gz`
**And** `PayerRoute` is a frozen dataclass with fields: `clearinghouse`, `payer_id_at_clearinghouse`, `priority`, `supports` (frozenset)
**And** the mapping file follows the same gzip+JSON lazy-loading pattern as existing code tables
**And** loading is thread-safe with double-check locking

### Story 1.2: PayerRouter with Route and Fallback

As a developer,
I want to resolve a payer ID to the correct clearinghouse provider,
So that claims are automatically routed without manual clearinghouse selection.

**Acceptance Criteria:**

**Given** a `PayerRouter` initialized with default or custom mappings
**When** `route(payer_id)` is called with a known payer ID
**Then** it returns the highest-priority `PayerRoute` for that payer
**And** when `route_with_fallback(payer_id)` is called, it returns an ordered list of all `PayerRoute` options for that payer sorted by priority
**And** when called with an unknown payer ID, it raises `PayerRoutingError` with a descriptive message
**And** `PayerRouter` is stateless and thread-safe

### Story 1.3: ClearinghouseClientPool with Lazy Client Management

As a developer,
I want a single pool that manages multiple clearinghouse clients simultaneously,
So that I can submit claims to any clearinghouse without manually instantiating clients.

**Acceptance Criteria:**

**Given** a `ClearinghouseClientPool` initialized with a dict of `ClearinghouseConfig` objects
**When** `get_client(provider_name)` is called
**Then** it lazy-instantiates the correct `BaseClearinghouseClient` subclass on first call and caches it for reuse
**And** `submit_claim(claim, payer_id)` routes via `PayerRouter` then delegates to the correct client
**And** `check_eligibility(request, payer_id)` routes via `PayerRouter` then delegates to the correct client
**And** clients are only instantiated when first requested, not at pool construction

### Story 1.4: Settings Integration and Backward Compatibility

As a developer using the existing single-clearinghouse configuration,
I want the new multi-clearinghouse routing to be opt-in,
So that my existing `CLEARINGHOUSE_PROVIDER` env var setup continues to work unchanged.

**Acceptance Criteria:**

**Given** `ClaimValidatorSettings` with only `CLEARINGHOUSE_PROVIDER` set (existing pattern)
**When** the pipeline runs
**Then** it behaves identically to current behavior — single clearinghouse, no routing
**And** when `clearinghouse_configs` dict is set in settings, a `ClearinghouseClientPool` is created with all configured providers
**And** when `payer_routing_overrides` is set, those overrides take precedence over bundled default mappings
**And** all existing tests pass without modification

### Story 1.5: Update Package Extras for New Clearinghouses

As a developer,
I want to install only the clearinghouse clients I need via pip extras,
So that I don't pull unnecessary dependencies.

**Acceptance Criteria:**

**Given** the updated `pyproject.toml`
**When** `pip install claim-validator[change]` is run
**Then** it installs httpx (the only dependency for Change Healthcare client)
**And** `[availity]`, `[resilience]`, `[all-clearinghouses]` extras are also available
**And** `[resilience]` installs `tenacity>=8.2`
**And** `[all-clearinghouses]` installs httpx for all clearinghouse clients
**And** existing extras (`[ai]`, `[server]`, `[stedi]`, `[claimmd]`, `[waystar]`) remain unchanged

---

## Epic 2: Reach 40% More of the US Market via Change Healthcare

Developers can submit claims, check eligibility, and query claim status through Change Healthcare (Optum) — the largest clearinghouse in the US.

### Story 2.1: Change Healthcare OAuth2 Authentication

As a developer,
I want the Change Healthcare client to handle OAuth2 authentication automatically,
So that I only need to provide client_id and client_secret — not manage tokens manually.

**Acceptance Criteria:**

**Given** a `ChangeHealthcareClient` initialized with `client_id` and `client_secret`
**When** the first API call is made
**Then** it obtains an OAuth2 token via client_credentials flow from Change Healthcare's token endpoint
**And** the token is cached and reused until 5 minutes before expiry
**And** when the token expires, it refreshes automatically before the next call
**And** `_get_oauth_token()` and `_refresh_token()` are private methods on the client class
**And** authentication failure raises `ClearinghouseAuthError`

### Story 2.2: Change Healthcare Eligibility Check

As a developer,
I want to verify patient eligibility through Change Healthcare,
So that I can check coverage for patients whose payers route through Change Healthcare.

**Acceptance Criteria:**

**Given** a `ChangeHealthcareClient` with valid credentials
**When** `check_eligibility(request)` is called with a valid `EligibilityRequest`
**Then** it posts JSON to Change Healthcare's eligibility v3 endpoint
**And** returns a `ClearinghouseEligibilityResponse` parsed from the 271 JSON response
**And** business rejections (AAA segments) are returned in the response, not raised as exceptions
**And** HTTP/network failures raise `ClearinghouseError` subclasses

### Story 2.3: Change Healthcare Claims Submission

As a developer,
I want to submit professional and institutional claims through Change Healthcare,
So that I can process claims for the ~40% of the market routed through this clearinghouse.

**Acceptance Criteria:**

**Given** a `ChangeHealthcareClient` with valid credentials
**When** `submit_claim(claim_data)` is called with a valid claim
**Then** it posts JSON to the appropriate endpoint (professional v3 or institutional v1 based on claim type)
**And** returns a `SubmissionResult` with clearinghouse reference ID
**And** the client is registered in the clearinghouse factory as `"change"`

### Story 2.4: Change Healthcare Claim Status

As a developer,
I want to check the status of claims submitted through Change Healthcare,
So that I can track claim progress without logging into a portal.

**Acceptance Criteria:**

**Given** a `ChangeHealthcareClient` with valid credentials
**When** `check_claim_status(claim_ref)` is called with a valid claim reference
**Then** it posts to Change Healthcare's claim status v2 endpoint
**And** returns a `ClaimStatusResponse` with current status
**And** respects `Retry-After` headers if rate-limited (PFR8)

---

## Epic 3: Reach BCBS/Humana/Cigna via Availity

Developers can route claims through Availity to reach BCBS affiliates, Humana, and Cigna — including handling Availity's async response pattern for select payers.

### Story 3.1: Availity OAuth2 Authentication

As a developer,
I want the Availity client to handle OAuth2 authentication automatically,
So that I only need to provide credentials — not manage tokens manually.

**Acceptance Criteria:**

**Given** an `AvailityClient` initialized with `client_id` and `client_secret`
**When** the first API call is made
**Then** it obtains an OAuth2 token via client_credentials flow from Availity's token endpoint
**And** the token is cached and reused until expiry
**And** `_get_oauth_token()` and `_refresh_token()` are private methods
**And** authentication failure raises `ClearinghouseAuthError`

### Story 3.2: Availity Eligibility with Payer-Specific Variations

As a developer,
I want to check eligibility through Availity with support for payer-specific API differences,
So that I can verify coverage for BCBS, Humana, and Cigna patients.

**Acceptance Criteria:**

**Given** an `AvailityClient` with valid credentials
**When** `check_eligibility(request)` is called
**Then** it posts to Availity's coverages endpoint with payer-appropriate parameters
**And** handles payer-specific response format variations
**And** returns a `ClearinghouseEligibilityResponse`

### Story 3.3: Availity Claims Submission

As a developer,
I want to submit claims through Availity,
So that I can reach BCBS/Humana/Cigna payers.

**Acceptance Criteria:**

**Given** an `AvailityClient` with valid credentials
**When** `submit_claim(claim_data)` is called
**Then** it posts to Availity's claims endpoint
**And** returns a `SubmissionResult` with reference ID
**And** the client is registered in the clearinghouse factory as `"availity"`

### Story 3.4: Availity Async Response Polling

As a developer,
I want the Availity client to handle payers that return async responses,
So that I don't need to implement custom polling logic for slow-responding payers.

**Acceptance Criteria:**

**Given** an Availity submission that returns an async status (pending/processing)
**When** the client detects an async response
**Then** it polls the status endpoint at configurable intervals (default 5s, max 3 attempts)
**And** returns the final response when available
**And** raises `ClearinghouseTimeoutError` if polling exceeds max attempts
**And** sync-responding payers are returned immediately without polling

---

## Epic 4: Complete Waystar Claim Submission

The Waystar integration is fully functional — developers can submit claims and check claim status.

### Story 4.1: Waystar Claim Submission

As a developer,
I want to submit claims through Waystar,
So that I can use the full Waystar integration (not just eligibility and prior auth).

**Acceptance Criteria:**

**Given** an existing `WaystarClient` with valid credentials
**When** `submit_claim(claim_data)` is called
**Then** it posts to Waystar's claims endpoint with HMAC + basic auth
**And** returns a `SubmissionResult` with reference ID
**And** existing eligibility and prior auth methods remain unchanged
**And** all existing Waystar tests continue to pass

### Story 4.2: Waystar Claim Status Check

As a developer,
I want to check claim status through Waystar,
So that I can track submitted claims programmatically.

**Acceptance Criteria:**

**Given** a `WaystarClient` with valid credentials
**When** `check_claim_status(claim_ref)` is called
**Then** it queries Waystar's status endpoint
**And** returns a `ClaimStatusResponse`
**And** handles not-found claims gracefully (returns status "unknown", not exception)

---

## Epic 5: Validate Institutional (Hospital) Claims

Developers can validate 837I institutional claims (UB-04) — enabling hospital, SNF, and outpatient facility billing.

### Story 5.1: Institutional Claim Data Models

As a developer,
I want Pydantic models for institutional (UB-04) claims,
So that I can represent hospital and facility claims with proper type safety.

**Acceptance Criteria:**

**Given** the new `models/institutional.py` module
**When** creating an `InstitutionalClaimData` instance
**Then** it accepts all UB-04 fields: bill_type_code, attending_physician_npi, operating_physician_npi, admission_date, discharge_date, admission_type_code, admission_source_code, patient_status_code, drg_code, condition_codes, occurrence_codes, value_codes
**And** `InstitutionalServiceLine` has: revenue_code, hcpcs_code, rate, units, modifiers
**And** `OccurrenceCode` has: code, date; `ValueCode` has: code, amount
**And** all models are frozen (immutable) with `ConfigDict(frozen=True)`
**And** `ClaimType` StrEnum is added to `models/enums.py` with values "837P", "837I", "837D"

### Story 5.2: Revenue Codes Code Table

As a developer,
I want a bundled revenue code lookup table,
So that the RevenueCodeValidator can check codes offline without external calls.

**Acceptance Criteria:**

**Given** a new `data/revenue_codes.json.gz` file
**When** `load_compressed_json("revenue_codes.json.gz")` is called
**Then** it returns a dict of valid UB-04 revenue codes with descriptions
**And** follows the same lazy-loading, thread-safe, gzip pattern as existing code tables
**And** includes all standard revenue code ranges (0001-0999)

### Story 5.3: Bill Type and Revenue Code Validators

As a developer,
I want validators that check 837I-specific codes,
So that institutional claims are validated for correct bill type and revenue code usage.

**Acceptance Criteria:**

**Given** a `BillTypeValidator`
**When** `validate(claim)` is called with an institutional claim
**Then** it validates the 3-digit bill_type_code structure (position 1: facility type, position 2: classification, position 3: frequency)
**And** rejects invalid combinations with finding code `INST_INVALID_BILL_TYPE`

**Given** a `RevenueCodeValidator`
**When** `validate(claim)` is called
**Then** it validates each service line's revenue_code against the bundled revenue codes table
**And** rejects unknown codes with finding code `INST_INVALID_REVENUE_CODE`

### Story 5.4: Admission and Institutional Completeness Validators

As a developer,
I want validators that check admission data and UB-04 required fields,
So that institutional claims pass clearinghouse edits on first submission.

**Acceptance Criteria:**

**Given** an `AdmissionValidator`
**When** `validate(claim)` is called with an institutional claim
**Then** it validates admission_date <= discharge_date (if both present)
**And** validates admission_type_code and admission_source_code are valid values
**And** validates patient_status_code is valid
**And** rejects invalid data with finding codes prefixed `INST_ADMISSION_`

**Given** an `InstitutionalCompletenessValidator`
**When** `validate(claim)` is called
**Then** it checks all UB-04 required fields are present based on bill type
**And** validates attending_physician_npi is present
**And** validates at least one service line with revenue code exists
**And** rejects missing fields with finding code `INST_MISSING_`

### Story 5.5: Pipeline Claim Type Detection and Routing

As a developer,
I want the pipeline to automatically detect 837I vs 837P claims and apply the correct validators,
So that I can pass any claim type to `validate()` or `process_claim_full()` without manual configuration.

**Acceptance Criteria:**

**Given** an `InstitutionalClaimData` instance passed to the pipeline
**When** the pipeline detects the claim type (via `isinstance` check or explicit `claim_type` field)
**Then** it selects institutional validators (BillType, RevenueCode, Admission, InstitutionalCompleteness) plus shared validators (NPI, demographics, coding)
**And** routes to institutional clearinghouse endpoints when submitting
**And** `ClaimValidatorSettings` supports `institutional_rule_validators` and `institutional_ai_validators` lists
**And** existing 837P claims continue to work unchanged

---

## Epic 6: Resilient Clearinghouse Communication

All clearinghouse calls automatically retry on transient failures, circuit-break when a provider is down, and fall back to alternate clearinghouses.

### Story 6.1: Retry Decorator with Tenacity

As a developer,
I want clearinghouse HTTP calls to automatically retry on transient failures,
So that temporary network issues don't cause claim processing failures.

**Acceptance Criteria:**

**Given** the `resilience/retry.py` module with a `@retry_clearinghouse` decorator
**When** a clearinghouse HTTP call fails with a retryable error (timeout, network error, 429, 502, 503, 504)
**Then** it retries up to 3 times with exponential backoff (1s, 2s, 4s, max 30s)
**And** respects `Retry-After` header when present (overrides wait strategy)
**And** does NOT retry on client errors (400, 401, 403, 404)
**And** logs a warning before each retry attempt

### Story 6.2: Circuit Breaker per Clearinghouse

As a developer,
I want clearinghouse calls to be circuit-broken when a provider is persistently failing,
So that the system stops wasting time on a downed provider and fails fast.

**Acceptance Criteria:**

**Given** a `CircuitBreaker` class in `resilience/circuit_breaker.py`
**When** 5 consecutive failures occur within 60 seconds
**Then** the circuit opens and subsequent calls raise `CircuitOpenError` immediately (no HTTP call)
**And** after 30 seconds in OPEN state, the circuit transitions to HALF_OPEN
**And** in HALF_OPEN, one request is allowed through — success closes the circuit, failure reopens it
**And** the circuit breaker is per-instance (one per `BaseClearinghouseClient`), NOT a global singleton
**And** `CircuitOpenError` is added to `clearinghouse/exceptions.py`

### Story 6.3: Integrate Resilience into BaseClearinghouseClient

As a developer,
I want all clearinghouse clients to automatically use retry and circuit breaker,
So that I get resilient communication without configuring each client manually.

**Acceptance Criteria:**

**Given** `BaseClearinghouseClient` with updated `_make_request()` method
**When** any HTTP call is made through any clearinghouse client
**Then** the resilience chain executes in order: circuit breaker check → retry wrapper → HTTP call
**And** existing Stedi, ClaimMD, and Waystar clients gain resilience without code changes
**And** new Change Healthcare and Availity clients inherit resilience automatically
**And** circuit breaker and retry are opt-in via `[resilience]` extra — without tenacity installed, calls work without retry

### Story 6.4: Fallback Routing on Circuit Open

As a developer,
I want claims to be automatically routed to a fallback clearinghouse when the primary is down,
So that claim processing continues even during clearinghouse outages.

**Acceptance Criteria:**

**Given** a `ClearinghouseClientPool` with `PayerRouter` configured
**When** the primary clearinghouse for a payer has an open circuit
**Then** `ClearinghouseClientPool` tries the next clearinghouse from `route_with_fallback()` list
**And** if all clearinghouses for a payer have open circuits, it returns an error with `clearinghouse_unavailable` status and list of attempted providers
**And** fallback only applies to submission and eligibility — status queries must go to the original clearinghouse

---

## Epic 7: Platform — Async Claim Processing Engine

The platform accepts claims via REST API, processes them asynchronously in background workers, persists all results to PostgreSQL, and serves job status queries.

### Story 7.1: Platform Repository Scaffolding

As a platform developer,
I want the platform repository initialized with proper structure and dependencies,
So that I have a working foundation to build platform features on.

**Acceptance Criteria:**

**Given** a new `claim-validator-platform/` repository
**When** the scaffolding is complete
**Then** `pyproject.toml` declares dependency on `claim-validator[all-clearinghouses,resilience,ai,server]`
**And** `src/platform/__init__.py` exists with package structure matching architecture (tenancy/, persistence/, queue/, webhooks/, api/, observability/)
**And** `alembic.ini` is configured for PostgreSQL migrations
**And** `infrastructure/docker-compose.yml` defines PostgreSQL + Redis + API + Worker services
**And** `pip install -e .` succeeds and imports `platform` package

### Story 7.2: PostgreSQL Schema and Alembic Setup

As a platform developer,
I want the database schema created via Alembic migrations,
So that the platform has persistent storage with version-controlled schema changes.

**Acceptance Criteria:**

**Given** `persistence/tables.py` with SQLAlchemy Core table definitions
**When** `alembic upgrade head` is run against a PostgreSQL database
**Then** it creates tables: `tenants`, `claims`, `transactions`, `findings`, `audit_log`, `payer_mappings`
**And** all tables have `tenant_id` and `created_at` columns
**And** `audit_log` has no UPDATE or DELETE grants (append-only)
**And** row-level security policies are created on `claims`, `transactions`, `findings`
**And** the migration is reversible via `alembic downgrade`

### Story 7.3: Persistence Query Functions

As a platform developer,
I want query functions for all database operations,
So that the platform has a clean data access layer using SQLAlchemy Core.

**Acceptance Criteria:**

**Given** `persistence/queries/` with domain-organized modules
**When** query functions are called
**Then** `claims.create_claim(tenant_id, claim_data)` inserts and returns claim with UUID
**And** `claims.update_claim_status(claim_id, tenant_id, status, result)` updates status and pipeline_result
**And** `transactions.create_transaction(claim_id, tenant_id, clearinghouse, type, direction, payload)` inserts transaction record
**And** `findings.bulk_insert_findings(claim_id, tenant_id, findings_list)` batch inserts findings
**And** `audit.append_audit_log(tenant_id, action, actor, metadata)` inserts audit entry
**And** all queries use SQLAlchemy Core expressions (NOT ORM)
**And** all queries accept explicit `tenant_id` parameter

### Story 7.4: Celery and Redis Configuration

As a platform developer,
I want Celery workers connected to Redis as the message broker,
So that claim processing tasks can be enqueued and executed asynchronously.

**Acceptance Criteria:**

**Given** `queue/celery_app.py` with Celery application configuration
**When** a Celery worker starts
**Then** it connects to Redis broker and is ready to consume tasks
**And** `queue/worker.py` configures worker startup, concurrency, and signal handlers
**And** task serialization uses JSON (not pickle — security)
**And** task results are stored in PostgreSQL (not Redis)

### Story 7.5: Claim Processing Task and Job Lifecycle

As a platform developer,
I want a Celery task that runs the claim-validator pipeline and persists results,
So that claims are processed in the background with full audit trail.

**Acceptance Criteria:**

**Given** a `process_claim_task` in `queue/tasks.py`
**When** the task executes
**Then** it updates claim status to `"processing"` in DB
**And** calls `claim_validator.process_claim_full()` with the claim data
**And** stores pipeline_result in `claims` table
**And** creates `transactions` records for each clearinghouse interaction
**And** bulk-inserts `findings` from pipeline results
**And** updates claim status to `"completed"` or `"failed"`
**And** appends to `audit_log` for each state transition
**And** configurable timeout (default 120s) — status set to `"timeout"` on expiry

### Story 7.6: Job Status API Endpoint

As a developer using the platform API,
I want to check the status of my submitted claim processing job,
So that I know when results are ready.

**Acceptance Criteria:**

**Given** `GET /api/v1/jobs/{job_id}` endpoint
**When** called with a valid job_id
**Then** it returns `{"job_id": "...", "status": "pending|processing|completed|failed|timeout", "result": {...}}`
**And** `result` is null when status is `pending` or `processing`
**And** `result` contains full pipeline result when status is `completed`
**And** returns 404 for unknown job_id
**And** only returns jobs belonging to the authenticated tenant

---

## Epic 8: Platform — Multi-Tenant API with Isolation

Multiple customers can use the platform simultaneously with full data isolation.

### Story 8.1: Tenant Model and API Key Generation

As a platform operator,
I want to create tenants with unique API keys,
So that customers can authenticate to the platform.

**Acceptance Criteria:**

**Given** `tenancy/models.py` with tenant SQLAlchemy Core table
**When** a tenant is created
**Then** it generates a UUID tenant_id
**And** generates an API key with `cv_live_` prefix (production) or `cv_test_` prefix (sandbox)
**And** stores bcrypt hash of the API key in `tenants.api_key_hash`
**And** stores per-tenant `clearinghouse_configs` as JSONB
**And** `tenancy/api_keys.py` provides `generate_api_key()` and `verify_api_key()` functions

### Story 8.2: Authentication Middleware

As a developer using the platform API,
I want to authenticate with my API key on every request,
So that the platform knows which tenant I am and isolates my data.

**Acceptance Criteria:**

**Given** `tenancy/middleware.py` with FastAPI middleware
**When** a request includes `Authorization: Bearer cv_live_xxx`
**Then** the middleware resolves the tenant from the API key hash
**And** sets `tenant_id` in the request state for downstream use
**And** returns 401 for invalid or missing API keys
**And** sets PostgreSQL session variable `app.tenant_id` for RLS enforcement

### Story 8.3: Credential Encryption

As a platform operator,
I want tenant clearinghouse credentials encrypted at rest,
So that a database breach doesn't expose clearinghouse API keys.

**Acceptance Criteria:**

**Given** `tenancy/crypto.py` with AES-256-GCM encrypt/decrypt functions
**When** per-tenant clearinghouse credentials are stored
**Then** they are encrypted with a master key from environment variable (not in DB)
**And** `encrypt_credentials(plaintext, master_key)` returns ciphertext + nonce
**And** `decrypt_credentials(ciphertext, nonce, master_key)` returns plaintext
**And** each encryption uses a unique nonce (never reused)

### Story 8.4: Platform API Routes

As a developer using the platform API,
I want REST endpoints for submitting claims and checking eligibility,
So that I can process claims through the platform.

**Acceptance Criteria:**

**Given** the platform API routes in `api/routes/`
**When** `POST /api/v1/claims` is called with claim data and payer_id
**Then** it creates a DB record, enqueues a processing task, and returns `{"job_id": "...", "status": "pending"}` with HTTP 202
**And** `POST /api/v1/eligibility` works similarly for eligibility checks
**And** `GET /api/v1/claims/{id}` returns the claim result (pipeline_result + findings)
**And** `GET /api/v1/tenants/me` returns current tenant info
**And** all endpoints require valid API key authentication
**And** errors return consistent envelope: `{"error": {"code": "...", "message": "..."}}`

### Story 8.5: Rate Limiting and Usage Metering

As a platform operator,
I want per-tenant rate limiting and usage tracking,
So that no single tenant can overwhelm the system and I can bill based on usage.

**Acceptance Criteria:**

**Given** `api/middleware.py` with rate limiting middleware
**When** a tenant exceeds their rate limit (configurable, default 100 req/min)
**Then** it returns HTTP 429 with `Retry-After` header
**And** usage counters track per-tenant: total validations, total submissions, total API calls
**And** counters are stored in Redis for performance (flushed to DB periodically)
**And** `GET /api/v1/tenants/me` includes current period usage stats

---

## Epic 9: Platform — Webhooks & Monitoring

Tenants receive automatic webhook notifications when claims complete, operators can monitor system health.

### Story 9.1: Webhook Delivery with HMAC Signing

As a developer using the platform API,
I want to receive webhook notifications when my claims finish processing,
So that I don't need to poll for results.

**Acceptance Criteria:**

**Given** a tenant with a configured webhook URL and webhook secret
**When** a claim processing job completes (status = completed, failed, or timeout)
**Then** the platform POSTs a webhook payload to the tenant's URL
**And** the payload follows the format: `{"event": "claim.completed", "job_id": "...", "timestamp": "ISO8601", "data": {...}}`
**And** the request includes `X-Webhook-Signature` header with HMAC-SHA256(body, webhook_secret)
**And** delivery retries 3 times with exponential backoff (1s, 5s, 25s) on failure
**And** failed webhooks are stored as dead letters for manual retry

### Story 9.2: Structured Logging

As a platform operator,
I want structured JSON logs with tenant and claim context,
So that I can search and filter logs effectively in production.

**Acceptance Criteria:**

**Given** `observability/logging.py` with structlog configuration
**When** any platform operation logs a message
**Then** it outputs JSON with fields: timestamp, level, message, tenant_id, claim_id (when available), module
**And** structlog context binding automatically includes tenant_id from request middleware
**And** log levels follow: DEBUG for detailed tracing, INFO for request lifecycle, WARNING for retries, ERROR for failures

### Story 9.3: Prometheus Metrics

As a platform operator,
I want Prometheus metrics exposed for monitoring dashboards,
So that I can track system health and performance.

**Acceptance Criteria:**

**Given** `observability/metrics.py` with prometheus-client metrics
**When** the platform processes claims
**Then** it increments `claims_processed_total` counter (labels: status, clearinghouse, claim_type)
**And** records `pipeline_duration_seconds` histogram per stage
**And** tracks `celery_queue_depth` gauge for worker queue depth
**And** metrics are exposed at `GET /metrics` endpoint (Prometheus scrape target)

### Story 9.4: Health Check Endpoints

As a platform operator,
I want health check endpoints for orchestration systems,
So that load balancers and Kubernetes can determine if the service is healthy.

**Acceptance Criteria:**

**Given** `api/routes/health.py`
**When** `GET /health` is called
**Then** it returns 200 if the API process is running (liveness check)
**And** `GET /ready` returns 200 only if PostgreSQL AND Redis connections are healthy (readiness check)
**And** `GET /ready` returns 503 with details if either dependency is unreachable

### Story 9.5: Celery Beat Response Polling

As a platform operator,
I want the platform to automatically poll clearinghouses for delayed responses,
So that 277CA acknowledgments and future 835 remittances are captured without manual intervention.

**Acceptance Criteria:**

**Given** `queue/scheduler.py` with a Celery Beat periodic task
**When** the polling task runs (configurable interval, default every 5 minutes)
**Then** it queries each clearinghouse for new inbound responses (277CA, 999 acknowledgments)
**And** matches inbound responses to original submissions via claim reference ID in `transactions` table
**And** stores matched responses as new `transactions` rows with `direction: "inbound"`
**And** triggers webhook notification to tenant when a matched response is received
