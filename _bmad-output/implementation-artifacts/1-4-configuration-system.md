# Story 1.4: Configuration System

Status: ready-for-dev

## Story

As a **developer**,
I want to configure the library via a settings object or environment variables,
so that I can customize validation behavior without modifying code.

## Acceptance Criteria

1. **Given** no explicit configuration, **When** I call `ClaimValidatorSettings()`, **Then** sensible defaults are used: all 8 rule-based validators enabled, AI disabled, `skip_ai_on_rule_failure=True`.

2. **Given** environment variables with `CLAIM_VALIDATOR_` prefix, **When** I construct `ClaimValidatorSettings()`, **Then** environment variables override default values (e.g., `CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE=false`).

3. **Given** explicit parameters, **When** I construct `ClaimValidatorSettings(rule_validators=[...], ai_validators=[...], ai_config={...})`, **Then** the settings object validates types and stores the configuration, and validator paths are stored as dotted path strings.

4. **Given** a `ClaimValidatorSettings` instance, **When** I inspect configurable fields, **Then** it includes `rule_validators` (list of dotted paths), `ai_validators` (list of dotted paths), `skip_ai_on_rule_failure` (bool), and `ai_config` (optional dict with provider, api_key, model).

5. **Given** invalid configuration values, **When** I construct `ClaimValidatorSettings(rule_validators="not-a-list")`, **Then** a `ConfigurationError` or Pydantic `ValidationError` is raised with a clear message.

## Tasks / Subtasks

- [ ] Task 1: Add `pydantic-settings` dependency (AC: all)
  - [ ] Add `pydantic-settings>=2.0,<3.0` to `dependencies` in `pyproject.toml`
  - [ ] Run `uv sync --all-extras` to install
