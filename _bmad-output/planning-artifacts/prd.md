---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
completedAt: '2026-02-18'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-18.md'
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-17.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-17.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-02-18.md'
  - '_bmad-output/project-context.md'
workflowType: 'prd'
documentCounts:
  briefs: 2
  research: 0
  brainstorming: 2
  projectDocs: 1
classification:
  projectType: 'developer_tool'
  domain: 'healthcare'
  complexity: 'high'
  projectContext: 'brownfield'
---

# Product Requirements Document - claim-validator

**Author:** aniket
**Date:** 2026-02-18

## Executive Summary

`claim-validator` is an open-source, pip-installable Python library for US healthcare claim validation (CMS-1500 / 837P). It provides a two-phase validation pipeline: deterministic rule-based checks that work fully offline with zero configuration, and AI-powered clinical validation that supports any LLM provider (Claude, GPT, Gemini, Llama, Ollama, or any OpenAI-compatible endpoint).

**The Problem:** The US healthcare system wastes $19.7 billion/year on claim denial rework. 60-80% of denials are preventable with pre-submission validation. Yet zero open-source Python libraries exist for claim validation — developers either pay $50K-$500K/year for commercial engines or build fragile custom solutions.

**The Solution:** A framework-agnostic Python library — `pip install claim-validator` → `from claim_validator import validate` → `result = validate(claim_dict)`. Rule-based validation works offline with bundled code tables. AI validation is opt-in with built-in HIPAA de-identification that strips all 18 identifiers before any LLM call.

**Key Differentiators:**
1. **Only open-source option** — zero competition on PyPI
2. **Bring Your Own LLM** — no vendor lock-in on AI provider
3. **Offline-first** — rule-based validation with zero network calls
4. **5-minute integration** — pip install and call `validate()`
5. **Two-phase pipeline** — deterministic rules catch 60-75%; AI catches clinical edge cases
6. **Community-driven payer rules** — collective intelligence for payer-specific quirks

**Business Model:** Open-source core (free forever) + paid premium tier (hosted API, enterprise support, managed AI, premium payer rules).

**Target Users:** Python developers building healthcare billing systems (primary), billing company tech leads (primary), CTOs evaluating build-vs-buy (secondary), medical billing specialists (indirect beneficiary).

**Project Context:** Brownfield — extracting from an existing Django-based healthcare claim analyzer into a standalone library. Python 3.11+, Pydantic 2.x core.

## Success Criteria

### User Success

| Criteria | Metric | Target |
|---|---|---|
| **5-Minute Onboarding** | Time from `pip install` to first successful `validate()` call | < 5 min (Month 1), < 3 min (Month 6) |
| **Denial Rate Reduction** | First-submission denial rate delta for adopters | 40-60% reduction (6 mo), 60-80% (12 mo) |
| **Integration Effort** | Developer-hours to production integration | Rule-based: < 1 day. Full pipeline with AI: < 1 week |
| **Aha! Moment** | AI catches a clinically implausible claim that rule-based passed | Within first 100 claims validated with AI enabled |
| **Actionable Output** | Every finding includes field, severity, message, fix suggestion | 100% of findings — zero cryptic error codes |
| **Week-2 Retention** | Developers still calling `validate()` in week 2 | 60%+ of first-week users |

### Business Success

| Criteria | Metric | Target (12 mo) |
|---|---|---|
| **North Star** | Claims validated/month through the library | 10K (3 mo) → 100K (6 mo) → 1M (12 mo) |
| **Adoption** | PyPI downloads/month | 500 (3 mo) → 2K (6 mo) → 10K (12 mo) |
| **Community** | GitHub stars / contributors | 2K+ stars, 50+ contributors |
| **Revenue** | ARR from premium tier | $100K ARR |
| **Enterprise** | Enterprise contracts ($5K+/year) | 5+ contracts |
| **Premium Conversion** | Free → paid conversion rate | 3-5% of active users |
| **Category Ownership** | Default recommendation in r/healthIT, healthcare Python lists | Recognized as the standard by month 9-12 |

### Technical Success

| Criteria | Metric | Target |
|---|---|---|
| **Validator Accuracy** | Rule-based validators against curated test claims with known outcomes | 95%+ accuracy |
| **Zero PHI Leakage** | No PHI ever sent to any LLM provider | 100% — de-identification automatic, verified by test suite |
| **LLM Provider Coverage** | Working out-of-box providers | 3 at MVP (Anthropic, OpenAI, OpenAI-compatible), 5+ by month 12 |
| **Offline-First** | Rule-based validation with zero network calls | 100% offline — bundled code tables, no API keys required |
| **Framework Independence** | Core library has zero Django/Flask/FastAPI dependency | Core depends only on Pydantic + httpx |
| **HIPAA Compliance** | De-identification strips all 18 HIPAA identifiers | 100% — verified by compliance test suite |
| **Test Coverage** | Unit + integration test coverage on validators | 90%+ line coverage |

