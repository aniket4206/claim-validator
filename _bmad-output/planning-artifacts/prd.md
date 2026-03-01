---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-27.md'
  - '_bmad-output/planning-artifacts/research/domain-healthcare-prior-authorization-278-research-2026-02-27.md'
  - '_bmad-output/project-context.md'
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 0
  projectDocs: 1
classification:
  projectType: 'developer_tool'
  domain: 'healthcare'
  complexity: 'high'
  projectContext: 'brownfield'
---

# Product Requirements Document - Prior Authorization Module

**Author:** aniket
**Date:** 2026-02-27

## Executive Summary

The Prior Authorization (PA) module extends `claim-validator` to complete the pre-claim workflow chain: eligibility verification (270/271) → PA determination → PA submission (278) → claim submission (837). It is the first open-source Python library combining Pydantic-modeled 278 request/response validation, clearinghouse integration (abstract), and AI-powered response interpretation with HIPAA-compliant PHI de-identification.

**Core Problem:** After eligibility verification flags `authOrCertIndicator=Y`, no Python library exists to programmatically determine PA requirements, validate and submit 278 requests, or interpret HCR action codes and AAA reject reasons. Developers fall back to phone/fax workflows (65% of PA today), costing the industry $10B+ annually.

**Solution:** Three-phase pipeline mirroring existing library patterns — rule-based validation (offline, catches 80%+ of rejections) → clearinghouse submission (abstract interface) → AI interpretation (PHI-safe). Top-level API: `submit_prior_auth(request) -> PriorAuthResult`.

**Target Users:** Healthcare platform developers (primary) already using `claim-validator`; solo devs building healthcare SaaS (secondary). Indirect beneficiaries: revenue cycle managers, compliance officers.

**Key Differentiators:** (1) Pre-claim workflow chain completion in one package, (2) Pre-submission validation prevents rejections before clearinghouse, (3) AI-powered 278 interpretation with PHI de-identification, (4) CMS-0057-F ready architecture (FHIR PAS extensible), (5) Zero-config offline mode for immediate developer value.

**MVP Scope:** 12 features — 278 Pydantic models, enums/code tables, rule-based validators, PA determination from 271, response parsing, AAA error mapping, AI interpretation, PHI de-identification, `submit_prior_auth()` API, abstract clearinghouse interface. No concrete clearinghouse provider in MVP.

## Success Criteria

### User Success

| Criteria | Metric | Target |
|---|---|---|
| Time to first PA submission | Minutes from `pip install` to working 278 submission (sandbox/mock) | < 45 minutes |
| Pre-submission validation catch rate | % of common 278 rejections caught by rule-based validators before clearinghouse | > 80% of top 8 rejection categories |
| PA determination accuracy | Correct PA required/not-required from 271 `authOrCertIndicator` + free-text | > 95% |
| AI interpretation usefulness | Correct HCR action code interpretation + actionable next-step recommendation | > 85% vs manual review |
| Zero-config rule-based mode | Developer can validate PA requests with zero API keys or external calls | 100% offline capability |
| API ergonomics | `submit_prior_auth(dict)` accepts plain dict input, returns typed Pydantic model | Same pattern as `validate()` and `check_eligibility()` |

### Business Success

| Criteria | Target | Timeframe |
|---|---|---|
| PyPI monthly downloads (PA module adoption) | 500+ | 6 months post-release |
| GitHub stars (cumulative library) | 1,000+ | 12 months post-PA release |
| PA rejection rate reduction for adopters | 50%+ reduction (from ~30% baseline to <15%) | 12 months |
| Competitive gap | Only open-source Python library combining Pydantic 278 models + AI interpretation | At launch |
| Regulatory readiness | Architecture supports FHIR PAS addition without breaking changes before CMS Jan 2027 deadline | v2.1 release by Q3 2026 |

### Technical Success

| Criteria | Target |
|---|---|
| Test coverage | > 90% for all `prior_auth/` module code |
| Type safety | mypy strict mode passes with zero errors |
| Code quality | ruff clean (line-length=100, rules E,F,I,N,W,UP) |
| Backwards compatibility | Zero breaking changes to existing `validate()` and `check_eligibility()` APIs |
| PHI de-identification | All 18 HIPAA identifiers stripped — verified by automated tests |
| PHI logging safety | Zero PHI in logs — clearinghouse request/response bodies never logged |
| Response parsing resilience | Missing/unexpected fields return None or WARNING finding, never exception (NFR16) |
| Pipeline latency (rule-based only) | < 100ms for pre-submission validation (NFR1) |
| Public API docstrings | All public classes and functions documented (NFR32) |

### Measurable Outcomes

- **Developer adoption signal**: Number of `determine_pa_required()` calls in production (eligibility→PA chain)
- **Full-chain signal**: % of `determine_pa_required()` calls that proceed to `submit_prior_auth()`
- **Quality signal**: GitHub issues for incorrect HCR/AAA code mapping (target: < 5 in first 6 months)
- **Ecosystem signal**: Third-party blog posts, tutorials, or integrations referencing PA module

## Product Scope

### MVP — Minimum Viable Product (v2.0)

**Core deliverables (12 features from product brief):**

1. **278 Pydantic models**: `PriorAuthRequest`, `PriorAuthResponse`, `ServiceLine`, `ServiceLineDecision`, `PriorAuthError` — frozen=True
2. **Enums and code tables**: `RequestCategoryCode`, `CertificationTypeCode`, `CertificationActionCode` (A1-NA), `ServiceTypeCode`, `PlaceOfServiceCode`, AAA reject reason codes with human-readable descriptions
3. **Pre-submission rule-based validators**: NPI Luhn, member ID, DOB, ICD-10 dx validity, CPT/HCPCS validity, service date logic, cross-field consistency (dx-supports-procedure, gender/age-procedure)
4. **PA determination from 271**: `determine_pa_required(eligibility_response) -> PADeterminationResult` — parses `authOrCertIndicator` (Y/N/U) + free-text `additionalInformation.description`
5. **278 response parsing**: `parse_278_response(raw: dict) -> PriorAuthResponse` — HCR action codes, auth number, effective dates
6. **AAA error code mapping**: Top 20+ codes (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4) → human-readable messages + suggested fixes
7. **AI response interpretation**: `PriorAuthInterpreterAI` — decision summary, next-step recommendations for pended/denied cases
8. **PHI de-identification**: `PriorAuthDeidentifier` — strips all 18 HIPAA identifiers before LLM
9. **Top-level API**: `submit_prior_auth(request) -> PriorAuthResult`
10. **Pipeline**: `PriorAuthPipeline` — three-phase orchestration (rule-based → clearinghouse → AI)
11. **Abstract clearinghouse**: `BaseClearinghouseClient.submit_prior_auth()` — no concrete provider in MVP
12. **Finding code prefixes**: `PA_` (rule-based), `AI_PA_` (AI), `AAA_PA_REJECTION` (AAA errors)

