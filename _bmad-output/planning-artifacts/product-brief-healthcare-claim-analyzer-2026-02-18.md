---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-17.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-18.md'
  - '_bmad-output/project-context.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-17.md'
date: '2026-02-18'
author: 'aniket'
---

# Product Brief: healthcare-claim-analyzer

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

**healthcare-claim-analyzer** is an open-source, pip-installable Python library for healthcare claim validation and submission in the US market. It provides comprehensive pre-claim validation (CMS-1500 / 837P) through a two-phase pipeline: deterministic rule-based checks that work fully offline with zero configuration, and AI-powered clinical validation that supports any LLM provider — Claude, GPT, Gemini, Llama, Ollama, or any OpenAI-compatible endpoint.

The US healthcare system processes 5.5 billion claims annually, with 10-15% denied on first submission. 60-80% of those denials are preventable with adequate pre-submission validation, yet no open-source library exists to address this — forcing developers to either pay $50K-$500K/year for commercial engines or build fragile custom solutions from scratch. healthcare-claim-analyzer fills this gap with a framework-agnostic core (Django, FastAPI, Flask, or raw Python), built-in HIPAA-compliant de-identification for safe LLM usage, and a pluggable validator architecture that supports community-contributed payer-specific rule sets.

**Business Model:** Open-source core (rule-based validation, multi-LLM support, all integrations) with a paid premium tier for hosted API, enterprise support, advanced analytics, and managed AI validation.

---

## Core Vision

### Problem Statement

Developers building healthcare billing systems in the US face a broken tooling landscape for pre-claim validation. The choice today is: pay enterprise prices for opaque commercial engines (Change Healthcare, Inovalon, Waystar), build custom validation from scratch spending months encoding CMS rules and payer quirks, or rely on basic clearinghouse scrubbers that catch format errors but miss the majority of preventable denials. There is no maintained open-source Python library for healthcare claim validation — not a single one on PyPI.

### Problem Impact

- **$19.7 billion/year** wasted on claim denial rework in the US alone
- **10-15% initial denial rate** across the industry, climbing annually as payers tighten cost containment
- **60-80% of denials are preventable** with pre-submission checks (missing fields, invalid NPI, coding errors, eligibility gaps, timely filing)
- **$25-$118 cost per denied claim** to rework, with only 35-50% of denials ever appealed
- Developers on Reddit/HealthIT forums consistently report: "We spent 6 months building our own claim scrubber and it still misses things" and "Every payer is a special snowflake"
- Health-tech startups and small billing companies are priced out of commercial solutions and locked into vendor ecosystems

### Why Existing Solutions Fall Short

| Solution | Gap |
|---|---|
| **Change Healthcare / Inovalon** | $50K-$500K/year, enterprise sales cycles, vendor lock-in, conflict-of-interest (Optum/UHG owns Change Healthcare AND is a payer) |
| **Stedi** | Solves EDI format translation but NOT content validation — helps you produce valid 837P but doesn't check if the claim will pay |
| **Candid Health** | API-first RCM but full-service SaaS, not embeddable as a library |
| **Clearinghouse scrubbers (ClaimMD, Office Ally)** | Basic format checks only — miss clinical plausibility, coding logic, payer-specific rules |
| **Open-source (pyx12, python-hl7)** | EDI parsing only, zero business rule validation, zero claim logic |
| **All of the above** | Locked to single AI provider or no AI at all. None offer LLM-agnostic AI validation with HIPAA-safe de-identification |

### Proposed Solution

A pip-installable Python library — `claim-validator` — with:

1. **Zero-config rule-based validation** — NPI (Luhn + NPPES), ICD-10, CPT/HCPCS format, required fields, date logic, duplicate detection, timely filing — all offline, no API keys, no database
2. **LLM-agnostic AI validation** — Plug in Claude, GPT-4, Gemini, Llama, Ollama, vLLM, or any OpenAI-compatible endpoint. Built-in HIPAA de-identification strips all 18 identifiers before any LLM call
3. **Framework-agnostic core** — Works with raw Python dicts, Django models, Pydantic models, or FHIR resources. Optional integrations: `pip install claim-validator[django]`, `[fastapi]`, `[flask]`
4. **Pluggable payer-specific rules** — Ship with CMS/Medicare rules, community-contributed payer rule sets as plugins
5. **Structured, actionable output** — Every finding includes severity, field, human-readable explanation, fix suggestion, and stable error code
6. **CLI tool** — `claim-validate file.json` for CI/CD pipelines and command-line validation

