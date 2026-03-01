---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '_bmad-output/planning-artifacts/research/domain-healthcare-prior-authorization-278-research-2026-02-27.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-26.md'
  - '_bmad-output/project-context.md'
date: '2026-02-27'
author: 'aniket'
---

# Product Brief: Prior Authorization Module for claim-validator

## Executive Summary

The `claim-validator` library provides two-phase claim validation (rule-based → AI-powered) and is extending to eligibility verification (270/271). This product brief defines a **Prior Authorization Module** (v2.x) that completes the pre-claim workflow chain: eligibility check → prior auth determination → prior auth request (278) → claim submission (837).

Prior authorization is the most burdensome administrative process in US healthcare, costing the industry an estimated **$10+ billion annually** and consuming 13 hours per physician per week. Yet only ~35% of medical PA requests are fully electronic via 278 (compared to 94%+ for eligibility), and no Python library exists that combines Pydantic-modeled 278 validation with clearinghouse integration and AI-powered response interpretation.

The module introduces `submit_prior_auth()` as the top-level API, mirroring the existing `validate()` and `check_eligibility()` patterns. It follows the same three-phase pipeline architecture (rule-based → clearinghouse → AI interpretation) that developers already know from the eligibility module, with the addition of PA determination from 271 responses and 278 response parsing with HCR action code handling.

---

## Core Vision

### Problem Statement

Healthcare organizations and developers building provider-facing systems face a critical gap in the prior authorization workflow. After verifying eligibility (271 response indicates `authOrCertIndicator=Y`), there is no Python library to programmatically:

1. **Determine if PA is required** — parsing `authOrCertIndicator` and free-text indicators from 271 responses
2. **Validate PA request data** — catching the ~80% of rejections caused by missing fields, invalid codes, and cross-field inconsistencies before submission
3. **Submit 278 requests** — through a clearinghouse with proper envelope construction
4. **Interpret 278 responses** — mapping HCR action codes (A1/A2/A3/A4/A6/CT/NA) and AAA reject reason codes to actionable decisions
5. **De-identify PHI for AI interpretation** — safely sending PA decisions to LLMs for human-readable summaries

Today, developers must manually construct X12 278 EDI segments, integrate with clearing house APIs one-off, and write custom response parsers — or resign their users to phone/fax workflows that consume 2+ days per authorization.

### Problem Impact

| Impact Area | Metric |
|---|---|
| Industry cost of PA administration | $10+ billion annually |
| Physician time spent on PA | 13 hours per week (AMA 2023) |
| Electronic PA adoption rate (278) | ~35% (vs 94% for eligibility) |
| Average PA turnaround (non-electronic) | 2+ business days |
| PA-related claim denials | ~30% denied for medical necessity, ~25% for incomplete docs |
| PA automation market size | $2.18B (2024) → $5.99B (2032), CAGR 10-18% |

### Why Existing Solutions Fall Short

| Solution | Gap |
|---|---|
| **Existing `PriorAuthAI` validator** | Only detects procedures likely needing PA (AI hint); does NOT submit or manage actual 278 transactions |
| **x12-edi-tools** | Has some X12 parsing, but no 278 models, no clearinghouse connectivity, no AI interpretation |
| **Stedi platform** | Provides 278 EDI Guides and JSON format, but no dedicated 278 API endpoint yet; no Python SDK |
| **pyx12 / TigerShark** | Legacy X12 parsers; no Pydantic, no AI, no clearinghouse integration |
| **Waystar / Availity** | Commercial platforms; closed source, expensive, no library-level Python integration |
| **Manual fax/phone workflows** | 2+ day turnaround, 65% of PA still processed this way |

### Proposed Solution

Extend `claim-validator` with a `prior_auth/` module that follows the established three-phase pipeline architecture:

