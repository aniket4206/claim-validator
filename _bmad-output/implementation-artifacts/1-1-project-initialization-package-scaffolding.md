# Story 1.1: Project Initialization & Package Scaffolding

Status: ready-for-dev

## Story

As a **developer**,
I want to install `claim-validator` via pip into my Python 3.11+ project,
so that I can start using healthcare claim validation with zero friction.

## Acceptance Criteria

1. **Given** a Python 3.11+ environment with pip or uv, **When** I run `pip install claim-validator`, **Then** the package installs successfully with only Pydantic as a runtime dependency and `import claim_validator` completes in under 500ms.

2. **Given** the installed package, **When** I check for type support, **Then** a `py.typed` marker file exists and mypy/pyright recognize the package as typed.

3. **Given** a developer cloning the repository, **When** they run `uv sync --all-extras`, **Then** all dev dependencies (pytest, ruff, mypy, factory-boy) are installed, `uv run ruff check .` passes with zero warnings, and `uv run mypy src/` passes with zero errors.

4. **Given** the `pyproject.toml`, **When** I inspect optional extras, **Then** extras `[ai]`, `[anthropic]`, `[openai]`, `[dev]`, `[all]` are defined with correct dependencies, and the core package depends only on `pydantic>=2.0,<3.0`.

5. **Given** the project structure, **When** I inspect the repository, **Then** it uses src layout (`src/claim_validator/`), has MIT LICENSE, `.gitignore`, `.env.example`, and hatchling build backend with hatch-vcs versioning.

## Tasks / Subtasks

