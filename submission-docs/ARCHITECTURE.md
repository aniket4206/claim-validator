# Healthcare Claim Validation & Analytics System — Architecture Document

## 1. Project Overview

This system is a **comprehensive healthcare claim validation and analytics platform** composed of two integrated components:

| Component | Role | Technology |
|-----------|------|------------|
| **claim-validator** | Reusable Python validation library | Python 3.11+, Pydantic 2.x |
| **healthcare-claim-analyzer** | Full-stack Django REST API service | Django 5.x, DRF, Celery, PostgreSQL |

The system validates healthcare professional claims (CMS-1500 / 837P format) through a **dual-phase pipeline** — deterministic rule-based checks followed by AI-powered clinical analysis — before submitting them to the **ClaimMD** clearinghouse.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                 │
│  REST API Clients  │  MCP Server (Claude Code)  │  Django Admin     │
└────────┬────────────────────┬────────────────────────┬──────────────┘
         │                    │                        │
         ▼                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     API LAYER (Django REST Framework)               │
│                                                                     │
│  Claims CRUD  │  Validation  │  Submission  │  Eligibility │ Analytics│
│  /api/v1/claims/             /api/v1/analytics/                     │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                                   │
│                                                                     │
│  ValidationService  │  SubmissionService  │  EligibilityService     │
│  AnalyticsService   │  AIService                                    │
└────────┬────────────────────┬───────────────────────┬───────────────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌──────────────────┐ ┌────────────────┐ ┌─────────────────────────────┐
│ VALIDATION       │ │ EXTERNAL       │ │ ASYNC TASK QUEUE            │
│ PIPELINE         │ │ INTEGRATIONS   │ │ (Celery + Redis)            │
│                  │ │                │ │                             │
│ Phase 1: Rules   │ │ ClaimMD Client │ │ validate_claim_task         │
│  (8 validators)  │ │ LLM Client     │ │ submit_claims_task          │
│                  │ │  ├ Anthropic   │ │ check_eligibility_task      │
│ Phase 2: AI      │ │  ├ OpenAI     │ │ poll_all_batches (5 min)    │
│  (3 validators)  │ │  └ Compatible │ │ analyze_rejection_patterns  │
│                  │ │                │ │  (daily 2:00 AM)            │
│ De-identification│ │ Rate Limiter   │ │                             │
└────────┬─────────┘ └────────┬───────┘ └──────────────┬──────────────┘
         │                    │                        │
         ▼                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DATA LAYER                                      │
│                                                                     │
│  PostgreSQL / SQLite                                                │
│  ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────┐   │
│  │  Claim    │ │ Validation   │ │ Submission  │ │ Rejection    │   │
│  │  ClaimLine│ │ Result       │ │ Batch       │ │ History      │   │
│  └──────────┘ │ Finding      │ └─────────────┘ │ Pattern      │   │
│               └──────────────┘                  └──────────────┘   │
│  ┌──────────────┐ ┌──────────────┐                                 │
│  │ Eligibility  │ │ AuditLog     │  ← Immutable (HIPAA)           │
│  │ Check        │ │ (encrypted)  │                                 │
│  └──────────────┘ └──────────────┘                                 │
│                                                                     │
│  PHI Encryption: Fernet (django-encrypted-model-fields)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Validation Pipeline Architecture

```
                     ┌─────────────┐
                     │  ClaimData   │
                     │  (CMS-1500)  │
                     └──────┬──────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   PHASE 1: RULE-BASED   │
              │   (Deterministic, Fast) │
              ├─────────────────────────┤
              │ 1. CompletenessValidator│ ← Required fields check
              │ 2. NPIValidator         │ ← Luhn check-digit
              │ 3. SubscriberIDValidator│ ← Member ID format
              │ 4. DemographicsValidator│ ← DOB, gender, age
              │ 5. CodingValidator      │ ← ICD-10, CPT/HCPCS
              │ 6. MonetaryValidator    │ ← Charges, totals
              │ 7. DuplicateValidator   │ ← Duplicate detection
              │ 8. TimelyFilingValidator│ ← Filing deadlines
              └──────────┬──────────────┘
                         │
                    Has Errors?
                    ┌────┴────┐
                    │ YES     │ NO
                    ▼         ▼
              Skip AI?   ┌────────────────────────┐
              (config)   │   DE-IDENTIFICATION     │
                │        │   (HIPAA Safe Harbor)   │
                │        │   Strips 18 identifiers │
                │        └────────────┬────────────┘
                │                     │
                │                     ▼
                │        ┌─────────────────────────┐
                │        │   PHASE 2: AI-POWERED   │
                │        │   (LLM Analysis)        │
                │        ├─────────────────────────┤
                │        │ 1. CodeValidationAI     │ ← Clinical plausibility
                │        │ 2. CoverageCheckAI      │ ← Coverage likelihood
                │        │ 3. PriorAuthAI          │ ← Prior auth needs
                │        └────────────┬────────────┘
                │                     │
                ▼                     ▼
              ┌─────────────────────────────┐
              │       PipelineResult        │
              │  ┌─────────┐ ┌───────────┐ │
              │  │ Errors   │ │ Warnings  │ │
              │  │ (FAIL)   │ │ (PASS)    │ │
              │  └─────────┘ └───────────┘ │
              │  passed = (errors == 0)     │
              └─────────────────────────────┘
```