**Phase 1 — Offline Rule-Based Validation** (zero external calls):
- Validate requester NPI (Luhn check), subscriber member ID, patient demographics
- Validate ICD-10 diagnosis codes and CPT/HCPCS procedure codes against bundled code tables
- Validate service dates (not past, reasonable future), cross-field consistency (diagnosis-supports-procedure, gender/age-procedure compatibility)
- PA determination from 271 response (`determine_pa_required()`) — parses `authOrCertIndicator` and free-text `additionalInformation.description`
- Finding code prefix: `PA_` (e.g., `PA_INVALID_NPI`, `PA_MISSING_DIAGNOSIS`)

**Phase 2 — Clearinghouse Submission** (online):
- `BaseClearinghouseClient.submit_prior_auth(request) → dict` — abstract interface
- Submit validated 278 request through clearinghouse
- Parse 278 response into `PriorAuthResponse` model with HCR action code handling
- Map AAA reject reason codes to human-readable error messages
- Finding code prefix: `CLEARINGHOUSE_` for infrastructure errors, `AAA_PA_REJECTION` for business rejections

**Phase 3 — AI Interpretation** (optional):
- `PriorAuthDeidentifier.deidentify()` — strips all 18 HIPAA identifiers from PA response
- AI interprets authorization decision, suggests next steps based on HCR action code
- For pended cases (A4): AI identifies what additional documentation is likely needed
- For denials (A3): AI suggests appeal strategies based on decision reason codes
- Finding code prefix: `AI_PA_` (e.g., `AI_PA_DECISION_SUMMARY`, `AI_PA_APPEAL_SUGGESTION`)

**Top-level API:** `submit_prior_auth(request_dict_or_PriorAuthRequest) -> PriorAuthResult`

### Key Differentiators

1. **Completes the pre-claim chain** — First library to connect eligibility (271) → PA determination → PA submission (278) → claim (837) in a single package
2. **Same library, same patterns** — Developers using `validate()` and `check_eligibility()` get `submit_prior_auth()` with identical pipeline architecture and PHI handling
3. **Pre-submission validation prevents 80%+ of rejections** — Rule-based validators catch missing fields, invalid codes, and cross-field inconsistencies before hitting the clearinghouse
4. **First open-source Python 278 library** — Pydantic models for the full 278 loop hierarchy with HCR action codes, AAA error codes, and UM/SV1/SV2 segment support
5. **AI-powered decision interpretation** — Maps cryptic HCR/AAA codes to actionable next steps with PHI de-identification
6. **CMS-0057-F ready architecture** — Abstract clearinghouse interface supports both X12 278 and future FHIR PAS providers; FHIR models deferred to v2.1 (mandate not until Jan 2027)
7. **Regulatory timing** — CMS turnaround requirements (72hr expedited / 7 day standard) effective Jan 2026; FHIR PA API mandate Jan 2027; PA automation market growing 10-18% CAGR

---

## Target Users

### Primary Users

**Persona 1: "Raj" — The Healthcare Platform Developer**
- **Role**: Senior Python developer at a mid-size health-tech company building EHR/practice management platforms
- **Context**: Already using `claim-validator` for claim validation and `check_eligibility()` for 270/271. His platform's eligibility responses flag `authOrCertIndicator=Y` for imaging and surgical procedures — but today, that flag goes nowhere. Staff fall back to phone/fax for PA
- **Current Pain**: After eligibility check returns "PA required," his system hits a dead end. Staff must manually call the payer's authorization line (30-45 min hold), fax clinical documentation, and wait 2-5 business days for a decision. He maintains a separate spreadsheet to track pending authorizations
- **Motivation**: One `pip install` upgrade that adds `submit_prior_auth()` alongside existing `validate()` and `check_eligibility()` — same pipeline, same PHI handling, same patterns. Complete the pre-claim chain without learning a new library
- **Success Vision**: "When our eligibility check flags PA required, the system automatically builds the 278 request, validates it, submits it, and shows the authorization decision — all in the same pipeline I already know"
- **Aha! Moment**: Rule-based validators catch a missing diagnosis code that would have caused a rejection 3 days later via fax