**MVP clearinghouse strategy**: Abstract interface only. Rule-based validation + response parsing work fully offline. Developers implement their own clearinghouse client by subclassing `BaseClearinghouseClient`.

### Post-MVP Roadmap

See **Project Scoping & Phased Development** for detailed phased roadmap with drivers and dependencies. Summary:

- **v2.1 (Growth):** Concrete clearinghouse provider, FHIR PAS models, Da Vinci CRD, status polling, 278 update/revision
- **v2.2+ (Expansion):** 275 attachments, batch 278, auth lifecycle state machine, payer-specific PA lists, framework helpers
- **v3.0 (Intelligence):** AI medical necessity pre-screening, predictive approval probability, multi-payer analytics

## User Journeys

### Journey 1: Raj — Closing the Gap After Eligibility (Primary, Happy Path)

**Opening Scene:** Raj is a senior Python dev at MedFlow, a mid-size health-tech company. His platform already uses `claim-validator` — `validate()` for claims and `check_eligibility()` for 270/271. Every day, their eligibility checks return `authOrCertIndicator=Y` for imaging and surgical procedures. That flag shows up in their UI as a yellow warning: "Prior auth may be required." But nothing happens next. The front-desk staff prints the warning, picks up the phone, and calls the payer. Sometimes they forget. Last month, three MRI claims were denied because PA wasn't obtained — $4,500 in lost revenue.

**Rising Action:** Raj sees `prior_auth` in the `claim-validator` v2.0 changelog. He runs `pip install --upgrade claim-validator`. He adds two lines after his existing eligibility check:

```python
pa_needed = determine_pa_required(eligibility_result.response)
if pa_needed.required:
    pa_result = submit_prior_auth({"requester_npi": "1234567893", ...})
```

The rule-based validators immediately catch a missing diagnosis code in his test data — something that would have caused an AAA rejection 3 days later via fax.

**Climax:** Raj connects his clearinghouse client (his company already has an Optum contract). He subclasses `BaseClearinghouseClient`, implements `submit_prior_auth()`, and submits his first real 278 request. The response comes back: `pa_result.approved` is `True`, `pa_result.authorization_number` is `AUTH2026030100001`. The AI interpretation says: "All requested services approved. Include authorization number AUTH2026030100001 on the 837 claim. Authorization valid through 2026-04-01."

**Resolution:** Raj's platform now runs the full chain automatically: eligibility → PA determination → PA submission → auth number stored for claim. The front desk no longer makes phone calls for PA. MRI denial rate drops from 12% to 2% in the first quarter. He spent one afternoon integrating — not a sprint.

---

### Journey 2: Priya — First PA Submission in 30 Minutes (Primary, Onboarding)

**Opening Scene:** Priya is building a telehealth scheduling app. Her users — small clinics — keep complaining that patients show up for appointments only to be told "your insurance requires prior authorization for this procedure." The clinic staff didn't know. Priya has no X12 expertise. She Googled "python prior authorization" and found `claim-validator`.

**Rising Action:** Priya follows the quickstart guide. She installs the library, copies the example dict, and calls `submit_prior_auth()` without a clearinghouse configured. The rule-based phase runs and catches three issues in her test data: invalid NPI format (`PA_INVALID_NPI`), service date in the past (`PA_SERVICE_DATE_PAST`), and missing subscriber member ID (`PA_MISSING_MEMBER_ID`). She fixes them.

She then tries `determine_pa_required()` with a sample eligibility response containing `authOrCertIndicator: "Y"`. It returns `PADeterminationResult(required=True, confidence="high", reason="authOrCertIndicator=Y for service type MRI/CAT Scan")`. She doesn't need to know what `authOrCertIndicator` means — the library tells her.

**Climax:** Priya feeds a sample 278 response JSON (from the docs) into `parse_278_response()`. She gets back a `PriorAuthResponse` with `is_approved = True` and `authorization_number = "AUTH123"`. She realizes she can build her entire PA workflow without ever reading the X12 278 specification.

**Resolution:** Priya builds a `/api/prior-auth/check` FastAPI endpoint that her clinic users can hit. The response is a clean JSON Pydantic model. She went from zero PA knowledge to a working endpoint in under an hour.

---

### Journey 3: Raj — Handling a Denied PA (Primary, Edge Case / Error Recovery)

**Opening Scene:** Raj's system submits a PA request for a spinal fusion procedure. The payer returns `HCR01=A3` (Not Certified / Denied) with decision reason code indicating "medical necessity not established."

**Rising Action:** The `PriorAuthResponse` model parses the response: `pa_result.response.is_denied` is `True`. The AAA error mapping returns: "Authorization denied: Medical necessity not established for the requested procedure. The submitted diagnosis codes do not support the clinical indication for spinal fusion."

Raj's system passes the de-identified response to the AI interpreter. The AI generates: "**Denial Summary:** Spinal fusion (CPT 22612) denied for medical necessity. The primary diagnosis (M54.5 — Low back pain) is considered conservative-treatment-first by most payers. **Recommended Next Steps:** (1) Submit additional documentation showing failed conservative treatment (6+ weeks PT, imaging showing structural pathology). (2) Consider adding secondary diagnosis if applicable (e.g., M43.16 — Spondylolisthesis). (3) File peer-to-peer review request within 30 days."

