# Claim Eligibility Check — Implementation Approach Document

**Project:** claim-validator (Python Library)
**Module:** Eligibility Verification Module (MVP)
**Date:** February 27, 2026
**Version:** 1.0
**Status:** Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [High-Level Architecture](#4-high-level-architecture)
5. [Eligibility Check Flow — Step by Step](#5-eligibility-check-flow--step-by-step)
6. [Data Models](#6-data-models)
7. [Phase 1: Rule-Based Validation (Offline)](#7-phase-1-rule-based-validation-offline)
8. [Phase 2: Clearinghouse Integration (Stedi API)](#8-phase-2-clearinghouse-integration-stedi-api)
9. [Phase 3: AI-Powered Interpretation (Optional)](#9-phase-3-ai-powered-interpretation-optional)
10. [HIPAA De-Identification](#10-hipaa-de-identification)
11. [API Design & Usage Examples](#11-api-design--usage-examples)
12. [Error Handling Strategy](#12-error-handling-strategy)
13. [Security & Compliance](#13-security--compliance)
14. [Technology Stack](#14-technology-stack)
15. [Implementation Phases & Timeline](#15-implementation-phases--timeline)
16. [Key Design Decisions](#16-key-design-decisions)
17. [Glossary](#17-glossary)

---

## 1. Executive Summary

We are building an **Eligibility Verification Module** that extends our existing `claim-validator` Python library. This module allows healthcare developers to verify patient insurance eligibility **before** submitting claims, reducing denial rates caused by eligibility issues.

**Our approach uses a three-phase pipeline:**

| Phase | What It Does | Requires Network? | Cost |
|-------|-------------|-------------------|------|
| Phase 1 | Rule-based request validation (catch bad data early) | No (offline) | Free |
| Phase 2 | Submit to clearinghouse (Stedi), get real-time eligibility response | Yes (Stedi API) | ~$0.15/check |
| Phase 3 | AI interprets the complex response into plain English | Yes (LLM API) | ~$0.01-0.05/check |

**Key value proposition:** Catch 90%+ of data quality issues in Phase 1 (free, offline) before spending money on clearinghouse calls in Phase 2, then use AI to make the complex eligibility response human-readable in Phase 3.

---

## 2. Problem Statement

### The Eligibility Denial Problem

- **22% of claim denials** are caused by eligibility and coverage issues
- This translates to **$500K–$2M+ annual revenue loss** per healthcare provider
- Manual eligibility verification is slow, error-prone, and requires X12 EDI expertise
- Most denials are preventable with upfront eligibility checks

### Why Existing Solutions Fall Short

| Gap | Description |
|-----|-------------|
| No Python library | No open-source Python library combines eligibility models + clearinghouse + AI |
| X12 complexity | Raw 270/271 EDI transactions require deep domain expertise to interpret |
| Wasted API costs | Bad requests (wrong NPI, invalid payer ID) still incur clearinghouse fees |
| PHI exposure | Many solutions send raw patient data to cloud LLMs without de-identification |

### What We Solve

We provide a **single Python function call** that:
1. Validates request data offline (catches errors for free)
2. Submits to the clearinghouse only if data is clean
3. Parses the complex response into structured Python objects
4. Optionally uses AI to generate a human-readable summary
5. Never sends raw PHI to any external AI service

---

## 3. Solution Overview

### How It Fits Into the Existing Library

```
claim-validator (existing)
├── validate()              ← Claim validation (already built)
│   ├── Rule-based validators (8 validators, offline)
│   ├── AI validators (3 validators, optional)
│   ├── De-identification pipeline
│   └── Multi-provider LLM support
│
└── check_eligibility()     ← Eligibility verification (NEW - what we're building)
    ├── Rule-based request validators (NEW)
    ├── Stedi clearinghouse client (NEW)
    ├── 271 response parser (NEW)
    ├── AI interpretation (NEW, reuses existing LLM layer)
    └── De-identification (extends existing)
```

### What We Reuse vs. What We Build New

| Component | Status | Notes |
|-----------|--------|-------|
| Pydantic model patterns | Reuse | Same `frozen=True`, `strict=False` pattern |
| Validator base class | Reuse | Same `BaseValidator` ABC |
| LLM abstraction layer | Reuse | Same `BaseLLMClient` + 3 providers |
| De-identification | Extend | Add eligibility-specific fields |
| Configuration system | Extend | Add Stedi credentials |
| Eligibility data models | **New** | `EligibilityRequest`, `EligibilityResponse`, etc. |
| Rule-based request validators | **New** | 6 validators specific to eligibility |
| Stedi API client | **New** | HTTP client for Stedi JSON API |
| 271 response parser | **New** | Parse Stedi JSON to structured models |
| AI interpretation validator | **New** | LLM-based eligibility summary |
| `check_eligibility()` API | **New** | Top-level entry point |

---

## 4. High-Level Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Developer's Application                      │
│                                                                     │
│   from claim_validator import check_eligibility                     │
│   result = check_eligibility(request_data, stedi_api_key="...")     │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  check_eligibility() Entry Point                    │
│                                                                     │
│   1. Parse input (dict → EligibilityRequest model)                 │
│   2. Load configuration                                            │
│   3. Build eligibility pipeline                                    │
│   4. Execute pipeline                                              │
│   5. Return EligibilityResult                                      │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Eligibility Pipeline                             │
│                                                                     │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│   │   PHASE 1    │──▶│   PHASE 2    │──▶│      PHASE 3         │  │
│   │  Rule-Based  │   │ Clearinghouse│   │  AI Interpretation   │  │
│   │  (Offline)   │   │ (Stedi API)  │   │  (LLM - Optional)   │  │
│   └──────────────┘   └──────────────┘   └──────────────────────┘  │
│         │                    │                      │              │
│    No network          HTTPS/TLS            De-identified         │
│    No cost             ~$0.15/call          data only             │
│    < 50ms              < 3 seconds          < 5 seconds           │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────┐
│ Developer│────▶│check_         │────▶│ Eligibility   │────▶│ Result   │
│ App      │     │eligibility() │     │ Pipeline      │     │ Object   │
└──────────┘     └──────┬───────┘     └───────┬───────┘     └──────────┘
                        │                     │
                 ┌──────▼───────┐      ┌──────▼───────┐
                 │ Eligibility  │      │ Validator    │
                 │ Request      │      │ Registry     │
                 │ Model        │      │              │
                 └──────────────┘      └──────┬───────┘
                                              │
                        ┌─────────────────────┼──────────────────────┐
                        │                     │                      │
                 ┌──────▼───────┐     ┌───────▼──────┐     ┌────────▼─────┐
                 │ Rule-Based   │     │ Stedi        │     │ AI           │
                 │ Validators   │     │ Client       │     │ Interpreter  │
                 │ (6 total)    │     │ (HTTP)       │     │ (LLM)        │
                 └──────────────┘     └───────┬──────┘     └────────┬─────┘
                                              │                     │
                                       ┌──────▼───────┐     ┌──────▼───────┐
                                       │ Stedi JSON   │     │ LLM Provider │
                                       │ API (3,400+  │     │ (Anthropic/  │
                                       │ payers)      │     │ OpenAI/Local)│
                                       └──────────────┘     └──────────────┘
```

---

## 5. Eligibility Check Flow — Step by Step

### Complete Flow Diagram

```
START: Developer calls check_eligibility(request_data)
  │
  ▼
┌─────────────────────────────────────┐
│ STEP 1: INPUT PARSING               │
│                                     │
│ Accept dict or EligibilityRequest   │
│ If dict → parse into model          │
│ If invalid → raise ValidationError  │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ STEP 2: CONFIGURATION LOADING       │
│                                     │
│ Load settings from:                 │
│ - Function parameters               │
│ - Environment variables              │
│ - Default values                     │
│ Determine: Stedi key, AI config     │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│ STEP 3: BUILD PIPELINE              │
│                                     │
│ Register validators:                │
│ - 6 rule-based validators            │
│ - Stedi client (if key provided)     │
│ - AI interpreter (if AI configured)  │
└───────────────┬─────────────────────┘
                │
                ▼
╔═════════════════════════════════════╗
║ PHASE 1: RULE-BASED VALIDATION     ║
║ (All offline, no network, free)    ║
╠═════════════════════════════════════╣
║                                     ║
║ Validator 1: NPI Validation          ║
║ ├─ 10-digit numeric format          ║
║ ├─ Luhn check-digit algorithm        ║
║ └─ Provider/billing NPI present      ║
║                                     ║
║ Validator 2: Payer ID Validation     ║
║ ├─ Payer ID format check             ║
║ ├─ Known payer lookup                ║
║ └─ Stedi payer mapping               ║
║                                     ║
║ Validator 3: Subscriber Demographics ║
║ ├─ Subscriber ID present + valid     ║
║ ├─ Patient name present              ║
║ ├─ Date of birth valid (not future)  ║
║ └─ Gender code valid                 ║
║                                     ║
║ Validator 4: Service Type Codes      ║
║ ├─ Valid ASC X12 service type code   ║
║ └─ Standard code set compliance      ║
║                                     ║
║ Validator 5: Date Range Validation   ║
║ ├─ Service date not in far past      ║
║ ├─ Service date not in far future    ║
║ └─ Date range logical (from < to)    ║
║                                     ║
║ Validator 6: Request Completeness    ║
║ ├─ All required fields present       ║
║ ├─ Minimum field lengths met         ║
║ └─ No placeholder/dummy values       ║
║                                     ║
╚═══════════════╦═════════════════════╝
                ║
                ▼
        ┌───────────────┐
        │ Has Errors?   │
        └───┬───────┬───┘
           YES      NO
            │       │
            ▼       ▼
    ┌───────────┐  ┌─────────────────────────┐
    │ Check:    │  │ Proceed to Phase 2      │
    │ skip on   │  └────────────┬────────────┘
    │ error?    │               │
    └──┬────┬───┘               │
      YES   NO                  │
       │     │                  │
       │     └──────────────────┤
       ▼                        ▼
  ┌─────────┐  ╔════════════════════════════════════════╗
  │ Return  │  ║ STEP 4: DE-IDENTIFICATION              ║
  │ early   │  ║ (Before any external API call)         ║
  │ with    │  ╠════════════════════════════════════════╣
  │ findings│  ║                                        ║
  └─────────┘  ║ Strip 18 HIPAA identifiers:            ║
               ║ ✗ Patient name → removed                ║
               ║ ✗ Date of birth → year only             ║
               ║ ✗ SSN → removed                         ║
               ║ ✗ Member/subscriber ID → removed        ║
               ║ ✗ Address → removed                     ║
               ║ ✗ Phone/email → removed                 ║
               ║ ✗ Account numbers → removed             ║
               ║                                        ║
               ║ Retain for processing:                  ║
               ║ ✓ NPI (public registry data)            ║
               ║ ✓ Payer ID (not PHI)                    ║
               ║ ✓ Service type codes                    ║
               ║ ✓ Age (capped at 90)                    ║
               ║ ✓ Gender                                ║
               ╚════════════════╦═══════════════════════╝
                                ║
                                ▼
  ╔═════════════════════════════════════════════════════╗
  ║ PHASE 2: CLEARINGHOUSE (Stedi JSON API)            ║
  ║ (Network call, ~$0.15 per check)                   ║
  ╠═════════════════════════════════════════════════════╣
  ║                                                     ║
  ║ STEP 5: BUILD 270 REQUEST                           ║
  ║ ├─ Map EligibilityRequest → Stedi JSON format       ║
  ║ ├─ Add service type codes                           ║
  ║ └─ Include provider/subscriber details              ║
  ║                                                     ║
  ║ STEP 6: SUBMIT TO STEDI                             ║
  ║ ├─ POST to Stedi Eligibility API                    ║
  ║ ├─ HTTPS/TLS 1.2+ encrypted                        ║
  ║ ├─ Timeout: 30 seconds (configurable)               ║
  ║ └─ Retry on transient failures (max 2 retries)      ║
  ║                                                     ║
  ║ STEP 7: RECEIVE 271 RESPONSE                        ║
  ║ ├─ Stedi returns JSON (not raw X12)                 ║
  ║ ├─ Contains: coverage status, benefits,              ║
  ║ │   copay, coinsurance, deductible amounts           ║
  ║ └─ May contain rejection/AAA error segments          ║
  ║                                                     ║
  ║ STEP 8: PARSE RESPONSE                              ║
  ║ ├─ Map Stedi JSON → EligibilityResponse model       ║
  ║ ├─ Extract coverage status (active/inactive)         ║
  ║ ├─ Extract benefit details per service type          ║
  ║ ├─ Parse copay/coinsurance/deductible amounts        ║
  ║ ├─ Identify coverage date ranges                     ║
  ║ └─ Capture any error/rejection reasons               ║
  ║                                                     ║
  ╚═══════════════════════╦═════════════════════════════╝
                          ║
                          ▼
                  ┌───────────────┐
                  │ AI configured?│
                  └───┬───────┬───┘
                     NO      YES
                      │       │
                      │       ▼
                      │  ╔════════════════════════════════════════════╗
                      │  ║ PHASE 3: AI INTERPRETATION (Optional)     ║
                      │  ║ (LLM call, ~$0.01-0.05 per check)        ║
                      │  ╠════════════════════════════════════════════╣
                      │  ║                                            ║
                      │  ║ STEP 9: PREPARE AI INPUT                   ║
                      │  ║ ├─ De-identified eligibility data only     ║
                      │  ║ ├─ Structured 271 response data            ║
                      │  ║ └─ No raw PHI ever sent to LLM             ║
                      │  ║                                            ║
                      │  ║ STEP 10: LLM ANALYSIS                      ║
                      │  ║ ├─ Send to configured provider:            ║
                      │  ║ │   - Anthropic (Claude)                   ║
                      │  ║ │   - OpenAI (GPT)                         ║
                      │  ║ │   - Local/self-hosted (Ollama, vLLM)     ║
                      │  ║ ├─ Prompt includes:                        ║
                      │  ║ │   - Parsed eligibility response           ║
                      │  ║ │   - Service types requested               ║
                      │  ║ │   - Coverage/benefit details              ║
                      │  ║ └─ Response: structured JSON + text summary ║
                      │  ║                                            ║
                      │  ║ STEP 11: GENERATE SUMMARY                   ║
                      │  ║ ├─ Plain English coverage explanation        ║
                      │  ║ ├─ Patient responsibility estimates         ║
                      │  ║ ├─ Coverage limitations/exclusions          ║
                      │  ║ ├─ Prior authorization requirements         ║
                      │  ║ └─ Recommended next steps                   ║
                      │  ║                                            ║
                      │  ╚══════════════╦═════════════════════════════╝
                      │                 ║
                      └────────┬────────┘
                               ▼
          ╔════════════════════════════════════════════╗
          ║ STEP 12: ASSEMBLE RESULT                   ║
          ╠════════════════════════════════════════════╣
          ║                                            ║
          ║  EligibilityResult                         ║
          ║  ├─ .eligible      → True/False/None       ║
          ║  ├─ .response      → Structured 271 data   ║
          ║  ├─ .findings      → All validation issues ║
          ║  ├─ .ai_summary    → Plain English summary ║
          ║  ├─ .raw_response  → Raw Stedi JSON        ║
          ║  ├─ .passed        → Rule validation OK?   ║
          ║  ├─ .errors        → Error-level findings  ║
          ║  └─ .warnings      → Warning-level findings║
          ║                                            ║
          ╚════════════════════════════════════════════╝
                               │
                               ▼
                          END: Return to developer
```

---

## 6. Data Models

### Input Model: EligibilityRequest

This is what the developer provides to check eligibility.

```
EligibilityRequest
├── provider_npi: str               # Provider's NPI (10-digit)
├── provider_organization: str      # Provider organization name
├── provider_taxonomy: str | None   # Provider taxonomy code
├── payer_id: str                   # Insurance payer ID
├── subscriber_id: str              # Member/subscriber ID
├── patient_first_name: str         # Patient first name
├── patient_last_name: str          # Patient last name
├── patient_dob: str                # Date of birth (YYYY-MM-DD)
├── patient_gender: str             # M/F/U
├── relationship_to_subscriber: str # Self, Spouse, Child, Other
├── service_type_codes: list[str]   # What services to check (e.g., "30" = health plan)
├── service_date: str | None        # Date of service
└── service_date_end: str | None    # End date (for date ranges)
```

### Output Model: EligibilityResponse (parsed 271)

This is the structured data extracted from the clearinghouse response.

```
EligibilityResponse
├── status: str                     # active, inactive, unknown
├── subscriber_name: str            # Subscriber name from payer
├── payer_name: str                 # Insurance company name
├── plan_name: str | None           # Plan name
├── plan_number: str | None         # Plan/group number
├── coverage_start: str | None      # Coverage effective date
├── coverage_end: str | None        # Coverage termination date
├── benefits: list[BenefitInfo]     # List of benefits
└── errors: list[str]               # AAA rejection reasons
```

### Benefit Detail: BenefitInfo

```
BenefitInfo
├── service_type: str               # Service type description
├── service_type_code: str          # ASC X12 service type code
├── coverage_level: str             # Individual, Family
├── in_network: bool | None         # In-network flag
├── benefit_amount: float | None    # Dollar amount
├── benefit_percent: float | None   # Percentage (coinsurance)
├── time_qualifier: str | None      # Per visit, per year, etc.
├── authorization_required: bool    # Prior auth needed?
└── description: str | None         # Free-text description
```

### Result Model: EligibilityResult

This is what the developer receives back.

```
EligibilityResult
├── eligible: bool | None           # Overall eligibility determination
├── response: EligibilityResponse   # Structured 271 data
├── findings: list[Finding]         # All validation findings
├── ai_summary: str | None          # Human-readable summary (if AI enabled)
├── raw_response: dict              # Raw clearinghouse JSON
├── execution_time: float           # Total processing time (seconds)
├── phases: list[PhaseResult]       # Per-phase timing/results
│
│   (Convenience properties)
├── .passed → bool                  # True if no ERROR-level findings
├── .errors → list[Finding]         # Only ERROR severity
└── .warnings → list[Finding]       # Only WARNING severity
```

---

## 7. Phase 1: Rule-Based Validation (Offline)

### Purpose

Catch data quality issues **before** making any network calls. This saves money (no wasted clearinghouse fees), time (instant feedback), and ensures compliance (catches obvious errors early).

### Validators

| # | Validator | What It Checks | Example Error |
|---|-----------|---------------|---------------|
| 1 | **NPI Validator** | 10-digit format, Luhn check-digit, provider/billing NPI present | "NPI 123456789 fails Luhn check-digit validation" |
| 2 | **Payer ID Validator** | Payer ID format, known payer lookup, Stedi payer mapping | "Unknown payer ID 'XYZ'. Check Stedi payer list." |
| 3 | **Subscriber Demographics** | Subscriber ID format, patient name present, DOB valid, gender valid | "Patient DOB 2030-01-01 is in the future" |
| 4 | **Service Type Codes** | Valid ASC X12 service type code values | "Service type code '99' is not a valid X12 code" |
| 5 | **Date Range Validator** | Service date in reasonable range, from-date before to-date | "Service date is 400 days in the future" |
| 6 | **Request Completeness** | All required fields present, no placeholder values | "subscriber_id is required but missing" |

### How Validators Work (Pattern)

Each validator follows the same pattern established in the existing claim validation:

```
Input: EligibilityRequest model
  │
  ▼
BaseValidator.validate(request) → ValidatorOutput
  │
  ├─ Check each rule
  ├─ For each failure, create a Finding:
  │   ├─ code: "INVALID_NPI_FORMAT"
  │   ├─ message: "NPI must be 10 numeric digits"
  │   ├─ severity: ERROR or WARNING
  │   ├─ field_name: "provider_npi"
  │   └─ suggestion: "Verify at NPI Registry"
  │
  └─ Return ValidatorOutput with all findings
```

### Finding Severity Levels

| Severity | Meaning | Pipeline Impact |
|----------|---------|-----------------|
| **ERROR** | Must fix before proceeding | Blocks Phase 2 (configurable) |
| **WARNING** | Potential issue, review recommended | Does not block Phase 2 |
| **INFO** | Informational note | Does not block Phase 2 |

---

## 8. Phase 2: Clearinghouse Integration (Stedi API)

### Why Stedi?

| Factor | Stedi | Alternative |
|--------|-------|-------------|
| API Format | Modern JSON (no raw X12 parsing needed) | Most use raw X12 |
| Payer Coverage | 3,400+ payers | Varies |
| Pricing | ~$0.15 per eligibility check | $0.10–0.50 |
| Authentication | Simple API key | Often complex |
| Documentation | Excellent REST API docs | Varies |
| Response Format | Structured JSON | Raw X12 segments |

### Stedi Integration Flow

```
Step 1: Map our model → Stedi request format
┌─────────────────────────────┐      ┌──────────────────────────────┐
│ EligibilityRequest          │      │ Stedi JSON Request           │
│ ├─ provider_npi             │  ──▶ │ ├─ informationSource         │
│ ├─ payer_id                 │      │ │   └─ providerNPI           │
│ ├─ subscriber_id            │      │ ├─ informationReceiver       │
│ ├─ patient_dob              │      │ │   └─ payerID               │
│ ├─ service_type_codes       │      │ ├─ subscriber                │
│ └─ ...                      │      │ │   ├─ memberId              │
└─────────────────────────────┘      │ │   ├─ dateOfBirth           │
                                     │ │   └─ ...                    │
                                     │ └─ encounter                  │
                                     │     └─ serviceTypeCodes       │
                                     └──────────────────────────────┘

Step 2: POST to Stedi API
  HTTP POST https://healthcare.stedi.com/2024-04-01/change/medicalnetwork/
            eligibility/v3
  Headers: Authorization: Bearer {stedi_api_key}
  Body: Stedi JSON Request

Step 3: Receive Stedi response → Map to our model
┌──────────────────────────────┐      ┌─────────────────────────────┐
│ Stedi JSON Response          │      │ EligibilityResponse         │
│ ├─ planStatus                │  ──▶ │ ├─ status: "active"         │
│ ├─ subscriber                │      │ ├─ subscriber_name          │
│ ├─ payer                     │      │ ├─ payer_name               │
│ ├─ planInformation           │      │ ├─ plan_name                │
│ ├─ benefitsInformation[]     │      │ ├─ benefits: [BenefitInfo]  │
│ │   ├─ serviceTypes          │      │ │   ├─ copay: $30           │
│ │   ├─ benefitAmount         │      │ │   ├─ coinsurance: 20%     │
│ │   └─ authRequired          │      │ │   └─ auth_required: true  │
│ └─ errors[]                  │      │ └─ errors: []               │
└──────────────────────────────┘      └─────────────────────────────┘
```

### Error Scenarios

| Scenario | How We Handle It |
|----------|-----------------|
| Stedi API timeout | Return finding with CLEARINGHOUSE_TIMEOUT code, include partial data |
| Stedi returns error (AAA segment) | Parse error reason, return as finding + in response.errors |
| Invalid API key | Return finding with AUTH_ERROR code, suggest checking key |
| Network failure | Return finding with NETWORK_ERROR code, suggest retry |
| Patient not found | Return finding, set eligible=None, include payer error text |
| Coverage terminated | Parse termination date, set eligible=False, include in summary |

---

## 9. Phase 3: AI-Powered Interpretation (Optional)

### Why AI Interpretation?

Raw eligibility responses are complex and hard to understand:

```
Without AI (raw structured data):
  benefits[0]: serviceType="Health Benefit Plan Coverage"
               code="1" level="INDIVIDUAL"
               inPlanNetwork="YES" benefitAmount=null
  benefits[1]: serviceType="Health Benefit Plan Coverage"
               code="A" level="INDIVIDUAL"
               coinsurancePercent=20 timePeriod="CALENDAR_YEAR"
  benefits[2]: serviceType="Professional (Physician) Visit"
               code="B" level="INDIVIDUAL"
               benefitAmount=30.00 timePeriod="VISIT"
  ...  (25+ more benefit entries)

With AI (human-readable summary):
  "Patient has active coverage under Blue Cross PPO Plan.
   For the requested office visit (CPT 99213):
   - Copay: $30 per visit
   - Coinsurance: 20% after deductible
   - Remaining deductible: $450 of $1,500
   - Prior authorization: NOT required
   - Network status: In-network provider confirmed
   Estimated patient responsibility: $30 copay + 20% of charges
   above deductible."
```

### AI Flow

```
                    ┌──────────────────────────┐
                    │ De-identified 271 data    │
                    │ (NO patient names,        │
                    │  NO DOB, NO member ID)    │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Build Prompt:             │
                    │                          │
                    │ "Given this eligibility   │
                    │  response for a [age]    │
                    │  year old [gender]        │
                    │  patient, requesting      │
                    │  [service types]:         │
                    │                          │
                    │  [structured 271 data]    │
                    │                          │
                    │  Provide:                 │
                    │  1. Coverage summary      │
                    │  2. Patient costs         │
                    │  3. Limitations           │
                    │  4. Auth requirements     │
                    │  5. Recommendations"      │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ LLM Provider             │
                    │                          │
                    │ ┌─ Anthropic (Claude) ◄───── Recommended
                    │ ├─ OpenAI (GPT)          │
                    │ └─ Local (Ollama/vLLM)   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Parse Response:           │
                    │                          │
                    │ Structured JSON:          │
                    │ ├─ eligible: true/false   │
                    │ ├─ summary: "text..."     │
                    │ ├─ copay: 30.00           │
                    │ ├─ coinsurance: 0.20      │
                    │ ├─ deductible_remaining   │
                    │ ├─ auth_required: false   │
                    │ └─ limitations: [...]     │
                    │                          │
                    │ + Plain text summary      │
                    └──────────────────────────┘
```

### LLM Provider Options

| Provider | Model | Cost/Check | Latency | Best For |
|----------|-------|-----------|---------|----------|
| Anthropic | Claude Haiku | ~$0.01 | ~1-2s | Production (cost-effective) |
| Anthropic | Claude Sonnet | ~$0.03 | ~2-3s | Higher accuracy |
| OpenAI | GPT-4o-mini | ~$0.01 | ~1-2s | Production alternative |
| Local | Ollama (Llama 3) | Free | ~2-5s | Data sovereignty, no cloud |

---

## 10. HIPAA De-Identification

### Why De-Identification?

HIPAA requires that Protected Health Information (PHI) is not shared with unauthorized entities. When we send data to:
- **Stedi (clearinghouse):** PHI is allowed — Stedi has a Business Associate Agreement (BAA)
- **LLM providers (AI):** PHI must be stripped — no standard BAA for AI inference

### What Gets Stripped (18 HIPAA Identifiers)

```
BEFORE De-identification              AFTER De-identification
─────────────────────────             ─────────────────────────
patient_first_name: "John"            patient_first_name: [REMOVED]
patient_last_name: "Smith"            patient_last_name: [REMOVED]
patient_dob: "1985-03-15"             patient_age: 40 (year only → age)
subscriber_id: "ABC123456789"         subscriber_id: [REMOVED]
ssn: "123-45-6789"                    ssn: [REMOVED]
address: "123 Main St"               address: [REMOVED]
phone: "555-0123"                     phone: [REMOVED]
email: "john@example.com"            email: [REMOVED]

provider_npi: "1234567890"           provider_npi: "1234567890"  ✓ Kept
payer_id: "BCBS01"                   payer_id: "BCBS01"          ✓ Kept
service_type_codes: ["30"]           service_type_codes: ["30"]  ✓ Kept
patient_gender: "M"                  patient_gender: "M"         ✓ Kept
```

### De-Identification in the Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Phase 1           │     │ De-Identification │     │ Phase 2 & 3      │
│ (Rule-based)      │────▶│ Gate              │────▶│ (External APIs)  │
│                   │     │                   │     │                   │
│ Uses FULL data    │     │ Strips PHI        │     │ Uses DE-ID data  │
│ (all local,       │     │ Creates safe copy │     │ (Stedi gets full │
│  never leaves     │     │                   │     │  via BAA; LLM    │
│  the machine)     │     │                   │     │  gets de-id only)│
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## 11. API Design & Usage Examples

### Basic Usage (Rule-Based Only)

```python
from claim_validator import check_eligibility

# Minimal example - rule validation only (no Stedi key = no clearinghouse)
result = check_eligibility({
    "provider_npi": "1234567893",
    "payer_id": "BCBS01",
    "subscriber_id": "XYZ123456789",
    "patient_first_name": "Jane",
    "patient_last_name": "Doe",
    "patient_dob": "1985-03-15",
    "patient_gender": "F",
    "service_type_codes": ["30"],  # Health plan coverage
})

print(result.passed)     # True if no errors in rule validation
print(result.findings)   # List of any validation issues found
```

### Full Usage (Rule-Based + Stedi + AI)

```python
from claim_validator import check_eligibility

result = check_eligibility(
    {
        "provider_npi": "1234567893",
        "provider_organization": "ABC Medical Group",
        "payer_id": "BCBS01",
        "subscriber_id": "XYZ123456789",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1985-03-15",
        "patient_gender": "F",
        "service_type_codes": ["30"],
        "service_date": "2026-03-01",
    },
    stedi_api_key="key_live_...",
    ai_config={
        "provider": "anthropic",
        "api_key": "sk-ant-...",
        "model": "claude-haiku-4-5-20251001",
    },
)

# Check overall eligibility
print(result.eligible)        # True, False, or None
print(result.passed)          # True if rule validation passed

# Access structured response
if result.response:
    print(result.response.status)           # "active"
    print(result.response.plan_name)        # "Blue Cross PPO"
    for benefit in result.response.benefits:
        print(f"  {benefit.service_type}: copay=${benefit.benefit_amount}")

# Read AI summary
if result.ai_summary:
    print(result.ai_summary)
    # "Patient has active coverage under Blue Cross PPO Plan.
    #  Copay: $30 per visit. Coinsurance: 20% after deductible..."

# Check for issues
for finding in result.errors:
    print(f"ERROR: {finding.message}")
for finding in result.warnings:
    print(f"WARNING: {finding.message}")
```

### Integration Example (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from claim_validator import check_eligibility

app = FastAPI()

@app.post("/api/eligibility/check")
async def check_patient_eligibility(request: dict):
    result = check_eligibility(
        request,
        stedi_api_key=settings.STEDI_API_KEY,
        ai_config=settings.AI_CONFIG,
    )

    return {
        "eligible": result.eligible,
        "summary": result.ai_summary,
        "errors": [f.message for f in result.errors],
        "warnings": [f.message for f in result.warnings],
        "benefits": [b.dict() for b in result.response.benefits]
            if result.response else [],
    }
```

### Installation Options

```bash
# Rule-based only (no network dependencies)
pip install claim-validator

# With Stedi clearinghouse integration
pip install claim-validator[stedi]

# With Stedi + Claude AI interpretation
pip install claim-validator[stedi,anthropic]

# With Stedi + OpenAI interpretation
pip install claim-validator[stedi,openai]

# Everything (all providers, server, etc.)
pip install claim-validator[all]
```

---

## 12. Error Handling Strategy

### Error Categories

```
┌──────────────────────────────────────────────────────────────────┐
│                    Error Handling Hierarchy                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Validation Errors (expected - returned as Findings)             │
│  ├─ INVALID_NPI_FORMAT          → "NPI must be 10 digits"       │
│  ├─ UNKNOWN_PAYER               → "Payer ID not recognized"     │
│  ├─ MISSING_REQUIRED_FIELD      → "subscriber_id is required"   │
│  ├─ INVALID_DATE                → "DOB is in the future"        │
│  ├─ INVALID_SERVICE_TYPE        → "Code '99' not valid"         │
│  └─ PATIENT_NOT_FOUND           → "Payer returned no match"     │
│                                                                  │
│  Infrastructure Errors (returned as Findings, never crash)       │
│  ├─ CLEARINGHOUSE_TIMEOUT       → "Stedi did not respond"       │
│  ├─ CLEARINGHOUSE_ERROR         → "Stedi returned HTTP 500"     │
│  ├─ NETWORK_ERROR               → "Could not reach Stedi"       │
│  ├─ AI_PROVIDER_ERROR           → "LLM call failed"             │
│  └─ AI_PARSE_ERROR              → "Could not parse AI response" │
│                                                                  │
│  Configuration Errors (raised as exceptions - must fix)          │
│  ├─ ConfigurationError          → "Missing stedi_api_key"       │
│  └─ ConfigurationError          → "Unknown LLM provider 'xyz'" │
│                                                                  │
│  Input Errors (raised as exceptions - invalid input)             │
│  └─ pydantic.ValidationError    → "Invalid request format"      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Principle: Validators Never Crash

Validation errors and infrastructure errors are **always returned as Findings**, never raised as exceptions. The pipeline always returns a result object. Only configuration and input errors raise exceptions (because the developer needs to fix their code, not their data).

---

## 13. Security & Compliance

### HIPAA Compliance Summary

| Requirement | How We Meet It |
|---|---|
| PHI Protection | De-identification strips all 18 HIPAA identifiers before AI calls |
| Minimum Necessary | Only clinical codes and non-PHI data sent to LLM |
| Clearinghouse BAA | Stedi operates under BAA for covered entities |
| Encryption in Transit | All external calls use HTTPS/TLS 1.2+ |
| No PHI in Logs | Findings reference field names, never field values |
| API Key Security | Environment variables only, never hardcoded or logged |
| No Telemetry | Zero undisclosed network calls from the library |
| Audit Trail | Every pipeline phase is timed and logged in result object |

### Security Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Developer's Server                      │
│                   (PHI boundary - FULL data)                │
│                                                            │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Rule-Based  │    │ De-ID Gate   │    │ API Clients  │  │
│  │ Validators  │    │              │    │              │  │
│  │ (local)     │───▶│ Strip PHI    │───▶│ Stedi/LLM    │  │
│  └─────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                │          │
└────────────────────────────────────────────────┼──────────┘
                                                 │
                              HTTPS/TLS 1.2+     │
                                                 │
         ┌───────────────────────────────────────┤
         │                                       │
         ▼                                       ▼
┌─────────────────┐                  ┌───────────────────┐
│ Stedi API       │                  │ LLM Provider      │
│ (BAA covered)   │                  │ (De-ID data only) │
│ Receives: PHI   │                  │ Receives: No PHI  │
│ allowed per BAA │                  │ (age, gender,     │
└─────────────────┘                  │  codes only)      │
                                     └───────────────────┘
```

---

## 14. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.11+ | Core implementation |
| Data Models | Pydantic | v2 | Request/response validation, immutability |
| Configuration | pydantic-settings | v2 | Env var configuration |
| HTTP Client | httpx | >= 0.27 | Stedi API calls, LLM API calls |
| LLM (Option A) | anthropic SDK | latest | Claude integration |
| LLM (Option B) | openai SDK | latest | GPT integration |
| LLM (Option C) | httpx (direct) | >= 0.27 | Self-hosted LLM (Ollama, vLLM) |
| Testing | pytest | >= 8.0 | Unit and integration tests |
| Type Checking | mypy | strict | Full type safety |
| Linting | ruff | latest | Code quality |
| Build | hatchling | latest | Package building |
| Versioning | hatch-vcs | latest | Git-tag-based versions |

---

## 15. Implementation Phases & Timeline

### Phase Breakdown

```
WEEK 1-2: Foundation
├─ [1] Eligibility data models (EligibilityRequest, EligibilityResponse,
│      BenefitInfo, CoverageInfo, EligibilityResult)
├─ [2] Configuration extension (add Stedi settings to ClaimValidatorSettings)
└─ [3] Base eligibility pipeline structure

WEEK 3-4: Rule-Based Validators
├─ [4] NPI Validator (reuse existing + eligibility-specific checks)
├─ [5] Payer ID Validator (format + known payer lookup)
├─ [6] Subscriber Demographics Validator
├─ [7] Service Type Code Validator
├─ [8] Date Range Validator
└─ [9] Request Completeness Validator

WEEK 4-5: Clearinghouse Integration
├─ [10] BaseClearinghouseClient ABC
├─ [11] StediClient implementation (request mapping, submission, response parsing)
├─ [12] 271 response parser (Stedi JSON → EligibilityResponse model)
└─ [13] Error handling (timeouts, rejections, network failures)

WEEK 5-6: AI Interpretation
├─ [14] Eligibility de-identification (extend ClaimDeidentifier)
├─ [15] AI interpretation validator (prompt design, response parsing)
└─ [16] Multi-provider support (Anthropic, OpenAI, local)

WEEK 6-7: Integration & API
├─ [17] check_eligibility() top-level API function
├─ [18] Eligibility pipeline orchestrator (3-phase)
├─ [19] CLI extension (claim-validator eligibility command)
└─ [20] REST API extension (/eligibility/check endpoint)

WEEK 7-8: Quality & Documentation
├─ [21] Unit tests (90%+ coverage target)
├─ [22] Integration tests (mock Stedi, mock LLM)
├─ [23] De-identification verification tests
├─ [24] Documentation (quickstart, API reference)
└─ [25] End-to-end demo script
```

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Stedi API changes | High | Abstract behind `BaseClearinghouseClient` interface |
| LLM response quality | Medium | Structured JSON output + regex fallback parsing |
| PHI leakage | Critical | Mandatory de-id gate, type-driven enforcement, test suite |
| Performance (LLM latency) | Medium | AI phase optional, async support in v1.1 |

---

## 16. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Three-phase pipeline (rule → clearinghouse → AI) | Catches errors cheaply before expensive calls |
| D2 | Stedi as primary clearinghouse | Best JSON API, 3,400+ payers, good docs |
| D3 | AI interpretation optional | Not all users want/need AI; keeps core lightweight |
| D4 | De-identification mandatory before AI | HIPAA compliance, zero-trust PHI approach |
| D5 | Same validator pattern as claim validation | Consistent architecture, reuse base classes |
| D6 | Pydantic frozen models | Immutability prevents accidental data mutation |
| D7 | `BaseClearinghouseClient` ABC | Future-proofs for Waystar, ClaimMD, etc. |
| D8 | Multi-LLM provider support | Flexibility: cloud (Claude, GPT) or self-hosted (Ollama) |
| D9 | Findings over exceptions | Validation issues are expected; only config errors throw |
| D10 | Optional dependency extras | `pip install claim-validator[stedi,anthropic]` — pay for what you use |

---

## 17. Glossary

| Term | Definition |
|------|-----------|
| **270** | EDI eligibility inquiry transaction (request) |
| **271** | EDI eligibility response transaction (response) |
| **AAA** | Request validation error segment in X12 EDI |
| **ASC X12** | Accredited Standards Committee X12 — EDI standard for healthcare |
| **BAA** | Business Associate Agreement — HIPAA requirement for data sharing |
| **Clearinghouse** | Intermediary that routes eligibility checks to payers |
| **CMS-1500** | Standard paper claim form for professional services |
| **Copay** | Fixed dollar amount patient pays per visit |
| **Coinsurance** | Percentage of costs patient pays after deductible |
| **Deductible** | Amount patient pays before insurance covers costs |
| **De-identification** | Removing personally identifiable information per HIPAA Safe Harbor |
| **EDI** | Electronic Data Interchange — healthcare transaction standard |
| **Finding** | A single validation issue (error, warning, or info) |
| **HIPAA** | Health Insurance Portability and Accountability Act |
| **LLM** | Large Language Model (AI) — Claude, GPT, Llama, etc. |
| **NPI** | National Provider Identifier — 10-digit provider ID |
| **Payer** | Insurance company (e.g., Blue Cross, Aetna, United) |
| **PHI** | Protected Health Information — HIPAA-regulated patient data |
| **Pipeline** | Sequence of validation phases executed in order |
| **Stedi** | Cloud clearinghouse providing modern JSON APIs for healthcare EDI |
| **Subscriber** | Person who holds the insurance policy |
| **Validator** | Component that checks one aspect of the data and returns findings |

---

*This document describes the implementation approach for the Claim Eligibility Check module of the claim-validator library. For the full PRD, architecture decisions, and epic/story breakdown, see the `_bmad-output/planning-artifacts/` directory.*
