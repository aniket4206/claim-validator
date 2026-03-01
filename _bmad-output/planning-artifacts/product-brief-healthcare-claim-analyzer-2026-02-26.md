---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '_bmad-output/planning-artifacts/research/domain-healthcare-eligibility-verification-research-2026-02-26.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-17.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-18.md'
  - '_bmad-output/project-context.md'
date: '2026-02-26'
author: 'aniket'
---

# Product Brief: Eligibility Verification Module for claim-validator

## Executive Summary

The `claim-validator` library already provides two-phase claim validation (rule-based → AI-powered). This product brief defines an **Eligibility Verification Module** that extends the same library to handle the pre-claim eligibility workflow: build and validate an EDI 270 request, submit it to a clearinghouse, and interpret the EDI 271 response — all through the same pipeline architecture developers already know.

The module fills a critical gap in the Python ecosystem: no open-source library today combines **Pydantic-native eligibility models + clearinghouse connectivity + AI-powered response interpretation** in a single package.

---

## 1. Vision & Problem Statement

### 1.1 Problem Statement

Healthcare organizations lose **$500K–$2M+ annually** to eligibility-related claim denials. **22% of all claim denials** stem from eligibility and coverage issues — the single largest denial category. Yet Python developers building healthcare systems have no library that handles the full eligibility verification lifecycle end-to-end.

Today, a developer who wants to verify patient eligibility before submitting a claim must:

1. **Manually construct EDI 270 requests** — error-prone, no validation
2. **Integrate with a clearinghouse API** — each one has different conventions
3. **Parse cryptic EDI 271 responses** — nested segment hierarchies, payer-specific quirks
4. **Interpret coverage details** — service type codes, benefit levels, date ranges, copay/coinsurance splits
5. **Handle Medicare/Medicaid specifics** — HETS enrollment, state-level Medicaid variations

Each step is a separate library, separate integration, separate headache.

### 1.2 Problem Impact

| Impact Area | Metric |
|---|---|
| Denial rate from eligibility issues | 22% of all denials |
| Revenue loss per provider | $500K–$2M+ annually |
| Staff time on manual verification | 15–20 min per patient |
| Rework cost per denied claim | $25–118 per claim |
| Industry-wide waste | $262B annually (administrative complexity) |

### 1.3 Why Existing Solutions Fall Short

| Solution | Gap |
|---|---|
| **x12-edi-tools** | Has EligibilityChecker class + Pydantic, but no clearinghouse connectivity, no AI interpretation |
| **Stedi API** | Excellent JSON API for clearinghouse, but no Python SDK, no validation, no AI |
| **pyx12 / TigerShark** | Legacy X12 parsers, no Pydantic, no AI, no clearinghouse integration |
| **Commercial platforms** (Availity, Waystar) | Closed source, expensive, no library-level integration |
| **Claude/GPT for Healthcare** | Can interpret 271 responses, but no structured eligibility pipeline |

**The gap**: No Python library combines request validation + clearinghouse submission + AI-powered response interpretation.

### 1.4 Proposed Solution

Extend `claim-validator` with a `check_eligibility()` top-level API that follows the same two-phase pipeline pattern:

**Phase 1 — Offline Rule-Based Validation** (before hitting any external API):
- Validate subscriber/patient demographics (name, DOB, member ID format)
- Validate provider identifiers (NPI Luhn check, taxonomy codes)
- Validate payer ID against known payer directory
- Validate service type codes, date ranges, request structure
- Ensure data quality before spending money on clearinghouse calls

**Phase 2 — Online Clearinghouse + AI Interpretation**:
- Submit validated request to clearinghouse via Stedi JSON API (primary provider)
- Parse 271 response into structured Pydantic models
- AI-powered interpretation of coverage details, benefit limits, payer-specific notes
- Generate human-readable eligibility summary with actionable findings
- De-identify PHI before sending to LLM (reuse existing `ClaimDeidentifier` pattern)

### 1.5 Key Differentiators