### Key Differentiators

1. **Only open-source option** — Zero competition on PyPI. The "SQLite of claim validation"
2. **Bring Your Own LLM** — No vendor lock-in on AI. Use Claude today, switch to self-hosted Llama tomorrow. HIPAA de-identification is built into the library, not the LLM provider
3. **Offline-first** — Rule-based validation works with zero network calls, zero API keys, zero database. Ship bundled code tables (ICD-10, HCPCS, taxonomy) with annual update commands
4. **5-minute integration** — `pip install claim-validator` → `from claim_validator import validate` → `result = validate(claim_dict)`. Done
5. **Two-phase pipeline** — Deterministic rules catch 80% of issues instantly; AI catches clinical edge cases that rules can't (wrong gender/age for codes, implausible diagnosis-procedure combinations, undocumented payer quirks)
6. **Community-driven payer rules** — Open-source payer rule repository (like tax code libraries), reducing the "every payer is a snowflake" problem through collective intelligence

---

## Target Users

### Primary Users

#### Persona 1: "Priya" — Backend Developer at a Health-Tech Startup

**Background:** Priya is a mid-level Python/Django developer at a Series A telehealth startup (15-person engineering team). They're building a patient billing portal and need to submit claims to clearinghouses. She has strong Python skills but zero healthcare billing domain expertise — she's never seen a CMS-1500 form before this project.

**Current Pain:**
- Spent 3 weeks reading CMS-1500 documentation and X12 837P specs (which cost $500 to purchase)
- Built a basic NPI Luhn check from a Stack Overflow answer — later discovered it doesn't verify the NPI is active or matches the provider's taxonomy
- Hand-coded ICD-10 format validation with regex — misses clinical plausibility entirely
- Claims get rejected with cryptic CARC/RARC codes she has to Google one by one
- Her company's 18% first-submission denial rate is bleeding revenue
- CTO rejected a $75K/year Change Healthcare contract — "find an open-source solution"

**Goals:**
- Validate claims before submission with confidence, not guesswork
- Understand WHY a claim will be denied, not just THAT it's invalid
- Integrate validation into their Django app without rearchitecting
- Use AI to catch edge cases her rules can't — but her CTO won't approve sending PHI to external APIs without HIPAA guarantees

**Success Moment:** First week after integration, denial rate drops from 18% to 5%. Her CTO asks "what changed?" She shows `pip install claim-validator` and 12 lines of code.

**Tech Profile:** Python 3.11+, Django/DRF, PostgreSQL, Celery, deployed on AWS. Evaluates libraries by: GitHub stars, docs quality, `pip install` simplicity, and "can I get a working example in 5 minutes?"

---

#### Persona 2: "Marcus" — Lead Developer at a Medical Billing Company

**Background:** Marcus is a senior developer at a mid-size billing company that processes claims for 200+ small practices across 15 states. He maintains their internal claim processing pipeline — a mix of Python scripts, a Django admin interface, and direct ClaimMD API integration. He's been in healthcare IT for 8 years and knows the domain deeply.

**Current Pain:**
- Maintains 12,000+ lines of custom validation code that he wrote over 4 years — brittle, undocumented, and only he fully understands
- Every quarter, CMS updates NCCI edits and MUE limits — he spends 2 weeks manually updating rule tables
- Each of the 15 payers has quirks: "UnitedHealthcare wants modifier 25 on E/M with procedures, BCBS-FL rejects if rendering NPI isn't on the claim even when billing NPI is individual" — all encoded as if/else spaghetti
- Processes 3,000+ claims/day in batch — needs performance and reliability, not just correctness
- Has wanted to add AI-powered coding validation for years but can't justify building an LLM integration with de-identification from scratch
- When he's on vacation, nobody can fix validation bugs — single point of failure