**Persona 2: "Priya" — The Solo Dev / Startup Founder**
- **Role**: Full-stack developer building a telehealth scheduling platform
- **Context**: No deep X12/EDI expertise. Her platform handles appointment booking, and patients keep getting turned away at the provider's office because prior auth wasn't obtained
- **Current Pain**: Cannot afford commercial PA platforms ($$$). Tried to read the X12 278 specification directly — gave up after encountering the 6-level hierarchical loop structure (2000A through 2000F). Her workaround: a web form that emails the provider's office to call the payer manually
- **Motivation**: Get PA determination and submission working in her app in a day. She wants to call one function with a dict of patient/procedure data and get back a Pydantic model she can use in her FastAPI endpoint
- **Success Vision**: "I call `determine_pa_required(eligibility_response)` to check if PA is needed, then `submit_prior_auth(request)` to submit it. I never have to think about HL segments or AAA codes"
- **Aha! Moment**: The `PriorAuthResponse.is_approved` property and human-readable `decision_reason_description` mean she doesn't need to learn HCR action codes

### Secondary Users

**Persona 3: "Karen" — Revenue Cycle Manager (Indirect Beneficiary)**
- **Role**: Revenue cycle manager at a multi-provider healthcare organization
- **Context**: Doesn't use the library directly, but her team spends 4-6 hours daily on phone-based PA submissions. Authorization delays cause appointment cancellations and revenue loss
- **Influence**: Tells the CTO "our PA denial rate is 30% and it's costing us $200K/year in rework — we need electronic submission." Drives adoption decisions
- **Success Vision**: PA turnaround drops from 2-5 days to same-day for auto-adjudicable requests; pre-submission validation cuts rejection rate from 30% to under 10%

**Persona 4: "DevOps / Compliance Officer"**
- **Role**: Security/compliance team evaluating the library for production PA workflows
- **Context**: PA data is especially sensitive — contains diagnosis codes, procedure codes, and clinical justification alongside patient demographics. PHI exposure risk is higher than eligibility
- **Influence**: Gates production deployment of PA module. Requires proof that PHI is de-identified before any LLM call and that clearinghouse communication follows HIPAA requirements
- **Success Vision**: Clear documentation showing `PriorAuthDeidentifier` strips all 18 HIPAA identifiers. Audit trail for all 278 submissions. BAA coverage for clearinghouse partner

### User Journey

| Stage | Raj (Platform Dev) | Priya (Solo Dev) |
|---|---|---|
| **Discovery** | Sees `prior_auth` module in `claim-validator` changelog after upgrading for eligibility | Searches PyPI/GitHub for "python prior authorization 278" |
| **Onboarding** | `pip install claim-validator[stedi]`, reads familiar three-phase pipeline docs | Follows quickstart: "Submit your first PA in 15 minutes" |
| **First Use** | Adds `determine_pa_required()` after existing `check_eligibility()` call | Runs first PA submission against clearinghouse sandbox |
| **Aha! Moment** | Pre-submission validation catches invalid NPI that would have been rejected 3 days later | `PriorAuthResponse.is_approved` + `authorization_number` — no HCR codes to learn |
| **Core Usage** | Integrates full chain: eligibility → PA determination → PA submission → auth# on 837 claim | Builds PA status endpoint in her FastAPI app |
| **Long-term** | Extends with custom validators for payer-specific rules; contributes back to OSS | Upgrades to production clearinghouse; relies on library for all payer PA workflows |

---

## Success Metrics

### User Success Metrics

| Metric | Measure | Target |
|---|---|---|
| Time to first PA submission | Minutes from `pip install` to working 278 submission (sandbox) | < 45 minutes |
| Pre-submission validation catch rate | % of common 278 rejections caught by rule-based validators before clearinghouse | > 80% |
| PA determination accuracy from 271 | Correct identification of PA required/not required from eligibility response | > 95% |
| AI interpretation accuracy | Correct action code interpretation + next-step recommendation vs manual review | > 85% |
| HCR action code coverage | % of HCR action codes (A1/A2/A3/A4/A6/CT/NA) correctly parsed and mapped | 100% (all 7 codes) |
| AAA error code coverage | % of common AAA reject reason codes mapped to human-readable messages | > 90% of top 20 codes |

