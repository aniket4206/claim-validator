# Prototype Demo Guide — Healthcare Claim Validation & Analytics System

## Quick Start

### Prerequisites
- Python 3.11+
- Redis (for Celery async tasks)
- Git

---

## Demo 1: claim-validator Library (Standalone)

### Setup
```bash
cd claim-validator
pip install -e ".[dev]"
```

### Run End-to-End Demo
```bash
# Rule-based only (no API keys needed)
uv run python demo_e2e.py --no-ai

# With local AI (Ollama)
ollama pull mistral
ollama serve
uv run python demo_e2e.py --model mistral
```

### Demo Scenarios Walkthrough

#### Scenario 1: Clean Claim (PASS)
A valid CMS-1500 claim with correct NPI, valid ICD-10 codes, proper charges, and timely filing.

**Expected Output:**
```
Pipeline Result: PASSED
Phase 1 (rule_based): 0 errors, 0 warnings
Total execution time: ~15ms
```

**What to highlight:**
- All 8 rule-based validators execute in sequence
- Zero findings = clean claim ready for submission
- Sub-20ms execution for instant feedback

#### Scenario 2: Broken Claim (FAIL)
A claim with multiple deliberate errors for demonstration:
- Invalid NPI (fails Luhn check-digit)
- Missing required fields
- Negative charge amounts
- Invalid diagnosis pointers
- Duplicate service lines

**Expected Output:**
```
Pipeline Result: FAILED
Phase 1 (rule_based): 8+ errors, 2+ warnings
Findings include:
  - INVALID_NPI (NPIValidator)
  - MISSING_FIELD (CompletenessValidator)
  - INVALID_CHARGE_AMOUNT (MonetaryValidator)
  - DUPLICATE_LINE (DuplicateValidator) [WARNING]
```

**What to highlight:**
- Each validator independently catches its own category of errors
- Error codes are structured and actionable
- Severity levels (ERROR vs WARNING) distinguish blocking vs advisory issues
- Field names and line numbers pinpoint exact issues

#### Scenario 3: De-identification Demo
Shows the HIPAA Safe Harbor de-identification process.

**Expected Output:**
```
Original Claim:
  Patient: Alice Smith, DOB: 1975-03-10, Subscriber: XYZ987654

De-identified Claim:
  Patient Age: 50 (computed), Gender: F
  Names: REMOVED, DOB: REMOVED, Subscriber ID: REMOVED
  Retained: Diagnosis codes, procedure codes, charges, NPI
```

**What to highlight:**
- All 18 HIPAA identifiers stripped
- Age computed from DOB (capped at 90)
- Medical codes and charges retained for clinical analysis
- This de-identified version is what goes to the LLM

#### Scenario 4: AI Detection (with LLM)
A clinically implausible claim designed for AI to flag:
- Male patient with female-specific diagnosis (vaginitis)
- High-cost MRI (prior authorization candidate)

**Expected Output:**
```
Pipeline Result: PASSED (warnings only)
Phase 1 (rule_based): 0 errors
Phase 2 (ai_powered):
  - AI_CLINICAL_IMPLAUSIBILITY: Male patient with diagnosis N76.0 [WARNING]
  - AI_PRIOR_AUTH_LIKELY: MRI procedure 70553 likely requires prior auth [WARNING]
  - AI_COVERAGE_CONCERN: High-cost imaging may require documentation [WARNING]
```

**What to highlight:**
- Rule-based validators pass (syntax is valid)
- AI validators catch clinical implausibility
- De-identification happens transparently before AI call
- Warnings don't block submission but flag for review

---

## Demo 2: healthcare-claim-analyzer Django API

### Setup
```bash
cd healthcare-claim-analyzer
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys (DJANGO_SECRET_KEY, optional CLAUDE_API_KEY)
python manage.py migrate
python manage.py runserver
```

### API Walkthrough

#### Step 1: Create a Claim
```bash
curl -X POST http://127.0.0.1:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "patient_control_number": "DEMO-001",
    "claim_type": "837P",
    "billing_provider_npi": "1234567893",
    "billing_provider_name": "Demo Medical Group",
    "billing_provider_tax_id": "12-3456789",
    "billing_provider_taxonomy": "207Q00000X",
    "subscriber_id": "XYZ987654321",
    "subscriber_first_name": "John",
    "subscriber_last_name": "Smith",
    "subscriber_dob": "1980-05-15",
    "subscriber_gender": "M",
    "payer_id": "BCBS001",
    "payer_name": "Blue Cross Blue Shield",
    "total_charge": "150.00",
    "service_date_from": "2026-01-15",
    "diagnosis_codes": [
      {"code": "J06.9", "description": "Acute upper respiratory infection"}
    ],
    "lines": [
      {
        "line_number": 1,
        "procedure_code": "99213",
        "charge_amount": "150.00",
        "unit_count": 1,
        "diagnosis_pointers": [1],
        "service_date_from": "2026-01-15",
        "place_of_service": "11"
      }
    ]
  }'
```