**Goals:**
- Replace his custom validation code with a maintained, tested, community-supported library
- Pluggable payer-specific rules so he can encode his hard-won payer knowledge as structured rule sets instead of spaghetti code
- Batch validation with analytics — "show me top 10 failure reasons across all 200 practices this month"
- Add LLM-powered validation (any provider — he wants to try Ollama locally first, then maybe Claude for production) with PHI safety guaranteed
- CLI tool for quick ad-hoc validation: `claim-validate batch.json --payer=BCBS_FL`

**Success Moment:** Migrates his 12,000 lines of custom code to claim-validator in 2 sprints. Contributes his payer-specific rules back to the community. His team can now maintain the system without him. AI validation catches a pattern of age-inappropriate procedure codes he never would have written a rule for.

**Tech Profile:** Python 3.11+, Django, PostgreSQL, Redis/Celery, comfortable with CLI tools. Evaluates libraries by: validator coverage, extensibility, payer rule support, batch performance, and "can I contribute back without jumping through hoops?"

---

### Secondary Users

#### Persona 3: "David" — CTO / Tech Lead (Decision Maker)

**Role:** Makes the "build vs buy vs adopt OSS" decision. Doesn't use the library directly but evaluates it for:
- **License:** Must be permissive (MIT/Apache 2.0) for commercial use
- **HIPAA compliance:** PHI handling, de-identification guarantees, audit logging
- **Maintenance:** Active community, regular releases, responsive to issues
- **Security:** No PHI leakage to third parties, encryption at rest, vulnerability management
- **Cost:** Free core vs $75K+/year commercial alternative is a compelling business case

**Key Question:** "If we adopt this, will we be explaining to auditors why we're using an open-source library for HIPAA-regulated claim processing? Or will the library make compliance easier?"

#### Persona 4: "Angela" — Medical Billing Specialist (Indirect Beneficiary)

**Role:** Processes claims daily using whatever system her developer team builds. Doesn't interact with the library but directly benefits from:
- Fewer rejected claims to rework (saves hours/week)
- Clear, actionable error messages ("Missing modifier 25 on E/M code 99213 when billed with procedure 20610 for payer UnitedHealthcare" vs cryptic CARC codes)
- AI-flagged clinical issues caught before submission instead of after denial
- Confidence that claims are validated against the latest CMS rules

**Key Quote:** "I don't care what's under the hood — I just need fewer denials and error messages I can actually understand."

---

### User Journey

#### Discovery → Integration → Value (Primary User Path)

**1. Discovery**
- Developer searches PyPI/GitHub for "healthcare claim validation python"
- Finds claim-validator — README shows 3-line quickstart, comprehensive validator list, zero dependencies for rule-based mode
- Compares to alternatives: pyx12 (parsing only), commercial APIs ($$$), building from scratch (months)

**2. Onboarding (5-Minute Path)**
```
pip install claim-validator
```
```python
from claim_validator import validate

result = validate({
    "billing_provider_npi": "1234567893",
    "diagnosis_codes": [{"code": "J06.9"}],
    "lines": [{"procedure_code": "99213", "charge_amount": 150.00}],
    # ... minimal required fields
})

print(result.passed)       # True/False
print(result.findings)     # Structured errors with fix suggestions
```
No database, no API keys, no config files. Works immediately.

**3. Core Usage**
- **Week 1:** Rule-based validation in development/staging
- **Week 2:** Add LLM provider for AI validation: `pip install claim-validator[ai]`, configure `CLAIM_VALIDATOR_LLM_PROVIDER=anthropic`
- **Month 1:** Add payer-specific rules: `pip install claim-validator-rules-unitedhealthcare`
- **Month 2:** Batch validation in production, monitoring denial rate reduction

**4. Aha! Moment**
- First denied claim that would have been caught: "AI validator flagged CPT 59400 (obstetric care) on a male patient — our rule-based checks passed it because the codes were valid formats"
- First batch report: "Top failure: 23% of claims missing modifier 25 on E/M + procedure combinations for BCBS"