**Climax:** The front desk staff sees actionable guidance instead of a cryptic "A3" code. They gather the additional clinical documentation and know exactly what to submit for appeal.

**Resolution:** The appeal succeeds. Without the AI interpretation, the staff would have called the payer, waited 45 minutes on hold, and asked "why was it denied?" — getting the same information 3 days later.

---

### Journey 4: Karen — Revenue Cycle Impact (Secondary, Business User)

**Opening Scene:** Karen manages revenue cycle at a 50-provider orthopedic group. Her team processes ~200 PA requests per week. Currently, 3 FTEs spend their entire day on phone-based PA: calling payers, faxing clinical notes, tracking pending auths in a spreadsheet. Their PA denial rate is 28%.

**Rising Action:** After Raj's team deploys the PA module, Karen starts seeing the impact in her weekly metrics dashboard. Pre-submission validation catches bad data before it reaches the payer — the "rejected at submission" category drops to near-zero. Electronic submission replaces 80% of phone calls. The team can process the same 200 PAs with 1 FTE instead of 3.

**Climax:** At the quarterly review, Karen presents: PA denial rate dropped from 28% to 11%. Average turnaround went from 3.2 days to same-day for auto-adjudicable requests. The two reassigned FTEs now focus on complex appeals and peer-to-peer reviews — higher-value work.

**Resolution:** Karen's CFO approves expanding electronic PA to all service lines. She becomes an internal champion for the platform.

---

### Journey 5: DevOps / Compliance Review (Secondary, Gatekeeper)

**Opening Scene:** The compliance officer at MedFlow receives a request to deploy the PA module to production. PA data contains diagnosis codes, procedure codes, clinical justification, and patient demographics — more sensitive than eligibility data. She needs to verify HIPAA compliance before sign-off.

**Rising Action:** She reviews the library documentation and finds:
- `PriorAuthDeidentifier` strips all 18 HIPAA identifiers before any LLM call
- Automated tests verify de-identification completeness
- Clearinghouse request/response bodies are never logged (PHI)
- Ages 90+ capped to 90 per HIPAA Safe Harbor
- Dates reduced to year-only before LLM
- PHI does not persist in memory beyond a single `submit_prior_auth()` call

**Climax:** She runs the HIPAA test suite (`tests/test_prior_auth/test_hipaa/`) — all pass. She traces a sample PA request through the pipeline and confirms PHI never leaves the clearinghouse path unprotected.

**Resolution:** Compliance sign-off granted. She adds the PA module to the approved software inventory with a note: "PHI handling follows same verified pattern as eligibility module."

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---|---|
| **Raj — Happy Path** | `determine_pa_required()` from 271, `submit_prior_auth()` API, clearinghouse client interface, auth number extraction, full-chain workflow |
| **Priya — Onboarding** | Zero-config rule-based validation, dict input support, `parse_278_response()` standalone use, quickstart documentation, Pydantic model ergonomics |
| **Raj — Denial** | HCR action code mapping, AAA error messages, AI denial interpretation, appeal guidance, `PriorAuthDeidentifier`, `is_denied` property |
| **Karen — Business** | Pre-submission validation impact, electronic submission throughput, denial rate metrics, turnaround time improvement |
| **DevOps — Compliance** | `PriorAuthDeidentifier`, HIPAA test suite, PHI logging prevention, memory lifecycle, Safe Harbor compliance |

## Domain-Specific Requirements

### Compliance & Regulatory

**HIPAA (Health Insurance Portability and Accountability Act):**
- All 18 HIPAA identifiers MUST be stripped before any LLM/AI call via `PriorAuthDeidentifier`
- PHI dual-path: clearinghouse receives raw PHI (covered entity with BAA), AI path strips PHI
- Ages 90+ capped to 90 per HIPAA Safe Harbor
- Dates reduced to year-only before LLM
- PHI must not persist in memory beyond a single `submit_prior_auth()` call
- Clearinghouse request/response bodies MUST NOT be logged (contain PHI)
- Automated test coverage for all 18 identifiers (same pattern as eligibility module)

**X12 278 HIPAA Standard (005010X217):**
- 278 Request/Response must conform to ASC X12N 005010X217 implementation guide
- BHT segment: BHT02="13" (Request) or "11" (Response)
- UM segment: Request category codes (AR/HS/SC/IN), certification types (I/R/S/E)
- HCR segment (response only): Action codes A1/A2/A3/A4/A6/CT/NA
- AAA segment: Standard X12 reject reason codes at each loop level
- SNIP levels 1-4 syntax validation expected at clearinghouse layer

**CMS-0057-F (Interoperability and Prior Authorization Final Rule):**
- Turnaround requirements effective Jan 1, 2026: 72 hours (expedited), 7 calendar days (standard)
- FHIR Prior Authorization API mandate: January 1, 2027
- CMS enforcement discretion: FHIR can satisfy HIPAA X12 278 mandate
- Architecture must support FHIR PAS addition without breaking changes (v2.1 target)
- Denial responses must include specific clinical rationale (not just administrative codes)

**CAQH CORE Operating Rules:**
- 2 business day response requirement for 278 transactions (90% compliance target)
- Standardized UM segment codes across all payers
- AAA error codes must use standard X12 reject reason codes
- HCR03 decision reason codes from WPC External Code Source 886

### Technical Constraints

**Security:**
- All clearinghouse communication over TLS 1.2+ (HIPAA Security Rule)
- API keys stored in environment variables, never in code or logs
- `BaseClearinghouseClient` implementations must use `httpx.Client` with TLS verification
- No PHI in exception messages, stack traces, or error responses

**Privacy:**
- `PriorAuthDeidentifier` MUST be called before any AI/LLM path — no exceptions
- De-identification is a pipeline gate: if it fails, AI phase must not execute
- Raw 278 request/response preserved in `PriorAuthResult.raw_response` for advanced users (not sent to LLM)
- PHI fields: patient name, DOB, member ID, SSN, address, phone, email, subscriber ID, provider NPI (when combined with patient data), diagnosis codes (when combined with demographics)

