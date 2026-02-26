# Story 3.4: AI Clinical Validators

Status: review

## Story

As a **developer**,
I want AI validators that catch clinical edge cases rules miss — implausible diagnosis-procedure pairs, coverage concerns, and prior auth requirements,
so that I can reduce denials caused by clinical issues that deterministic rules can't detect.

## Acceptance Criteria

1. **Given** a de-identified claim with a clinically implausible diagnosis-procedure combination (e.g., CPT 59400 obstetric package for a male patient), **When** `CodeValidationAI.validate_deidentified(claim)` is called, **Then** a `Finding` with code `AI_CLINICAL_IMPLAUSIBILITY`, severity `WARNING`, specific `field_name`, and `line_number` is produced, **And** the suggestion explains why the combination is implausible.

2. **Given** a de-identified claim with valid clinical coding, **When** `CodeValidationAI.validate_deidentified(claim)` is called, **Then** zero AI clinical findings are produced.

3. **Given** a de-identified claim with a service likely to be denied for medical necessity, **When** `CoverageCheckAI.validate_deidentified(claim)` is called, **Then** a `Finding` with code `AI_COVERAGE_CONCERN`, severity `WARNING` is produced, **And** the suggestion describes the coverage concern and recommended documentation.

4. **Given** a de-identified claim with a service likely requiring prior authorization, **When** `PriorAuthAI.validate_deidentified(claim)` is called, **Then** a `Finding` with code `AI_PRIOR_AUTH_LIKELY`, severity `WARNING` is produced, **And** the suggestion recommends checking prior auth status before submission.

5. **Given** each AI validator, **When** I inspect its implementation, **Then** it has per-validator prompt templates as class constants (system prompt, user prompt template), **And** uses hybrid response parsing (structured JSON preferred, free-text regex fallback).

6. **Given** AI findings from any AI validator, **When** I inspect the findings, **Then** all AI finding codes are prefixed with `AI_`, **And** severity is always `WARNING` (AI findings are advisory, never authoritative ERROR), **And** no PHI appears in any finding message or suggestion.

## Tasks / Subtasks