**5. Long-Term Adoption**
- Contributes payer rules back to community
- Upgrades to premium tier for hosted API and enterprise support
- Integrates CLI into CI/CD pipeline: claims validated on every PR
- Becomes advocate: talks about it at local Python meetup / PyCon healthcare track

---

## Success Metrics

### User Success Metrics

| Metric | Target (6 mo) | Target (12 mo) | Measurement |
|---|---|---|---|
| **Time to First Validation** | < 5 minutes from `pip install` to first successful `validate()` call | < 3 minutes (improved docs/quickstart) | Tracked via quickstart tutorial completion analytics |
| **Denial Rate Reduction** | Adopters see 40-60% reduction in preventable denials (from ~15% to 6-9% first-submission denial rate) | 60-80% reduction (as payer rules and AI validation mature) | Self-reported by adopters + case studies |
| **Integration Effort** | Rule-based: < 1 day. Full pipeline with AI: < 1 week | Same, with more frameworks supported | GitHub issues tagged "integration-help", time-to-close |
| **Validator Coverage** | 8 rule-based + 3 AI validators covering top 6 denial reasons (missing info, eligibility, coding, duplicates, timely filing, NPI) | 15+ validators covering top 10 denial reasons + NCCI edits + MUE limits | Validator count, mapped against MGMA top denial categories |
| **Payer Rule Availability** | CMS/Medicare rules built-in + 5 major commercial payers (UHC, Aetna, Cigna, BCBS, Humana) | 20+ payer rule sets (community + maintained) | PyPI package count for `claim-validator-rules-*` |
| **LLM Provider Coverage** | 3 providers working out-of-box (Anthropic, OpenAI, Ollama/OpenAI-compatible) | 5+ providers (add Gemini, AWS Bedrock) + any OpenAI-compatible endpoint | Provider adapter count, integration test pass rate |

### Community & Adoption Metrics

| Metric | Target (3 mo) | Target (6 mo) | Target (12 mo) | Measurement |
|---|---|---|---|---|
| **PyPI Downloads/month** | 500 | 2,000 | 10,000+ | PyPI Stats / pepy.tech |
| **GitHub Stars** | 200 | 500 | 2,000+ | GitHub |
| **Companies in Production** | 5 | 20 | 50+ | Self-reported, GitHub discussions, case studies |
| **Contributors** | 5 (core team) | 15 | 50+ (incl. payer rule contributors) | GitHub contributor count |
| **Community Payer Rules** | 0 (all built-in) | 3 community-contributed rule packages | 10+ community packages | PyPI `claim-validator-rules-*` ecosystem |
| **Documentation Score** | README + quickstart + API reference | Full docs site with healthcare context explanations, migration guides | Comparable to Stripe/Sentry docs quality | User surveys, GitHub issue sentiment |
| **Open Issues Resolution** | < 72hr median response time | < 48hr response, < 1 week resolution | < 24hr response | GitHub issue metrics |

### Business Objectives

#### Revenue Model: Open-Source Core + Premium Tier

**Open-Source Core (Free):**
- All rule-based validators
- All LLM provider integrations (bring your own key)
- HIPAA de-identification
- CLI tool
- Framework integrations (Django, FastAPI, Flask)
- Community payer rule sets

**Premium Tier (Paid):**

| Offering | Pricing Model | Target |
|---|---|---|
| **Hosted Validation API** | Per-claim ($0.05-$0.15/claim for rule-based, $0.25-$0.50 with AI) | Startups that don't want to self-host |
| **Managed AI Validation** | Monthly subscription ($99-$499/mo based on volume) | Companies that want AI validation without managing LLM keys/costs |
| **Enterprise Support** | Annual contract ($5K-$25K/year) | Billing companies + hospital RCM teams needing SLAs, priority fixes, HIPAA BAA |
| **Premium Payer Rule Sets** | Subscription ($49-$199/mo per payer) | Real-time updated, verified payer rules beyond community-maintained sets |
| **Analytics Dashboard** | SaaS ($199-$999/mo) | Batch validation analytics, denial prediction, trend reporting across practices |