### Measurable Outcomes (Go/No-Go Gates)

| Milestone | Timeframe | Go/No-Go Decision |
|---|---|---|
| **G1: It Works** | Month 1 | 10 external developers successfully validate claims with < 1hr support each |
| **G2: It's Valued** | Month 2 | 200+ PyPI downloads/month with week-over-week growth |
| **G3: It's Correct** | Month 2 | 95%+ accuracy against curated denial test suite |
| **G4: AI Adds Value** | Month 3 | 5+ documented cases where AI caught clinical edge cases rules missed |
| **G5: Community Interest** | Month 3-4 | 10+ issues filed, 3+ external PRs, 2+ custom validators shared |

## Product Scope

### MVP Strategy

**MVP Approach:** Problem-Solving MVP — deliver the minimum that makes a developer say "this replaced my custom validation code."

**Rationale:** The market has zero alternatives. We need to prove the concept works, not out-feature competitors.

**Resource Requirements:** 1 senior Python developer with healthcare domain knowledge. Existing Django codebase provides extraction source for ~70% of validator logic. Estimated 6-8 weeks.

**Core User Journeys Supported:** J1 (Priya — first validation), J2 (Marcus — custom validators), J3 (David — compliance evaluation).

### MVP Feature Set (Phase 1: Months 1-2)

| # | Capability | Justification |
|---|---|---|
| M1 | `validate(claim_dict) -> PipelineResult` | Without this, the product doesn't exist |
| M2 | 8 rule-based validators (Completeness, NPI, SubscriberID, Demographics, Coding, Monetary, Duplicate, TimelyFiling) | Catch 60-75% of preventable denials offline |
| M3 | `BaseValidator` ABC + custom validator API | Power users need extensibility from day 1 |
| M4 | `ValidationPipeline` + `ValidatorRegistry` | Configurable pipeline is the architecture |
| M5 | Pydantic `ClaimData` / `ClaimLineData` models | Framework-agnostic data layer |
| M6 | `Finding` with code, message, severity, field, suggestion | Actionable output is the core value proposition |
| M7 | LLM-agnostic AI validation — 3 AI validators (CodeValidation, CoverageCheck, PriorAuth), 3 providers (Anthropic, OpenAI, OpenAI-compatible) | Key differentiator; de-risks vendor lock-in |
| M8 | `ClaimDeidentifier` stripping all 18 HIPAA identifiers | Without this, AI validation is a HIPAA violation |
| M9 | Bundled ICD-10-CM, HCPCS, taxonomy, POS code tables | Offline-first is a core differentiator |
| M10 | `pyproject.toml` + PyPI distribution | Must be pip-installable |
| M11 | `py.typed` + full type annotations | Developer tool without types won't be taken seriously |
| M12 | README + quickstart + API reference | Developers evaluate libraries by docs quality first |

**Dependencies:** Pydantic only (core). httpx + provider SDKs (AI extras).

### Explicitly NOT in MVP

| Feature | Why Deferred | Earliest Phase |
|---|---|---|
| Django/FastAPI/Flask integrations | Core must prove value framework-agnostic first | Phase 2 |
| CLI tool | Nice-to-have DX, not required for library adoption | Phase 2 |
| Payer plugin architecture | Need community first; custom validators cover the use case | Phase 2 |
| NCCI edits / MUE limits | Large data sets, complex quarterly updates | Phase 2 |
| Batch validation + analytics | Requires persistence layer design | Phase 2 |
| Hosted API / premium tier | Validate library adoption before infrastructure | Phase 3 |
| Clearinghouse submission | Separate concern from validation | Phase 3 |
| FHIR support | Future interoperability, not immediate need | Phase 3 |

### Phase 2: Ecosystem (Months 3-6)

| Feature | Dependency | User Journey |
|---|---|---|
| Django integration (`[django]`) | Stable core API | J1, J4 |
| FastAPI / Flask integrations | Stable core API | J4 |
| CLI tool | Core validation working | J2 |
| Payer rule plugin spec + 5 payer packages | Custom validator API proven | J2, J5 |
| NCCI edit checking | CMS data ingestion pipeline | J2 |
| MUE limit checking | CMS data ingestion pipeline | J2 |
| Gemini + AWS Bedrock providers | BaseLLMClient stable | All AI users |
| `claim-validator update-codes` CLI | Bundled tables infrastructure | All users |
| Celery async task definitions | Framework integration layer | J4 |
| Documentation site (mkdocs) | API reference stable | All users |

### Phase 3: Platform (Months 6-12)

