# Healthcare Claim Validation & Analytics System

## Project Abstract

Healthcare claim denials cost the US healthcare system an estimated $262 billion annually, with approximately 30% of claims denied on first submission. The majority of these denials are preventable — caused by coding errors, missing fields, eligibility mismatches, and lack of prior authorization.

This project implements a **comprehensive healthcare claim validation and analytics platform** that addresses this problem through a dual-phase validation pipeline combining deterministic rule-based checks with AI-powered clinical analysis, all while maintaining strict HIPAA compliance.

---

## System Components

### 1. claim-validator (Python Library)
A reusable, pip-installable validation engine for CMS-1500 / 837P healthcare professional claims.

**Key Capabilities:**
- 8 rule-based validators (completeness, NPI Luhn check, demographics, ICD-10/CPT coding, monetary, duplicate detection, timely filing)
- 3 AI-powered validators (clinical code plausibility, coverage likelihood, prior authorization detection)
- HIPAA Safe Harbor de-identification before any LLM interaction
- Multi-provider LLM support (Anthropic Claude, OpenAI GPT-4, Ollama, vLLM)
- Thread-safe code table loading (ICD-10-CM, HCPCS, Taxonomy, POS, Timely Filing)
- Zero-config defaults with full extensibility via plugin architecture

### 2. healthcare-claim-analyzer (Django REST API Service)
A production-ready web service built on Django REST Framework with async processing.

**Key Capabilities:**
- 15+ REST API endpoints for claims CRUD, validation, submission, eligibility, and analytics
- ClaimMD clearinghouse integration (batch submission, status polling, eligibility checks)
- Celery async task queue with Redis broker (5 scheduled tasks)
- Rejection analytics engine (summary, trends, validator effectiveness, pattern learning)
- MCP server with 7 tools for Claude Code AI-assisted billing workflows
- PHI encryption at rest (Fernet), immutable audit logging, exception scrubbing middleware

---

## Technical Architecture

```
Client Layer (REST API / MCP Server / Django Admin)
        ↓
API Layer (Django REST Framework — 15+ endpoints)
        ↓
Service Layer (Validation, Submission, Eligibility, Analytics)
        ↓
Validation Pipeline (Two-Phase: 8 Rule-Based → 3 AI-Powered)
        ↓
Integration Layer (ClaimMD, LLM Providers, De-identification)
        ↓
Data Layer (PostgreSQL, Fernet Encryption, Immutable Audit Log)
```

---

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **Backend** | Python 3.11+, Django 5.2, Django REST Framework 3.16 |
| **Data Validation** | Pydantic 2.x (frozen models, strict validation) |
| **Async Processing** | Celery 5.6, Redis |
| **Database** | PostgreSQL (production), SQLite (development) |
| **AI/LLM** | Anthropic Claude SDK, OpenAI SDK, httpx (OpenAI-compatible) |
| **Security** | Fernet encryption, HIPAA Safe Harbor de-identification |
| **Integration** | ClaimMD clearinghouse, MCP 1.26 server |
| **Quality** | pytest 9.0, mypy (strict), ruff, factory-boy, 50+ test files |

---

## Validation Pipeline

### Phase 1: Rule-Based (Deterministic, Offline, <20ms)
| # | Validator | What It Checks |
|---|-----------|---------------|
| 1 | Completeness | Required CMS-1500 fields, min 1 diagnosis + 1 line |
| 2 | NPI | 10-digit format + Luhn check-digit algorithm |
| 3 | Subscriber ID | Format, min length, placeholder detection |
| 4 | Demographics | DOB, gender, age, patient fields for dependents |
| 5 | Coding | ICD-10-CM, CPT/HCPCS format, diagnosis pointer integrity |
| 6 | Monetary | Charges > 0, line total = claim total, patient paid check |
| 7 | Duplicate | Cross-claim detection (same subscriber + date + payer) |
| 8 | Timely Filing | Payer-specific deadline enforcement with 30-day warnings |

### Phase 2: AI-Powered (LLM Analysis, De-identified Input)
| # | Validator | What It Detects |
|---|-----------|----------------|
| 1 | Code Validation AI | Gender/age mismatches, implausible diagnosis-procedure pairs |
| 2 | Coverage Check AI | Non-covered diagnoses, documentation requirements |
| 3 | Prior Auth AI | High-cost imaging, surgical procedures, specialty meds |

---

## HIPAA Compliance

| Security Layer | Implementation |
|---------------|---------------|
| **Encryption at Rest** | Fernet-encrypted PHI fields in database |
| **De-identification** | HIPAA Safe Harbor — strips 18 identifiers before LLM |
| **Audit Logging** | Immutable AuditLog (save() prevents updates/deletes) |
| **Exception Scrubbing** | PHIFilterMiddleware removes SSN/DOB from error messages |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Total Validators | 11 (8 rule-based + 3 AI-powered) |
| REST API Endpoints | 15+ |
| MCP Server Tools | 7 |
| Celery Async Tasks | 5 (including 2 scheduled beat tasks) |
| Test Files | 50+ |
| Data Models | 8 Django ORM models |
| LLM Providers Supported | 5+ (Anthropic, OpenAI, Ollama, vLLM, LocalAI) |
| Code Tables | 5 compressed datasets (ICD-10, HCPCS, Taxonomy, POS, Timely Filing) |

---

## Design Patterns

- **Abstract Base Classes** — BaseValidator, BaseLLMClient for extensibility
- **Factory Pattern** — LLM client factory, Validator registry
- **Strategy Pattern** — Swappable validators via dotted path configuration
- **Builder Pattern** — Fluent ValidationPipeline.builder() API
- **Service Layer** — Thin views, all business logic in services
- **Dependency Injection** — LLM client injected into AI validators
- **Immutable Models** — Frozen Pydantic models for data integrity
- **Double-Check Locking** — Thread-safe singleton code table caching

---

## Conclusion

This system demonstrates a production-ready approach to reducing healthcare claim denials through intelligent pre-submission validation. By combining fast deterministic rule checks with AI-powered clinical analysis — all within a HIPAA-compliant architecture — it addresses the $262 billion claim denial problem while maintaining the security and auditability required in healthcare IT.