### Key Performance Indicators

#### North Star Metric

**Claims Successfully Validated Before Submission** — Total number of claims processed through the library that passed validation and were submitted with reduced denial risk. This single metric captures adoption (someone is using it), value delivery (claims are being validated), and market penetration (volume implies scale).

- **3 months:** 10,000 claims/month validated
- **6 months:** 100,000 claims/month validated
- **12 months:** 1,000,000 claims/month validated

#### Leading Indicators (Predict Future Success)

| KPI | What It Predicts | Target (6 mo) |
|---|---|---|
| **Weekly Active Integrations** | Sustained adoption (not just one-time install) | 100+ unique projects calling `validate()` weekly |
| **Validator Extension Rate** | Community health — are people building on the platform? | 10+ custom validators shared publicly |
| **Issue-to-PR Conversion** | Community engagement depth | 20% of filed issues result in community PRs |
| **Quickstart Completion Rate** | Onboarding quality | 80% of developers who start quickstart complete it |
| **Return Usage (Week 2)** | Retention / real value delivery | 60% of first-week users still active in week 2 |

#### Lagging Indicators (Confirm Success)

| KPI | What It Confirms | Target (12 mo) |
|---|---|---|
| **Denial Rate Delta** | Product actually works — adopters see fewer denials | Avg 50% reduction reported by tracked adopters |
| **Premium Conversion Rate** | Business viability — free users become paying customers | 3-5% of active users convert to any paid tier |
| **Annual Recurring Revenue (ARR)** | Business sustainability | $100K ARR from premium tier by month 12 |
| **Enterprise Contracts** | Market credibility — serious organizations trust this | 5+ enterprise contracts ($5K+ each) |
| **Conference Mentions / Blog Posts** | Market awareness — becoming the standard | 10+ external blog posts, 2+ conference talks mentioning the library |

#### Strategic Milestones

| Milestone | Timeframe | Significance |
|---|---|---|
| **First PyPI release with passing CI** | Month 1 | Product exists and is installable |
| **First external company in production** | Month 2-3 | Real-world validation |
| **First community-contributed payer rule set** | Month 4-6 | Ecosystem is emerging |
| **First premium tier customer** | Month 3-6 | Business model validated |
| **Featured in a "best healthcare Python tools" list** | Month 6-9 | Market recognition |
| **1,000 GitHub stars** | Month 6-12 | Developer community traction |
| **First enterprise contract** | Month 6-12 | Enterprise credibility |
| **Recognized as default recommendation in r/healthIT** | Month 9-12 | Category ownership |

---

## MVP Scope

### Core Features (MVP — Option B: Rule-Based + LLM-Agnostic AI)

**The MVP Principle:** A developer can `pip install claim-validator`, validate a claim using a Python dict, optionally plug in any LLM for AI validation, and get structured, actionable findings — with zero Django, zero database, zero mandatory API keys.

#### F1: Framework-Agnostic Core Library

| Component | What Ships | Extracted From |
|---|---|---|
| **Pydantic Claim Models** | `ClaimData`, `ClaimLineData`, `DiagnosisCode` — pure Pydantic models replacing Django ORM dependency | `claim_analyzer/models/claim.py` fields mapped to Pydantic |
| **Constants & Enums** | `ClaimStatus`, `ValidationSeverity`, `ValidatorType`, `ClaimType` — standard Python enums (not Django TextChoices) | `claim_analyzer/constants.py` |
| **Exception Hierarchy** | `ClaimValidatorError`, `ValidationError`, `ConfigurationError` | `claim_analyzer/exceptions.py` |
| **Configuration** | `ClaimValidatorSettings` — Pydantic-based config with env var support, no Django dependency | `claim_analyzer/conf.py` refactored |