| Feature | Dependency | Business Impact |
|---|---|---|
| Hosted Validation API | Proven library adoption | Premium revenue stream |
| Clearinghouse integrations | Validation pipeline mature | Full submit workflow |
| Eligibility checking (270/271) | External API framework | Expand beyond validation |
| Batch validation + analytics | Persistence layer design | Enterprise use case |
| Enterprise support tier | Community + adoption | $5K-$25K/year contracts |
| FHIR R4 input support | CMS interoperability push | Future-proofing |
| Community payer rule marketplace | Plugin ecosystem mature | Network effects |

### Phase 4: Intelligence (Months 12-24)

- Denial prediction ML model (requires training data from community)
- Prior auth automation via FHIR Da Vinci PAS
- Real-time payer rule updates from companion guide parsing
- Multi-language SDK generation (TypeScript, Go, Java)
- ICD-11 readiness (when CMS mandates)

## User Journeys

### Journey 1: Priya's First Validation — "From Googling to Green" (Primary User, Success Path)

*Opening Scene:* It's 11pm on a Tuesday. Priya has been debugging a claims rejection from ClaimMD for the third time this week. The CARC code says "N362" — she Googles it, gets a CMS PDF from 2019, and still doesn't understand why the claim was rejected. Her startup's denial rate is 18% and the CTO told her today: "We can't afford the $75K Change Healthcare contract. Find something open-source."

*Rising Action:* Priya searches PyPI for "healthcare claim validation" and finds `claim-validator`. The README shows a 3-line quickstart. She runs `pip install claim-validator` in her Django project's virtualenv. In under 5 minutes, she writes:

```python
from claim_validator import validate

result = validate({
    "billing_provider_npi": "1234567890",
    "diagnosis_codes": [{"code": "J06.9"}],
    "lines": [{"procedure_code": "99213", "charge_amount": 150.00}],
})
```

The result comes back immediately: `result.passed = False`. One finding: `INVALID_NPI — NPI fails Luhn check digit validation. Verify NPI at https://npiregistry.cms.hhs.gov`. She fixes the NPI to the correct one. Runs again — passes. She starts feeding in real claims from their staging database.

*Climax:* She adds AI validation with their existing Anthropic key. The AI validator flags: "CPT 59400 (obstetric care package) billed for a male patient — likely coding error." Their rule-based checks had passed it because the codes were valid formats. This exact claim type was responsible for 6 denials last month.

*Resolution:* Two weeks later, their denial rate drops from 18% to 6%. The CTO asks "what changed?" Priya shows `pip install claim-validator` and 15 lines of integration code. The CTO approves purchasing the premium tier for managed AI validation.

**Requirements revealed:** PyPI installation, zero-config rule-based validation, dict-based input, AI config injection, structured findings with human-readable suggestions, Anthropic provider support.

---

### Journey 2: Marcus Migrates 12,000 Lines — "From Spaghetti to Structured" (Primary User, Power User)

*Opening Scene:* Marcus stares at `validators/custom_rules.py` — 12,000 lines of if/else spaghetti he wrote over 4 years. Every payer quirk is hardcoded. He's the only person who knows where anything is. His vacation request was denied because "nobody else can fix validation bugs."

*Rising Action:* Marcus discovers claim-validator and tests it against his curated set of 500 "known outcome" claims. The 8 built-in validators catch 73% of the same issues his custom code catches. He starts migrating — encoding each payer rule as a structured `BaseValidator` subclass: testable, documented, version-controlled.

*Climax:* Marcus runs the AI validator on a batch of 3,000 claims queued for submission. It flags 47 claims with age-inappropriate procedure codes — pediatric vaccines billed for patients over 18, a pattern he never wrote a rule for. Estimated savings: $11,000 in avoided denials for that single batch.

*Resolution:* Over 2 sprints, Marcus replaces his 12,000-line file with 23 structured validator classes. He contributes his UHC and BCBS-FL rule sets back to the community. His team can now maintain the validation pipeline without him. He finally takes vacation.

**Requirements revealed:** Custom validator API (BaseValidator subclassing), payer-specific rule encoding, batch validation, CLI for ad-hoc testing, community contribution path, validator testing against known outcomes.

---

### Journey 3: David Evaluates — "The Build vs Buy vs Adopt Decision" (Decision Maker)

*Opening Scene:* David, CTO of a 40-person health-tech company, receives two proposals: adopt claim-validator (free, open-source) vs Change Healthcare ($75K/year, 3-month onboarding). His board wants to know: "Is open-source safe for HIPAA-regulated claim processing?"

*Rising Action:* David reviews claim-validator's documentation — MIT license, PHI never leaves the library, de-identification strips all 18 identifiers before LLM calls, no cloud dependency for rule-based validation. His compliance officer confirms: "The library handles PHI better than most commercial tools — it never transmits PHI at all in rule-based mode."

*Climax:* David runs the numbers: $75K/year vs free core + $10K/year enterprise support. He presents to the board: "We adopt the open-source library, purchase enterprise support for SLA guarantees, and redirect the $65K savings to engineering headcount."