### Business Objectives

| Objective | Target | Timeframe |
|---|---|---|
| PyPI monthly downloads (PA module) | 500+ | 6 months post-release |
| GitHub stars (cumulative library) | 1,000+ | 12 months post-PA release |
| PA rejection rate reduction for adopters | 50%+ reduction (from ~30% to <15%) | 12 months |
| Electronic PA adoption among library users | 80%+ of PA submissions via 278 (vs fax/phone) | 12 months |
| PA market TAM addressable | PA automation market $2.18B (2024) → $5.99B (2032) | Ongoing |

### Key Performance Indicators

- **Leading indicator**: Number of `determine_pa_required()` calls in production (signals eligibility-to-PA workflow adoption)
- **Engagement indicator**: Ratio of rule-based-only vs full pipeline usage (adoption of clearinghouse + AI phases)
- **Quality indicator**: GitHub issues related to incorrect HCR/AAA code mapping or 278 response parsing
- **Conversion indicator**: % of `determine_pa_required()` calls that proceed to `submit_prior_auth()` (measures full-chain adoption)
- **Ecosystem indicator**: Third-party blog posts, tutorials, or integrations referencing the PA module
- **Regulatory indicator**: Adoption rate increase as CMS-0057-F FHIR PA API deadline (Jan 2027) approaches

---

## MVP Scope

### Core Features (MVP v2.0)

| # | Feature | Description |
|---|---|---|
| 1 | **278 Request/Response Pydantic models** | `PriorAuthRequest`, `PriorAuthResponse`, `ServiceLine`, `ServiceLineDecision`, `PriorAuthError` — frozen=True, same pattern as `ClaimData` and `EligibilityRequest` |
| 2 | **Enums and code tables** | `RequestCategoryCode` (AR/HS/SC/IN), `CertificationTypeCode` (I/R/S/E), `CertificationActionCode` (A1/A2/A3/A4/A6/CT/NA), `ServiceTypeCode`, `PlaceOfServiceCode`, AAA reject reason codes |
| 3 | **Pre-submission rule-based validators** | NPI Luhn check, subscriber member ID present, patient DOB present, ICD-10 diagnosis code validity, CPT/HCPCS procedure code validity, service date validation (not past, reasonable future), cross-field consistency (diagnosis-supports-procedure, gender/age-procedure) |
| 4 | **PA determination from 271 response** | `determine_pa_required(eligibility_response) -> PADeterminationResult` — parses `authOrCertIndicator` (Y/N/U), free-text `additionalInformation.description`, returns structured determination with confidence level |
| 5 | **278 response parsing** | Parse clearinghouse JSON response into `PriorAuthResponse` model — HCR action code mapping (A1=approved, A2=partial, A3=denied, A4=pended, A6=modified, CT=contact, NA=not required), authorization number extraction, effective date range |
| 6 | **AAA error code mapping** | Map top 20+ AAA reject reason codes (04, 15, 33, 35, 41-51, 56-58, 60, 71-73, 79, T4) to human-readable error messages with suggested fixes |
| 7 | **AI-powered response interpretation** | `PriorAuthInterpreterAI` — de-identify PHI via `PriorAuthDeidentifier`, send to LLM for decision summary, next-step recommendations for pended/denied cases, appeal strategy suggestions |
| 8 | **`submit_prior_auth()` top-level API** | `submit_prior_auth(request_dict_or_PriorAuthRequest) -> PriorAuthResult` — orchestrates three-phase pipeline, mirrors `validate()` and `check_eligibility()` patterns |
| 9 | **`PriorAuthDeidentifier`** | Strips all 18 HIPAA identifiers from PA request/response before LLM — extends existing de-identification pattern (`ClaimDeidentifier`, `EligibilityDeidentifier`) |
| 10 | **Finding code prefixes** | `PA_` for rule-based findings, `AI_PA_` for AI findings, `AAA_PA_REJECTION` for AAA errors, `CLEARINGHOUSE_` for infrastructure errors |
| 11 | **Abstract clearinghouse interface** | `BaseClearinghouseClient.submit_prior_auth(request) -> dict` — no concrete provider in MVP (validation-only + response parsing mode supported) |
| 12 | **`PriorAuthResult` pipeline output** | `approved`, `response`, `findings`, `ai_summary`, `passed`, `authorization_number`, `raw_response`, `execution_time` — mirrors `EligibilityResult` |