---

## 4. Data Model Relationships

```
                    ┌──────────────┐
                    │    Claim     │
                    │  (CMS-1500)  │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────────────────┐
          │                │                │            │
          ▼                ▼                ▼            ▼
   ┌────────────┐  ┌──────────────┐ ┌───────────┐ ┌──────────┐
   │ ClaimLine  │  │ Validation   │ │ Rejection │ │Eligibility│
   │ (1..N)     │  │ Result       │ │ History   │ │ Check    │
   └────────────┘  └──────┬───────┘ └─────┬─────┘ └──────────┘
                          │               │
                          ▼               ▼
                   ┌──────────────┐ ┌───────────┐
                   │ Validation   │ │ Rejection │
                   │ Finding      │ │ Pattern   │
                   │ (1..N)       │ └───────────┘
                   └──────────────┘

   ┌───────────────┐     ┌──────────────┐
   │ Submission     │     │  AuditLog    │
   │ Batch         │     │ (Immutable)  │
   └───────────────┘     └──────────────┘
```

---

## 5. Claim Lifecycle State Machine

```
  ┌─────────┐
  │  DRAFT  │
  └────┬────┘
       │ validate()
       ▼
  ┌──────────────┐
  │  VALIDATING  │
  └──────┬───────┘
         │
    ┌────┴──────┐
    ▼           ▼
┌─────────┐ ┌────────────────────┐
│VALIDATED│ │ VALIDATION_FAILED  │
└────┬────┘ └────────────────────┘
     │ submit()
     ▼
┌────────────┐
│ SUBMITTING │
└─────┬──────┘
      ▼
┌────────────┐
│ SUBMITTED  │
└─────┬──────┘
      │ poll_status()
      ▼
┌──────────────┐
│ ACKNOWLEDGED │
└──────┬───────┘
       │
  ┌────┴────────┬──────────┐
  ▼             ▼          ▼
┌──────┐  ┌──────────┐ ┌────────┐
│ PAID │  │ REJECTED │ │ DENIED │
└──────┘  └────┬─────┘ └────────┘
               │ appeal()
               ▼
          ┌───────────┐
          │ APPEALING │
          └───────────┘
```

---

## 6. Technology Stack

### 6.1 claim-validator (Library)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11+ | Core runtime |
| Data Validation | Pydantic 2.x | Model validation, frozen models |
| Configuration | Pydantic Settings | Environment-based config |
| AI/LLM | Anthropic SDK, OpenAI SDK, httpx | Multi-provider LLM support |
| Code Tables | gzip + JSON | ICD-10, HCPCS, Taxonomy, POS |
| Testing | pytest, factory-boy | Comprehensive test suite |
| Quality | ruff, mypy (strict) | Linting, type checking |

### 6.2 healthcare-claim-analyzer (Service)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web Framework | Django 5.2 | Backend framework |
| API | Django REST Framework 3.16 | REST API endpoints |
| Task Queue | Celery 5.6 + Redis | Async processing |
| Database | PostgreSQL (prod) / SQLite (dev) | Data persistence |
| Encryption | django-encrypted-model-fields | PHI encryption at rest |
| HTTP Client | httpx | ClaimMD API communication |
| AI/LLM | Anthropic Claude SDK | AI-powered validation |
| MCP Server | mcp 1.26 | Claude Code integration |
| Audit | django-auditlog | Compliance logging |

---

## 7. Security & HIPAA Compliance

### 7.1 PHI Protection Layers

