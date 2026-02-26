---
project_name: 'healthcare-claim-analyzer'
user_name: 'aniket'
date: '2026-02-17'
sections_completed: ['technology_stack']
existing_patterns_found: 47
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Python**: 3.11+ (target-version in ruff)
- **Django**: 5.2.11 (constraint: >=4.2,<6.0)
- **DRF**: 3.16.1
- **Celery**: 5.6.2 (Redis broker, django-db result backend)
- **Anthropic SDK**: 0.79.0
- **httpx**: 0.28.1 (ClaimMD client)
- **django-encrypted-model-fields**: 0.6.5 (PHI at rest)
- **django-filter**: 25.2
- **django-auditlog**: 3.4.1
- **django-environ**: 0.12.1
- **pydantic**: 2.12.5
- **mcp**: 1.26.0 (Model Context Protocol server)
- **psycopg2-binary**: 2.9 (PostgreSQL)
- **factory-boy**: >=3.3 (test factories)
- **pytest**: >=8.0, **pytest-django**: >=4.7
- **ruff**: >=0.2 (lint + format), **mypy**: >=1.8 (django-stubs)

## Critical Implementation Rules

### HIPAA / PHI — NEVER Violate

- **NEVER** send raw PHI to any external API — always deidentify first via `ClaimDeidentifier`
- **NEVER** log patient names, SSNs, member IDs, or DOBs
- All PHI model fields **MUST** use `EncryptedCharField` from django-encrypted-model-fields
- `PHIFilterMiddleware` scrubs SSN/DOB patterns from exception messages
- `AuditLog` entries are **immutable** — raises `ValueError` on save if pk exists
- Production enforces 15-minute session timeout (`SESSION_COOKIE_AGE = 900`)
- Production middleware includes `PHIAuditMiddleware` + `PHIFilterMiddleware`

### Service Layer Pattern — Strict

- **Views are thin dispatchers.** Business logic lives in `claim_analyzer/services/`
- **NEVER** put business logic in views or models
- Services are single-responsibility: one service per domain (`ValidationService`, `SubmissionService`, `AIService`, etc.)

### Validation Pipeline Architecture

- **Two-phase execution**: rule-based validators run first, AI validators run second
- AI validators **skipped** if rule-based fails (configurable via `skip_ai_on_rule_failure`)
- Validators are **stateless** — `BaseValidator.validate(claim) -> ValidatorOutput` must NOT modify the claim
- `ValidatorOutput` contains `Finding` objects: `code`, `message`, `severity`, `field_name`, `suggestion`, `context`
- `ValidatorRegistry` loads validators **lazily by dotted path** from settings
- `ValidationPipeline.run(claim) -> PipelineResult` aggregates all outputs
- `ValidationService` orchestrates: prefetch lines → build pipeline → run → persist results → update claim status

### Adding a New Validator

1. Subclass `BaseValidator` from `claim_analyzer/validators/base.py`
2. Implement `validate(claim) -> ValidatorOutput`
3. Use `self._make_output(findings)` to build output
4. Add dotted class path to `CLAIM_ANALYZER_VALIDATION_PIPELINE` (rule-based) or `CLAIM_ANALYZER_AI_VALIDATION_PIPELINE` (AI) in settings

### Model Patterns

- **ALL models** inherit `TimeStampedModel` (UUID pk via `uuid4`, `created_at`, `updated_at`)
- One model file per domain in `claim_analyzer/models/`, re-exported from `__init__.py`
- Status fields use Django `TextChoices` enums from `claim_analyzer/constants.py`
- Claim status lifecycle: `DRAFT → VALIDATING → VALIDATED/VALIDATION_FAILED → SUBMITTING → SUBMITTED → ACKNOWLEDGED → ACCEPTED/REJECTED/DENIED → PAID`
- PHI fields: `subscriber_id`, `subscriber_first_name`, `subscriber_last_name`, `subscriber_address_line`, `patient_first_name`, `patient_last_name` — all `EncryptedCharField`

### API Patterns

- DRF `ModelViewSet` with `@action` decorators for custom endpoints
- Async operations return `202 ACCEPTED` with `{"task_id": ..., "status": "queued"}`
- Nested serializers: `ClaimSerializer` includes `ClaimLineSerializer(many=True)`
- `ClaimDetailSerializer` extends `ClaimSerializer` with `latest_validation` field
- Filtering via `django_filters.FilterSet` on `ClaimFilter`
- Permissions: `HasPHIAccess` extends `IsAuthenticated` (currently permissive, production should enforce roles)
- Pagination: `PageNumberPagination` with `PAGE_SIZE = 50`

### Integration Patterns

- **ClaimMD**: `httpx.Client` with context manager support, built-in `RateLimiter` (thread-safe sliding window), exception hierarchy (`ClaimMDError → ClaimMDAuthError | ClaimMDRateLimitError`)
- **Claude**: `Anthropic` SDK wrapper, tool-use pattern with `PromptTemplates`, `parse_structured_response()` for output mapping
- **Deidentification**: `ClaimDeidentifier.deidentify(claim) -> dict` — converts DOB to age, dates to year-only, strips all 18 HIPAA identifiers

### Celery Task Patterns

- All tasks use `@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)`
- Retry with `max_retries=3`, `default_retry_delay=60` (validation) or `120` (submission)
- Beat schedule: polling every 5 min, analytics daily at 2am UTC
- Task naming: `{action}_{target}_task` (e.g., `validate_claim_task`)

### App Settings Pattern

- `ClaimAnalyzerSettings` in `claim_analyzer/conf.py` reads `CLAIM_ANALYZER_*` prefixed Django settings with defaults
- Access via: `from claim_analyzer.conf import app_settings`
- Settings split: `config/settings/{base,development,test,production}.py` using `django-environ`

### Testing Conventions

- `pytest-django` with `config.settings.test` (in-memory SQLite, eager Celery, fixed encryption key)
- Factory Boy: `ClaimFactory`, `ClaimLineFactory`, `ValidClaimFactory`, `InvalidNPIClaimFactory`
- Valid Luhn NPI: `1234567893`; invalid: `1234567890`
- Tests are `@pytest.mark.django_db` decorated classes with `setup_method`
- Test structure: `tests/test_{module}/test_{name}.py`
- Assertions: `result.passed`, `len(result.findings)`, `any(f.code == "..." for f in result.findings)`

### Code Style

- ruff: `line-length = 100`, target Python 3.11, rules `E, F, I, N, W, UP`
- Constants/enums in `claim_analyzer/constants.py` as Django `TextChoices`
- Naming: Models=`PascalCase`, validators=`{Name}Validator`, services=`{Name}Service`, tasks=`{action}_{target}_task`
- Private methods prefixed with `_`
- File naming: models=`{domain}.py`, services=`{domain}_service.py`, tests=`test_{module}.py`

### MCP Server

- Standalone stdio server in `mcp_server/`
- Tools: `validate_claim`, `check_eligibility`, `lookup_icd10`, `lookup_npi`, `analyze_rejection`, `get_rejection_stats`, `list_validators`
- Resources: `claim://schema`, `claim://validators`, `claim://rejection-codes`

### Environment Setup

- Copy `.env.example` → `.env`
- Rule-based validation works without API keys
- AI validation requires `CLAUDE_API_KEY`
- ClaimMD submission requires `CLAIMMD_ACCOUNT_KEY`
- `FIELD_ENCRYPTION_KEY` required — generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