1. **Two-phase pipeline** — Rule-based validation prevents garbage-in/garbage-out before hitting clearinghouse
2. **Same library, same patterns** — Developers already using `claim-validator` for claims get eligibility for free
3. **AI-powered 271 interpretation** — First open-source library to use LLMs for eligibility response analysis
4. **Stedi JSON API** — Modern developer-first clearinghouse, 3,400+ payers, $0.15/check
5. **HIPAA-compliant by design** — PHI de-identification before LLM, no raw patient data leaves the pipeline
6. **Only Python library** combining Pydantic models + clearinghouse + AI for eligibility

---

## 2. Target Users

### 2.1 Primary Users

**Persona 1: "Raj" — The Healthcare Platform Developer**
- **Role**: Senior Python developer at a mid-size health-tech company building EHR/practice management platforms
- **Context**: Already using `claim-validator` for pre-claim validation, now needs eligibility verification in the same workflow
- **Current Pain**: Maintaining separate integrations — raw X12 parsing, manual clearinghouse API calls, custom 271 response interpretation logic. 3-4 libraries stitched together with glue code
- **Motivation**: One `pip install` that gives `check_eligibility()` alongside `validate()` — same patterns, same pipeline, same PHI handling
- **Success Vision**: "I added eligibility checks to our platform in an afternoon, not a sprint"
- **Aha! Moment**: AI interpretation turns a cryptic 271 EB segment into "Patient has $40 copay for office visits, deductible met, prior auth required for imaging"

**Persona 2: "Priya" — The Solo Dev / Startup Founder**
- **Role**: Full-stack developer building a niche healthcare SaaS (patient intake, telehealth, billing automation)
- **Context**: No deep EDI/X12 expertise. Needs a library that abstracts the complexity
- **Current Pain**: Can't afford Availity/Waystar commercial licenses ($$$). Can't spend weeks learning X12 segment hierarchies and payer-specific quirks
- **Motivation**: Get eligibility verification working in her app in a day, not a month
- **Success Vision**: "I call one function and get back a Pydantic model I can use directly in my FastAPI endpoint"
- **Aha! Moment**: Rule-based validation catches a bad payer ID before it costs $0.15 on a wasted Stedi call

### 2.2 Secondary Users

**Persona 3: "Karen" — Revenue Cycle Manager (Indirect Beneficiary)**
- **Role**: Revenue cycle manager at a healthcare organization
- **Context**: Doesn't use the library directly, but her denial rates drop because the developer's system now catches eligibility issues pre-claim
- **Influence**: Tells the CTO "we need this" — drives adoption decisions
- **Success Vision**: Eligibility-related denials drop from 22% to under 5%

**Persona 4: "DevOps / Compliance Officer"**
- **Role**: Security/compliance team evaluating the library for production deployment
- **Context**: Needs to verify HIPAA compliance — PHI de-identification before LLM calls, audit trail, BAA coverage for external services
- **Influence**: Gates production deployment — if compliance fails, the library doesn't ship
- **Success Vision**: Clear documentation showing PHI never reaches LLM providers in raw form

### 2.3 User Journey

| Stage | Raj (Platform Dev) | Priya (Solo Dev) |
|---|---|---|
| **Discovery** | Finds module while already using `claim-validator` for claims | Searches PyPI/GitHub for "python eligibility verification" |
| **Onboarding** | `pip install claim-validator[ai]`, reads familiar API patterns | Follows quickstart guide, copies example code |
| **First Use** | Adds `check_eligibility()` call next to existing `validate()` | Runs first eligibility check against Stedi sandbox |
| **Aha! Moment** | AI interprets 271 response into structured coverage summary | Rule-based catches bad data before wasting clearinghouse call |
| **Core Usage** | Integrates into patient registration workflow, batch eligibility checks | Builds eligibility endpoint in her FastAPI app |
| **Long-term** | Extends with custom validators, contributes back to open source | Upgrades to production Stedi plan, relies on library for all payers |