**Performance:**
- Rule-based validation: < 100ms (offline, no network calls)
- Clearinghouse round-trip: dependent on provider (Stedi ~2-5s, payer response may be async)
- AI interpretation: dependent on LLM provider (typically 2-10s)
- 278 response may be asynchronous (HCR01=A4 pended) — MVP returns pended status, polling deferred to v2.1

**Data Integrity:**
- All Pydantic models frozen=True (immutable after creation)
- Response parser must handle missing fields gracefully (None, not exception)
- Unmapped/unexpected fields generate WARNING finding, never exception
- `parse_278_response()` must NOT modify the raw input dict

### Integration Requirements

**Clearinghouse Integration:**
- `BaseClearinghouseClient.submit_prior_auth(request: PriorAuthRequest) -> dict` — abstract interface
- Must raise `ClearinghouseError` for HTTP/network failures
- Must NOT raise for business rejections (AAA segments returned in response)
- Must NOT log request/response bodies (PHI)
- Context manager support: `__enter__`, `__exit__`, `close()`
- 30s default timeout (consistent with eligibility module NFR12)

**Eligibility Module Integration:**
- `determine_pa_required()` accepts `EligibilityResponse` from existing eligibility module
- Parses `authOrCertIndicator` field from 271 benefit information
- Parses free-text `additionalInformation.description` for PA indicators
- Critical rule: If free-text says PA required, trust it even if `authOrCertIndicator` contradicts

**LLM Integration:**
- Reuses existing `BaseLLMClient` and `LLMFactory` from claim-validator core
- Same provider support: Anthropic Claude, OpenAI GPT
- Same configuration pattern: `CLAIM_VALIDATOR_AI_CONFIG` environment variable
- `PriorAuthInterpreterAI` follows `EligibilityInterpreterAI` pattern

**Code Table Integration:**
- ICD-10-CM validation: reuses existing `claim_validator/data/` code tables
- CPT/HCPCS validation: reuses existing `claim_validator/data/` code tables
- New: AAA reject reason code table (`prior_auth/data/aaa_reject_codes.json`)
- New: HCR action code descriptions (`prior_auth/data/hcr_action_codes.json`)
- New: Service type codes for PA (`prior_auth/data/service_type_codes.json`)
- Lazy singleton loading with `threading.Lock` (existing pattern)

### Risk Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| PHI leaked to LLM provider | HIPAA violation, legal liability | `PriorAuthDeidentifier` as mandatory pipeline gate; automated HIPAA test suite |
| Incorrect HCR action code mapping | Wrong authorization decision communicated to provider | 100% coverage of all 7 HCR codes; automated tests for each code path |
| AAA error misinterpretation | Provider takes wrong corrective action | Human-readable error messages reviewed against X12 specification; include raw code alongside interpretation |
| Stale ICD-10/CPT code tables | Valid codes rejected as invalid | Version code tables with release dates; document update cadence |
| Clearinghouse API changes | Submission failures | Abstract `BaseClearinghouseClient` isolates provider-specific changes; no concrete provider in MVP |
| CMS-0057-F FHIR mandate (Jan 2027) | Architecture not extensible for FHIR PAS | Abstract clearinghouse interface designed to support both X12 278 and FHIR PAS providers |
| Pended PA (A4) with no status polling | Provider doesn't know when decision is made | MVP returns pended status clearly; AI recommends manual follow-up; polling deferred to v2.1 |
| Cross-field validation false positives | Valid PA requests rejected by rule-based validators | Conservative validation (WARNING not ERROR for uncertain cross-field checks); allow override via `skip_rule_validators` config |

## Innovation & Novel Patterns

### Detected Innovation Areas

1. **Pre-Claim Workflow Chain Completion (New Paradigm)**
   - First open-source Python library to connect eligibility (270/271) → PA determination → PA submission (278) → claim (837) in a single package
   - `determine_pa_required()` bridges the gap between eligibility response and PA request — this function does not exist in any comparable library
   - The chain enables "one `pip install`, three workflows" developer experience

2. **AI-Powered 278 Response Interpretation (Novel Combination)**
   - No existing library uses LLMs to interpret X12 278 responses (HCR action codes, AAA reject reasons)
   - AI generates actionable appeal strategies for denials (A3) and documentation guidance for pended cases (A4)
   - PHI de-identification makes this possible within HIPAA constraints — first library to solve the PHI-safe AI interpretation for PA responses

3. **Pre-Submission Validation as Rejection Prevention (Paradigm Shift)**
   - Industry approach: submit → get rejected → fix → resubmit (2+ day cycle per iteration)
   - Our approach: validate offline → catch 80%+ of rejections before clearinghouse → submit clean requests
   - Cross-field consistency checks (diagnosis-supports-procedure, gender/age-procedure) go beyond basic field validation
   - This "shift left" pattern mirrors software testing best practices applied to healthcare transactions

4. **Abstract-First Clearinghouse Architecture (Strategic Design)**
   - MVP ships without a concrete clearinghouse provider — unusual but deliberate
   - Developers get full offline validation + response parsing value immediately
   - Abstract interface (`BaseClearinghouseClient`) designed to support both X12 278 and future FHIR PAS providers
   - When Stedi adds 278 API or CMS-0057-F FHIR mandate activates, concrete providers plug in without breaking changes

### Market Context & Competitive Landscape

- **No direct competitor**: Zero open-source Python libraries combine 278 Pydantic models + rule-based validation + AI interpretation
- **PA automation market**: $2.18B (2024) → $5.99B (2032), CAGR 10-18% — growing due to CMS mandates and provider demand
- **Regulatory tailwind**: CMS-0057-F turnaround requirements (effective Jan 2026) and FHIR PA API mandate (Jan 2027) drive electronic PA adoption
- **Electronic PA adoption gap**: Only ~35% of PA requests are fully electronic (vs 94%+ for eligibility) — massive room for growth
- **AMA advocacy**: 2024 AMA survey shows 94% of physicians report PA-related care delays; organized medicine pushing for reform

### Validation Approach

