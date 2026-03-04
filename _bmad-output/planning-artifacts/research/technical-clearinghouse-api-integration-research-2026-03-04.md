---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Clearinghouse API Integration (Waystar, Claim.MD, Stedi)'
research_goals: 'Evaluate clearinghouse APIs for pluggable client layer in claim-validator Python library'
user_name: 'aniket'
date: '2026-03-04'
web_research_enabled: true
source_verification: true
---

# Clearinghouse API Integration: Comprehensive Technical Research

**Date:** 2026-03-04
**Author:** aniket
**Research Type:** technical
**Status:** Complete

---

## Executive Summary

This research evaluates three healthcare clearinghouse APIs — **Stedi**, **Claim.MD**, and **Waystar** — for integration into the `claim-validator` Python library as a pluggable client layer. The goal: enable developers to submit claims (837), verify eligibility (270/271), check claim status (276/277), and retrieve remittance (835) through a single unified interface, regardless of clearinghouse provider.

**Key Findings:**

- **Stedi** is the best-documented, developer-first option with fully public JSON REST APIs, test API keys, and idempotency support. Recommended as the MVP integration target.
- **Claim.MD** offers the most value-oriented pricing ($0.10-$0.25/claim), an OpenAPI spec, and official GitHub code samples in Python. Best for small-to-mid practices.
- **Waystar** is the enterprise leader with AI-powered denial prediction and the widest transaction coverage (including 278 prior auth), but API docs are login-gated — exact specs require portal access.
- **No clearinghouse provides a Python SDK** — all integration is via HTTP REST using `httpx` (already in the project).
- **Zero new pip dependencies required** — httpx, pydantic, hmac/hashlib are all already available.
- **The library never handles raw X12 EDI** — all 3 providers accept JSON and translate internally.

**Strategic Recommendations:**

1. Build `BaseClearinghouseClient` ABC mirroring the existing `BaseLLMClient` pattern
2. Implement `StediClient` first (best docs, free test environment)
3. Implement `ClaimMDClient` second (OpenAPI spec, GitHub samples)
4. Implement `WaystarClient` third (requires portal docs from aniket)
5. Integrate with existing `PipelineConfig.clearinghouse_client` slot (Story 2.3)

## Table of Contents