*Resolution:* Board approves. Six months later, claim-validator processes 50,000 claims/month in production. The compliance audit passes without findings on the validation component.

**Requirements revealed:** MIT license, HIPAA compliance documentation, de-identification guarantees, enterprise support tier, no mandatory cloud dependency, offline-capable architecture.

---

### Journey 4: Raj Builds a Custom Pipeline — "Integration at Scale" (API/Integration Developer)

*Opening Scene:* Raj is a senior engineer at a health-tech platform processing claims for 50 small practices using FastAPI + PostgreSQL. His architecture is async workers with a custom claim format from their own database.

*Rising Action:* Raj discovers claim-validator works with plain Python dicts — no framework coupling. He constructs a custom pipeline with selective validators and his own practice-specific validator, maps his database objects to dicts, and feeds them through the pipeline.

*Climax:* The async worker processes 500 claims/minute with the rule-based pipeline. AI validation adds 2-3 seconds per claim but only runs on claims that pass rule-based checks first. His team builds a dashboard showing top denial reasons across all 50 practices.

*Resolution:* Average denial rates across practices drop from 14% to 5%. Three practices upgrade to paid tiers. Raj opens a PR adding a FastAPI middleware example to the docs.

**Requirements revealed:** Dict-based input (no framework coupling), configurable pipeline construction, selective validator loading, settings object API, PipelineResult serialization, async-friendly architecture, performance at scale.

---

### Journey 5: Angela Sees Fewer Denials — "Error Messages I Understand" (End User/Indirect Beneficiary)

*Opening Scene:* Angela has processed medical claims for 15 years. Every morning, she opens a spreadsheet of yesterday's rejected claims and starts the rework cycle: look up the CARC code, figure out what went wrong, call the payer, resubmit. Today she has 23 rejections. It takes her until 2pm.

*Rising Action:* Her company integrates claim-validator into their billing system. Now, before Angela clicks "Submit," the system shows a validation panel with plain-English messages: "Missing modifier 25 on E/M code 99213 when billed with procedure 20610 for payer UnitedHealthcare — Add modifier 25 to the E/M service line."

*Climax:* Angela fixes the modifier, checks prior auth (already approved), and submits. Clean first-submission. She processes all 45 of today's claims by 11am — with zero rejections. For the first time in 15 years, she finishes her queue before lunch.

*Resolution:* Daily rejection rework drops from 23 claims/day to 3. She uses freed-up time for patient follow-ups and collections.

**Requirements revealed:** Human-readable finding messages, payer-specific context in suggestions, severity levels (ERROR vs WARNING), field-level specificity, actionable fix suggestions.

---

### Journey Requirements Summary

| Capability | Revealed By | Priority |
|---|---|---|
| **Zero-config pip install + validate()** | J1 (Priya) | MVP |
| **Structured findings with suggestions** | J1 (Priya), J5 (Angela) | MVP |
| **AI validation with provider config** | J1 (Priya), J2 (Marcus) | MVP |
| **Custom validator API (BaseValidator)** | J2 (Marcus), J4 (Raj) | MVP |
| **Dict-based input (no framework coupling)** | J1 (Priya), J4 (Raj) | MVP |
| **HIPAA de-identification** | J1 (Priya), J3 (David) | MVP |
| **Configurable pipeline construction** | J4 (Raj) | MVP |
| **Payer-specific rule encoding** | J2 (Marcus), J5 (Angela) | Growth |
| **Batch validation** | J2 (Marcus), J4 (Raj) | Growth |
| **CLI tool** | J2 (Marcus) | Growth |
| **Enterprise support tier** | J3 (David) | Growth |
| **Community contribution path** | J2 (Marcus) | Growth |
| **Analytics/reporting** | J4 (Raj) | Vision |

## Domain-Specific Requirements

### Compliance & Regulatory

| Requirement | Specification | Impact on Library |
|---|---|---|
| **HIPAA Privacy Rule** | No PHI transmitted to external services without de-identification | `ClaimDeidentifier` strips all 18 HIPAA identifiers before any LLM call. Rule-based validation never transmits data externally |
| **HIPAA Security Rule** | PHI at rest must be encrypted; access must be auditable | Library never persists PHI — validates in-memory. Persistence is the consumer's responsibility |
| **HIPAA Minimum Necessary** | Only minimum PHI required for purpose | De-identification sends only: codes, charges, payer ID, NPI, taxonomy, facility, patient age, gender, state, service year |
| **CMS-1500 / 837P Standards** | Claims conform to NUCC CMS-1500 field definitions | Pydantic models enforce CMS-1500 structure. Validators check CMS specifications |
| **ICD-10-CM Annual Updates** | Code sets updated October 1 by CMS | Bundled tables with annual update mechanism. Grace period logic for transitions |
| **HCPCS/CPT Updates** | HCPCS quarterly; CPT annually by AMA | Bundled tables. CPT is AMA-copyrighted — library validates format only |
| **State Timely Filing Rules** | Deadlines vary by payer/state (90 days to 1 year) | Configurable per-payer limits with sensible defaults |
| **NPI Validation** | Valid per CMS NPI Final Rule | Luhn check-digit + format validation. NPPES live lookup deferred to Growth |