**MVP Clearinghouse Strategy: Abstract Interface Only**

The MVP ships with `BaseClearinghouseClient.submit_prior_auth()` as an abstract method, with no concrete clearinghouse provider. This means:
- Rule-based validation works fully offline (zero API keys needed)
- Response parsing works with any raw 278 JSON dict (clearinghouse-agnostic)
- Developers can implement their own clearinghouse client by subclassing `BaseClearinghouseClient`
- AI interpretation works on any `PriorAuthResponse` model

**Rationale:** Stedi does not yet have a dedicated 278 API endpoint. The existing Stedi integration (for eligibility) can be extended when Stedi adds 278 support, or developers can implement Optum's 278x215 API as a concrete provider. Shipping validation + parsing without a locked-in provider maximizes immediate value.

### Out of Scope (MVP)

| Feature | Rationale | Target Version |
|---|---|---|
| **FHIR PAS models** (Claim/ClaimResponse) | CMS mandate not until Jan 2027; premature abstraction | v2.1 |
| **Da Vinci CRD/DTR integration** | PA determination via CDS Hooks; requires SMART on FHIR auth | v2.1+ |
| **Status polling / webhook support** | For pended PAs (HCR01=A4); adds async complexity | v2.1 |
| **278 update/revision/extension requests** | UM02=S (Revised), UM02=E (Extension); secondary workflow | v2.1 |
| **275 attachment submission** | Additional documentation for pended cases; separate transaction | v2.2 |
| **Batch 278 submissions** | Multiple PAs in single file; adds concurrency complexity | v2.2 |
| **Auth lifecycle state machine** | Request→Received→Review→Decision→Active→Used→Expired; application-level concern | v2.2 |
| **Concrete clearinghouse provider** | No Stedi 278 API yet; Optum/Availity possible in v2.1 | v2.1 |
| **Payer-specific PA requirement lists** | CPT/HCPCS codes requiring PA by payer; large data maintenance burden | v2.2 |
| **Django/FastAPI view helpers** | Framework integration convenience; not core PA functionality | v2.2 |

### MVP Success Criteria

- Developer submits first PA (sandbox or mock) in < 45 minutes from `pip install`
- Rule-based validators catch > 80% of common 278 rejection scenarios (tested against AAA code catalog)
- `determine_pa_required()` correctly identifies PA requirement from 271 responses with > 95% accuracy
- All 7 HCR action codes parsed correctly with human-readable descriptions
- Top 20 AAA reject reason codes mapped to actionable error messages
- AI interpretation produces actionable decision summary with next-step recommendations
- All tests pass, mypy strict, ruff clean — same quality bar as existing library
- PHI de-identification verified against all 18 HIPAA identifiers (automated tests)

### Future Vision

| Phase | Version | Features |
|---|---|---|
| **PA Foundation** | v2.0 (MVP) | 278 models, rule-based validators, PA determination from 271, response parsing, AAA mapping, AI interpretation, `submit_prior_auth()` API |
| **Clearinghouse + FHIR** | v2.1 | Concrete clearinghouse provider (Stedi 278 when available, or Optum/Availity), FHIR PAS Claim/ClaimResponse models, Da Vinci CRD integration for PA determination, status polling for pended cases |
| **Full Lifecycle** | v2.2 | 278 update/revision/extension, 275 attachment submission, batch 278, auth lifecycle state machine, payer PA requirement lists, Django/FastAPI helpers |
| **Intelligence** | v3.0 | AI-powered medical necessity pre-screening, automated clinical documentation assembly, predictive PA approval probability, multi-payer PA analytics |
