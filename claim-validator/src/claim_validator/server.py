"""REST API server for claim-validator.

Start with:
    claim-validator serve
    claim-validator serve --port 8080 --host 127.0.0.1

Any language can call this over HTTP:
    curl -X POST http://localhost:8000/api/v1/validate \
        -H "Content-Type: application/json" \
        -d @claim.json

    Node.js:  fetch("http://localhost:8000/api/v1/validate", { method: "POST", body: JSON.stringify(claim) })
    Go:       http.Post("http://localhost:8000/api/v1/validate", "application/json", bytes.NewReader(body))
    Java:     HttpClient.newHttpClient().send(request, BodyHandlers.ofString())
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from claim_validator import __version__
from claim_validator._api import validate
from claim_validator.conf import ClaimValidatorSettings

# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title="claim-validator",
    description="Healthcare claim validation API — rule-based and AI-powered",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────


class DiagnosisCodeRequest(BaseModel):
    code: str
    pointer: int = 1
    type: str = "principal"


class ClaimLineRequest(BaseModel):
    procedure_code: str
    modifiers: list[str] = []
    diagnosis_pointers: list[int] = []
    charge_amount: float
    units: float = 1.0
    service_date_from: str | None = None
    service_date_to: str | None = None
    place_of_service: str | None = None
    rendering_provider_npi: str | None = None


class ClaimRequest(BaseModel):
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    rendering_provider_npi: str | None = None
    subscriber_id: str | None = None
    subscriber_first_name: str | None = None
    subscriber_last_name: str | None = None
    subscriber_dob: str | None = None
    subscriber_gender: str | None = None
    patient_first_name: str | None = None
    patient_last_name: str | None = None
    patient_dob: str | None = None
    patient_gender: str | None = None
    patient_relationship: str | None = None
    payer_id: str | None = None
    payer_name: str | None = None
    claim_type: str = "professional"
    place_of_service: str | None = None
    total_charge: float | None = None
    filing_date: str | None = None
    diagnosis_codes: list[DiagnosisCodeRequest] = []
    lines: list[ClaimLineRequest] = []


class AIConfigRequest(BaseModel):
    provider: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None


class ValidateRequest(BaseModel):
    claim: ClaimRequest
    ai_config: AIConfigRequest | None = None
    skip_ai_on_rule_failure: bool = True


class FindingResponse(BaseModel):
    code: str
    message: str
    severity: str
    field_name: str
    line_number: int | None = None
    suggestion: str = ""


class PhaseResponse(BaseModel):
    phase: str
    execution_time: float
    validators: list[dict[str, Any]]


class ValidateResponse(BaseModel):
    passed: bool
    execution_time: float
    total_findings: int
    total_errors: int
    total_warnings: int
    findings: list[FindingResponse]
    phases: list[PhaseResponse]


class HealthResponse(BaseModel):
    status: str
    version: str


class ValidatorsResponse(BaseModel):
    rule_based: list[str]
    ai: list[str]


# ── Endpoints ─────────────────────────────────────────────────


@app.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check."""
    return HealthResponse(status="ok", version=__version__)


@app.get("/api/v1/validators", response_model=ValidatorsResponse)
def list_validators() -> ValidatorsResponse:
    """List all configured validators."""
    settings = ClaimValidatorSettings()
    return ValidatorsResponse(
        rule_based=settings.rule_validators,
        ai=settings.ai_validators,
    )


@app.post("/api/v1/validate", response_model=ValidateResponse)
def validate_claim(request: ValidateRequest) -> ValidateResponse:
    """Validate a healthcare claim.

    Accepts a claim object and optional AI configuration.
    Returns structured validation results with findings.
    """
    claim_dict = request.claim.model_dump(exclude_none=True)

    settings_kwargs: dict[str, Any] = {
        "skip_ai_on_rule_failure": request.skip_ai_on_rule_failure,
    }

    ai_config: dict[str, Any] | None = None
    if request.ai_config:
        ai_config = {
            k: v
            for k, v in request.ai_config.model_dump().items()
            if v is not None
        }
        settings_kwargs["ai_validators"] = [
            "claim_validator.validators.ai.code_validation.CodeValidationAI",
            "claim_validator.validators.ai.coverage_check.CoverageCheckAI",
            "claim_validator.validators.ai.prior_auth.PriorAuthAI",
        ]

    settings = ClaimValidatorSettings(**settings_kwargs)

    try:
        result = validate(claim_dict, settings=settings, ai_config=ai_config)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ValidateResponse(
        passed=result.passed,
        execution_time=result.execution_time,
        total_findings=len(result.findings),
        total_errors=len(result.errors),
        total_warnings=len(result.warnings),
        findings=[
            FindingResponse(
                code=f.code,
                message=f.message,
                severity=f.severity.value,
                field_name=f.field_name,
                line_number=f.line_number,
                suggestion=f.suggestion,
            )
            for f in result.findings
        ],
        phases=[
            PhaseResponse(
                phase=p.phase,
                execution_time=p.execution_time,
                validators=[
                    {
                        "name": v.validator_name,
                        "findings_count": len(v.findings),
                    }
                    for v in p.validator_outputs
                ],
            )
            for p in result.phase_results
        ],
    )


@app.post("/api/v1/validate/quick")
def validate_quick(claim: ClaimRequest) -> ValidateResponse:
    """Quick validation — rule-based only, no AI config needed.

    Send a claim directly as the request body (no wrapper object).
    """
    claim_dict = claim.model_dump(exclude_none=True)

    try:
        result = validate(claim_dict)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ValidateResponse(
        passed=result.passed,
        execution_time=result.execution_time,
        total_findings=len(result.findings),
        total_errors=len(result.errors),
        total_warnings=len(result.warnings),
        findings=[
            FindingResponse(
                code=f.code,
                message=f.message,
                severity=f.severity.value,
                field_name=f.field_name,
                line_number=f.line_number,
                suggestion=f.suggestion,
            )
            for f in result.findings
        ],
        phases=[
            PhaseResponse(
                phase=p.phase,
                execution_time=p.execution_time,
                validators=[
                    {
                        "name": v.validator_name,
                        "findings_count": len(v.findings),
                    }
                    for v in p.validator_outputs
                ],
            )
            for p in result.phase_results
        ],
    )
