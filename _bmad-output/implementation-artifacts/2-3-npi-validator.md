# Story 2.3: NPI Validator

Status: review

## Story

As a **developer**,
I want NPI numbers validated using the Luhn check-digit algorithm,
so that claims with invalid provider identifiers are caught before submission.

## Acceptance Criteria

1. **Given** a claim with a valid NPI (e.g., `"1234567893"` — passes Luhn check), **When** `NPIValidator.validate(claim)` is called, **Then** the output contains zero NPI-related findings.

2. **Given** a claim with an invalid NPI (e.g., `"1234567890"` — fails Luhn check), **When** `NPIValidator.validate(claim)` is called, **Then** the output contains a `Finding` with code `INVALID_NPI`, severity `ERROR`, field_name `billing_provider_npi`, and a suggestion to verify at `https://npiregistry.cms.hhs.gov`.

3. **Given** a claim with an NPI that is not exactly 10 digits, **When** `NPIValidator.validate(claim)` is called, **Then** the output contains a finding about invalid NPI format.

4. **Given** a claim with both billing and rendering provider NPIs, **When** `NPIValidator.validate(claim)` is called, **Then** both NPIs are validated independently with appropriate `field_name` on each finding.

5. **Given** the NPI value `"1234567890"` in the finding, **When** I inspect the `message` field, **Then** it does NOT contain the actual NPI value (no PHI in messages).

## Tasks / Subtasks