| Innovation | Validation Method |
|---|---|
| Pre-claim workflow chain | Integration test: eligibility result → `determine_pa_required()` → `submit_prior_auth()` → auth number extracted → embedded in claim |
| AI 278 interpretation | Benchmark against manual review of 50+ real 278 responses across all 7 HCR action codes |
| Pre-submission validation | Compare rejection rates: with validators (target <5%) vs without (baseline ~30%) using clearinghouse sandbox |
| Abstract clearinghouse | Verify concrete provider can be added without modifying existing tests or public API surface |

### Innovation Risk Mitigation

See **Domain-Specific Requirements > Risk Mitigations** for the consolidated risk table. Key innovation-specific risks: AI interpretation accuracy (mitigated by raw code inclusion), abstract clearinghouse perception (mitigated by offline value + v2.1 roadmap), workflow chain coupling (mitigated by duck typing on `determine_pa_required()`).

## Developer Tool Specific Requirements

### Project-Type Overview

The Prior Authorization module is a **Python library extension** (brownfield, adding to existing `claim-validator` package) targeting healthcare platform developers. It follows established patterns from the existing claim validation and eligibility modules — same pipeline architecture, same Pydantic model conventions, same testing and quality standards. The module is distributed via PyPI as part of the `claim-validator` package.

### Language & Platform Matrix

| Dimension | Requirement |
|---|---|
| **Language** | Python 3.10+ (match existing library requirement) |
| **Type checking** | mypy strict mode — all public APIs fully typed |
| **Linting** | ruff (line-length=100, rules E,F,I,N,W,UP) |
| **Runtime** | CPython (primary), no PyPy-specific optimizations |
| **OS support** | Linux, macOS, Windows — no OS-specific dependencies |
| **Dependencies** | Pydantic v2 (core), httpx (clearinghouse HTTP), existing `claim-validator` dependencies |

### Installation Methods

| Method | Command | Use Case |
|---|---|---|
| **Base install** | `pip install claim-validator` | Rule-based PA validation only (zero external dependencies beyond Pydantic) |
| **AI extras** | `pip install claim-validator[ai]` | Adds LLM provider SDKs (anthropic, openai) for AI interpretation |
| **Clearinghouse extras** | `pip install claim-validator[stedi]` | Adds Stedi SDK when concrete provider available (v2.1) |
| **Full install** | `pip install claim-validator[ai,stedi]` | Complete PA pipeline with AI + clearinghouse |
| **Development** | `pip install -e ".[dev,ai]"` | Local development with test dependencies |

### API Surface

**Top-level public API (3 new entry points):**

```python
# PA determination from eligibility response
determine_pa_required(eligibility_response: dict | EligibilityResponse) -> PADeterminationResult

# Full PA submission pipeline
submit_prior_auth(request: dict | PriorAuthRequest, config: PipelineConfig | None = None) -> PriorAuthResult

# Standalone 278 response parsing
parse_278_response(raw_response: dict) -> PriorAuthResponse
```

**Public Pydantic models:**

| Model | Purpose |
|---|---|
| `PriorAuthRequest` | 278 request data (subscriber, patient, requester, service lines) |
| `PriorAuthResponse` | Parsed 278 response (HCR action code, authorization number, dates) |
| `PriorAuthResult` | Pipeline output (approved, response, findings, ai_summary) |
| `PADeterminationResult` | PA required/not-required determination from 271 |
| `ServiceLine` | Individual service within a PA request |
| `ServiceLineDecision` | Per-service authorization decision from response |
| `PriorAuthError` | AAA error segment parsed |

**Public enums:**

| Enum | Values |
|---|---|
| `CertificationActionCode` | A1, A2, A3, A4, A6, CT, NA |
| `RequestCategoryCode` | AR (Admission Review), HS (Health Services Review), SC (Specialty Care Review), IN (Individual) |
| `CertificationTypeCode` | I (Initial), R (Renewal/Revision), S (Revised), E (Extension) |

**Abstract base classes (for extension):**

| Class | Purpose |
|---|---|
| `BaseClearinghouseClient` | Abstract interface for 278 clearinghouse submission |
| `PriorAuthDeidentifier` | PHI de-identification for AI path |
| `PriorAuthInterpreterAI` | AI-powered response interpretation |

### Code Examples

**Example 1 — PA determination from eligibility response:**

```python
from claim_validator import check_eligibility, determine_pa_required

eligibility_result = check_eligibility({"subscriber_id": "XYZ123", ...})
pa_determination = determine_pa_required(eligibility_result.response)

if pa_determination.required:
    print(f"PA required (confidence: {pa_determination.confidence})")
    print(f"Reason: {pa_determination.reason}")
```

**Example 2 — Full PA submission pipeline (rule-based only, no clearinghouse):**

```python
from claim_validator import submit_prior_auth

result = submit_prior_auth({
    "requester_npi": "1234567893",
    "subscriber": {"member_id": "MBR001", "first_name": "J", "last_name": "D", "dob": "1980-01-15"},
    "diagnosis_codes": ["M54.5"],
    "service_lines": [{"cpt_code": "72148", "quantity": 1, "from_date": "2026-04-01"}],
})

if not result.passed:
    for finding in result.findings:
        print(f"[{finding.code}] {finding.message}")
```

**Example 3 — Parse 278 response from clearinghouse:**

```python
from claim_validator import parse_278_response

response = parse_278_response(raw_278_json_from_clearinghouse)
if response.is_approved:
    print(f"Approved! Auth#: {response.authorization_number}")
elif response.is_denied:
    print(f"Denied: {response.decision_reason_description}")
elif response.is_pended:
    print(f"Pended — follow up after {response.follow_up_date}")
```

### Migration Guide

**For existing `claim-validator` users (v1.x → v2.0):**