- [ ] Task 2: Implement `ClaimValidatorSettings` in `conf.py` (AC: #1, #2, #3, #4)
  - [ ] Import from `pydantic_settings` (not `pydantic`)
  - [ ] Define settings with `SettingsConfigDict(env_prefix="CLAIM_VALIDATOR_")`
  - [ ] Define all fields with correct types and defaults
  - [ ] Default `rule_validators`: all 8 dotted paths
  - [ ] Default `ai_validators`: empty list
  - [ ] Default `skip_ai_on_rule_failure`: True
  - [ ] Default `ai_config`: None
- [ ] Task 3: Wire up re-exports (AC: all)
  - [ ] Add `ClaimValidatorSettings` to `claim_validator/__init__.py` imports and `__all__`
- [ ] Task 4: Write tests in `tests/test_conf.py` (AC: all)
  - [ ] Test default construction produces sensible defaults
  - [ ] Test env var override via monkeypatch
  - [ ] Test explicit parameter construction
  - [ ] Test invalid input raises validation error
  - [ ] Test all fields accessible and correctly typed
  - [ ] Test frozen/immutable behavior
- [ ] Task 5: Verify tooling
  - [ ] `uv run ruff check .` — zero warnings
  - [ ] `uv run mypy src/` — zero errors
  - [ ] `uv run pytest` — all tests pass

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/` — edit existing placeholder `src/claim_validator/conf.py`.

### Previous Story Intelligence (Stories 1.1-1.3)

- All models use `frozen=True`, `strict=False` via `ConfigDict` from pydantic
- Pattern: `from __future__ import annotations` at top of every file
- Constants in `constants.py`: `Severity` (ERROR/WARNING), `ClaimType` (PROFESSIONAL/INSTITUTIONAL)
- Exceptions in `exceptions.py`: `ClaimValidatorError` base, `ConfigurationError`, `ValidationError`, `LLMError`, `CodeTableError`
- Re-export pattern: subpackage `__init__.py` → top-level `__init__.py` with `__all__`
- 58 tests passing, ruff/mypy/pytest all green
- `pyproject.toml` currently has `dependencies = ["pydantic>=2.0,<3.0"]`
- uv requires PATH export: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`

### Critical: `pydantic-settings` Is a Separate Package

`BaseSettings` was **split out** of pydantic core into `pydantic-settings` in Pydantic v2. Current stable: **pydantic-settings 2.13.0** (Feb 2026).

- **Package**: `pydantic-settings` (NOT `pydantic`)
- **Import**: `from pydantic_settings import BaseSettings, SettingsConfigDict`
- **Dependency**: Add `"pydantic-settings>=2.0,<3.0"` to `dependencies` in `pyproject.toml`
- **NOT**: `from pydantic import BaseSettings` — this will `ImportError`

### Implementation Design

```python
# src/claim_validator/conf.py
from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default 8 rule-based validators (dotted paths)
DEFAULT_RULE_VALIDATORS: list[str] = [
    "claim_validator.validators.rule_based.completeness.CompletenessValidator",
    "claim_validator.validators.rule_based.npi.NPIValidator",
    "claim_validator.validators.rule_based.subscriber_id.SubscriberIDValidator",
    "claim_validator.validators.rule_based.demographics.DemographicsValidator",
    "claim_validator.validators.rule_based.coding.CodingValidator",
    "claim_validator.validators.rule_based.monetary.MonetaryValidator",
    "claim_validator.validators.rule_based.duplicate.DuplicateValidator",
    "claim_validator.validators.rule_based.timely_filing.TimelyFilingValidator",
]


class ClaimValidatorSettings(BaseSettings):
    """Configuration for the claim-validator library."""

    model_config = SettingsConfigDict(
        env_prefix="CLAIM_VALIDATOR_",
        frozen=True,
    )

    rule_validators: list[str] = DEFAULT_RULE_VALIDATORS
    ai_validators: list[str] = []
    skip_ai_on_rule_failure: bool = True
    ai_config: dict[str, Any] | None = None
```

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **BaseSettings vs BaseModel** | `BaseSettings` | Architecture D4 mandates env var support with `CLAIM_VALIDATOR_` prefix |
| **frozen=True** | Yes | Consistent with all other models (D3). Settings should be immutable once constructed |
| **ai_config type** | `dict[str, Any] \| None` | Architecture shows dict input. Future stories may add a typed `AIConfig` model, but for now dict matches the public API examples |
| **DEFAULT_RULE_VALIDATORS** | Module-level constant | Reusable reference, testable, avoids mutable default in class definition |
| **env_prefix** | `CLAIM_VALIDATOR_` | Architecture D4. Env vars: `CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE`, etc. |

### pyproject.toml Change

Update the `dependencies` line:

```toml
dependencies = ["pydantic>=2.0,<3.0", "pydantic-settings>=2.0,<3.0"]
```

### Environment Variable Mapping

| Env Var | Field | Type | Example |
|---|---|---|---|
| `CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE` | `skip_ai_on_rule_failure` | bool | `"false"` |
| `CLAIM_VALIDATOR_RULE_VALIDATORS` | `rule_validators` | JSON list | `'["my.Validator"]'` |
| `CLAIM_VALIDATOR_AI_VALIDATORS` | `ai_validators` | JSON list | `'["my.AIValidator"]'` |
| `CLAIM_VALIDATOR_AI_CONFIG` | `ai_config` | JSON dict | `'{"provider":"anthropic","api_key":"sk-..."}'` |

**Note**: Pydantic-settings parses JSON strings for complex types (list, dict) from env vars automatically.

### Re-Export Wiring

Add to `src/claim_validator/__init__.py`:

```python
from claim_validator.conf import ClaimValidatorSettings

# In __all__:
"ClaimValidatorSettings",
```

### Anti-Patterns to Avoid

- **DO NOT** import from `pydantic.BaseSettings` — it was removed in Pydantic v2; use `pydantic_settings`
- **DO NOT** use `class Config:` inner class — deprecated; use `model_config = SettingsConfigDict(...)` instead
- **DO NOT** validate dotted paths at settings construction time — that's the registry's job (Story 2.1). Settings just stores strings
- **DO NOT** add `env_file=".env"` — the library should not assume file system layout; consumers handle `.env` loading
- **DO NOT** create a nested `AIConfig` Pydantic model yet — keep it as `dict[str, Any] | None` per architecture. A typed model may come in Epic 3
- **DO NOT** add `extra="forbid"` — use default behavior (`extra="ignore"`) for forward compatibility

### Test Expectations (`tests/test_conf.py`)

```python
class TestClaimValidatorSettings:
    def test_defaults(self):
        settings = ClaimValidatorSettings()
        assert len(settings.rule_validators) == 8
        assert settings.ai_validators == []
        assert settings.skip_ai_on_rule_failure is True
        assert settings.ai_config is None

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE", "false")
        settings = ClaimValidatorSettings()
        assert settings.skip_ai_on_rule_failure is False

    def test_explicit_construction(self):
        settings = ClaimValidatorSettings(
            rule_validators=["my.Validator"],
            ai_config={"provider": "anthropic", "api_key": "sk-test", "model": "claude-sonnet-4-5-20241022"},
        )
        assert settings.rule_validators == ["my.Validator"]
        assert settings.ai_config["provider"] == "anthropic"

    def test_frozen(self):
        settings = ClaimValidatorSettings()
        with pytest.raises(ValidationError):
            settings.skip_ai_on_rule_failure = False

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            ClaimValidatorSettings(rule_validators="not-a-list")
```

### Architecture Compliance

| Decision | Requirement for This Story |
|---|---|
| **D4: Configuration** | Pydantic `BaseSettings` with `env_prefix="CLAIM_VALIDATOR_"` |
| **D3: Frozen models** | `frozen=True` on settings |
| **D13: Import/export** | Re-export `ClaimValidatorSettings` at top level |
| **Naming** | `ClaimValidatorSettings` — not `Config`, `Settings`, or `Preferences` |
| **FR43** | Pydantic settings object with env var support |
| **FR44** | Override validator lists, AI settings, pipeline behavior |
| **FR45** | Zero-config for basic rule-based validation (sensible defaults) |

### File Targets

| File | Action | Contents |
|---|---|---|
| `pyproject.toml` | Edit | Add `pydantic-settings` to dependencies |
| `src/claim_validator/conf.py` | Edit (exists, placeholder) | `ClaimValidatorSettings`, `DEFAULT_RULE_VALIDATORS` |
| `src/claim_validator/__init__.py` | Edit | Add `ClaimValidatorSettings` import and `__all__` entry |
| `tests/test_conf.py` | Create | All settings tests |

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions — D4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Format Patterns — Configuration Format]
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns — Settings naming]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4] — Full acceptance criteria
- [Source: pydantic-settings 2.13.0 docs] — BaseSettings, SettingsConfigDict, env_prefix

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
