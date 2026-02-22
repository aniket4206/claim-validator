# claim-validator

Open-source healthcare claim validation library for Python 3.11+. Validates CMS-1500 / 837P professional healthcare claims through a dual-phase pipeline: deterministic rule-based checks followed by AI-powered clinical analysis, all with HIPAA-compliant de-identification.

Healthcare claim denials cost the US healthcare system an estimated $262 billion annually, with approximately 30% of claims denied on first submission. The majority of these denials are preventable. `claim-validator` catches coding errors, missing fields, eligibility mismatches, and authorization gaps **before** submission.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Tool](#cli-tool)
- [REST API Server (Any Language)](#rest-api-server-any-language)
- [Publishing to PyPI](#publishing-to-pypi)
- [Configuration](#configuration)
- [Validation Pipeline](#validation-pipeline)
  - [Phase 1: Rule-Based Validators](#phase-1-rule-based-validators)
  - [Phase 2: AI-Powered Validators](#phase-2-ai-powered-validators)
- [Data Models](#data-models)
- [LLM Provider Abstraction](#llm-provider-abstraction)
- [Code Tables](#code-tables)
- [HIPAA De-identification](#hipaa-de-identification)
- [Extending with Custom Validators](#extending-with-custom-validators)
- [Library Reference](#library-reference)
  - [Core Dependencies](#core-dependencies)
  - [Optional Dependencies](#optional-dependencies)
  - [Development Dependencies](#development-dependencies)
  - [Build & Tooling](#build--tooling)
- [Running the Demo](#running-the-demo)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Exception Hierarchy](#exception-hierarchy)
- [License](#license)

---

## Features

- **11 validators** — 8 deterministic rule-based + 3 AI-powered
- **Zero-config defaults** — all 8 rule-based validators work out of the box with no API keys or external services
- **CLI tool** — `claim-validator validate claim.json` for shell/CI usage
- **REST API server** — `claim-validator serve` exposes HTTP endpoints callable from **any language** (Node.js, Go, Java, Ruby, etc.)
- **HIPAA Safe Harbor** — strips all 18 identifiers before any LLM interaction
- **Multi-provider LLM support** — Anthropic Claude, OpenAI GPT, Ollama, vLLM, LocalAI
- **Compressed code tables** — ICD-10-CM, HCPCS/CPT, Provider Taxonomy, Place of Service, Timely Filing rules (gzip JSON, lazy-loaded, thread-safe)
- **Immutable data models** — all Pydantic models are frozen for data integrity
- **Plugin architecture** — add custom validators via dotted import paths
- **Typed** — full mypy strict mode compliance

---

## Architecture

```
ClaimData (dict or Pydantic model)
        |
        v
+-------------------------------+
|  PHASE 1: RULE-BASED         |
|  (Deterministic, Offline)     |
|-------------------------------|
|  1. CompletenessValidator     |
|  2. NPIValidator              |
|  3. SubscriberIDValidator     |
|  4. DemographicsValidator     |
|  5. CodingValidator           |
|  6. MonetaryValidator         |
|  7. DuplicateValidator        |
|  8. TimelyFilingValidator     |
+---------------+---------------+
                |
          Has errors?
          /          \
        YES           NO
         |             |
    Skip AI?     +-----------------------+
    (config)     |  DE-IDENTIFICATION    |
         |       |  (HIPAA Safe Harbor)  |
         |       |  Strips 18 IDs       |
         |       +----------+------------+
         |                  |
         |                  v
         |       +-------------------------------+
         |       |  PHASE 2: AI-POWERED          |
         |       |  (LLM Analysis)               |
         |       |-------------------------------|
         |       |  1. CodeValidationAI          |
         |       |  2. CoverageCheckAI           |
         |       |  3. PriorAuthAI               |
         |       +----------+--------------------+
         |                  |
         v                  v
    +-----------------------------+
    |       PipelineResult        |
    |  .passed   (bool)           |
    |  .findings (list[Finding])  |
    |  .errors   (list[Finding])  |
    |  .warnings (list[Finding])  |
    |  .execution_time (float)    |
    +-----------------------------+
```

---

## Installation

**Rule-based only (zero external dependencies beyond Pydantic):**

```bash
pip install claim-validator
```

**With REST API server (for cross-language use):**

```bash
pip install "claim-validator[server]"
```

**With AI support (all LLM providers):**

```bash
pip install "claim-validator[ai]"
```

**With a specific LLM provider:**

```bash
pip install "claim-validator[anthropic]"   # Anthropic Claude only
pip install "claim-validator[openai]"      # OpenAI GPT only
```

**With framework integrations:**

```bash
pip install "claim-validator[django]"      # Django integration
pip install "claim-validator[fastapi]"     # FastAPI integration
```

**Everything:**

```bash
pip install "claim-validator[all]"
```

---

## Quick Start

### Rule-Based Validation (no API keys needed)

```python
from claim_validator import validate

result = validate({
    "billing_provider_npi": "1234567893",
    "subscriber_id": "XYZ987654",
    "subscriber_first_name": "Alice",
    "subscriber_last_name": "Smith",
    "subscriber_dob": "1975-03-10",
    "subscriber_gender": "F",
    "patient_first_name": "Alice",
    "patient_last_name": "Smith",
    "patient_dob": "1975-03-10",
    "patient_gender": "F",
    "patient_relationship": "self",
    "payer_id": "BCBS001",
    "payer_name": "Blue Cross Blue Shield",
    "place_of_service": "11",
    "total_charge": 150.00,
    "filing_date": "2026-02-01",
    "diagnosis_codes": [
        {"code": "J06.9", "pointer": 1},
    ],
    "lines": [
        {
            "procedure_code": "99213",
            "diagnosis_pointers": [1],
            "charge_amount": 150.00,
            "service_date_from": "2026-01-15",
        },
    ],
})

print(result.passed)     # True if no ERROR findings
print(result.errors)     # List of ERROR-severity findings
print(result.warnings)   # List of WARNING-severity findings
```

### With AI Validators (requires an LLM provider)

```python
from claim_validator import validate

result = validate(
    claim_dict,
    ai_config={
        "provider": "anthropic",
        "api_key": "sk-ant-...",
        "model": "claude-sonnet-4-5-20241022",
    },
)
```

### With Local Ollama (free, private)

```python
from claim_validator import validate

result = validate(
    claim_dict,
    ai_config={
        "provider": "openai_compatible",
        "api_key": "ollama",
        "model": "mistral",
        "base_url": "http://localhost:11434/v1",
    },
)
```

### Using the Pipeline Builder

```python
from claim_validator import ClaimData, ClaimValidatorSettings, ValidationPipeline

settings = ClaimValidatorSettings(
    ai_validators=[
        "claim_validator.validators.ai.code_validation.CodeValidationAI",
        "claim_validator.validators.ai.coverage_check.CoverageCheckAI",
        "claim_validator.validators.ai.prior_auth.PriorAuthAI",
    ],
    skip_ai_on_rule_failure=True,
    ai_config={
        "provider": "openai_compatible",
        "api_key": "ollama",
        "model": "tinyllama",
        "base_url": "http://localhost:11434/v1",
    },
)

pipeline = ValidationPipeline.from_settings(settings)
claim = ClaimData(**claim_dict)
result = pipeline.run(claim)
```

---

## CLI Tool

After installation, the `claim-validator` command is available globally.

### Validate a claim from a JSON file

```bash
# Rule-based only (default)
claim-validator validate claim.json

# Pretty-print output
claim-validator validate claim.json --pretty

# With AI (Ollama)
claim-validator validate claim.json \
    --ai-provider openai_compatible \
    --ai-api-key ollama \
    --ai-model mistral \
    --ai-base-url http://localhost:11434/v1

# From stdin (pipe from another command)
cat claim.json | claim-validator validate -

# Exit code: 0 = passed, 1 = failed
claim-validator validate claim.json && echo "PASS" || echo "FAIL"
```

### Output format (JSON)

```json
{
  "passed": false,
  "execution_time": 0.012,
  "total_findings": 3,
  "total_errors": 2,
  "total_warnings": 1,
  "findings": [
    {
      "code": "INVALID_NPI",
      "message": "NPI fails Luhn check-digit validation",
      "severity": "error",
      "field_name": "billing_provider_npi",
      "line_number": null,
      "suggestion": "Verify NPI at NPPES"
    }
  ],
  "phases": [...]
}
```

### Run as a Python module

```bash
python -m claim_validator validate claim.json
python -m claim_validator serve --port 8080
python -m claim_validator version
```

---

## REST API Server (Any Language)

Start the server and any language can validate claims over HTTP.

### Start the server

```bash
# Install with server dependencies
pip install "claim-validator[server]"

# Start on default port 8000
claim-validator serve

# Custom host and port
claim-validator serve --host 127.0.0.1 --port 8080

# Development mode with auto-reload
claim-validator serve --reload
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/validators` | List configured validators |
| `POST` | `/api/v1/validate` | Full validation (with optional AI config) |
| `POST` | `/api/v1/validate/quick` | Quick rule-based validation (send claim directly) |
| `GET` | `/docs` | Interactive Swagger UI documentation |
| `GET` | `/redoc` | ReDoc documentation |

### Usage from Any Language

Once the server is running (`claim-validator serve`), call it from anywhere:

**curl:**

```bash
curl -X POST http://localhost:8000/api/v1/validate/quick \
  -H "Content-Type: application/json" \
  -d '{
    "billing_provider_npi": "1234567893",
    "subscriber_id": "XYZ987654",
    "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
    "lines": [{"procedure_code": "99213", "charge_amount": 150.00, "diagnosis_pointers": [1]}],
    "total_charge": 150.00
  }'
```

**Node.js / JavaScript:**

```javascript
const response = await fetch("http://localhost:8000/api/v1/validate/quick", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    billing_provider_npi: "1234567893",
    subscriber_id: "XYZ987654",
    diagnosis_codes: [{ code: "J06.9", pointer: 1 }],
    lines: [{ procedure_code: "99213", charge_amount: 150.0, diagnosis_pointers: [1] }],
    total_charge: 150.0,
  }),
});
const result = await response.json();
console.log(result.passed);    // true or false
console.log(result.findings);  // array of validation findings
```

**Go:**

```go
body := `{"billing_provider_npi":"1234567893","subscriber_id":"XYZ987654",
  "diagnosis_codes":[{"code":"J06.9","pointer":1}],
  "lines":[{"procedure_code":"99213","charge_amount":150.00,"diagnosis_pointers":[1]}],
  "total_charge":150.00}`

resp, err := http.Post("http://localhost:8000/api/v1/validate/quick",
    "application/json", strings.NewReader(body))
```

**Java:**

```java
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("http://localhost:8000/api/v1/validate/quick"))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(claimJson))
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
```

**Ruby:**

```ruby
require "net/http"
require "json"

uri = URI("http://localhost:8000/api/v1/validate/quick")
res = Net::HTTP.post(uri, claim.to_json, "Content-Type" => "application/json")
result = JSON.parse(res.body)
puts result["passed"]
```

**C# / .NET:**

```csharp
var client = new HttpClient();
var content = new StringContent(claimJson, Encoding.UTF8, "application/json");
var response = await client.PostAsync("http://localhost:8000/api/v1/validate/quick", content);
var result = await response.Content.ReadAsStringAsync();
```

### Full validation request (with AI config)

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "claim": {
      "billing_provider_npi": "1234567893",
      "subscriber_id": "XYZ987654",
      "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
      "lines": [{"procedure_code": "99213", "charge_amount": 150.00, "diagnosis_pointers": [1]}],
      "total_charge": 150.0
    },
    "ai_config": {
      "provider": "openai_compatible",
      "api_key": "ollama",
      "model": "mistral",
      "base_url": "http://localhost:11434/v1"
    },
    "skip_ai_on_rule_failure": true
  }'
```

---

## Publishing to PyPI

### Prerequisites

1. Create a free account at [pypi.org](https://pypi.org/account/register/)
2. Create an API token at [pypi.org/manage/account/token/](https://pypi.org/manage/account/#api-tokens)
3. Install build tools:

```bash
pip install build twine
```

### Build and publish

```bash
cd claim-validator

# Build the package (creates dist/ with .whl and .tar.gz)
python -m build

# Upload to Test PyPI first (optional, recommended)
twine upload --repository testpypi dist/*

# Upload to production PyPI
twine upload dist/*
```

### Or publish with uv (simpler)

```bash
cd claim-validator

# Build
uv build

# Publish (will prompt for token)
uv publish
```

### After publishing

Anyone in the world can install your library:

```bash
pip install claim-validator                  # Python users
pip install "claim-validator[server]"        # Start REST API for any language
pip install "claim-validator[ai]"            # With AI validators
pip install "claim-validator[all]"           # Everything
```

### Versioning

The version is derived automatically from git tags via `hatch-vcs`:

```bash
git tag v0.1.0
git push --tags
python -m build   # version will be 0.1.0
```

---

## Configuration

All settings use the `CLAIM_VALIDATOR_` environment variable prefix via `pydantic-settings`:

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| `rule_validators` | `CLAIM_VALIDATOR_RULE_VALIDATORS` | All 8 validators | List of dotted paths to rule validator classes |
| `ai_validators` | `CLAIM_VALIDATOR_AI_VALIDATORS` | `[]` (none) | List of dotted paths to AI validator classes |
| `skip_ai_on_rule_failure` | `CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE` | `True` | Skip AI phase if rule-based phase has errors |
| `ai_config` | `CLAIM_VALIDATOR_AI_CONFIG` | `None` | Dict with `provider`, `api_key`, `model`, and provider-specific kwargs |

Example `.env` file:

```env
CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE=true
```

---

## Validation Pipeline

### Phase 1: Rule-Based Validators

All 8 validators run offline with zero API calls. They execute deterministically in under 20ms.

| # | Validator | Class | What It Checks |
|---|-----------|-------|----------------|
| 1 | **Completeness** | `CompletenessValidator` | Required CMS-1500 fields present, at least 1 diagnosis code and 1 service line |
| 2 | **NPI** | `NPIValidator` | 10-digit NPI format + Luhn check-digit algorithm (healthcare prefix 80840) |
| 3 | **Subscriber ID** | `SubscriberIDValidator` | Member ID format, minimum length, placeholder detection (e.g., "000000", "UNKNOWN") |
| 4 | **Demographics** | `DemographicsValidator` | Valid DOB (not future), gender values, age range, required patient fields for dependents |
| 5 | **Coding** | `CodingValidator` | ICD-10-CM format (A00-Z99), CPT/HCPCS format, diagnosis pointer integrity (pointers reference existing diagnoses) |
| 6 | **Monetary** | `MonetaryValidator` | Charges > 0, line item total equals claim total, patient paid amount check |
| 7 | **Duplicate** | `DuplicateValidator` | Cross-claim detection based on subscriber + service date + payer combination |
| 8 | **Timely Filing** | `TimelyFilingValidator` | Payer-specific filing deadline enforcement with 30-day advance warnings |

### Phase 2: AI-Powered Validators

AI validators only run after claims are **de-identified** (HIPAA Safe Harbor). They require an LLM provider.

| # | Validator | Class | What It Detects |
|---|-----------|-------|-----------------|
| 1 | **Code Validation AI** | `CodeValidationAI` | Gender/age mismatches (e.g., male patient with vaginitis diagnosis), implausible diagnosis-procedure pairs |
| 2 | **Coverage Check AI** | `CoverageCheckAI` | Non-covered diagnoses, documentation requirements, coverage likelihood issues |
| 3 | **Prior Auth AI** | `PriorAuthAI` | High-cost imaging that likely requires prior authorization, surgical procedures, specialty medications |

---

## Data Models

All models are **frozen** (immutable) Pydantic models with `ConfigDict(frozen=True)`.

### ClaimData

Represents a CMS-1500 professional healthcare claim. All fields are optional to support partial validation.

```python
from claim_validator import ClaimData

claim = ClaimData(
    billing_provider_npi="1234567893",
    billing_provider_taxonomy="207Q00000X",
    rendering_provider_npi="9876543210",
    subscriber_id="XYZ987654",
    subscriber_first_name="Alice",
    subscriber_last_name="Smith",
    subscriber_dob="1975-03-10",
    subscriber_gender="F",
    patient_first_name="Alice",
    patient_last_name="Smith",
    patient_dob="1975-03-10",
    patient_gender="F",
    patient_relationship="self",       # self, spouse, child, other
    payer_id="BCBS001",
    payer_name="Blue Cross Blue Shield",
    claim_type="professional",          # professional or institutional
    place_of_service="11",
    total_charge=150.00,
    filing_date="2026-02-01",
    diagnosis_codes=[...],              # List of DiagnosisCode
    lines=[...],                        # List of ClaimLineData
)
```

### DiagnosisCode

```python
from claim_validator import DiagnosisCode

dx = DiagnosisCode(
    code="J06.9",       # ICD-10-CM code
    pointer=1,          # Position (1-based) referenced by service lines
    type="principal",   # principal or secondary
)
```

### ClaimLineData

```python
from claim_validator import ClaimLineData

line = ClaimLineData(
    procedure_code="99213",          # CPT or HCPCS code
    modifiers=["25"],                # Procedure modifiers
    diagnosis_pointers=[1],          # References to DiagnosisCode pointers
    charge_amount=150.00,            # Line item charge
    units=1.0,                       # Service units
    service_date_from="2026-01-15",
    service_date_to="2026-01-15",
    place_of_service="11",
    rendering_provider_npi=None,
)
```

### Finding

A single validation finding returned by any validator.

```python
Finding(
    code="INVALID_NPI",                    # Machine-readable error code
    message="NPI fails Luhn check-digit",  # Human-readable message
    severity=Severity.ERROR,               # ERROR or WARNING
    field_name="billing_provider_npi",     # Field that triggered the finding
    line_number=None,                      # Service line number (if applicable)
    suggestion="Verify NPI at NPPES",      # Suggested fix
    context={"npi": "1234567890"},         # Additional context dict
)
```

### PipelineResult

Aggregated result from the full validation pipeline.

| Property | Type | Description |
|----------|------|-------------|
| `passed` | `bool` | `True` if zero ERROR-severity findings (warnings are allowed) |
| `findings` | `list[Finding]` | All findings sorted by severity (errors first) |
| `errors` | `list[Finding]` | Only ERROR-severity findings |
| `warnings` | `list[Finding]` | Only WARNING-severity findings |
| `phase_results` | `list[PhaseResult]` | Per-phase results with execution times |
| `execution_time` | `float` | Total elapsed seconds |

---

## LLM Provider Abstraction

The `llm` module provides a unified interface for multiple LLM providers through `BaseLLMClient`.

### Supported Providers

| Provider | Class | Install Extra | Description |
|----------|-------|---------------|-------------|
| **Anthropic** | `AnthropicClient` | `claim-validator[anthropic]` | Claude models via the Anthropic SDK |
| **OpenAI** | `OpenAIClient` | `claim-validator[openai]` | GPT models via the OpenAI SDK |
| **OpenAI-Compatible** | `OpenAICompatibleClient` | `claim-validator[openai]` | Ollama, vLLM, LocalAI, or any OpenAI-compatible endpoint |

### Factory Function

```python
from claim_validator import get_llm_client

# Anthropic Claude
client = get_llm_client(
    provider="anthropic",
    api_key="sk-ant-...",
    model="claude-sonnet-4-5-20241022",
)

# OpenAI GPT
client = get_llm_client(
    provider="openai",
    api_key="sk-...",
    model="gpt-4",
)

# Ollama (local, free)
client = get_llm_client(
    provider="openai_compatible",
    api_key="ollama",
    model="mistral",
    base_url="http://localhost:11434/v1",
)
```

### Message Protocol

```python
from claim_validator import Message

messages = [
    Message(role="system", content="You are a medical coding expert."),
    Message(role="user", content="Is ICD-10 code N76.0 valid for a male patient?"),
]
response = client.send_messages(messages)
```

---

## Code Tables

Compressed reference datasets bundled with the library for offline validation. All tables are **lazy-loaded on first access** and cached with **thread-safe double-check locking**.

| Table | File | Description |
|-------|------|-------------|
| **ICD-10-CM** | `icd10_cm.json.gz` | Diagnosis codes (International Classification of Diseases, 10th revision) |
| **HCPCS/CPT** | `hcpcs.json.gz` | Procedure codes (Healthcare Common Procedure Coding System / Current Procedural Terminology) |
| **Taxonomy** | `taxonomy.json.gz` | Provider taxonomy codes (healthcare provider specialties) |
| **Place of Service** | `pos_codes.json.gz` | CMS Place of Service codes (office, hospital, telehealth, etc.) |
| **Timely Filing** | `timely_filing.json` | Payer-specific filing deadline rules |

Lookup modules:

```python
from claim_validator.code_tables.icd10 import is_valid_icd10
from claim_validator.code_tables.hcpcs import is_valid_hcpcs
from claim_validator.code_tables.taxonomy import is_valid_taxonomy
from claim_validator.code_tables.pos import is_valid_pos
```

---

## HIPAA De-identification

Before any claim data is sent to an LLM, the `ClaimDeidentifier` strips all 18 HIPAA Safe Harbor identifiers.

```python
from claim_validator import ClaimData, ClaimDeidentifier

claim = ClaimData(**claim_dict)
deidentified = ClaimDeidentifier.deidentify(claim)

# Retained: codes, charges, age, gender, state, NPI
# Removed: names, DOB, SSN, member ID, address, phone, email, etc.
# Ages 90+ are capped to 90
# Dates are reduced to year only
```

The `DeidentifiedClaim` model has no PHI fields — `patient_first_name`, `subscriber_id`, etc. do not exist on it.

---

## Extending with Custom Validators

### Custom Rule-Based Validator

```python
from claim_validator import BaseValidator, ClaimData, Severity
from claim_validator.models.results import Finding, ValidatorOutput


class MyCustomValidator(BaseValidator):
    name = "my_custom_validator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings = []

        if claim.total_charge and claim.total_charge > 100_000:
            findings.append(self._make_finding(
                code="HIGH_CHARGE",
                message="Total charge exceeds $100,000 — manual review required",
                severity=Severity.WARNING,
                field_name="total_charge",
                suggestion="Verify charge amount before submission",
            ))

        return self._make_output(findings)
```

Register it in settings:

```python
from claim_validator import ClaimValidatorSettings
from claim_validator.conf import DEFAULT_RULE_VALIDATORS

settings = ClaimValidatorSettings(
    rule_validators=[
        *DEFAULT_RULE_VALIDATORS,
        "my_package.validators.MyCustomValidator",
    ],
)
```

---

## Library Reference

### Core Dependencies

These are the only required dependencies. Rule-based validation works with nothing else.

| Library | Version | Purpose |
|---------|---------|---------|
| [**pydantic**](https://docs.pydantic.dev/) | `>=2.0, <3.0` | Data validation and parsing. All claim models (`ClaimData`, `ClaimLineData`, `DiagnosisCode`, `Finding`, `PipelineResult`) are Pydantic `BaseModel` subclasses with `frozen=True` for immutability and `strict=False` for flexible input coercion. Provides automatic type validation, JSON serialization, and schema generation. |
| [**pydantic-settings**](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | `>=2.0, <3.0` | Environment-based configuration management. `ClaimValidatorSettings` extends `BaseSettings` to read configuration from environment variables with the `CLAIM_VALIDATOR_` prefix. Supports frozen config, dotenv files, and type-safe setting validation. |

### Optional Dependencies

#### `ai` extra — All LLM providers

```bash
pip install "claim-validator[ai]"
```

| Library | Version | Purpose |
|---------|---------|---------|
| [**httpx**](https://www.python-httpx.org/) | `>=0.27` | Modern async-capable HTTP client. Used as the transport layer for LLM API calls. Provides connection pooling, timeout handling, and HTTP/2 support. Required by both the Anthropic and OpenAI SDKs. |
| [**anthropic**](https://docs.anthropic.com/en/docs/sdks) | `>=0.40` | Official Anthropic Python SDK. Provides the `AnthropicClient` implementation for calling Claude models. Handles authentication, message formatting, retry logic, and streaming for the Anthropic Messages API. |
| [**openai**](https://platform.openai.com/docs/libraries/python-library) | `>=1.50` | Official OpenAI Python SDK. Provides the `OpenAIClient` implementation for GPT models, and the `OpenAICompatibleClient` for any endpoint that implements the OpenAI Chat Completions API (Ollama, vLLM, LocalAI, etc.). |

#### `server` extra — REST API server

```bash
pip install "claim-validator[server]"
```

| Library | Version | Purpose |
|---------|---------|---------|
| [**fastapi**](https://fastapi.tiangolo.com/) | `>=0.110` | ASGI web framework. Powers the REST API server with automatic OpenAPI/Swagger documentation, request validation, and JSON serialization. |
| [**uvicorn**](https://www.uvicorn.org/) | `>=0.30` | ASGI server. Runs the FastAPI application with high-performance async I/O. Installed with `[standard]` extras for lifespan, watchfiles reload, and httptools. |

#### `anthropic` extra — Anthropic only

```bash
pip install "claim-validator[anthropic]"
```

Installs `httpx` and `anthropic` only (no OpenAI SDK).

#### `openai` extra — OpenAI only

```bash
pip install "claim-validator[openai]"
```

Installs `httpx` and `openai` only (no Anthropic SDK).

#### `django` extra — Django integration

```bash
pip install "claim-validator[django]"
```

| Library | Version | Purpose |
|---------|---------|---------|
| [**django**](https://www.djangoproject.com/) | `>=4.2` | Web framework integration for building claim validation REST API services on Django/DRF. |

#### `fastapi` extra — FastAPI integration

```bash
pip install "claim-validator[fastapi]"
```

| Library | Version | Purpose |
|---------|---------|---------|
| [**fastapi**](https://fastapi.tiangolo.com/) | `>=0.110` | ASGI framework integration for building claim validation API services with automatic OpenAPI documentation. |

### Development Dependencies

```bash
pip install "claim-validator[dev]"
```

| Library | Version | Purpose |
|---------|---------|---------|
| [**pytest**](https://docs.pytest.org/) | `>=8.0` | Test framework. Runs 48 test files covering all validators, models, LLM providers, de-identification, code tables, HIPAA compliance, and integration tests. |
| [**pytest-cov**](https://pytest-cov.readthedocs.io/) | latest | Code coverage plugin for pytest. Generates coverage reports to track test completeness across the validation pipeline. |
| [**ruff**](https://docs.astral.sh/ruff/) | `>=0.5` | Fast Python linter and formatter. Configured for line-length 100, Python 3.11 target, with rule sets: E (pycodestyle errors), F (pyflakes), I (isort), N (naming), W (pycodestyle warnings), UP (pyupgrade). |
| [**mypy**](https://mypy.readthedocs.io/) | `>=1.10` | Static type checker. Runs in **strict mode** with the Pydantic plugin enabled (`pydantic.mypy`). Enforces typed function signatures, no implicit optional, and strict equality checking. |
| [**factory-boy**](https://factoryboy.readthedocs.io/) | `>=3.3` | Test fixture factory. Generates realistic claim data for test scenarios without manual fixture files. |

### Build & Tooling

| Tool | Purpose |
|------|---------|
| [**hatchling**](https://hatch.pypa.io/latest/) | PEP 517 build backend. Builds wheels and sdists from the `src/` layout. |
| [**hatch-vcs**](https://github.com/ofek/hatch-vcs) | Version plugin for hatchling. Derives the package version automatically from git tags (e.g., `v0.1.0` tag becomes version `0.1.0`). Generates `_version.py` at build time. |
| [**uv**](https://docs.astral.sh/uv/) | Fast Python package manager. The `uv.lock` lockfile pins all transitive dependencies for reproducible installs. |

---

## Running the Demo

The project includes an end-to-end demo script with multiple scenarios:

```bash
# Rule-based only (no Ollama needed)
uv run python claim-validator/demo_e2e.py --no-ai

# Full pipeline with Ollama
ollama pull tinyllama
ollama serve
uv run python claim-validator/demo_e2e.py

# With a specific model
uv run python claim-validator/demo_e2e.py --model mistral
```

Demo scenarios:
1. **Clean claim** — valid claim passes all rule-based validators
2. **Broken claim** — multiple errors (bad NPI, missing subscriber ID, negative charges, bad pointers)
3. **De-identification** — shows PHI stripping before/after
4. **Full pipeline with AI** — rule-based + AI validators via Ollama
5. **Force AI on failure** — AI runs even when rules fail (`skip_ai_on_rule_failure=False`)

---

## Testing

```bash
# Run all tests
cd claim-validator && uv run pytest

# Run with coverage
uv run pytest --cov=claim_validator

# Run specific test suites
uv run pytest tests/test_validators/test_rule_based/
uv run pytest tests/test_validators/test_ai/
uv run pytest tests/test_llm/
uv run pytest tests/test_deidentifier/
uv run pytest tests/test_code_tables/
uv run pytest tests/test_models/
uv run pytest tests/test_hipaa/

# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/claim_validator/
```

---

## Project Structure

```
claim-validator/                         # Repository root
├── README.md                            # This file
├── claim-validator/                     # Python library package
│   ├── src/claim_validator/
│   │   ├── __init__.py                  # Public API exports
│   │   ├── __main__.py                  # python -m claim_validator support
│   │   ├── _api.py                      # validate() entry point
│   │   ├── _version.py                  # Dynamic version (hatch-vcs)
│   │   ├── cli.py                       # CLI tool (validate, serve, version)
│   │   ├── server.py                    # REST API server (FastAPI)
│   │   ├── conf.py                      # ClaimValidatorSettings
│   │   ├── constants.py                 # Severity, ClaimType enums
│   │   ├── exceptions.py               # Exception hierarchy
│   │   ├── models/
│   │   │   ├── claim.py                 # ClaimData, ClaimLineData, DiagnosisCode
│   │   │   ├── deidentified.py          # DeidentifiedClaim (HIPAA Safe Harbor)
│   │   │   └── results.py              # Finding, ValidatorOutput, PipelineResult
│   │   ├── validators/
│   │   │   ├── base.py                  # BaseValidator abstract class
│   │   │   ├── pipeline.py              # ValidationPipeline orchestrator
│   │   │   ├── registry.py              # ValidatorRegistry factory
│   │   │   ├── rule_based/              # 8 deterministic validators
│   │   │   │   ├── completeness.py
│   │   │   │   ├── npi.py
│   │   │   │   ├── subscriber_id.py
│   │   │   │   ├── demographics.py
│   │   │   │   ├── coding.py
│   │   │   │   ├── monetary.py
│   │   │   │   ├── duplicate.py
│   │   │   │   └── timely_filing.py
│   │   │   └── ai/                      # 3 AI-powered validators
│   │   │       ├── base.py
│   │   │       ├── code_validation.py
│   │   │       ├── coverage_check.py
│   │   │       └── prior_auth.py
│   │   ├── llm/                         # Multi-provider LLM abstraction
│   │   │   ├── base.py                  # BaseLLMClient, Message
│   │   │   ├── factory.py               # get_llm_client()
│   │   │   └── providers/
│   │   │       ├── anthropic.py
│   │   │       ├── openai.py
│   │   │       └── openai_compatible.py
│   │   ├── deidentifier/
│   │   │   └── deidentifier.py          # ClaimDeidentifier
│   │   ├── code_tables/
│   │   │   ├── loader.py                # Thread-safe gzip JSON loader
│   │   │   ├── icd10.py
│   │   │   ├── hcpcs.py
│   │   │   ├── taxonomy.py
│   │   │   ├── pos.py
│   │   │   └── timely_filing.py
│   │   └── data/                        # Compressed reference datasets
│   │       ├── icd10_cm.json.gz
│   │       ├── hcpcs.json.gz
│   │       ├── taxonomy.json.gz
│   │       ├── pos_codes.json.gz
│   │       ├── timely_filing.json
│   │       └── manifest.json
│   ├── tests/                           # 48 test files
│   ├── pyproject.toml
│   ├── CHANGELOG.md
│   ├── demo_e2e.py
│   ├── .env.example
│   └── uv.lock
└── submission-docs/                     # Architecture documentation
    ├── PROJECT_ABSTRACT.md
    ├── ARCHITECTURE.md
    └── PROTOTYPE_DEMO_GUIDE.md
```

---

## Exception Hierarchy

```
ClaimValidatorError          # Base exception
├── ValidationError          # Invalid input data (malformed claim, missing fields)
├── ConfigurationError       # Invalid config (bad validator path, missing provider)
├── LLMError                 # LLM provider communication failure
└── CodeTableError           # Code table loading or lookup failure
```

---

## License

MIT