| Aspect | Impact |
|---|---|
| **Existing `validate()` API** | Zero breaking changes — untouched |
| **Existing `check_eligibility()` API** | Zero breaking changes — untouched |
| **New imports** | `from claim_validator import submit_prior_auth, determine_pa_required, parse_278_response` |
| **New optional dependency** | None for rule-based only; `[ai]` extra for AI interpretation (same as eligibility) |
| **Configuration** | Same `CLAIM_VALIDATOR_AI_CONFIG` env var; same `PipelineConfig` pattern |
| **Finding codes** | New prefixes (`PA_`, `AI_PA_`, `AAA_PA_REJECTION`) — no conflicts with existing `CLM_`, `AI_`, `ELIG_` prefixes |
| **Pydantic model pattern** | Same `frozen=True` convention; same field naming (snake_case) |

**Upgrade path:**
```bash
pip install --upgrade claim-validator  # v2.0 — adds prior_auth module
# Existing code continues to work unchanged
# New PA features available via new imports
```

### Implementation Considerations

- **Module structure**: `claim_validator/prior_auth/` sub-package mirroring `claim_validator/eligibility/` layout
- **Code table loading**: Lazy singleton with `threading.Lock` (same pattern as existing `claim_validator/data/` loaders)
- **Finding severity levels**: Reuse existing `FindingSeverity` enum (ERROR, WARNING, INFO)
- **Pipeline configuration**: Extend existing `PipelineConfig` with `prior_auth_settings` section (optional, backward-compatible)
- **Test structure**: `tests/test_prior_auth/` mirroring `tests/test_eligibility/` — include `test_hipaa/` subdirectory for PHI verification
- **Documentation**: Inline docstrings on all public APIs; README section for PA quickstart; separate PA tutorial in docs/

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP — Deliver the minimum set of capabilities that solve the core developer pain point: "I verified eligibility and it says PA is required — now what?" The MVP answers this question with offline validation, response parsing, and AI interpretation, without requiring a concrete clearinghouse provider.

**Resource Requirements:** Solo developer or 2-person team with Python + healthcare domain familiarity. Estimated 4-6 weeks for a developer familiar with the existing `claim-validator` codebase patterns. No external dependencies (clearinghouse contracts, payer onboarding) needed for MVP — abstract interface only.

**MVP Philosophy Rationale:**
- The product brief identifies that 65% of PA is still phone/fax — the biggest value unlock is pre-submission validation + response parsing, not end-to-end clearinghouse submission
- Developers using `claim-validator` already have clearinghouse relationships for eligibility; they need a library that handles the PA-specific data models and validation, not a new clearinghouse connector
- Abstract interface + offline validation = zero-cost experimentation for developers (no API keys, no sandbox accounts)

### MVP Feature Set (Phase 1 — v2.0)

**Core User Journeys Supported:**
- Journey 1 (Raj — Happy Path): Full chain from `determine_pa_required()` through `submit_prior_auth()` with custom clearinghouse client
- Journey 2 (Priya — Onboarding): Zero-config rule-based validation + `parse_278_response()` standalone
- Journey 3 (Raj — Denial): HCR/AAA code mapping + AI denial interpretation
- Journey 5 (DevOps — Compliance): `PriorAuthDeidentifier` + HIPAA test suite

**Must-Have Capabilities:**

| # | Capability | Justification |
|---|---|---|
| 1 | `PriorAuthRequest` / `PriorAuthResponse` Pydantic models | Without typed models, the library has no structured data layer — product fails |
| 2 | Enums: `CertificationActionCode`, `RequestCategoryCode`, `CertificationTypeCode` | HCR/UM codes are the language of 278 — without them, responses are uninterpretable |
| 3 | Pre-submission rule-based validators (NPI, ICD-10, CPT, dates, cross-field) | Core differentiator: catch 80%+ of rejections offline before clearinghouse — this is the "aha moment" |
| 4 | `determine_pa_required()` from 271 response | Bridge function that connects eligibility to PA — unique to this library, no alternative exists |
| 5 | `parse_278_response()` with HCR action code mapping | Without response parsing, developers still need to manually decode 278 responses |
| 6 | AAA error code mapping (top 20+ codes) | Rejection errors are cryptic — human-readable messages are a deal-breaker for Priya persona |
| 7 | `PriorAuthDeidentifier` | HIPAA compliance gate — without this, AI phase cannot execute and compliance officer blocks deployment |
| 8 | `PriorAuthInterpreterAI` | AI interpretation is the second differentiator — turns "A3" into actionable appeal strategy |
| 9 | `submit_prior_auth()` top-level API | Single entry point mirrors `validate()` and `check_eligibility()` — API consistency is a must-have |
| 10 | `BaseClearinghouseClient` abstract interface | Extension point — without it, no path to concrete clearinghouse providers |
| 11 | `PriorAuthResult` pipeline output | Consistent result model — developers expect same shape as `ValidationResult` and `EligibilityResult` |
| 12 | Finding code prefixes (`PA_`, `AI_PA_`, `AAA_PA_REJECTION`) | Namespace consistency with existing library — required for finding filtering/routing |

**Can Be Manual/Deferred:**
- Concrete clearinghouse provider — developers bring their own (subclass `BaseClearinghouseClient`)
- Status polling for pended PAs — MVP returns pended status; manual follow-up via phone
- Payer-specific PA requirement lists — too large a data maintenance burden for MVP

### Post-MVP Features

**Phase 2 — Growth (v2.1):**

| Feature | Driver | Dependency |
|---|---|---|
| Concrete clearinghouse provider (Stedi 278 / Optum) | Removes "bring your own client" barrier for Priya persona | Stedi 278 API availability or Optum contract |
| FHIR PAS Claim/ClaimResponse models | CMS-0057-F mandate (Jan 2027) | FHIR R4 + Da Vinci PAS IG |
| Da Vinci CRD integration | Real-time PA determination via CDS Hooks | SMART on FHIR auth infrastructure |
| Status polling for pended PAs (HCR01=A4) | Karen persona: same-day resolution tracking | Clearinghouse webhook/polling API |
| 278 update/revision/extension (UM02=S/E) | Complete PA lifecycle for Raj persona | MVP 278 models as foundation |

**Phase 3 — Expansion (v2.2+):**