```
┌───────────────────────────────────────────────────────┐
│                SECURITY LAYERS                        │
├───────────────────────────────────────────────────────┤
│                                                       │
│  Layer 1: ENCRYPTION AT REST                         │
│  ├─ Fernet encryption for all PHI fields             │
│  ├─ Subscriber name, ID, address                     │
│  ├─ Patient name, DOB                                │
│  └─ django-encrypted-model-fields                    │
│                                                       │
│  Layer 2: DE-IDENTIFICATION BEFORE AI                │
│  ├─ HIPAA Safe Harbor method                         │
│  ├─ Strips all 18 identifiers before LLM calls      │
│  ├─ Retains: codes, charges, age, gender, state      │
│  └─ Removes: names, DOB, SSN, member ID, address    │
│                                                       │
│  Layer 3: IMMUTABLE AUDIT LOGGING                    │
│  ├─ Every PHI access logged                          │
│  ├─ Actions: CREATE, READ, UPDATE, DELETE, SUBMIT    │
│  ├─ User, IP, timestamp, resource tracked            │
│  └─ AuditLog.save() prevents modifications           │
│                                                       │
│  Layer 4: EXCEPTION SCRUBBING                        │
│  ├─ PHIFilterMiddleware                              │
│  └─ Removes SSN/DOB patterns from error messages     │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 8. External Integration Architecture

```
┌──────────────────┐          ┌──────────────────────┐
│   Our System     │          │   ClaimMD            │
│                  │  HTTPS   │   Clearinghouse      │
│  SubmissionSvc ──┼─────────►│   upload_claims()    │
│  EligibilitySvc ─┼─────────►│   check_eligibility()│
│  PollingTask ────┼─────────►│   poll_responses()   │
│                  │          │                      │
│  Rate Limiter:   │          │   → Payers (BCBS,    │
│  100 req/min     │          │     Aetna, UHC, etc.)│
└──────────────────┘          └──────────────────────┘

┌──────────────────┐          ┌──────────────────────┐
│   Our System     │          │   LLM Providers      │
│                  │  HTTPS   │                      │
│  AI Validators ──┼─────────►│   Anthropic (Claude) │
│  (de-identified  │          │   OpenAI (GPT-4)     │
│   claims only)   │          │   Ollama (local)     │
│                  │          │   vLLM, LocalAI      │
└──────────────────┘          └──────────────────────┘
```

---

## 9. API Endpoint Map

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/claims/` | List claims (with filters) |
| POST | `/api/v1/claims/` | Create claim with lines |
| GET | `/api/v1/claims/{id}/` | Get claim detail |
| PUT | `/api/v1/claims/{id}/` | Update claim |
| DELETE | `/api/v1/claims/{id}/` | Delete claim |
| POST | `/api/v1/claims/{id}/validate/` | Validate claim |
| POST | `/api/v1/claims/batch-validate/` | Batch validate |
| GET | `/api/v1/claims/{id}/validations/` | Validation history |
| POST | `/api/v1/claims/{id}/submit/` | Submit to ClaimMD |
| POST | `/api/v1/claims/batch-submit/` | Batch submit |
| POST | `/api/v1/claims/{id}/eligibility/` | Check eligibility |
| GET | `/api/v1/analytics/rejection-summary/` | Rejection stats |
| GET | `/api/v1/analytics/rejection-trends/` | Weekly trends |
| GET | `/api/v1/analytics/validator-effectiveness/` | Validator metrics |
| GET | `/api/v1/analytics/top-rejections/` | Top rejection codes |

---

## 10. MCP Server Tools

The MCP server exposes 7 tools for Claude Code AI-assisted workflows:

| Tool | Description |
|------|-------------|
| `validate_claim` | Run full validation pipeline on claim JSON |
| `lookup_icd10` | Validate ICD-10 code format |
| `lookup_npi` | Validate NPI with Luhn check-digit |
| `analyze_rejection` | Explain rejection codes + corrective actions |
| `get_rejection_stats` | Rejection rate statistics |
| `list_validators` | List all configured validators |
| `check_eligibility` | Real-time eligibility verification |

---

## 11. Directory Structure

```
project-root/
├── claim-validator/                    # Reusable Python Library
│   ├── src/claim_validator/
│   │   ├── models/                     # Pydantic data models
│   │   ├── validators/
│   │   │   ├── rule_based/             # 8 deterministic validators
│   │   │   └── ai/                     # 3 AI-powered validators
│   │   ├── llm/                        # Multi-provider LLM abstraction
│   │   ├── deidentifier/               # HIPAA Safe Harbor
│   │   ├── code_tables/                # ICD-10, HCPCS, POS, etc.
│   │   └── data/                       # Compressed reference data
│   ├── tests/                          # 50+ test files
│   └── demo_e2e.py                     # End-to-end demo scenarios
│
├── healthcare-claim-analyzer/          # Django REST API Service
│   ├── claim_analyzer/
│   │   ├── models/                     # Django ORM models
│   │   ├── validators/                 # Extended validation framework
│   │   ├── services/                   # Business logic layer
│   │   ├── api/                        # DRF views & serializers
│   │   ├── tasks/                      # Celery async tasks
│   │   ├── integrations/
│   │   │   ├── claimmd/                # ClaimMD clearinghouse client
│   │   │   ├── claude/                 # De-identification & prompts
│   │   │   └── llm/                    # Multi-provider LLM factory
│   │   └── middleware/                 # Audit & PHI filtering
│   ├── config/                         # Django settings
│   ├── mcp_server/                     # MCP server for Claude Code
│   └── tests/                          # Test suite
│
└── submission-docs/                    # This documentation
```