### Technical Constraints

| Constraint | Rationale | Implementation |
|---|---|---|
| **Zero PHI in logs** | PHI in logs = HIPAA breach | Finding messages reference field names, not values |
| **No mandatory external calls** | Healthcare orgs in restricted networks | Rule-based is 100% offline. AI is opt-in. No telemetry |
| **Deterministic before probabilistic** | Clinical systems need predictable behavior | Two-phase pipeline: rules first, AI second. Configurable via `skip_ai_on_rule_failure` |
| **Stateless validation** | Validators must not modify claim data | `validate(claim) -> ValidatorOutput` is read-only. No side effects |
| **No PHI in error messages** | Exceptions may be logged by consumers | PHI patterns never in exception messages or suggestions |
| **Thread safety** | Billing systems process claims in parallel | Stateless validators. Reusable pipeline instances. No shared mutable state |

### Integration Requirements

| Integration Point | Specification | Phase |
|---|---|---|
| **Python dict input** | Raw dicts with CMS-1500 field mapping | MVP |
| **Pydantic model input** | `ClaimData` instances | MVP |
| **LLM provider abstraction** | `BaseLLMClient` ABC with factory (Anthropic, OpenAI, OpenAI-compatible) | MVP |
| **Custom validator registration** | Dotted path loading via `ValidatorRegistry` | MVP |
| **Framework integrations** | Django, FastAPI, Flask adapters | Growth |
| **Clearinghouse submission** | ClaimMD and other APIs | Vision |
| **FHIR R4 input** | FHIR Claim resources mapped to internal model | Vision |

### Risk Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **PHI leakage through LLM calls** | HIPAA breach, legal liability | De-identification automatic in pipeline. Test suite verifies no PHI in payloads |
| **Stale code tables** | False negatives/positives after CMS updates | Version metadata. CLI update command. Warnings when tables >12 months old |
| **Incorrect validation logic** | Financial harm to users | 95%+ accuracy target. Community-reported errors as high-priority bugs |
| **AI hallucination** | Incorrect clinical advice | AI findings supplementary, never sole basis for rejection. Rules authoritative, AI advisory |
| **CPT copyright** | AMA copyright on descriptions | Format validation only. No bundled descriptions |
| **Liability for missed denials** | User relies on library, claim denied | MIT license + disclaimer. Documentation states no guarantee of acceptance |
| **Breaking CMS rule changes** | Annual invalidation of validator logic | Semantic versioning. Annual review aligned with CMS October 1 updates |

## Innovation & Novel Patterns

### Detected Innovation Areas

| Innovation | What's Novel | Why It Matters |
|---|---|---|
| **First-of-kind on PyPI** | Zero open-source Python claim validation libraries. pyx12/python-hl7 handle EDI parsing only | New category. No competition — only a vacuum to fill |
| **LLM-Agnostic Healthcare AI** | No tool offers pluggable LLM providers with automatic HIPAA de-identification | No vendor lock-in. Claude today, self-hosted Llama tomorrow |
| **Two-Phase Pipeline** | Deterministic rules (60-75%) + AI clinical edge cases | Immediate value with rules-only; AI is force multiplier, not dependency |
| **Offline-First Healthcare Tool** | Zero network calls, zero API keys, zero database for rule-based | Air-gap compliance. Restricted networks can adopt immediately |
| **Community-Driven Payer Rules** | Open-source payer rule repository | "Every payer is a snowflake" → collective intelligence |

### Competitive Landscape

| Competitor | What They Do | Gap |
|---|---|---|
| **Change Healthcare / Optum** | Full RCM platform | Not embeddable, not open-source, UHG conflict-of-interest |
| **Stedi** | EDI format translation | No content validation — doesn't check if claim will pay |
| **Candid Health** | API-first RCM | Full SaaS, not a library |
| **pyx12 / python-hl7** | EDI parsing | Zero business rule validation |
| **claim-validator** | Embeddable rules + AI | **Only open-source, pip-installable, LLM-agnostic, HIPAA-safe option** |

### Innovation Validation

| Aspect | Validation Method | Success Signal |
|---|---|---|
| **Market need** | PyPI downloads, GitHub stars | 500+ downloads/month, 200+ stars |
| **Rules catch denials** | Curated 500+ claim test corpus | 95%+ accuracy |
| **AI adds value** | Rules-only vs rules+AI comparison | 5+ cases where AI caught what rules missed |
| **LLM-agnostic works** | Integration tests across 3+ providers | Same findings regardless of provider |
| **Community contributes** | Track PRs, external packages | 3+ community payer rule sets in 6 months |