**Expected:** 201 Created with claim UUID in response.

#### Step 2: Validate the Claim
```bash
# Synchronous validation (rule-based only)
curl -X POST http://127.0.0.1:8000/api/v1/claims/{claim_id}/validate/ \
  -H "Content-Type: application/json" \
  -d '{"async": false, "include_ai": false}'
```

**Expected:** 200 OK with validation results:
```json
{
  "is_valid": true,
  "total_errors": 0,
  "total_warnings": 0,
  "findings": [],
  "duration_ms": 12
}
```

#### Step 3: View Validation History
```bash
curl http://127.0.0.1:8000/api/v1/claims/{claim_id}/validations/
```

#### Step 4: Submit to ClaimMD (requires CLAIMMD_ACCOUNT_KEY)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/claims/{claim_id}/submit/
```

**Expected:** 202 Accepted with task_id for async tracking.

#### Step 5: Check Analytics
```bash
# Rejection summary
curl http://127.0.0.1:8000/api/v1/analytics/rejection-summary/?days=30

# Rejection trends
curl http://127.0.0.1:8000/api/v1/analytics/rejection-trends/?days=90

# Validator effectiveness
curl http://127.0.0.1:8000/api/v1/analytics/validator-effectiveness/?days=30

# Top rejection codes
curl http://127.0.0.1:8000/api/v1/analytics/top-rejections/?days=30&limit=10
```

---

## Demo 3: MCP Server (Claude Code Integration)

### Setup
```bash
cd healthcare-claim-analyzer
python -m mcp_server
```

### Available Tools
Once the MCP server is running, Claude Code can use these tools:

1. **validate_claim** — Run full validation pipeline on claim JSON
2. **lookup_icd10** — Validate ICD-10 code format
3. **lookup_npi** — Validate NPI with Luhn check-digit
4. **analyze_rejection** — Explain rejection codes with corrective actions
5. **get_rejection_stats** — Get rejection rate statistics
6. **list_validators** — List all configured validators
7. **check_eligibility** — Real-time eligibility verification

### Demo Script
```
You: "Validate this claim: NPI 1234567893, diagnosis J06.9, procedure 99213"
Claude: [Uses validate_claim tool → returns validation results]

You: "Is NPI 1234567890 valid?"
Claude: [Uses lookup_npi tool → reports Luhn check failure]

You: "What does rejection code CO-4 mean?"
Claude: [Uses analyze_rejection tool → explains code with fix suggestions]
```

---

## Demo 4: Running Tests

### claim-validator
```bash
cd claim-validator
pytest                              # All tests
pytest tests/test_validators/       # Validator tests only
pytest tests/test_hipaa/            # HIPAA compliance tests
pytest -v --tb=short                # Verbose with short tracebacks
```

### healthcare-claim-analyzer
```bash
cd healthcare-claim-analyzer
pytest                              # All tests
pytest tests/test_validators/       # Validator tests
pytest tests/test_integrations/     # Integration tests
pytest -x                           # Stop on first failure
```

---

## Key Points to Highlight During Demo

### Technical Excellence
- **Dual-phase pipeline:** Deterministic rules first, then AI for clinical judgment
- **Sub-20ms rule validation:** Fast enough for real-time use
- **Zero PHI to LLM:** HIPAA de-identification is automatic and transparent
- **Multi-LLM support:** Works with Claude, GPT-4, or local Ollama models

### Architecture Quality
- **Clean separation:** Library (claim-validator) vs Service (healthcare-claim-analyzer)
- **Plugin architecture:** Validators registered via dotted paths, fully extensible
- **Service layer pattern:** No business logic in views or models
- **Thread-safe:** Code table loading with double-check locking

### Production Readiness
- **Async processing:** Celery tasks for validation, submission, polling
- **Rate limiting:** ClaimMD API calls throttled (100 req/min)
- **Encryption at rest:** Fernet encryption for all PHI fields
- **Immutable audit trail:** HIPAA-compliant logging that can't be tampered with

### Real-World Value
- **$262B problem:** Claim denials cost the US healthcare system billions
- **30% first-pass denial rate:** This system catches errors before submission
- **Rejection analytics:** Learn from past denials to prevent future ones
- **End-to-end pipeline:** Validate → Submit → Track → Analyze → Learn