- [x] Task 1: Implement `_check_luhn_npi()` private helper function (AC: #2, #3)
  - [x] Implement NPI Luhn algorithm: prepend "80840" prefix, standard Luhn mod-10 check
  - [x] Return `True` if valid, `False` if not
  - [x] Handle non-numeric input gracefully (return `False`)
- [x] Task 2: Implement `NPIValidator` in `src/claim_validator/validators/rule_based/npi.py` (AC: #1-#5)
  - [x] Subclass `BaseValidator` with `name = "NPIValidator"`
  - [x] Validate `billing_provider_npi` (claim-level) — skip if None/empty
  - [x] Validate `rendering_provider_npi` (claim-level) — skip if None/empty
  - [x] Validate `rendering_provider_npi` on each line — skip if None/empty, include `line_number`
  - [x] Check format first (exactly 10 digits) → code `INVALID_NPI_FORMAT`
  - [x] Check Luhn checksum → code `INVALID_NPI`
  - [x] No PHI in messages — never include the actual NPI value
- [x] Task 3: Write tests in `tests/test_validators/test_rule_based/test_npi.py` (AC: all)
  - [x] Test valid NPI `"1234567893"` → zero findings
  - [x] Test invalid Luhn NPI `"1234567890"` → `INVALID_NPI` finding
  - [x] Test non-10-digit NPI → `INVALID_NPI_FORMAT` finding
  - [x] Test non-numeric NPI → `INVALID_NPI_FORMAT` finding
  - [x] Test None billing_provider_npi → no NPI findings (CompletenessValidator handles required check)
  - [x] Test empty string billing_provider_npi → no NPI findings
  - [x] Test rendering_provider_npi validated when present
  - [x] Test rendering_provider_npi None → no findings
  - [x] Test line-level rendering_provider_npi validated with correct `line_number`
  - [x] Test both billing and rendering NPIs invalid → two separate findings with distinct `field_name`
  - [x] Test no PHI in messages (NPI value not in message or suggestion)
  - [x] Test severity is always `ERROR`
  - [x] Test suggestion contains npiregistry.cms.hhs.gov URL
  - [x] Test validator statelessness
  - [x] Test Luhn helper directly: known valid/invalid values
- [x] Task 4: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `NPIValidator` re-export
- [x] Task 5: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors (30 source files)
  - [x] `uv run pytest` — all 224 tests pass (193 existing + 31 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.2)

- CompletenessValidator established the pattern: module-level constants, class with `name`, `validate()` building findings list, `self._make_output(findings)`
- Test pattern: helper `_complete_claim_dict()` returning baseline valid claim, class-based tests with `setup_method`, `pytest.mark.parametrize` for field variations
- Line iteration: `for idx, line in enumerate(claim.lines, start=1)` — line_number is 1-indexed
- Empty/whitespace strings handled via `not value or (isinstance(value, str) and not value.strip())`
- 193 tests passing, ruff/mypy clean
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `test_rule_based/` directory and `__init__.py` already exist

### NPI Fields in ClaimData

| Field | Location | Type | Required? |
|---|---|---|---|
| `billing_provider_npi` | `ClaimData` (claim-level) | `str \| None = None` | Yes (CompletenessValidator) |
| `rendering_provider_npi` | `ClaimData` (claim-level) | `str \| None = None` | No (optional) |
| `rendering_provider_npi` | `ClaimLineData` (line-level) | `str \| None = None` | No (optional) |

**Validation scope:** NPIValidator checks all three NPI fields. If a field is None or empty, skip it (no finding). CompletenessValidator already checks required-ness of `billing_provider_npi`.

### NPI Luhn Algorithm

The NPI uses a modified Luhn check-digit with a healthcare prefix:

1. Take the 10-digit NPI string
2. Prepend `"80840"` to get a 15-digit string (80840 is the health industry identifier)
3. Apply standard Luhn mod-10 algorithm on the full 15 digits:
   - Starting from the rightmost digit, double every second digit
   - If doubled value > 9, subtract 9
   - Sum all digits
   - Valid if sum % 10 == 0

```python
def _check_luhn_npi(npi: str) -> bool:
    """Validate NPI using Luhn algorithm with healthcare prefix."""
    prefixed = "80840" + npi
    total = 0
    for i, ch in enumerate(reversed(prefixed)):
        digit = int(ch)
        if i % 2 == 1:  # Double every second digit from right
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
```

**Known test values:**
- `"1234567893"` → valid (Luhn passes) — used throughout test suite
- `"1234567890"` → invalid (Luhn fails)
- `"1234567891"` → invalid (Luhn fails)
- `"0000000000"` → valid format but check Luhn
- `"123456789"` → invalid format (9 digits)
- `"12345678901"` → invalid format (11 digits)
- `"123456789A"` → invalid format (non-numeric)

### Finding Codes

| Code | Meaning | Severity |
|---|---|---|
| `INVALID_NPI_FORMAT` | NPI is not exactly 10 numeric digits | `ERROR` |
| `INVALID_NPI` | NPI fails Luhn check-digit validation | `ERROR` |

### Implementation Spec

```python
# src/claim_validator/validators/rule_based/npi.py
from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_NPI_REGISTRY_URL = "https://npiregistry.cms.hhs.gov"


def _check_luhn_npi(npi: str) -> bool:
    """Validate NPI using Luhn algorithm with '80840' healthcare prefix."""
    try:
        prefixed = "80840" + npi
        total = 0
        for i, ch in enumerate(reversed(prefixed)):
            digit = int(ch)
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
    except (ValueError, TypeError):
        return False


class NPIValidator(BaseValidator):
    """Validates NPI numbers using the Luhn check-digit algorithm."""

    name = "NPIValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        # Claim-level NPIs
        self._check_npi(claim.billing_provider_npi, "billing_provider_npi", None, findings)
        self._check_npi(claim.rendering_provider_npi, "rendering_provider_npi", None, findings)

        # Line-level rendering NPI
        for idx, line in enumerate(claim.lines, start=1):
            self._check_npi(line.rendering_provider_npi, "rendering_provider_npi", idx, findings)

        return self._make_output(findings)

    def _check_npi(
        self,
        value: str | None,
        field_name: str,
        line_number: int | None,
        findings: list[Finding],
    ) -> None:
        """Validate a single NPI value. Skip None/empty (handled by CompletenessValidator)."""
        if not value or not value.strip():
            return

        npi = value.strip()

        # Format check: exactly 10 numeric digits
        if len(npi) != 10 or not npi.isdigit():
            findings.append(
                self._make_finding(
                    code="INVALID_NPI_FORMAT",
                    message=f"NPI in '{field_name}' must be exactly 10 numeric digits",
                    severity=Severity.ERROR,
                    field_name=field_name,
                    line_number=line_number,
                    suggestion=f"Verify the NPI format at {_NPI_REGISTRY_URL}",
                )
            )
            return  # Skip Luhn check if format is wrong

        # Luhn check
        if not _check_luhn_npi(npi):
            findings.append(
                self._make_finding(
                    code="INVALID_NPI",
                    message=f"NPI in '{field_name}' fails Luhn check-digit validation",
                    severity=Severity.ERROR,
                    field_name=field_name,
                    line_number=line_number,
                    suggestion=f"Verify the NPI at {_NPI_REGISTRY_URL}",
                )
            )
```

**Key design decisions:**
- `_check_npi()` private method avoids code duplication across 3 NPI fields
- Format check runs before Luhn check — skip Luhn if format is wrong (avoid confusing dual error)
- None/empty fields silently skipped — CompletenessValidator handles required field presence
- Messages reference `field_name` not the actual NPI value (no PHI)
- `_check_luhn_npi()` is a module-level function, not a method — makes it easy to test directly

### Anti-Patterns to Avoid

- **DO NOT** include the NPI value in finding messages — that's PHI
- **DO NOT** validate NPIs that are None or empty — CompletenessValidator handles that
- **DO NOT** make network calls to NPPES registry — rule-based validators are offline only
- **DO NOT** store state between validate() calls
- **DO NOT** use a different Luhn algorithm — NPI requires the "80840" prefix specifically
- **DO NOT** produce both FORMAT and LUHN findings for the same NPI — if format is wrong, skip Luhn

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR8** | Validate NPI via Luhn check-digit |
| **NFR1** | Rule-based latency < 50ms — Luhn is O(1), no I/O |
| **NFR8** | Zero network calls for rule-based |
| **NFR10** | No PHI in outputs — NPI values never in messages |
| **NFR15** | Stateless validation |
| **D10** | Dotted path: `claim_validator.validators.rule_based.npi.NPIValidator` |

### conf.py Default Validators

`NPIValidator` is already listed in `DEFAULT_RULE_VALIDATORS` in `conf.py`:
```python
"claim_validator.validators.rule_based.npi.NPIValidator",
```
No configuration changes needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR8] — NPI Luhn check-digit validation
- [Source: CMS NPI Final Rule] — 45 CFR 162.406, Luhn formula with "80840" prefix
- [Source: ISO/IEC 7812] — Luhn algorithm standard

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References
- RED phase: Tests written first, confirmed ImportError (module not yet created)
- GREEN phase: Implementation created, 30/31 tests passed initially
- Fix: Test value `"1730182885"` was incorrectly assumed valid — Luhn sum mod 10 = 3, replaced with verified valid NPI `"1306849450"`
- Removed unused `pytest` import flagged by ruff
- Final: 224 tests pass, ruff clean, mypy clean (30 source files)

### Completion Notes List
- All 5 acceptance criteria satisfied
- 31 new tests across 5 test classes: TestCheckLuhnNPI (7), TestNPIValidatorClaimLevel (12), TestNPIValidatorLineLevel (5), TestNPIValidatorFindings (4), TestNPIValidatorStatelessness (3)
- Implementation follows established BaseValidator pattern from Story 2.1/2.2
- Format check short-circuits before Luhn check (no dual findings)
- No PHI in any finding messages or suggestions
- Stateless validation confirmed

### File List
- `src/claim_validator/validators/rule_based/npi.py` — NEW: NPIValidator + _check_luhn_npi helper
- `src/claim_validator/validators/rule_based/__init__.py` — MODIFIED: Added NPIValidator re-export
- `tests/test_validators/test_rule_based/test_npi.py` — NEW: 31 tests for NPIValidator

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 224 tests pass, ruff/mypy clean |