## Developer Tool Specific Requirements

### Project-Type Overview

`claim-validator` is a pip-installable Python library targeting Python 3.11+ developers building healthcare billing systems. "Batteries-included, zero-config" philosophy — `pip install` and call `validate()`. Small public API surface with deep customization through validator registry and LLM provider system.

### Language & Platform Matrix

| Dimension | Specification |
|---|---|
| **Primary Language** | Python 3.11+ (modern typing, `|` union syntax, `StrEnum`) |
| **Target Platforms** | Linux, macOS, Windows |
| **Type Annotations** | Full type hints. `py.typed` marker for mypy/pyright |
| **Python Version Policy** | CPython 3.11, 3.12, 3.13. Drop per NEP 29 convention |

### Installation Methods

| Method | Command | What You Get |
|---|---|---|
| **Core** | `pip install claim-validator` | 8 validators, Pydantic models, pipeline, bundled code tables |
| **With AI** | `pip install claim-validator[ai]` | + httpx, Anthropic SDK, OpenAI SDK |
| **Anthropic only** | `pip install claim-validator[anthropic]` | + anthropic SDK |
| **OpenAI only** | `pip install claim-validator[openai]` | + openai SDK |
| **Django** | `pip install claim-validator[django]` | + Django adapter (Growth) |
| **FastAPI** | `pip install claim-validator[fastapi]` | + FastAPI dependency injection (Growth) |
| **All** | `pip install claim-validator[all]` | Everything |
| **Dev** | `pip install claim-validator[dev]` | + pytest, ruff, mypy, factory-boy |

Build system: `pyproject.toml`. Distribution: PyPI.

### Public API Surface

```python
# Core validation
from claim_validator import validate, ValidationPipeline, ValidatorRegistry

# Data models
from claim_validator import ClaimData, ClaimLineData, Finding, ValidatorOutput, PipelineResult

# Extension base classes
from claim_validator import BaseValidator, BaseLLMClient

# Enums
from claim_validator import Severity, ClaimType

# Configuration
from claim_validator import ClaimValidatorSettings

# De-identification
from claim_validator import ClaimDeidentifier

# Exceptions
from claim_validator import ClaimValidatorError, ValidationError, ConfigurationError
```

Design: Small top-level API (most users need only `validate()` + `Finding`). No global state. Explicit configuration. Stateless validators. Thread-safe pipeline instances.

### Code Examples

**Minimal:**
```python
from claim_validator import validate
result = validate({"billing_provider_npi": "1234567893", "diagnosis_codes": [{"code": "J06.9"}], "lines": [{"procedure_code": "99213", "charge_amount": 150.00}]})
print(result.passed, result.findings)
```

**With AI:**
```python
result = validate(claim_data, ai_config={"provider": "anthropic", "api_key": "sk-...", "model": "claude-sonnet-4-5-20241022"})
```

**Custom validator:**
```python
from claim_validator import BaseValidator, Finding, Severity

class MyValidator(BaseValidator):
    name = "MyValidator"
    def validate(self, claim):
        findings = []
        # custom logic
        return self._make_output(findings)
```

**Custom pipeline:**
```python
from claim_validator import ValidationPipeline, ClaimValidatorSettings

settings = ClaimValidatorSettings(
    rule_validators=["claim_validator.validators.NPIValidator", "my_app.validators.CustomValidator"],
    skip_ai_on_rule_failure=True,
)
pipeline = ValidationPipeline.from_settings(settings)
result = pipeline.run(claim_dict)
```

### Migration Guide (Django → Library)

| Current (Django) | New (Library) | Change |
|---|---|---|
| `Claim` model | `ClaimData` Pydantic | ORM → Pydantic or dicts |
| `ClaimStatus` TextChoices | `ClaimStatus` StrEnum | Same values, standard enum |
| `ClaimAnalyzerSettings` | `ClaimValidatorSettings` | Django settings → Pydantic config |
| `ValidationService.validate()` | `validate(claim_dict)` | Service layer → direct function |
| `CLAIM_ANALYZER_VALIDATION_PIPELINE` | `settings.rule_validators` | Same dotted paths, different config |
| `integrations/claude/` | `claim_validator.llm.AnthropicClient` | Provider-agnostic interface |
| `ClaimDeidentifier` | `ClaimDeidentifier` | Same API, accepts dicts |

### Documentation Strategy

| Doc Type | Priority |
|---|---|
| README.md (quickstart, 3-line example) | MVP |
| API Reference (auto-generated) | MVP |
| Quickstart Guide (install → validate → AI → custom) | MVP |
| Healthcare Context Guide (CMS-1500, denial reasons) | Growth |
| Migration Guide (Django, custom code, commercial) | Growth |
| Validator Cookbook (payer-specific recipes) | Growth |
| Contributing Guide (validators, payer packages) | Growth |