---

## 3. Success Metrics

### 3.1 User Success Metrics

| Metric | Measure | Target |
|---|---|---|
| Time to first eligibility check | Minutes from `pip install` to working check | < 30 minutes |
| Rule-based validation coverage | % of common 270 data errors caught before clearinghouse | > 90% |
| AI interpretation accuracy | Correct coverage summary vs manual 271 review | > 85% |
| Clearinghouse success rate | Valid 270 requests yielding valid 271 responses | > 95% |

### 3.2 Business Objectives

| Objective | Target | Timeframe |
|---|---|---|
| PyPI monthly downloads | 1,000+ | 6 months post-release |
| GitHub stars | 500+ | 12 months |
| Payer coverage via Stedi | 3,400+ payers | At launch |
| Eligibility denial reduction for adopters | 50%+ reduction | 12 months |

### 3.3 Key Performance Indicators

- **Leading indicator**: Number of Stedi sandbox API calls (developer experimentation)
- **Engagement indicator**: Ratio of rule-based-only vs full pipeline usage (adoption of AI phase)
- **Quality indicator**: GitHub issues related to incorrect 271 parsing or AI misinterpretation
- **Ecosystem indicator**: Third-party blog posts, tutorials, or integrations referencing the module

---

## 4. MVP Scope

### 4.1 Core Features (MVP)

| # | Feature | Description |
|---|---|---|
| 1 | **Eligibility data models** | `EligibilityRequest`, `EligibilityResponse` Pydantic models (frozen=True, same pattern as `ClaimData`) |
| 2 | **Rule-based request validators** | NPI Luhn check, payer ID validation, subscriber demographics, service type codes, date ranges |
| 3 | **Stedi JSON API integration** | Single clearinghouse provider — submit 270 / receive 271 via JSON API |
| 4 | **271 response parsing** | Parse Stedi JSON response into structured `EligibilityResponse` (coverage, benefits, copay, coinsurance, deductible) |
| 5 | **AI-powered 271 interpretation** | De-identify PHI → send to LLM → human-readable coverage summary with actionable findings |
| 6 | **`check_eligibility()` API** | Single top-level entry point mirroring existing `validate()` pattern |
| 7 | **Real-time checks only** | Synchronous single-patient eligibility verification |
| 8 | **PHI de-identification** | Reuse/extend existing `ClaimDeidentifier` for eligibility data |

### 4.2 Out of Scope (MVP)

| Feature | Rationale |
|---|---|
| Batch eligibility checks | Adds complexity; real-time covers primary use case |
| Multi-clearinghouse support | Stedi covers 3,400+ payers; additional providers add integration burden |
| Medicare HETS direct integration | Stedi routes Medicare checks; direct HETS requires per-NPI enrollment |
| FHIR mapping | Not yet mandated for eligibility; premature abstraction |
| Response caching/deduplication | Optimization, not core functionality |
| Async/background processing | Real-time sufficient for MVP; async adds concurrency complexity |
| Django/FastAPI view helpers | Framework integrations are a convenience layer, not core |
| Eligibility history/storage | Persistence is application-level concern, not library-level |

### 4.3 MVP Success Criteria

- Developer completes first eligibility check in < 30 minutes
- Rule-based validators catch > 90% of common 270 data errors
- Stedi integration works for commercial + Medicare + Medicaid payers
- AI interpretation produces actionable coverage summary from 271 response
- All tests pass, mypy strict, ruff clean — same quality bar as existing library

### 4.4 Future Vision

| Phase | Features |
|---|---|
| **v1.1** | Batch eligibility checks, response caching, async support |
| **v1.2** | Multi-clearinghouse (Waystar, ClaimMD), Django/FastAPI helpers |
| **v2.0** | FHIR CoverageEligibilityRequest/Response, eligibility history tracking, Stedi MCP server integration for agentic AI workflows |
| **v2.x** | Medicare HETS direct, state-level Medicaid adapters, prior authorization workflow |