| Feature | Driver | Dependency |
|---|---|---|
| 275 attachment submission | Pended cases need additional clinical documentation | Clearinghouse 275 support |
| Batch 278 submissions | Karen persona: 200 PAs/week efficiency | Async infrastructure |
| Auth lifecycle state machine | Enterprise PA tracking | Persistence layer (application-level) |
| Payer-specific PA requirement lists | Proactive PA determination by CPT/payer | Large data curation effort |
| Django/FastAPI view helpers | Framework convenience | Stable core API |

**Phase 4 — Intelligence (v3.0):**

| Feature | Driver | Dependency |
|---|---|---|
| AI medical necessity pre-screening | Predict PA likelihood before submission | Training data from real PA outcomes |
| Automated clinical documentation assembly | Reduce documentation burden | Clinical note parsing capability |
| Predictive PA approval probability | Risk-stratify PA submissions | Historical PA decision data |
| Multi-payer PA analytics | Revenue cycle optimization for Karen persona | Data aggregation infrastructure |

### Risk Mitigation Strategy

See **Domain-Specific Requirements > Risk Mitigations** for the comprehensive risk table. Additional scoping-specific risks:

| Risk | Severity | Mitigation |
|---|---|---|
| 278 data model complexity (6-level hierarchical loops) | High | Flatten to Pydantic models that hide loop structure; expose only developer-relevant fields |
| Developers wait for concrete clearinghouse provider | Medium | Ship offline validation value immediately; mock clearinghouse for testing; v2.1 concrete provider |
| Fewer resources than planned | Medium | MVP scoped for solo developer (4-6 weeks); features independent — can ship subset |
| Absolute minimum viable scope | — | `determine_pa_required()` + validators + `parse_278_response()` + HCR/AAA mapping = useful without AI or clearinghouse |

## Functional Requirements

### PA Determination from Eligibility

- FR1: Developer can determine if prior authorization is required by passing an eligibility response (dict or `EligibilityResponse`) to `determine_pa_required()`
- FR2: System can parse `authOrCertIndicator` field (Y/N/U) from 271 benefit information to determine PA requirement
- FR3: System can parse free-text `additionalInformation.description` from 271 responses for PA indicators
- FR4: System can resolve conflicts between `authOrCertIndicator` and free-text indicators (free-text takes precedence when it indicates PA required)
- FR5: Developer can access the determination result as a `PADeterminationResult` with `required` (bool), `confidence` (high/medium/low), and `reason` (human-readable string)

### PA Request Data Modeling

- FR6: Developer can construct a `PriorAuthRequest` from a Python dict with subscriber, patient, requester, diagnosis, and service line data
- FR7: Developer can construct a `PriorAuthRequest` directly using typed Pydantic model with field validation
- FR8: System can validate that all Pydantic models are immutable (`frozen=True`) after creation
- FR9: Developer can represent individual services within a PA request as `ServiceLine` objects with CPT/HCPCS code, quantity, and date range
- FR10: Developer can specify request category (AR/HS/SC/IN) and certification type (I/R/S/E) via typed enums

### Pre-Submission Rule-Based Validation

- FR11: System can validate requester NPI using Luhn check algorithm and return `PA_INVALID_NPI` finding on failure
- FR12: System can validate that subscriber member ID is present and non-empty
- FR13: System can validate patient date of birth is present and is a valid date
- FR14: System can validate ICD-10 diagnosis codes against bundled code tables and return `PA_INVALID_DIAGNOSIS` for unknown codes
- FR15: System can validate CPT/HCPCS procedure codes against bundled code tables and return `PA_INVALID_PROCEDURE` for unknown codes
- FR16: System can validate service dates are not in the past and are within a reasonable future range
- FR17: System can perform cross-field consistency checks (diagnosis-supports-procedure, gender/age-procedure compatibility) and return WARNING-level findings
- FR18: Developer can run rule-based validation with zero API keys and zero external network calls (fully offline)
- FR19: Developer can skip specific rule-based validators via `skip_rule_validators` configuration option

### Clearinghouse Integration

- FR20: Developer can implement a custom clearinghouse client by subclassing `BaseClearinghouseClient` and implementing `submit_prior_auth()`
- FR21: System can submit a validated `PriorAuthRequest` to a clearinghouse via the abstract client interface and receive a raw dict response
- FR22: System can raise `ClearinghouseError` for HTTP/network failures while returning business rejections (AAA segments) as normal responses
- FR23: System can enforce a configurable timeout on clearinghouse calls (default 30 seconds)
- FR24: Clearinghouse client can be used as a context manager with `__enter__`, `__exit__`, and `close()` methods

### 278 Response Parsing

- FR25: Developer can parse a raw 278 JSON dict into a structured `PriorAuthResponse` model via `parse_278_response()`
- FR26: System can map all 7 HCR action codes to structured decisions: A1 (approved), A2 (partial approval), A3 (denied), A4 (pended), A6 (modified), CT (contact payer), NA (not required)
- FR27: System can extract authorization number from approved/partial/modified responses
- FR28: System can extract effective date range (start/end) from authorization decisions
- FR29: System can parse per-service-line decisions into `ServiceLineDecision` objects
- FR30: Developer can access convenience properties on `PriorAuthResponse`: `is_approved`, `is_denied`, `is_pended`, `authorization_number`, `decision_reason_description`
- FR31: System can handle missing or unexpected fields in 278 response gracefully (return None, not exception)

### AAA Error Handling

- FR32: System can parse AAA reject segments from 278 responses into `PriorAuthError` objects
- FR33: System can map top 20+ AAA reject reason codes (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4) to human-readable error messages
- FR34: System can provide suggested fixes alongside each AAA error message
- FR35: System can generate `AAA_PA_REJECTION` finding codes for each AAA error encountered

### PHI De-Identification

- FR36: System can strip all 18 HIPAA identifiers from PA request/response data before any LLM call via `PriorAuthDeidentifier`
- FR37: System can cap ages 90+ to 90 per HIPAA Safe Harbor
- FR38: System can reduce dates to year-only before sending to LLM
- FR39: System can enforce de-identification as a mandatory pipeline gate — if de-identification fails, AI phase must not execute
- FR40: System can ensure PHI does not persist in memory beyond a single `submit_prior_auth()` call