### Implementation Considerations

- **Dependency minimalism:** Core = Pydantic only. AI extras add httpx + provider SDKs
- **Backward compatibility:** Semver. Public API stable within major versions. 2 minor versions deprecation warning
- **Error messages:** Designed for copy-paste into search engines. Error codes, field names, fix suggestions
- **Testing contract:** Public test suite consumers can run against their claim data

## Risk Mitigation Strategy

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Django extraction harder than expected | Medium | Delays MVP 2-4 weeks | Start with validators (least coupled). Iterative extraction |
| AI quality varies across LLM providers | Medium | Inconsistent experience | Standardized test suite. Anthropic as reference implementation |
| Bundled code tables bloat package size | Low | Slower pip install | Compress tables. Lazy-load. ICD-10 ≈ 2MB compressed |
| Pydantic v2 breaking changes | Low | Maintenance burden | Pin `pydantic>=2.0,<3.0`. CI tests against latest |

### Market Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Healthcare orgs won't adopt open-source | Medium | Low adoption | Enterprise support with HIPAA BAA. Security audit docs. Case studies |
| Discoverability problem | Medium | Low downloads | SEO README. Blog posts. r/healthIT outreach. PyCon talk |
| Commercial vendors release free tiers | Low | Reduced differentiation | Open-source moat: community, no vendor lock-in, offline capability |

### Resource Risks

| Risk | Mitigation |
|---|---|
| Solo developer (bus factor = 1) | Prioritize docs and tests. Recruit 2-3 core contributors by month 3 |
| Scope creep from community | Strict MVP boundaries. No non-MVP PRs until v1.0 |
| Fewer resources than planned | Minimum: rule-based validators + PyPI (no AI). Still fills market gap |

## Functional Requirements

### Claim Validation

- **FR1:** Developer can validate a healthcare claim by passing a Python dict or Pydantic model and receiving a structured result indicating pass/fail with detailed findings
- **FR2:** Developer can run rule-based validation with zero configuration, zero API keys, and zero network calls
- **FR3:** Developer can run AI-powered validation by providing an LLM provider configuration (provider name, API key, model)
- **FR4:** Developer can configure the validation pipeline to skip AI validation when rule-based validation fails
- **FR5:** Developer can receive findings that include error code, human-readable message, severity level, field name, line number, and actionable fix suggestion for every issue detected
- **FR6:** Developer can distinguish between ERROR severity (claim will be denied) and WARNING severity (claim may be denied or has quality issues)

### Rule-Based Validators

- **FR7:** System can validate all required CMS-1500 fields are present and non-empty
- **FR8:** System can validate NPI numbers using the Luhn check-digit algorithm
- **FR9:** System can validate subscriber/insurance ID presence and format
- **FR10:** System can validate patient demographics consistency (DOB, gender, relationship)
- **FR11:** System can validate ICD-10-CM diagnosis code format and existence against bundled code tables
- **FR12:** System can validate CPT/HCPCS procedure code format and modifier validity
- **FR13:** System can validate diagnosis pointer consistency between lines and diagnosis codes
- **FR14:** System can validate charge amounts are positive and line totals consistent
- **FR15:** System can validate date consistency (service dates, DOB, filing date)
- **FR16:** System can detect duplicate claim lines within a single claim
- **FR17:** System can check service dates against configurable payer-specific timely filing deadlines

### AI Validation

- **FR18:** System can assess clinical plausibility of diagnosis-procedure combinations using an LLM
- **FR19:** System can assess likely coverage and medical necessity concerns using an LLM
- **FR20:** System can identify services likely requiring prior authorization using an LLM
- **FR21:** System can automatically de-identify claims before sending to any LLM, stripping all 18 HIPAA identifiers
- **FR22:** System can send only clinically relevant, non-PHI data to LLMs (codes, charges, payer ID, NPI, age, gender, state, service year)

### LLM Provider Support

- **FR23:** Developer can use Anthropic Claude models for AI validation
- **FR24:** Developer can use OpenAI GPT models for AI validation
- **FR25:** Developer can use any OpenAI-compatible endpoint (Ollama, vLLM, LiteLLM) for AI validation
- **FR26:** Developer can switch LLM providers by changing configuration without modifying code
- **FR27:** Developer can create custom LLM provider adapters by subclassing a base client interface

### Pipeline & Extensibility

- **FR28:** Developer can create custom validators by subclassing a base class and implementing a validate method
- **FR29:** Developer can register custom validators into the pipeline via configuration (dotted path strings)
- **FR30:** Developer can construct custom pipelines with a specific subset of validators
- **FR31:** Developer can configure pipeline behavior via a settings object
- **FR32:** System can execute validators in two phases: rule-based first, AI second
- **FR33:** System can aggregate results from all validators into a single pipeline result