- [x] Task 1: Create `CodeValidationAI` in `src/claim_validator/validators/ai/code_validation.py` (AC: #1, #2, #5, #6)
  - [x] Class `CodeValidationAI(BaseAIValidator)` with `name = "CodeValidationAI"`
  - [x] `SYSTEM_PROMPT` class constant — instructs LLM to analyze clinical plausibility of diagnosis-procedure pairs
  - [x] `_build_user_prompt(claim: DeidentifiedClaim) -> str` — formats claim data (diagnosis codes, procedure codes, patient age/gender) into analysis prompt
  - [x] `validate_deidentified(claim) -> ValidatorOutput` — sends prompts via `_send_to_llm()`, parses response
  - [x] `_parse_response(response: str) -> list[Finding]` — hybrid parsing: JSON first, regex fallback
  - [x] Finding code `AI_CLINICAL_IMPLAUSIBILITY`, severity `WARNING`
  - [x] Include `line_number` and `field_name` in findings where the LLM identifies a specific line
- [x] Task 2: Create `CoverageCheckAI` in `src/claim_validator/validators/ai/coverage_check.py` (AC: #3, #5, #6)
  - [x] Class `CoverageCheckAI(BaseAIValidator)` with `name = "CoverageCheckAI"`
  - [x] `SYSTEM_PROMPT` class constant — instructs LLM to evaluate medical necessity and coverage concerns
  - [x] `_build_user_prompt(claim: DeidentifiedClaim) -> str` — formats claim data with payer context
  - [x] `validate_deidentified(claim) -> ValidatorOutput` — sends prompts, parses response
  - [x] `_parse_response(response: str) -> list[Finding]` — hybrid parsing
  - [x] Finding code `AI_COVERAGE_CONCERN`, severity `WARNING`
- [x] Task 3: Create `PriorAuthAI` in `src/claim_validator/validators/ai/prior_auth.py` (AC: #4, #5, #6)
  - [x] Class `PriorAuthAI(BaseAIValidator)` with `name = "PriorAuthAI"`
  - [x] `SYSTEM_PROMPT` class constant — instructs LLM to identify services requiring prior authorization
  - [x] `_build_user_prompt(claim: DeidentifiedClaim) -> str` — formats claim data
  - [x] `validate_deidentified(claim) -> ValidatorOutput` — sends prompts, parses response
  - [x] `_parse_response(response: str) -> list[Finding]` — hybrid parsing
  - [x] Finding code `AI_PRIOR_AUTH_LIKELY`, severity `WARNING`
- [x] Task 4: Update exports in `src/claim_validator/validators/ai/__init__.py` (AC: all)
  - [x] Export `CodeValidationAI`, `CoverageCheckAI`, `PriorAuthAI` alongside `BaseAIValidator`
- [x] Task 5: Write tests for `CodeValidationAI` in `tests/test_validators/test_ai/test_code_validation.py` (AC: #1, #2, #5, #6)
  - [x] Test implausible combination produces `AI_CLINICAL_IMPLAUSIBILITY` WARNING
  - [x] Test valid clinical coding produces zero findings
  - [x] Test prompt construction includes diagnosis codes, procedure codes, age, gender
  - [x] Test hybrid response parsing: structured JSON path
  - [x] Test hybrid response parsing: regex fallback path
  - [x] Test severity is always WARNING
  - [x] Test no PHI in finding messages
  - [x] Test `_send_to_llm` is called with correct message structure (system + user)
  - [x] Test line_number and field_name populated in findings
- [x] Task 6: Write tests for `CoverageCheckAI` in `tests/test_validators/test_ai/test_coverage_check.py` (AC: #3, #5, #6)
  - [x] Test coverage concern produces `AI_COVERAGE_CONCERN` WARNING
  - [x] Test no coverage concerns produces zero findings
  - [x] Test prompt includes payer context
  - [x] Test hybrid response parsing (JSON + regex fallback)
  - [x] Test severity is always WARNING
  - [x] Test no PHI in findings
- [x] Task 7: Write tests for `PriorAuthAI` in `tests/test_validators/test_ai/test_prior_auth.py` (AC: #4, #5, #6)
  - [x] Test prior auth likely produces `AI_PRIOR_AUTH_LIKELY` WARNING
  - [x] Test no prior auth concerns produces zero findings
  - [x] Test hybrid response parsing (JSON + regex fallback)
  - [x] Test severity is always WARNING
  - [x] Test no PHI in findings
- [x] Task 8: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors
  - [x] `uv run pytest` — all tests pass (existing + new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### uv PATH

```bash
export PATH="$HOME/snap/code/225/.local/bin:$PATH"
```

### Previous Story Intelligence (Story 3.3)

- 626 tests pass (580 existing + 46 new), ruff clean, mypy clean (41 source files)
- BaseAIValidator ABC fully implemented with: `validate_deidentified()` abstract method, `_send_to_llm()` helper, `_make_output()` / `_make_finding()` inherited from BaseValidator
- Pipeline AI phase: deidentify once, then run all AI validators on `DeidentifiedClaim`
- LLMError caught → `AI_PROVIDER_ERROR` WARNING (graceful degradation)
- Line-length limit is 100 characters — wrap long strings with implicit concatenation
- Test pattern: class-based tests with `setup_method`, helper functions for test data
- ruff catches unused imports (F401), unsorted imports (I001) — run `ruff check . --fix`
- `head`, `tail`, and `tee` commands unavailable in sandbox — don't pipe to them
- Mock AI validators in pipeline tests used `MockLLMClient(BaseLLMClient)` with hardcoded `send_messages()` return values

### Current State of Key Files

| File | Status | Notes |
|---|---|---|
| `validators/ai/base.py` | **Complete** | BaseAIValidator ABC — parent of all three new validators |
| `validators/ai/__init__.py` | **Has BaseAIValidator export** | Needs CodeValidationAI, CoverageCheckAI, PriorAuthAI exports |
| `validators/ai/code_validation.py` | **DOES NOT EXIST** | Primary deliverable |
| `validators/ai/coverage_check.py` | **DOES NOT EXIST** | Primary deliverable |
| `validators/ai/prior_auth.py` | **DOES NOT EXIST** | Primary deliverable |
| `validators/pipeline.py` | **Complete** | AI phase integration done — no changes needed |
| `validators/registry.py` | **Complete** | `create_ai_validators()` with llm_client injection — no changes needed |
| `llm/base.py` | **Complete** | `BaseLLMClient.send_messages(list[Message]) -> str`, `Message(role, content)` |
| `models/deidentified.py` | **Complete** | `DeidentifiedClaim` with all safe fields (see below) |
| `models/results.py` | **Complete** | `Finding`, `ValidatorOutput` — used via `_make_output()` / `_make_finding()` |
| `conf.py` | **Complete** | `ai_validators` list, `ai_config` dict |
| `constants.py` | **Complete** | `Severity.ERROR`, `Severity.WARNING` |
| `exceptions.py` | **Complete** | `LLMError(ClaimValidatorError)` |

### DeidentifiedClaim Fields Available to AI Validators

These are the ONLY fields accessible — all PHI has been stripped:

```python
class DeidentifiedClaim(BaseModel):
    # Provider (NPI is public, not PHI)
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    rendering_provider_npi: str | None = None

    # Demographics (de-identified)
    patient_age: int | None = None  # Capped at 90 per Safe Harbor
    patient_gender: str | None = None

    # Payer (organization identifier, not PHI)
    payer_id: str | None = None
    payer_name: str | None = None

    # Claim metadata
    claim_type: str = "professional"
    place_of_service: str | None = None
    total_charge: float | None = None

    # Clinical data (codes are not PHI)
    diagnosis_codes: list[dict[str, str | int]] = []
    lines: list[DeidentifiedLineData] = []

class DeidentifiedLineData(BaseModel):
    procedure_code: str
    modifiers: list[str] = []
    diagnosis_pointers: list[int] = []
    charge_amount: float
    units: float = 1.0
    place_of_service: str | None = None
    rendering_provider_npi: str | None = None
    service_year: int | None = None
```

### Implementation Spec

**Architecture Decision D8 — Per-validator prompts as class constants:**

Each AI validator MUST define its own `SYSTEM_PROMPT` and `_build_user_prompt()` method. Prompts are NOT shared. Each validator is a self-contained unit.

**Architecture Decision D9 — Hybrid response parsing:**

1. **Primary path (JSON):** Ask the LLM to respond in JSON. Parse with `json.loads()`.
2. **Fallback path (regex):** If JSON parsing fails, use regex to extract findings from free-text response.
3. Each validator defines BOTH parsing paths in `_parse_response()`.

**Common validator pattern (all three follow this):**

```python
"""CodeValidationAI — AI clinical plausibility validator."""

from __future__ import annotations

import json
import re

from claim_validator.constants import Severity
from claim_validator.llm.base import Message
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.ai.base import BaseAIValidator


class CodeValidationAI(BaseAIValidator):
    """Checks clinical plausibility of diagnosis-procedure pairs.

    Uses LLM analysis to detect combinations that are
    clinically implausible and likely to be denied.
    """

    name = "CodeValidationAI"

    SYSTEM_PROMPT = (
        "You are a medical coding auditor. Analyze the "
        "diagnosis-procedure combinations in this claim for "
        "clinical plausibility.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"line_number": <int>, "field_name": <str>, '
        '"reason": <str>}\n'
        "]}\n\n"
        "If all combinations are clinically plausible, "
        'respond: {"findings": []}\n\n'
        "Rules:\n"
        "- Flag gender-specific procedures billed for "
        "wrong gender\n"
        "- Flag age-inappropriate procedures\n"
        "- Flag diagnosis codes that do not clinically "
        "support the procedure\n"
        "- Only flag clear implausibilities, not borderline "
        "cases"
    )

    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        prompt = self._build_user_prompt(claim)
        response = self._send_to_llm([
            Message(role="system", content=self.SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ])
        findings = self._parse_response(response)
        return self._make_output(findings)

    def _build_user_prompt(
        self,
        claim: DeidentifiedClaim,
    ) -> str:
        """Format de-identified claim for LLM analysis."""
        parts: list[str] = []
        if claim.patient_age is not None:
            parts.append(f"Patient age: {claim.patient_age}")
        if claim.patient_gender:
            parts.append(f"Patient gender: {claim.patient_gender}")

        if claim.diagnosis_codes:
            codes = ", ".join(
                str(d.get("code", ""))
                for d in claim.diagnosis_codes
            )
            parts.append(f"Diagnosis codes: {codes}")

        for i, line in enumerate(claim.lines, start=1):
            mods = (
                f" (modifiers: {', '.join(line.modifiers)})"
                if line.modifiers
                else ""
            )
            parts.append(
                f"Line {i}: {line.procedure_code}{mods}"
                f" charge=${line.charge_amount:.2f}"
            )

        return "\n".join(parts)

    def _parse_response(
        self,
        response: str,
    ) -> list[Finding]:
        """Parse LLM response — JSON first, regex fallback."""
        # Try structured JSON
        try:
            data = json.loads(response)
            items = data.get("findings", [])
            if not items:
                return []
            return [
                self._make_finding(
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=item.get("reason", "..."),
                    severity=Severity.WARNING,
                    field_name=item.get(
                        "field_name", "procedure_code",
                    ),
                    line_number=item.get("line_number"),
                )
                for item in items
                if isinstance(item, dict)
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Regex fallback for free-text
        findings: list[Finding] = []
        pattern = re.compile(
            r"(?:line\s*(\d+))[:\s]+"
            r"(.+?)(?:\n|$)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(response):
            findings.append(
                self._make_finding(
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=match.group(2).strip(),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                    line_number=int(match.group(1)),
                )
            )

        # If regex found nothing but response indicates
        # issues, create a generic finding
        if not findings and _indicates_issue(response):
            findings.append(
                self._make_finding(
                    code="AI_CLINICAL_IMPLAUSIBILITY",
                    message=(
                        "AI detected clinical plausibility"
                        " concern"
                    ),
                    severity=Severity.WARNING,
                    field_name="procedure_code",
                )
            )
        return findings


def _indicates_issue(text: str) -> bool:
    """Check if free-text response signals an issue."""
    lower = text.lower()
    return any(
        kw in lower
        for kw in (
            "implausible",
            "inappropriate",
            "mismatch",
            "inconsistent",
            "unlikely",
            "concern",
            "flag",
        )
    )
```

**CoverageCheckAI follows the same pattern but with different prompts:**

```python
class CoverageCheckAI(BaseAIValidator):
    name = "CoverageCheckAI"

    SYSTEM_PROMPT = (
        "You are a healthcare coverage analyst. Evaluate "
        "this claim for potential medical necessity and "
        "coverage concerns.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"field_name": <str>, "reason": <str>, '
        '"documentation": <str>}\n'
        "]}\n\n"
        "If no coverage concerns, respond: "
        '{"findings": []}\n\n'
        "Consider:\n"
        "- Services that commonly require medical necessity"
        " documentation\n"
        "- Diagnosis codes that may not support the "
        "procedure for coverage purposes\n"
        "- High-cost services with strict coverage "
        "criteria\n"
        "- Payer-specific coverage patterns"
    )
    # validate_deidentified, _build_user_prompt, _parse_response
    # follow identical structure with AI_COVERAGE_CONCERN code
```

**PriorAuthAI follows the same pattern:**

```python
class PriorAuthAI(BaseAIValidator):
    name = "PriorAuthAI"

    SYSTEM_PROMPT = (
        "You are a prior authorization specialist. "
        "Identify services in this claim that commonly "
        "require prior authorization.\n\n"
        "Respond in JSON format:\n"
        '{"findings": [\n'
        '  {"field_name": <str>, "line_number": <int>, '
        '"reason": <str>}\n'
        "]}\n\n"
        "If no prior auth concerns, respond: "
        '{"findings": []}\n\n'
        "Common prior auth triggers:\n"
        "- Advanced imaging (MRI, CT, PET)\n"
        "- Surgical procedures\n"
        "- Specialty medications/infusions\n"
        "- DME over threshold cost\n"
        "- Genetic testing\n"
        "- Mental health inpatient stays"
    )
    # validate_deidentified, _build_user_prompt, _parse_response
    # follow identical structure with AI_PRIOR_AUTH_LIKELY code
```

### Key Design Decisions

- **Per-validator prompts (D8)** — each validator owns its SYSTEM_PROMPT constant and `_build_user_prompt()`. No shared prompt infrastructure
- **Hybrid response parsing (D9)** — try `json.loads()` first; if that fails, regex parse free-text. Each validator defines both paths
- **AI findings are always `WARNING` severity** — AI is advisory, never authoritative. WARNINGs don't fail the pipeline
- **All finding codes prefixed with `AI_`** — distinguishes AI findings from rule-based findings
- **`_build_user_prompt()` uses ONLY DeidentifiedClaim fields** — never reaches into raw claim data
- **No PHI in prompts** — only codes, charges, age, gender, payer ID, NPI (all non-PHI)
- **No retry logic** — pipeline catches LLMError for graceful degradation; consumers handle retries
- **Module-level helper `_indicates_issue()`** — shared heuristic for free-text fallback; keeps it simple
- **`_parse_response()` is a private method** — not part of public API

### Anti-Patterns to Avoid

- **DO NOT** access raw `ClaimData` from an AI validator — only `DeidentifiedClaim` fields
- **DO NOT** use `Severity.ERROR` in any AI finding — always `WARNING`
- **DO NOT** include patient names, DOB, subscriber ID in prompts — only de-identified fields
- **DO NOT** share prompts between validators — each owns its own (D8)
- **DO NOT** import or depend on rule-based validators — AI validators are independent
- **DO NOT** add retry logic in validators — pipeline handles LLM failures (caught as LLMError → AI_PROVIDER_ERROR)
- **DO NOT** add `validate()` implementation — inherited from BaseAIValidator (raises NotImplementedError)
- **DO NOT** construct `ValidatorOutput` directly — always use `self._make_output(findings)`
- **DO NOT** construct `Finding` directly — always use `self._make_finding(...)`
- **DO NOT** log PHI — Finding messages must reference field names, not values

### Testing Strategy

All tests use mock LLM clients — no real API calls. Use `MockLLMClient(BaseLLMClient)` that returns controlled response strings.

**Test pattern for each validator:**

```python
"""Tests for CodeValidationAI."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.ai.code_validation import (
    CodeValidationAI,
)


class MockLLMClient(BaseLLMClient):
    """Mock LLM client returning controlled responses."""

    provider_name = "mock"

    def __init__(
        self,
        *,
        model: str = "mock",
        api_key: str = "sk-mock",
        response: str = '{"findings": []}',
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._response = response
        self.last_messages: list[Message] | None = None

    def send_messages(
        self, messages: list[Message],
    ) -> str:
        self.last_messages = messages
        return self._response


def _make_claim(**overrides: object) -> DeidentifiedClaim:
    """Create a de-identified claim for testing."""
    defaults: dict = {
        "billing_provider_npi": "1234567893",
        "patient_age": 45,
        "patient_gender": "M",
        "payer_id": "BCBS01",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            DeidentifiedLineData(
                procedure_code="99213",
                diagnosis_pointers=[1],
                charge_amount=150.0,
            ),
        ],
    }
    defaults.update(overrides)
    return DeidentifiedClaim(**defaults)


class TestCodeValidationAICleanClaim:
    """Test no findings for valid clinical coding."""

    def test_valid_coding_returns_empty(self) -> None:
        client = MockLLMClient(
            response='{"findings": []}',
        )
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert isinstance(result, ValidatorOutput)
        assert len(result.findings) == 0

    def test_validator_name_set(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert result.validator_name == "CodeValidationAI"


class TestCodeValidationAIImplausibleClaim:
    """Test implausible combination produces findings."""

    def test_implausible_produces_warning(self) -> None:
        response = json.dumps({
            "findings": [{
                "line_number": 1,
                "field_name": "procedure_code",
                "reason": (
                    "Obstetric procedure for male patient"
                ),
            }],
        })
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        claim = _make_claim(
            patient_gender="M",
            lines=[
                DeidentifiedLineData(
                    procedure_code="59400",
                    diagnosis_pointers=[1],
                    charge_amount=3500.0,
                ),
            ],
        )
        result = validator.validate_deidentified(claim)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.code == "AI_CLINICAL_IMPLAUSIBILITY"
        assert f.severity == Severity.WARNING
        assert f.line_number == 1

    def test_severity_is_always_warning(self) -> None:
        # ... verify no ERROR severity ever produced


class TestCodeValidationAIPromptConstruction:
    """Test prompt includes correct de-identified fields."""

    def test_prompt_includes_age_gender(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(
            _make_claim(patient_age=72, patient_gender="F"),
        )
        user_msg = client.last_messages[-1].content
        assert "72" in user_msg
        assert "F" in user_msg

    def test_prompt_includes_diagnosis_codes(self) -> None:
        # ... verify diagnosis codes in prompt

    def test_system_message_present(self) -> None:
        client = MockLLMClient()
        validator = CodeValidationAI(llm_client=client)
        validator.validate_deidentified(_make_claim())
        assert client.last_messages[0].role == "system"


class TestCodeValidationAIResponseParsing:
    """Test hybrid JSON / regex parsing."""

    def test_json_response_parsed(self) -> None:
        # ... valid JSON response

    def test_malformed_json_falls_back_to_regex(self) -> None:
        response = (
            "Line 1: Obstetric procedure billed for"
            " male patient — implausible"
        )
        client = MockLLMClient(response=response)
        validator = CodeValidationAI(llm_client=client)
        result = validator.validate_deidentified(
            _make_claim(),
        )
        assert len(result.findings) >= 1
        assert (
            result.findings[0].code
            == "AI_CLINICAL_IMPLAUSIBILITY"
        )

    def test_no_phi_in_findings(self) -> None:
        # ... verify no patient names, DOB, SSN in messages
```

**Key testing considerations:**
- Each test file follows the same pattern: MockLLMClient → controlled responses → assert findings
- Test BOTH JSON and regex parsing paths for each validator
- Test clean claim → zero findings (AC: #2)
- Test problematic claim → correct finding code, WARNING severity, proper field_name
- Test prompt construction → verify de-identified fields only
- Test no PHI in any finding message or suggestion
- All tests use `DeidentifiedClaim` (not `ClaimData`)

### Project Structure Notes

```
src/claim_validator/validators/ai/
├── __init__.py          # Exports: BaseAIValidator, CodeValidationAI, CoverageCheckAI, PriorAuthAI
├── base.py              # BaseAIValidator ABC (COMPLETE — no changes)
├── code_validation.py   # NEW: CodeValidationAI
├── coverage_check.py    # NEW: CoverageCheckAI
└── prior_auth.py        # NEW: PriorAuthAI

tests/test_validators/test_ai/
├── __init__.py              # Empty (exists)
├── test_base_ai_validator.py  # Existing (16 tests — no changes)
├── test_code_validation.py    # NEW
├── test_coverage_check.py     # NEW
└── test_prior_auth.py         # NEW
```

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **D8** | Per-validator prompts — each AI validator owns SYSTEM_PROMPT and _build_user_prompt() |
| **D9** | Hybrid response parsing — JSON preferred, regex fallback |
| **D5** | Pipeline-integrated de-identification — validators receive DeidentifiedClaim (already done in pipeline) |
| **D6** | Type-driven PHI boundary — DeidentifiedClaim type guarantees no PHI |
| **D7** | Chat-based LLM — _send_to_llm() sends list[Message] |
| **FR18** | AI clinical plausibility assessment (CodeValidationAI) |
| **FR19** | AI coverage/medical necessity assessment (CoverageCheckAI) |
| **FR20** | AI prior authorization identification (PriorAuthAI) |
| **FR22** | Only non-PHI data sent to LLMs |
| **NFR18** | AI findings are WARNING (advisory, not blocking) |

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.4] — Acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#D8] — Per-validator prompts as class constants
- [Source: _bmad-output/planning-artifacts/architecture.md#D9] — Hybrid response parsing
- [Source: _bmad-output/planning-artifacts/architecture.md#AI validators naming] — `{Name}AI` convention: CodeValidationAI, CoverageCheckAI, PriorAuthAI
- [Source: _bmad-output/planning-artifacts/architecture.md#Finding codes] — `AI_` prefix for all AI finding codes
- [Source: _bmad-output/planning-artifacts/architecture.md#Source Organization] — `validators/ai/code_validation.py`, `coverage_check.py`, `prior_auth.py`
- [Source: _bmad-output/planning-artifacts/prd.md#FR18-FR20] — AI validation capabilities
- [Source: _bmad-output/planning-artifacts/prd.md#FR22] — Only non-PHI clinically relevant data to LLMs
- [Source: _bmad-output/implementation-artifacts/3-3-ai-validation-pipeline-integration.md] — Previous story intelligence

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- PriorAuthAI free-text parsing: initial keyword list was too broad — "prior authorization" matched negation phrases like "No services... require prior authorization." Fixed by using affirmative-only keywords and a negation regex guard.

### Completion Notes List

- All 3 AI clinical validators implemented using TDD (red-green-refactor)
- CodeValidationAI: 19 tests, checks clinical plausibility of diagnosis-procedure pairs
- CoverageCheckAI: 13 tests, evaluates medical necessity and coverage concerns, includes payer context
- PriorAuthAI: 13 tests, identifies services requiring prior authorization, negation-aware free-text parsing
- All validators follow identical architecture: SYSTEM_PROMPT constant, _build_user_prompt(), hybrid JSON/regex _parse_response()
- All AI findings use WARNING severity, codes prefixed with AI_
- Removed unused `import re` from coverage_check.py (caught by ruff)
- Total test count: 671 (up from 626, +45 new tests)

### File List

| File | Action |
|---|---|
| `src/claim_validator/validators/ai/code_validation.py` | Created |
| `src/claim_validator/validators/ai/coverage_check.py` | Created |
| `src/claim_validator/validators/ai/prior_auth.py` | Created |
| `src/claim_validator/validators/ai/__init__.py` | Modified (added exports) |
| `tests/test_validators/test_ai/test_code_validation.py` | Created (19 tests) |
| `tests/test_validators/test_ai/test_coverage_check.py` | Created (13 tests) |
| `tests/test_validators/test_ai/test_prior_auth.py` | Created (13 tests) |

### Change Log

| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-19 | Create-story workflow |
| Implementation complete | 2026-02-19 | Dev-story workflow — all 8 tasks done, 671 tests pass |