### AI-Powered Interpretation

- FR41: Developer can enable AI-powered response interpretation via `PriorAuthInterpreterAI` using existing LLM configuration (`CLAIM_VALIDATOR_AI_CONFIG`)
- FR42: System can generate a human-readable decision summary from HCR action codes and decision reason codes
- FR43: System can generate next-step recommendations for pended cases (A4) including likely documentation needed
- FR44: System can generate appeal strategy suggestions for denied cases (A3) based on decision reason codes
- FR45: System can produce AI findings with `AI_PA_` prefix codes at WARNING severity level
- FR46: System can include raw HCR/AAA codes alongside AI interpretation for verification

### Pipeline Orchestration

- FR47: Developer can submit a prior authorization through the complete three-phase pipeline via `submit_prior_auth()`
- FR48: System can orchestrate rule-based validation → clearinghouse submission → AI interpretation as sequential pipeline phases
- FR49: System can skip clearinghouse and AI phases when no clearinghouse client is configured (rule-based-only mode)
- FR50: System can skip AI phase when no LLM provider is configured (clearinghouse-only mode)
- FR51: Developer can access the pipeline result as `PriorAuthResult` with `approved`, `response`, `findings`, `ai_summary`, `passed`, `authorization_number`, `raw_response`, `execution_time`

### Finding Code System

- FR52: System can generate findings with `PA_` prefix for rule-based validation issues
- FR53: System can generate findings with `AI_PA_` prefix for AI interpretation results
- FR54: System can generate findings with `AAA_PA_REJECTION` prefix for AAA business rejections
- FR55: System can generate findings with `CLEARINGHOUSE_` prefix for infrastructure errors
- FR56: System can assign severity levels (ERROR, WARNING, INFO) to all findings using existing `FindingSeverity` enum

## Non-Functional Requirements

### Performance

- NFR1: Rule-based validation phase must complete in < 100ms for a single PA request (offline, no network calls)
- NFR2: Code table loading (ICD-10, CPT, AAA codes) must use lazy singleton pattern — first load < 500ms, subsequent lookups < 1ms
- NFR3: `parse_278_response()` must complete in < 50ms for a single 278 response dict
- NFR4: `determine_pa_required()` must complete in < 10ms for a single eligibility response
- NFR5: Pipeline overhead (orchestration, finding aggregation) must add < 20ms beyond individual phase execution times
- NFR6: Memory footprint of loaded code tables must not exceed 50MB

### Security & Privacy

- NFR7: All 18 HIPAA identifiers must be stripped by `PriorAuthDeidentifier` before any data reaches an LLM provider — verified by automated tests
- NFR8: De-identification must be a mandatory pipeline gate: if `PriorAuthDeidentifier` raises an exception, the AI phase must not execute under any circumstance
- NFR9: Clearinghouse communication must use TLS 1.2+ — `BaseClearinghouseClient` implementations must enforce TLS verification (no `verify=False`)
- NFR10: API keys and credentials must be sourced from environment variables only — never hardcoded, never in logs, never in exception messages
- NFR11: PHI must not appear in log output — clearinghouse request/response bodies must never be logged at any log level
- NFR12: PHI must not appear in exception messages or stack traces — error messages must reference field names, not field values
- NFR13: PHI must not persist in memory beyond a single `submit_prior_auth()` call — no module-level caching of patient data
- NFR14: Ages 90+ must be capped to 90 per HIPAA Safe Harbor before LLM path
- NFR15: Dates must be reduced to year-only before LLM path

### Reliability & Error Handling

- NFR16: Missing or unexpected fields in 278 response must return `None` or generate a WARNING finding — never raise an unhandled exception
- NFR17: Unmapped HCR action codes must generate a WARNING finding with the raw code value — never raise an exception
- NFR18: Unmapped AAA reject reason codes must generate a WARNING finding with the raw code value and a generic "Contact payer for details" message
- NFR19: Clearinghouse HTTP errors (timeout, connection refused, 5xx) must raise `ClearinghouseError` with a descriptive message — never expose raw HTTP response bodies
- NFR20: LLM provider errors (timeout, rate limit, API error) must be caught and result in AI phase skipping gracefully — rule-based and clearinghouse results must still be returned
- NFR21: Invalid input to `submit_prior_auth()` (wrong type, missing required fields) must raise `ValueError` with a clear message before any pipeline phase executes

### Integration Compatibility

- NFR22: PA module must not introduce any breaking changes to existing `validate()` or `check_eligibility()` public APIs
- NFR23: PA module must reuse existing `BaseLLMClient`, `LLMFactory`, and `CLAIM_VALIDATOR_AI_CONFIG` configuration — no parallel LLM configuration system
- NFR24: PA module must reuse existing `FindingSeverity` enum and finding model — no parallel finding system
- NFR25: PA module must reuse existing code table loading infrastructure (`claim_validator/data/`) with lazy singleton + `threading.Lock` pattern
- NFR26: New finding code prefixes (`PA_`, `AI_PA_`, `AAA_PA_REJECTION`, `CLEARINGHOUSE_`) must not conflict with existing prefixes (`CLM_`, `AI_`, `ELIG_`)
- NFR27: `PriorAuthRequest` must accept both dict and Pydantic model input (same as `validate()` and `check_eligibility()` patterns)
- NFR28: Default clearinghouse timeout must be 30 seconds (consistent with eligibility module)

### Code Quality & Maintainability

- NFR29: All `prior_auth/` module code must achieve > 90% test coverage
- NFR30: All code must pass mypy strict mode with zero errors
- NFR31: All code must pass ruff linting (line-length=100, rules E,F,I,N,W,UP) with zero warnings
- NFR32: All public classes and functions must have docstrings
- NFR33: All Pydantic models must use `frozen=True` (immutable after creation)
- NFR34: `parse_278_response()` must not modify the input dict (no side effects)
- NFR35: Module structure must mirror existing `claim_validator/eligibility/` layout for developer familiarity
- NFR36: Test structure must include dedicated `test_hipaa/` subdirectory verifying all 18 HIPAA identifier de-identification