### Data Models & Input

- **FR34:** Developer can provide claim data as a plain Python dictionary
- **FR35:** Developer can provide claim data as a typed Pydantic model with validation
- **FR36:** System can represent claims with multiple lines (procedure codes, modifiers, diagnosis pointers, charges)
- **FR37:** System can represent diagnosis codes with code value, pointer position, and type

### Code Tables & Reference Data

- **FR38:** System can validate ICD-10-CM codes against bundled CMS tables without network calls
- **FR39:** System can validate HCPCS Level II codes against bundled tables without network calls
- **FR40:** System can validate Place of Service codes against bundled reference data
- **FR41:** System can validate provider taxonomy codes against bundled NUCC data
- **FR42:** System can provide timely filing deadline defaults for common payers

### Configuration & Distribution

- **FR43:** Developer can configure the library using a Pydantic settings object with env var support
- **FR44:** Developer can override default validator lists, AI settings, and pipeline behavior via configuration
- **FR45:** Developer can use the library with zero configuration for basic rule-based validation
- **FR46:** Developer can install the core library via `pip install claim-validator` with no optional dependencies
- **FR47:** Developer can install AI support via `pip install claim-validator[ai]`
- **FR48:** Developer can install provider-specific extras (`[anthropic]`, `[openai]`)
- **FR49:** Library exposes type stubs (`py.typed`) for static type checking

## Non-Functional Requirements

### Performance

| NFR | Metric | Target |
|---|---|---|
| **NFR1:** Rule-based latency | `validate()` with all 8 validators, no AI | < 50ms per claim |
| **NFR2:** AI latency | Full pipeline with one LLM round-trip | < 5 seconds per claim |
| **NFR3:** Pipeline startup | First pipeline construction | < 100ms; near-zero subsequent |
| **NFR4:** Code table lookup | Single code validation | < 1ms (in-memory after first load) |
| **NFR5:** Memory footprint | Library with code tables loaded | < 100MB |
| **NFR6:** Batch throughput | Rule-based, single thread | 500+ claims/second |
| **NFR7:** Import time | `import claim_validator` | < 500ms (lazy-load tables) |

### Security

| NFR | Requirement | Verification |
|---|---|---|
| **NFR8:** Zero PHI transmission (rule-based) | No network calls ever | Static analysis + integration test |
| **NFR9:** PHI de-identification (AI) | All 18 HIPAA identifiers stripped before LLM | Unit tests per identifier type |
| **NFR10:** No PHI in outputs | No PHI in logs, exceptions, or findings | Grep-based output scanning test |
| **NFR11:** No telemetry | No phone-home or undisclosed network calls | Code audit + network monitoring |
| **NFR12:** Secrets handling | API keys never in logs or outputs | Unit test on all output paths |
| **NFR13:** Dependency security | No known CVEs at release | `pip-audit` in CI. Dependabot |

### Scalability

| NFR | Requirement | Target |
|---|---|---|
| **NFR14:** Thread safety | Safe concurrent use | Zero shared mutable state. Concurrent test (100 threads) |
| **NFR15:** Stateless validation | No state between calls | Each `validate()` independent |
| **NFR16:** Linear scaling | O(n) with claim lines | No exponential patterns |

### Reliability

| NFR | Requirement | Verification |
|---|---|---|
| **NFR17:** Deterministic results | Identical output per input (rule-based) | 1000 runs, assert identical |
| **NFR18:** Graceful AI failure | Returns rule-based results + warning if LLM down | Test with unreachable endpoint |
| **NFR19:** Invalid input handling | Clear errors, no unhandled exceptions | Fuzz testing |
| **NFR20:** Code table integrity | Match CMS official releases | Checksums + code count verification |

### Compatibility

| NFR | Requirement | Verification |
|---|---|---|
| **NFR21:** Python versions | 3.11, 3.12, 3.13 | CI matrix |
| **NFR22:** OS support | Linux, macOS, Windows | CI matrix |
| **NFR23:** Dependency minimalism | Core = Pydantic only | Clean venv import test |
| **NFR24:** Framework independence | Zero Django/Flask/FastAPI in core | Minimal environment test |
| **NFR25:** Type checker compatibility | `py.typed` for mypy + pyright | CI type checking |

### Code Quality

| NFR | Requirement | Target |
|---|---|---|
| **NFR26:** Test coverage | All public API paths | 90%+ lines, 100% validators + de-identifier |
| **NFR27:** Linting | ruff (E, F, I, N, W, UP) | Zero warnings |
| **NFR28:** Documentation | All public API docstrings | interrogate > 95% |
| **NFR29:** Package size | Published wheel | < 15MB with compressed tables |