- [ ] Task 1: Initialize project with uv (AC: #5)
  - [ ] Run `uv init --lib --build-backend hatchling claim-validator`
  - [ ] Verify src layout created: `src/claim_validator/__init__.py` and `py.typed`
- [ ] Task 2: Configure pyproject.toml fully (AC: #1, #3, #4, #5)
  - [ ] Set project metadata (name, description, license=MIT, requires-python=">=3.11", classifiers)
  - [ ] Set single core dependency: `pydantic>=2.0,<3.0`
  - [ ] Define optional extras: `[ai]`, `[anthropic]`, `[openai]`, `[django]`, `[fastapi]`, `[dev]`, `[all]`
  - [ ] Configure hatch-vcs for git-tag versioning
  - [ ] Configure hatchling build to include `data/` directory as package data
  - [ ] Add `[tool.ruff]` config: line-length=100, target-version="py311", select=["E","F","I","N","W","UP"]
  - [ ] Add `[tool.mypy]` config: strict mode, Pydantic plugin
  - [ ] Add `[tool.pytest.ini_options]` config: testpaths=["tests"]
- [ ] Task 3: Create package skeleton files (AC: #2, #5)
  - [ ] Create `src/claim_validator/__init__.py` with version import and placeholder `__all__`
  - [ ] Create `src/claim_validator/_version.py` fallback (hatch-vcs generates at build)
  - [ ] Verify `src/claim_validator/py.typed` marker exists
  - [ ] Create directory stubs for all subpackages with empty `__init__.py` files
  - [ ] Create `src/claim_validator/data/` directory for future bundled tables
- [ ] Task 4: Create project root files (AC: #5)
  - [ ] Create MIT `LICENSE` file
  - [ ] Create `.gitignore` (Python, uv, IDE, .env patterns)
  - [ ] Create `.env.example` with documented `CLAIM_VALIDATOR_*` env vars
  - [ ] Create minimal `README.md` with project name and install command
  - [ ] Create `.pre-commit-config.yaml` with ruff check + ruff format hooks
- [ ] Task 5: Create test scaffolding (AC: #3)
  - [ ] Create `tests/` directory with `conftest.py`
  - [ ] Create `tests/test_import.py` — verify `import claim_validator` works and `__version__` exists
  - [ ] Create placeholder test directories mirroring source structure
- [ ] Task 6: Verify all tooling passes (AC: #1, #2, #3)
  - [ ] Run `uv sync --all-extras` — all deps install
  - [ ] Run `uv run ruff check .` — zero warnings
  - [ ] Run `uv run ruff format --check .` — already formatted
  - [ ] Run `uv run mypy src/` — zero errors
  - [ ] Run `uv run pytest` — import test passes
  - [ ] Run `uv run python -c "import claim_validator"` — completes successfully

## Dev Notes

### CRITICAL: This is a new standalone library, NOT modifications to the existing Django project

This story creates a **brand new Python library** called `claim-validator` that will eventually be extracted from the existing Django healthcare-claim-analyzer codebase. The new library:
- Lives in a new directory structure (`claim-validator/` or at project root as the new package)
- Has **zero Django dependencies** — pure Python + Pydantic
- Uses `uv` as package manager (not pip/poetry)
- Uses `hatchling` as build backend (not setuptools)
- Is distributed via PyPI as `claim-validator` with importable name `claim_validator`

### Project Structure to Create

```
claim-validator/                    # Project root (or subdirectory — confirm with user)
├── .github/
│   └── workflows/                  # Empty dir — CI/CD added in later stories
├── src/
│   └── claim_validator/
│       ├── __init__.py             # Re-exports ~15 key symbols (placeholder for now)
│       ├── py.typed                # PEP 561 marker (empty file)
│       ├── _version.py             # Fallback version; hatch-vcs overrides at build
│       ├── _api.py                 # Placeholder for validate() function
│       ├── conf.py                 # Placeholder for ClaimValidatorSettings
│       ├── constants.py            # Placeholder for Severity, ClaimType enums
│       ├── exceptions.py           # Placeholder for exception hierarchy
│       ├── models/
│       │   ├── __init__.py
│       │   ├── claim.py            # Placeholder
│       │   ├── results.py          # Placeholder
│       │   └── deidentified.py     # Placeholder
│       ├── validators/
│       │   ├── __init__.py
│       │   ├── base.py             # Placeholder
│       │   ├── registry.py         # Placeholder
│       │   ├── pipeline.py         # Placeholder
│       │   ├── rule_based/
│       │   │   └── __init__.py
│       │   └── ai/
│       │       └── __init__.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py             # Placeholder
│       │   ├── factory.py          # Placeholder
│       │   └── providers/
│       │       └── __init__.py
│       ├── deidentifier/
│       │   └── __init__.py
│       ├── code_tables/
│       │   └── __init__.py
│       └── data/                   # Empty dir for future bundled tables
│           └── .gitkeep
├── tests/
│   ├── conftest.py
│   ├── test_import.py              # Verify package imports correctly
│   ├── test_models/
│   │   └── __init__.py
│   ├── test_validators/
│   │   ├── __init__.py
│   │   ├── test_rule_based/
│   │   │   └── __init__.py
│   │   └── test_ai/
│   │       └── __init__.py
│   ├── test_llm/
│   │   └── __init__.py
│   ├── test_deidentifier/
│   │   └── __init__.py
│   ├── test_code_tables/
│   │   └── __init__.py
│   └── test_hipaa/
│       └── __init__.py
├── pyproject.toml
├── README.md
├── LICENSE                         # MIT
├── CHANGELOG.md
├── .gitignore
├── .pre-commit-config.yaml
└── .env.example
```

### pyproject.toml Exact Specification

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "claim-validator"
dynamic = ["version"]
description = "Open-source healthcare claim validation library with rule-based and AI-powered checks"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [{ name = "aniket" }]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]
dependencies = ["pydantic>=2.0,<3.0"]

[project.optional-dependencies]
ai = ["httpx>=0.27", "anthropic>=0.40", "openai>=1.50"]
anthropic = ["httpx>=0.27", "anthropic>=0.40"]
openai = ["httpx>=0.27", "openai>=1.50"]
django = ["django>=4.2"]
fastapi = ["fastapi>=0.110"]
dev = ["pytest>=8.0", "pytest-cov", "ruff>=0.5", "mypy>=1.10", "factory-boy>=3.3"]
all = ["claim-validator[ai,django,fastapi]"]

[project.urls]
Homepage = "https://github.com/aniket/claim-validator"
Documentation = "https://claim-validator.readthedocs.io"
Repository = "https://github.com/aniket/claim-validator"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/claim_validator/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/claim_validator"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "src"

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Architecture Compliance

| Decision | Requirement for This Story |
|---|---|
| **D12: Versioning** | hatch-vcs configured. `_version.py` auto-generated at build. Fallback `__version__ = "0.0.0.dev0"` in source |
| **D13: Import/export** | `__init__.py` with placeholder `__all__` list. Actual re-exports added as modules are implemented |
| **D3: Pydantic models** | Core dependency on `pydantic>=2.0,<3.0` in pyproject.toml |
| **D4: Configuration** | `pydantic-settings` NOT needed yet — added in Story 1.4 when `ClaimValidatorSettings` is implemented |

### Library & Framework Version Requirements

| Tool | Minimum Version | Latest (Feb 2026) | Notes |
|---|---|---|---|
| **Python** | 3.11 | 3.13 | CI matrix: 3.11, 3.12, 3.13 |
| **Pydantic** | >=2.0,<3.0 | 2.12.5 | Frozen models, lax coercion |
| **hatchling** | latest | 1.28.0 | Build backend |
| **hatch-vcs** | latest | 0.5.0 | Git tag versioning |
| **ruff** | >=0.5 | 0.15.1 | Note: 0.15.0 has 2026 style guide changes — lambda formatting |
| **mypy** | >=1.10 | 1.19.1 | Strict mode + pydantic plugin |
| **pytest** | >=8.0 | 9.0.2 | Native TOML config support in v9 |
| **uv** | latest | 0.10.4 | Package manager |

### Anti-Patterns to Avoid

- **DO NOT** add Django as a dependency — this is a standalone library
- **DO NOT** use setuptools or setup.py — hatchling only
- **DO NOT** create a `requirements.txt` — use pyproject.toml `[project.optional-dependencies]`
- **DO NOT** load code tables or heavy modules at import time — violates NFR7 (<500ms import)
- **DO NOT** put implementation code in placeholder files — only empty classes/functions with `pass` or `...`
- **DO NOT** add `pydantic-settings` yet — that's Story 1.4's concern. Core Pydantic is sufficient
- **DO NOT** create CI/CD workflows yet — those come in a later story

### File Structure Notes

- Uses **src layout** per PEP 517 — prevents import confusion during development
- `py.typed` is an empty marker file (PEP 561) — enables type checker discovery
- `_version.py` contains `__version__ = "0.0.0.dev0"` as fallback; hatch-vcs overwrites during build
- `data/` directory needs `.gitkeep` to be tracked in git (empty directories aren't tracked)
- All `__init__.py` files in subpackages start empty — re-exports added when modules are implemented

### .env.example Contents

```bash
# claim-validator configuration
# All settings use CLAIM_VALIDATOR_ prefix

# AI Provider Configuration (optional — rule-based works without these)
# CLAIM_VALIDATOR_AI_PROVIDER=anthropic
# CLAIM_VALIDATOR_AI_API_KEY=sk-ant-...
# CLAIM_VALIDATOR_AI_MODEL=claude-sonnet-4-5-20241022

# Pipeline Configuration
# CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE=true
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation] — uv init command, hatchling selection rationale
- [Source: _bmad-output/planning-artifacts/architecture.md#Package & Distribution] — D12 versioning, D13 import/export, optional extras spec
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns] — Complete source and test directory structure
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules] — Naming conventions, enforcement guidelines
- [Source: _bmad-output/planning-artifacts/prd.md#Installation Methods] — All extras definitions
- [Source: _bmad-output/planning-artifacts/prd.md#Developer Tool Specific Requirements] — Public API surface, migration guide
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1] — Full acceptance criteria

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