**Entry Point:**
```python
from claim_validator import validate

result = validate({
    "billing_provider_npi": "1234567893",
    "payer_id": "BCBS_FL",
    "diagnosis_codes": [{"code": "J06.9"}],
    "lines": [{"procedure_code": "99213", "charge_amount": 150.00}],
})

result.passed          # bool
result.findings        # List[Finding]
result.findings[0].code       # "INVALID_NPI"
result.findings[0].message    # "NPI fails Luhn check digit validation"
result.findings[0].severity   # Severity.ERROR
result.findings[0].field_name # "billing_provider_npi"
result.findings[0].suggestion # "Verify NPI at https://npiregistry.cms.hhs.gov"
```

#### F2: Rule-Based Validators (8 Validators)

All extracted from `claim_analyzer/validators/rule_based/`, refactored to accept Pydantic models or raw dicts instead of Django model instances.

| Validator | What It Checks | Top Denial Reason Addressed |
|---|---|---|
| **CompletenessValidator** | All required CMS-1500 fields present and non-empty | #1: Missing/invalid patient information (25-30% of denials) |
| **NPIValidator** | Luhn check-digit validation for billing/rendering provider NPI | #9: Invalid NPI (3-5% of denials) |
| **SubscriberIDValidator** | Insurance subscriber ID format and presence | #1: Missing/invalid patient information |
| **DemographicsValidator** | Patient demographics consistency (DOB, gender, relationship) | #1: Missing/invalid patient information |
| **CodingValidator** | ICD-10-CM format, CPT/HCPCS format, modifier validity, diagnosis pointer consistency | #4: Coding errors (10-15% of denials) |
| **MonetaryValidator** | Charge amounts > 0, date consistency, line totals match claim total | #10: Charge/coding inconsistencies (3-5% of denials) |
| **DuplicateValidator** | Duplicate line detection within a single claim | #5: Duplicate claim (5-10% of denials) |
| **TimelyFilingValidator** | Service date within payer-specific filing deadline | #6: Timely filing exceeded (5-8% of denials) |

**Combined coverage:** Addresses 60-75% of all preventable denial reasons.

#### F3: Validation Pipeline & Registry

| Component | What Ships | Source |
|---|---|---|
| **BaseValidator** | Abstract base class — `validate(claim) -> ValidatorOutput`, stateless contract | `claim_analyzer/validators/base.py` |
| **Finding** | Dataclass: `code`, `message`, `severity`, `field_name`, `line_number`, `suggestion`, `context` | `claim_analyzer/validators/base.py` |
| **ValidatorOutput** | Dataclass: `validator_name`, `passed`, `findings`, `execution_time` | `claim_analyzer/validators/base.py` |
| **PipelineResult** | Aggregated results from all validators | `claim_analyzer/validators/pipeline.py` |
| **ValidationPipeline** | Two-phase orchestrator: rule-based first, AI second (skip AI on rule failure configurable) | `claim_analyzer/validators/pipeline.py` |
| **ValidatorRegistry** | Lazy loading by dotted path, runtime pipeline construction | `claim_analyzer/validators/registry.py` |

**Custom Validator API:**
```python
from claim_validator import BaseValidator, Finding, Severity

class MyCustomValidator(BaseValidator):
    name = "MyCustomValidator"

    def validate(self, claim) -> ValidatorOutput:
        findings = []
        if some_custom_check(claim):
            findings.append(Finding(
                code="CUSTOM_001",
                message="Custom validation failed",
                severity=Severity.WARNING,
                suggestion="How to fix this"
            ))
        return self._make_output(findings)
```

#### F4: LLM-Agnostic AI Validation (3 AI Validators)

| Component | What Ships | Source |
|---|---|---|
| **BaseLLMClient** | Abstract interface for any LLM provider | `claim_analyzer/integrations/llm/base.py` |
| **AnthropicClient** | Claude integration (tool-use pattern) | `claim_analyzer/integrations/llm/providers/anthropic.py` |
| **OpenAIClient** | GPT-4/GPT-4o integration | `claim_analyzer/integrations/llm/providers/openai.py` |
| **OpenAICompatibleClient** | Ollama, vLLM, any OpenAI-compatible endpoint | `claim_analyzer/integrations/llm/providers/openai_compatible.py` |
| **LLMFactory** | `get_llm_client(provider="anthropic")` factory | `claim_analyzer/integrations/llm/factory.py` |
| **HealthcareLLMClient** | Provider-agnostic healthcare methods: `validate_coding()`, `check_coverage()`, `assess_prior_auth()` | `claim_analyzer/integrations/llm/healthcare_client.py` |