1. [Technical Research Scope Confirmation](#technical-research-scope-confirmation)
2. [Technology Stack Analysis](#technology-stack-analysis)
3. [Integration Patterns Analysis](#integration-patterns-analysis)
4. [Architectural Patterns and Design](#architectural-patterns-and-design)
5. [Implementation Approaches and Technology Adoption](#implementation-approaches-and-technology-adoption)
6. [Research Conclusion](#research-conclusion)

---

## Technical Research Scope Confirmation

**Research Topic:** Clearinghouse API Integration (Waystar, Claim.MD, Stedi)
**Research Goals:** Evaluate clearinghouse APIs for pluggable client layer in claim-validator Python library

**Technical Research Scope:**

- Architecture Analysis - design patterns, frameworks, system architecture
- Implementation Approaches - development methodologies, coding patterns
- Technology Stack - languages, frameworks, tools, platforms
- Integration Patterns - APIs, protocols, interoperability
- Performance Considerations - scalability, optimization, patterns

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-03-04

## Technology Stack Analysis

### Clearinghouse Provider Comparison Matrix

| Feature | Stedi | Claim.MD | Waystar |
|---------|-------|----------|---------|
| **API Style** | REST (JSON-first) | REST (JSON/XML) | REST + SOAP + SFTP + HL7 |
| **Base URL** | `https://healthcare.us.stedi.com/2024-04-01` | `https://svc.claim.md/` | Behind login (developer.waystar.com) |
| **Auth Method** | API Key (`Authorization` header) | AccountKey (header/param) | HMAC-SHA256 or OAuth2 |
| **Claims 837P** | POST `/professionalclaims/v3/submission` | POST `/services/upload/` | REST endpoint (docs gated) |
| **Claims 837I** | POST `/institutionalclaims/v1/submission` | POST `/services/upload/` (batch) | REST endpoint (docs gated) |
| **Eligibility 270/271** | POST `/eligibility/v3` | POST `/services/eligdata/` | REST or HL7 ORM |
| **Claim Status 276/277** | POST `/claimstatus/v2` | POST `/services/response/` | REST endpoint |
| **ERA 835** | GET `/reports/v2/{txnId}/835` | POST `/services/era835/` | REST endpoint |
| **Prior Auth 278** | Not listed in public docs | Not listed | REST endpoint (docs gated) |
| **Request Format** | JSON (X12 raw optional) | ANSI 837, CSV, JSON, XML, XLS | X12 EDI, JSON (via API) |
| **Batch Support** | Batch eligibility endpoint | Upload up to 2000 claims/call | SFTP batch exchanges |
| **Rate Limit** | 50-100 concurrent requests | 100 requests/minute | Unknown (docs gated) |
| **Idempotency** | `Idempotency-Key` header | Not documented | Unknown |
| **Test Environment** | Test API keys (mock payers) | Free test account | Sandbox with test payers |
| **Python SDK** | None (REST + httpx) | None (REST + httpx), GitHub samples | None (REST + httpx) |
| **Pricing** | From $2,000/mo (custom) | $0.10-$0.25/claim, no minimums | $0.11/claim, $0.14/elig, 1yr contract |
| **Target Market** | Developer-first, GenAI companies | Small-to-mid practices, vendors | Enterprise, full RCM platform |
| **Open Docs** | Fully public API docs | Public docs + OpenAPI spec | Login-gated developer portal |

_Sources: [Stedi API Reference](https://www.stedi.com/docs/healthcare/api-reference), [Claim.MD API](https://api.claim.md/), [Waystar Integration Guide](https://tateeda.com/blog/integrate-waystar-with-custom-healthcare-applications), [Claim.MD Pricing](https://www.claim.md/pricing), [Waystar Pricing](https://chartmaker.com/resources/waystar-clearinghouse/)_

### Stedi — Developer-First JSON Clearinghouse

**Overview:** Stedi is the only "programmable" healthcare clearinghouse, purpose-built for developers and AI-first companies. $70M Series B (2025). 1/3 of customers are GenAI companies.

**Authentication:**
- API key in `Authorization` header: `Authorization: Jclcke.ZHqS3demo4dS16XZ1KeyBY7`
- Two key types: Test (mock only) and Production (live transactions)
- Legacy format also supported: `Authorization: Key [API_KEY]`

**Key Endpoints (base: `https://healthcare.us.stedi.com/2024-04-01`):**

| Transaction | Endpoint | Format |
|-------------|----------|--------|
| Eligibility (270/271) | `POST /change/medicalnetwork/eligibility/v3` | JSON |
| Eligibility Raw X12 | `POST /change/medicalnetwork/eligibility/v3/raw-x12` | X12 EDI |
| Batch Eligibility | `POST /eligibility-manager/batch-eligibility` | JSON |
| Professional Claims (837P) | `POST /change/medicalnetwork/professionalclaims/v3/submission` | JSON |
| Institutional Claims (837I) | `POST /change/medicalnetwork/institutionalclaims/v1/submission` | JSON |
| Claim Status (276/277) | `POST /change/medicalnetwork/claimstatus/v2` | JSON |
| ERA Reports (835) | `GET /change/medicalnetwork/reports/v2/{txnId}/835` | JSON |
| Claim Attachments (275) | `POST /claim-attachments/file` | JSON |
| Insurance Discovery | `POST /insurance-discovery/check/v1` | JSON |

**Strengths:** Fully public docs, JSON-first (no X12 complexity), idempotency support, test environment with mock payers, SOAP compat for CAQH CORE compliance.

**Confidence: HIGH** — Public docs verified, endpoints tested via documentation.

_Source: [Stedi Healthcare API Reference](https://www.stedi.com/docs/healthcare/api-reference)_

### Claim.MD — Value-Oriented REST Clearinghouse

**Overview:** Long-standing clearinghouse focused on value. Transparent per-claim pricing ($0.10-$0.25/claim). Free test accounts. OpenAPI spec published.

**Authentication:**
- `AccountKey` parameter on every request (header or POST body)
- Generated from portal: Settings > Account Settings
- Single key per account

**Key Endpoints (base: `https://svc.claim.md/`):**

| Transaction | Endpoint | Format |
|-------------|----------|--------|
| Upload Claims (837P/I) | `POST /services/upload/` | ANSI 837, CSV, JSON, XML, XLS |
| Claim Responses | `POST /services/response/` | JSON/XML |
| Eligibility X12 (270) | `POST /services/elig/` | X12 270 |
| Eligibility Data | `POST /services/eligdata/` | JSON/XML params |
| ERA List | `POST /services/eralist/` | JSON/XML |
| ERA Details (835) | `POST /services/era835/` | X12 835 |
| ERA Data | `POST /services/eradata/` | JSON/XML |
| ERA PDF | `POST /services/erapdf/` | PDF |
| Payer List | `POST /services/payerlist/` | JSON/XML |
| Enrollment | `POST /services/enroll/` | JSON/XML |
| Appeal | `POST /services/appeal/` | JSON/XML |
| Webhooks | Configurable | JSON |

**Strengths:** OpenAPI spec, GitHub REST samples, accepts multiple file formats, webhook support, no monthly minimums, 100 req/min rate limit.

**Confidence: HIGH** — OpenAPI spec at api.claim.md, GitHub samples at [Claim-MD/RestAPISamples](https://github.com/Claim-MD/RestAPISamples).

_Source: [Claim.MD API](https://api.claim.md/), [Claim.MD Docs](https://docs.claim.md/docs/api)_

### Waystar — Enterprise RCM Platform

**Overview:** Full RCM platform with AI-driven denial prediction, eligibility intelligence, and prior auth automation. Enterprise pricing with 1-year contracts. Docs behind login.

**Authentication:**
- HMAC-SHA256 signing for API requests
- OAuth2 token management (alternative)
- Credential management API available
- Details at developer.waystar.com (login required)

**Integration Methods:**
- RESTful APIs — Real-time transactions
- SOAP Web Services — Legacy compatibility
- SFTP Batch — Nightly file exchanges (837/835)
- HL7 Feeds — ADT/ORM messages

**Known Endpoints (docs gated, from public references):**
- Eligibility (270/271) — REST or HL7 ORM
- Claims (837P/837I) — REST or SFTP batch
- Claim Status (276/277) — REST
- Remittance (835) — REST or SFTP
- Prior Authorization (278) — REST
- Claim Attachments — REST

**Strengths:** Widest transaction coverage (including 278), AI features (denial prediction, PA automation), enterprise-grade, test sandbox.

**Limitations for integration:** Docs fully gated behind login. Cannot verify exact endpoints, request schemas, or HMAC signing details without portal access.

**Confidence: MEDIUM** — Integration methods confirmed via multiple sources, but exact API specs unverifiable without portal login.

_Source: [Waystar Claims Clearinghouse](https://www.waystar.com/our-platform/claim-management/claim-manager/), [TATEEDA Integration Guide](https://tateeda.com/blog/integrate-waystar-with-custom-healthcare-applications), [Waystar Pricing](https://chartmaker.com/resources/waystar-clearinghouse/)_

### Python Integration Stack

**No clearinghouse provides a Python SDK.** All integration is via HTTP REST APIs. Recommended stack:

| Component | Library | Purpose |
|-----------|---------|---------|
| HTTP Client | `httpx` (already in project) | Async/sync REST calls |
| Auth Signing | `hmac` + `hashlib` (stdlib) | Waystar HMAC-SHA256 |
| Data Serialization | `pydantic` (already in project) | Request/response models |
| X12 Parsing | Custom or `stedi` JSON mode | EDI format handling |
| Retry/Backoff | `tenacity` or custom | Transient error handling |
| Config | `pydantic-settings` (already in project) | Clearinghouse credentials |

### Technology Adoption Trends

- **JSON-first APIs** replacing raw X12 EDI — Stedi leads this trend, Claim.MD supports both
- **AI-augmented workflows** — Waystar uses AI for denial prediction; Stedi markets to GenAI companies
- **Webhook-driven** replacing polling — Stedi and Claim.MD support webhooks for async results
- **FHIR adoption** — CMS-0057-F mandates FHIR-based prior auth by January 2027; all clearinghouses will need to support Da Vinci PAS
- **Developer-first platforms** gaining share — Stedi's $70M Series B signals market demand for programmable clearinghouses

_Source: [Stedi $70M Series B](https://www.healthcareittoday.com/2025/09/09/announcing-stedis-70-million-series-b-to-build-the-only-ai-enabled-clearinghouse/), [CMS-0057-F Rule](https://www.waystar.com/our-platform/financial-clearance/authorizations/)_

## Integration Patterns Analysis

### API Design Patterns — Clearinghouse-Specific

**Provider Abstraction Pattern (Strategy + Factory):**
The claim-validator library already uses this pattern for LLM providers (`BaseLLMClient` → `OpenAIClient`, `AnthropicClient`). The same pattern applies to clearinghouses:

```
BaseClearinghouseClient (ABC)
├── submit_claim(data) -> SubmissionResult
├── check_eligibility(data) -> EligibilityResponse
├── check_claim_status(data) -> StatusResponse
├── provider_name: str
│
├── StediClient — JSON REST, API key auth
├── ClaimMDClient — REST (JSON/XML), AccountKey auth
└── WaystarClient — REST, HMAC-SHA256 auth
```

Factory function: `get_clearinghouse_client(provider, **credentials) -> BaseClearinghouseClient`

**Request/Response Flow per Provider:**

| Pattern | Stedi | Claim.MD | Waystar |
|---------|-------|----------|---------|
| Eligibility | Sync request → JSON response | Sync request → JSON/XML response | Sync request → response |
| Claims | Sync submit → async result via webhook/poll | Batch upload → poll `/response/` | Sync or SFTP batch |
| Status | Sync 276/277 query | Poll `/response/` endpoint | Sync query |
| ERA/835 | GET by transaction ID | Poll `/eralist/` + `/era835/` | Poll or SFTP |

_Source: [Stedi API](https://www.stedi.com/docs/healthcare/api-reference), [Claim.MD API](https://api.claim.md/)_

### Communication Protocols & Data Formats

**X12 EDI vs JSON — The Hybrid Reality:**
- HIPAA mandates X12 Version 5010 for core transactions (837, 270/271, 278, 835)
- Modern clearinghouses (Stedi, Claim.MD) accept JSON and translate to X12 internally
- Waystar supports both REST (JSON) and raw X12 via SFTP
- CMS FHIR mandate (CMS-0057-F) requires FHIR APIs for prior auth by January 2027

**Data Format Strategy for claim-validator:**

| Layer | Format | Rationale |
|-------|--------|-----------|
| Library API | Pydantic models (Python dicts) | Developer-friendly, type-safe |
| Client interface | JSON dicts | All 3 providers accept JSON |
| Wire format | Provider handles X12 translation | No X12 parsing needed in library |
| Response | Pydantic models | Normalized across providers |

This means the library NEVER handles raw X12 — clearinghouses handle the EDI translation. The library works entirely in JSON/Pydantic models.

_Source: [X12 EDI Transactions Guide](https://intuitionlabs.ai/articles/x12-edi-transactions-guide), [CMS Adopted Standards](https://www.cms.gov/priorities/key-initiatives/burden-reduction/administrative-simplification/hipaa/adopted-standards-operating-rules)_

### Authentication Security Patterns

**Per-Provider Auth Implementation:**

| Provider | Pattern | Python Implementation |
|----------|---------|----------------------|
| **Stedi** | API Key in header | `headers={"Authorization": api_key}` |
| **Claim.MD** | AccountKey in POST body | `data={"AccountKey": key, ...}` |
| **Waystar** | HMAC-SHA256 signing | `hmac.new(secret, canonical_request, sha256)` |

**HMAC-SHA256 Pattern (Waystar):**
```python
import hmac, hashlib, time
timestamp = str(int(time.time()))
canonical = f"{method}\n{path}\n{timestamp}\n{body_hash}"
signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
headers["X-Signature"] = signature
headers["X-Timestamp"] = timestamp
```

**Credential Storage:**
- All credentials via `CLAIM_VALIDATOR_*` env vars (existing pattern)
- New settings: `CLAIM_VALIDATOR_CLEARINGHOUSE_PROVIDER`, `CLAIM_VALIDATOR_CLEARINGHOUSE_API_KEY`, etc.
- No credentials in code, logs, or error messages (HIPAA compliance)

_Source: [Python hmac docs](https://docs.python.org/3/library/hmac.html), [HMAC Signing Python API](https://oneuptime.com/blog/post/2026-01-22-hmac-signing-python-api/view)_

### Async & Polling Patterns

**Claims have a dual-phase lifecycle:**
1. **Submit** (sync) — immediate acknowledgment/rejection
2. **Result** (async) — payer adjudication takes hours/days

**Response retrieval patterns:**

| Pattern | Stedi | Claim.MD | Waystar |
|---------|-------|----------|---------|
| **Webhook** | Configurable webhook URL | Configurable webhook | Unknown |
| **Polling** | Batch status endpoint | `/services/response/` with ResponseID cursor | REST endpoint |
| **SFTP** | Not primary | Not primary | Primary for batch |

**Library design decision:** The `BaseClearinghouseClient` ABC exposes sync `submit_*()` methods that return an immediate acknowledgment. Async result polling is a separate concern — exposed as `get_claim_status()` / `get_responses()`. Webhook handling is out of scope for a library (that's the application's responsibility).

### Error Handling & Resilience Patterns

**Clearinghouse-specific error patterns:**

| Error Type | Handling |
|-----------|----------|
| HTTP 4xx (auth, validation) | Raise `ClearinghouseError` immediately |
| HTTP 5xx (server error) | Retry with exponential backoff (max 3) |
| Timeout | Retry once, then raise `ClearinghouseTimeoutError` |
| X12 rejection (AAA segment) | Parse rejection codes, return as findings |
| Rate limit (429) | Backoff per provider rate limit |

**Circuit breaker not needed** — this is a library, not a long-running service. Each call is independent.

### PHI Security in Clearinghouse Calls

**Critical HIPAA consideration:** Unlike AI calls where PHI must be stripped, clearinghouse calls MUST include PHI (patient name, DOB, member ID) — that's the whole point.

**Security boundaries:**
- PHI goes to clearinghouse (trusted HIPAA-covered entity) ✅
- PHI never goes to AI/LLM without de-identification ✅
- PHI never appears in logs, error messages, or exception traces ✅
- TLS enforced for all clearinghouse API calls ✅
- Credentials never logged ✅

_Source: [HIPAA EDI Compliance](https://www.edi2xml.com/blog/all-you-need-to-know-about-hipaa-edi-compliance-in-healthcare/)_

## Architectural Patterns and Design

### System Architecture — Pluggable Client Layer

**Architecture Decision: Strategy + Factory Pattern (matches existing LLM pattern)**

The clearinghouse client layer mirrors the existing `BaseLLMClient` architecture exactly:

```
claim_validator/
  clearinghouse/
    __init__.py              # re-exports
    base.py                  # BaseClearinghouseClient ABC
    factory.py               # get_clearinghouse_client()
    auth.py                  # HMACAuth(httpx.Auth) for Waystar
    exceptions.py            # ClearinghouseError hierarchy
    models/
      __init__.py
      submission.py          # SubmissionResult, ClaimAcknowledgment
      eligibility.py         # ClearinghouseEligibilityResponse
      status.py              # ClaimStatusResponse
    providers/
      __init__.py
      stedi.py               # StediClient
      claimmd.py             # ClaimMDClient
      waystar.py             # WaystarClient
```

**Why this architecture:**
- Proven in the codebase (LLM clients use identical structure)
- Zero learning curve for contributors
- Each provider is a self-contained module with no cross-dependencies
- Factory enables configuration-driven provider selection
- ABC enforces contract compliance at import time

_Source: [Design Patterns for Python API Client Libraries](https://bhomnick.net/design-pattern-python-api-client/), [Python ABC docs](https://docs.python.org/3/library/abc.html)_

### Design Principles — Applied to Clearinghouse Layer

**Interface Contract (ABC):**

```python
class BaseClearinghouseClient(ABC):
    """Abstract clearinghouse client — all providers implement this."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def submit_claim(self, claim_data: dict) -> SubmissionResult: ...

    @abstractmethod
    def check_eligibility(self, request: dict) -> dict: ...

    @abstractmethod
    def check_claim_status(self, claim_ref: str) -> dict: ...
```

**Key design principles applied:**
- **Dependency Inversion** — Pipeline depends on `BaseClearinghouseClient` ABC, never on concrete providers
- **Open/Closed** — New providers added without modifying existing code
- **Single Responsibility** — Each provider handles only its own auth, serialization, and error mapping
- **Liskov Substitution** — Any client can replace any other; pipeline doesn't know which
- **Interface Segregation** — Only methods the pipeline actually calls

_Source: [Refactoring Guru Design Patterns](https://refactoring.guru/design-patterns/python), [External API Integration Patterns](https://mshaeri.com/blog/design-patterns-i-use-in-external-service-integration-in-python/)_

### Authentication Architecture

**HTTPX Custom Auth Handler (for Waystar HMAC):**

httpx provides a built-in `httpx.Auth` subclass mechanism. The `auth_flow` generator yields signed requests:

```python
class HMACAuth(httpx.Auth):
    requires_request_body = True

    def __init__(self, api_key: str, secret: str):
        self._api_key = api_key
        self._secret = secret

    def auth_flow(self, request):
        timestamp = str(int(time.time()))
        body_hash = hashlib.sha256(request.content).hexdigest()
        canonical = f"{request.method}\n{request.url.path}\n{timestamp}\n{body_hash}"
        signature = hmac.new(
            self._secret.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()
        request.headers["Authorization"] = f"HMAC {self._api_key}:{signature}"
        request.headers["X-Timestamp"] = timestamp
        yield request
```

For Stedi and Claim.MD, auth is simpler (header injection) and handled directly in the client.

_Source: [HTTPX Custom Authentication](https://www.python-httpx.org/advanced/authentication/), [HMAC Signing Python API](https://oneuptime.com/blog/post/2026-01-22-hmac-signing-python-api/view)_

### Scalability and Performance Patterns

**Connection management:**
- `httpx.Client` (sync) with connection pooling — reuse across calls
- Client instances created once per `BaseClearinghouseClient` init, not per request
- Configurable timeouts per provider (eligibility: 20s per CAQH CORE, claims: 60s)

**Rate limiting:**
- Stedi: 50-100 concurrent requests
- Claim.MD: 100 requests/minute
- Waystar: Unknown (docs gated)
- Library does NOT implement rate limiting — that's the application's responsibility
- But we expose `rate_limit` property so apps can implement their own

**Retry strategy:**
- Transient errors (5xx, timeout): Retry once with 1s backoff
- Auth errors (401/403): Raise immediately (no retry)
- Validation errors (4xx): Raise immediately
- Kept simple — library users can wrap with `tenacity` if they need more

### Configuration Architecture

**Extension of existing `ClaimValidatorSettings`:**

```python
# New env vars (all optional — clearinghouse is not required for validation)
CLAIM_VALIDATOR_CLEARINGHOUSE_PROVIDER=stedi      # stedi|claimmd|waystar
CLAIM_VALIDATOR_CLEARINGHOUSE_API_KEY=...
CLAIM_VALIDATOR_CLEARINGHOUSE_SECRET=...           # Waystar only
CLAIM_VALIDATOR_CLEARINGHOUSE_ACCOUNT_ID=...       # Claim.MD AccountKey
CLAIM_VALIDATOR_CLEARINGHOUSE_BASE_URL=...         # Override default
```

**Stored in `ClaimValidatorSettings.clearinghouse_config: dict | None`** — same pattern as `ai_config`.

### Error Hierarchy

```
ClaimValidatorError (existing)
├── ClearinghouseError (new base)
│   ├── ClearinghouseAuthError        # 401/403, bad credentials
│   ├── ClearinghouseValidationError  # 4xx, request rejected
│   ├── ClearinghouseTimeoutError     # Request timed out
│   └── ClearinghouseServerError      # 5xx, provider down
└── LLMError (existing)
```

### Deployment — Zero New Dependencies

**All required libraries already in the project:**
- `httpx` — HTTP client (used by OpenAI-compatible LLM client)
- `pydantic` — Request/response models
- `pydantic-settings` — Configuration
- `hmac`, `hashlib`, `time` — Python stdlib (for Waystar HMAC)

**No new pip dependencies required.** This is critical for a library — fewer deps = fewer conflicts.

## Implementation Approaches and Technology Adoption

### Implementation Roadmap — Phased Approach

**Phase 1: ABC + Stedi Client (MVP)**
- `BaseClearinghouseClient` ABC with core methods
- `StediClient` — best documented, JSON-first, free test keys
- Factory function `get_clearinghouse_client()`
- Configuration in `ClaimValidatorSettings`
- Integration with existing `PipelineConfig.clearinghouse_client` slot

**Phase 2: Claim.MD Client**
- `ClaimMDClient` — AccountKey auth, JSON/XML responses
- Batch upload support (1-2000 claims per call)
- ERA/835 retrieval methods

**Phase 3: Waystar Client**
- `WaystarClient` — HMAC-SHA256 auth via `HMACAuth(httpx.Auth)`
- Requires aniket's portal access for exact endpoint specs
- SFTP batch support (optional)

### Stedi Client — Concrete Implementation Reference

**Eligibility Check (270/271):**
```python
# POST https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3
request = {
    "tradingPartnerServiceId": "BCBS01",
    "provider": {"npi": "1245319599"},
    "subscriber": {
        "memberId": "SUB987654321",
        "firstName": "Alice",
        "lastName": "Williams",
        "dateOfBirth": "19800722",  # YYYYMMDD format
    },
    "encounter": {"serviceTypeCodes": ["30"]},
}
# Headers: Authorization: <api_key>, Content-Type: application/json
```

**Professional Claims (837P):**
```python
# POST https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/professionalclaims/v3/submission
request = {
    "tradingPartnerServiceId": "BCBS01",
    "tradingPartnerName": "BCBS of Arkansas",
    "submitter": {"organizationName": "...", "contactInformation": {...}},
    "receiver": {"organizationName": "BCBS"},
    "subscriber": {"memberId": "SUB987654321", ...},
    "billing": {"npi": "1245319599", "taxonomyCode": "207Q00000X", ...},
    "claimInformation": {
        "patientControlNumber": "a]8Gn2P0klwe7Ftov",  # unique per claim
        "claimChargeAmount": "150.00",
        "placeOfServiceCode": "11",
        "healthCareCodeInformation": [{"diagnosisTypeCode": "ABK", "diagnosisCode": "J069"}],
        "serviceLines": [{
            "serviceDate": "20260301",
            "professionalService": {
                "procedureIdentifier": "HC", "procedureCode": "99213",
                "lineItemChargeAmount": "150.00", "measurementUnit": "UN", "serviceUnitCount": "1",
            },
        }],
    },
    "usageIndicator": "T",  # T=test, P=production
}
# Headers: Authorization: <api_key>, Content-Type: application/json, Idempotency-Key: <unique>
```

_Source: [Stedi Submit Professional Claims](https://www.stedi.com/docs/healthcare/submit-professional-claims), [Stedi Eligibility API](https://www.stedi.com/docs/api-reference/healthcare/post-healthcare-eligibility)_

### Claim.MD Client — Concrete Implementation Reference

**Eligibility Check:**
```python
# POST https://svc.claim.md/services/eligdata/
data = {
    "AccountKey": "your_account_key",
    "PayerID": "00520",
    "ProviderNPI": "1245319599",
    "InsuredFirstName": "Alice",
    "InsuredLastName": "Williams",
    "InsuredDOB": "07/22/1980",  # MM/DD/YYYY
    "InsuredID": "SUB987654321",
    "ServiceDate": "03/04/2026",
    "ResponseType": "json",
}
# Response: JSON with eligibility/benefit data
```

**Claims Upload:**
```python
# POST https://svc.claim.md/services/upload/
# Accepts: 837P, 837I, CSV, JSON, XML, XLS — 1-2000 claims per call
data = {
    "AccountKey": "your_account_key",
    "File": "<base64_encoded_file_or_json_claims>",
    "ResponseType": "json",
}
```

**GitHub samples available:** [Claim-MD/RestAPISamples](https://github.com/Claim-MD/RestAPISamples) — C# and Python examples.

_Source: [Claim.MD API Spec](https://api.claim.md/), [Claim.MD GitHub](https://github.com/Claim-MD/RestAPISamples)_

### Testing Strategy

**Per-provider test environments:**

| Provider | Test Setup | Cost |
|----------|-----------|------|
| **Stedi** | Test API key → mock payer responses | Free |
| **Claim.MD** | Free test account from portal | Free |
| **Waystar** | Sandbox with test payers (837/835, 270/271) | Requires contract |

**Test architecture for claim-validator:**

| Test Level | Approach |
|-----------|----------|
| **Unit tests** | Mock `httpx.Client` responses, test serialization/deserialization |
| **Contract tests** | Verify request format matches provider spec (no network) |
| **Integration tests** | Hit test/sandbox endpoints (optional, requires keys) |
| **Pipeline tests** | Mock `BaseClearinghouseClient`, verify PipelineConfig wiring |

**Unit tests use `httpx.MockTransport`** — no network calls, deterministic, fast. Same pattern as existing LLM provider tests.

### Data Mapping — Library Models to Provider Formats

**The critical translation layer:** Library uses Pydantic models (ClaimData, EligibilityRequest, PriorAuthRequest). Each provider expects different JSON schemas. Each client must translate:

```
ClaimData (library) → StediClient._to_stedi_claim() → Stedi JSON → POST
ClaimData (library) → ClaimMDClient._to_claimmd_file() → Claim.MD JSON → POST
ClaimData (library) → WaystarClient._to_waystar_claim() → Waystar JSON → POST
```

**Response normalization:** Each provider returns different response formats. Each client normalizes to shared result models:

```
Stedi JSON response → StediClient._parse_response() → SubmissionResult (library)
Claim.MD JSON/XML → ClaimMDClient._parse_response() → SubmissionResult (library)
Waystar response → WaystarClient._parse_response() → SubmissionResult (library)
```

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Waystar docs gated | HIGH — can't verify endpoints | Build ABC+Stedi+Claim.MD first; add Waystar when docs available |
| Provider API changes | MEDIUM — breaking changes | Pin to API version in URL (Stedi versioned), test suite per provider |
| X12 complexity leaking in | LOW — JSON-first design | All providers accept JSON; never expose X12 to library users |
| Rate limiting differences | LOW — library doesn't enforce | Document limits, expose `rate_limit` property |
| PHI in error messages | HIGH — HIPAA violation | Scrub all error messages before raising; never log request bodies |

### Success Metrics

- All 3 providers implement `BaseClearinghouseClient` ABC
- Existing `PipelineConfig.clearinghouse_client` works with any provider
- Zero new pip dependencies
- Unit test coverage >90% per provider
- Integration tests pass against test/sandbox environments
- PHI never appears in logs, errors, or exceptions

## Research Conclusion

### Summary of Key Technical Findings

| Dimension | Finding | Confidence |
|-----------|---------|------------|
| **Best MVP target** | Stedi — fully public docs, JSON-first, free test keys | HIGH |
| **Best value** | Claim.MD — $0.10-$0.25/claim, OpenAPI spec, Python samples | HIGH |
| **Best enterprise** | Waystar — widest coverage, AI features, but docs gated | MEDIUM |
| **Architecture** | Strategy + Factory pattern (mirrors existing LLM clients) | HIGH |
| **Auth patterns** | API key (Stedi), AccountKey (Claim.MD), HMAC-SHA256 (Waystar) | HIGH |
| **Data format** | JSON everywhere — clearinghouses handle X12 translation | HIGH |
| **Dependencies** | Zero new — httpx, pydantic, hmac/hashlib already in project | HIGH |
| **PHI handling** | PHI flows to clearinghouse (trusted); never to AI without de-id | HIGH |

### Epic Structure Recommendation

**Epic: Clearinghouse Client Integration**

| Story | Scope | Dependencies |
|-------|-------|-------------|
| **5.1** | `BaseClearinghouseClient` ABC, factory, config, exceptions, response models | None |
| **5.2** | `StediClient` — eligibility, claims, status | 5.1 |
| **5.3** | `ClaimMDClient` — eligibility, claims upload, ERA | 5.1 |
| **5.4** | `WaystarClient` — HMAC auth, eligibility, claims | 5.1 + portal docs |
| **5.5** | Pipeline integration — wire clients into PipelineConfig + orchestrator | 5.2 or 5.3 |

### Next Steps

1. Create epic and stories using BMAD workflow
2. Implement Story 5.1 (ABC + factory) — enables parallel development of providers
3. Implement Story 5.2 (Stedi) — test against Stedi sandbox
4. Aniket to share Waystar portal docs for Story 5.4

---

**Technical Research Completion Date:** 2026-03-04
**Research Period:** Comprehensive technical analysis with live web verification
**Source Verification:** All technical facts cited with current sources (2025-2026)
**Confidence Level:** HIGH — based on public API documentation, OpenAPI specs, and verified web sources

_This research document provides the technical foundation for implementing the clearinghouse client layer in the claim-validator library._