**AI Validators:**

| Validator | What It Catches | Why Rules Can't |
|---|---|---|
| **CodeValidationAI** | Clinical implausibility — wrong gender/age for codes, illogical diagnosis-procedure combinations | Rules validate format; AI validates clinical meaning |
| **CoverageCheckAI** | Likely non-covered services, medical necessity concerns | Requires payer policy knowledge beyond static rules |
| **PriorAuthAI** | Services likely requiring prior authorization | Prior auth requirements vary by payer and change frequently |

**LLM Configuration:**
```python
from claim_validator import validate

# Rule-based only (no API key needed)
result = validate(claim_data)

# With AI validation — bring your own LLM
result = validate(claim_data, ai_config={
    "provider": "anthropic",
    "api_key": "sk-...",
    "model": "claude-sonnet-4-5-20241022",
})

# Self-hosted Ollama (zero API cost, full privacy)
result = validate(claim_data, ai_config={
    "provider": "openai_compatible",
    "base_url": "http://localhost:11434/v1",
    "model": "llama3:8b",
})
```

#### F5: HIPAA-Compliant De-identification

| Component | What Ships | Source |
|---|---|---|
| **ClaimDeidentifier** | Strips all 18 HIPAA identifiers before any LLM call | `claim_analyzer/integrations/claude/deidentifier.py` |

**What gets sent to LLM (safe):** diagnosis codes, procedure codes, modifiers, charges, payer ID, provider NPI, taxonomy, facility code, patient age (computed from DOB), gender, state, service year only.

**What NEVER leaves the library (PHI):** patient name, SSN, member ID, DOB, address, phone, email, account numbers, and all other HIPAA identifiers.

This is the key differentiator — developers don't need to build their own de-identification. It's built into the library pipeline, runs automatically before any AI validator, and works identically regardless of which LLM provider is configured.

#### F6: Bundled Code Tables (Offline-First)

| Data Set | Source | Update Frequency |
|---|---|---|
| **ICD-10-CM codes** | CMS annual release | Annual (October 1) |
| **HCPCS Level II codes** | CMS quarterly release | Quarterly |
| **NPI Luhn validation** | Algorithm (no data needed) | N/A |
| **Place of Service codes** | CMS reference table | As published |
| **Taxonomy codes** | NUCC taxonomy | Annual |
| **Timely filing limits** | Major payer defaults | Configurable per-payer |

Bundled as package data — works offline, no API calls for code validation. Future: `claim-validator update-codes` CLI command for updates.

---

### Out of Scope for MVP

| Feature | Why Deferred | Target Release |
|---|---|---|
| **Django integration** (`claim-validator[django]`) | Core must prove value framework-agnostic first | v1.1 |
| **FastAPI / Flask integrations** | Same — framework adapters follow core stability | v1.1 |
| **CLI tool** (`claim-validate file.json`) | Important for DX but not critical for library adoption | v1.1 |
| **Payer-specific rule plugins** (`claim-validator-rules-bcbs`) | Need community infrastructure first (plugin spec, testing, contribution guide) | v1.2 |
| **NCCI edit checking** (600K+ code-pair edits) | Large data set, complex quarterly updates — requires dedicated data pipeline | v1.2 |
| **MUE limit checking** (medically unlikely edits) | Same as NCCI — requires CMS data ingestion pipeline | v1.2 |
| **Batch validation with analytics** | Needs persistence layer design; MVP is single-claim focused | v1.3 |
| **ClaimMD clearinghouse integration** | Submission is separate concern from validation; keep library focused | v2.0 |
| **Eligibility checking (270/271)** | Requires external API calls, separate from claim validation | v2.0 |
| **Hosted Validation API** (premium) | Requires infrastructure; validate library adoption first | v2.0 |
| **Analytics Dashboard** (premium) | Requires frontend + persistence; post-adoption feature | v2.0+ |
| **FHIR resource input support** | FHIR claim resources as input format — future interoperability | v2.0+ |
| **Celery task definitions** | Framework-specific async — part of integration packages | v1.1 |
| **MCP server** | Separate package, not core library functionality | Separate repo |
| **Denial prediction ML model** | Requires training data; research phase | v3.0 |
| **ICD-11 support** | CMS hasn't set US adoption date (est. 2027-2030) | When CMS mandates |
| **Gemini / AWS Bedrock providers** | Add provider adapters as demand emerges | v1.1-1.2 |

---

### MVP Success Criteria

**Go/No-Go Gates for Post-MVP Investment:**

| Gate | Metric | Threshold | Decision |
|---|---|---|---|
| **G1: It Works** | First 10 external developers successfully validate claims | 10 successful integrations with < 1hr support per developer | Proceed to v1.1 |
| **G2: It's Valued** | PyPI downloads sustained over 4 weeks | 200+ downloads/month with week-over-week growth | Invest in framework integrations |
| **G3: It's Correct** | Rule-based validators catch known denial patterns in test suite | 95%+ accuracy against curated test claims with known outcomes | Expand validator coverage |
| **G4: AI Adds Value** | AI validators catch issues rule-based validators miss | At least 5 documented cases where AI caught clinical edge cases | Double down on AI pipeline |
| **G5: Community Interest** | GitHub engagement beyond stars | 10+ issues filed, 3+ external PRs, 2+ custom validators shared | Invest in plugin architecture |

**MVP Timeline Target:** 6-8 weeks from start of extraction work.

---

### Future Vision

#### Phase 1: Foundation (MVP — Months 1-2)
- Pure Python library on PyPI
- 8 rule-based + 3 AI validators
- 3 LLM providers (Anthropic, OpenAI, OpenAI-compatible)
- HIPAA de-identification built-in
- Bundled code tables (ICD-10, HCPCS, taxonomy)
- Zero dependencies beyond Pydantic + httpx

#### Phase 2: Ecosystem (Months 3-6)
- Django, FastAPI, Flask integrations as optional extras
- CLI tool for CI/CD and ad-hoc validation
- Payer-specific rule plugin architecture + first 5 payer packages
- NCCI edit checking + MUE limit checking
- Gemini + AWS Bedrock LLM providers
- `claim-validator update-codes` for annual code set updates
- Celery task definitions for async validation
- Comprehensive docs site with healthcare context explanations

#### Phase 3: Platform (Months 6-12)
- Hosted Validation API (premium tier launch)
- ClaimMD + other clearinghouse integrations (submission, not just validation)
- Eligibility checking (270/271) integration
- Batch validation with analytics and reporting
- Enterprise support tier with SLAs and HIPAA BAA
- FHIR resource input support (CMS interoperability alignment)
- Community payer rule marketplace
- Rejection pattern analysis and learning

#### Phase 4: Intelligence (Months 12-24)
- Denial prediction ML model trained on anonymized community data
- Prior authorization automation via FHIR Da Vinci PAS
- Real-time payer rule updates from companion guide parsing
- Multi-language SDK generation (TypeScript, Go, Java) from core Python
- Price transparency integration (flag charges above market rate)
- ICD-11 readiness (when CMS sets adoption timeline)
- TEFCA integration for real-time patient data enrichment

#### The 3-Year Vision

"The Stripe of healthcare claim validation" — an open-source foundation that becomes the default infrastructure layer for any application that touches healthcare claims in the US. Every telehealth app, every billing system, every EHR integration uses claim-validator the way every web app uses Stripe for payments: because building it yourself would be insane.

- Open-source core remains free forever — community-maintained, battle-tested
- Premium tier generates $1M+ ARR from hosted API, enterprise support, and managed AI
- Ecosystem of 50+ community-contributed payer rule packages
- Standard recognized in healthcare IT conferences, recommended by CMS/ONC as reference implementation
