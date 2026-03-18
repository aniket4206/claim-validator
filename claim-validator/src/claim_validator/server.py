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

import hashlib
import hmac
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from claim_validator import __version__
from claim_validator._api import validate
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility_api import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    RecentCheckOut,
    get_check_result,
    get_recent_checks,
    run_eligibility_check,
    seed_demo_data,
)

# ── Authentication ─────────────────────────────────────────────
_AUTH_SECRET = secrets.token_hex(32)
_TOKEN_EXPIRY = 86400 * 7  # 7 days

# Default users (username -> {password_hash, role, display_name})
_USERS: dict[str, dict[str, str]] = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "Administrator",
        "display_name": "Dr. Portal",
    },
    "staff": {
        "password": hashlib.sha256("staff123".encode()).hexdigest(),
        "role": "Staff",
        "display_name": "Staff User",
    },
}

# Active tokens: token -> {username, role, display_name, expires}
_active_tokens: dict[str, dict[str, Any]] = {}


def _create_token(username: str) -> str:
    """Create a signed auth token."""
    token = secrets.token_urlsafe(48)
    user = _USERS[username]
    _active_tokens[token] = {
        "username": username,
        "role": user["role"],
        "display_name": user["display_name"],
        "expires": time.time() + _TOKEN_EXPIRY,
    }
    return token


def _verify_token(token: str) -> dict[str, Any] | None:
    """Verify and return token data, or None if invalid/expired."""
    data = _active_tokens.get(token)
    if not data:
        return None
    if time.time() > data["expires"]:
        _active_tokens.pop(token, None)
        return None
    return data


def _get_token_from_request(request: Request) -> str | None:
    """Extract token from Authorization header or cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get("auth_token")

# ── Static files path ────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"

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

# ── Database seed on startup ────────────────────────────────
@app.on_event("startup")
def on_startup():
    seed_demo_data()

# ── Auth middleware — protect all routes except login/static ──
_PUBLIC_PATHS = {"/login", "/api/v1/auth/login", "/api/v1/health", "/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public paths and static assets
    if path in _PUBLIC_PATHS or path.startswith("/static/"):
        return await call_next(request)

    # Check auth token
    token = _get_token_from_request(request)
    if not token or not _verify_token(token):
        # For API calls return 401, for page requests redirect to login
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
        return FileResponse(
            str(STATIC_DIR / "login.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    return await call_next(request)


# ── Serve static assets ──────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Auth Endpoints ───────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/login")
def serve_login():
    """Serve the login page."""
    return FileResponse(
        str(STATIC_DIR / "login.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.post("/api/v1/auth/login")
def auth_login(req: LoginRequest):
    """Authenticate user and return a token."""
    user = _USERS.get(req.username)
    pw_hash = hashlib.sha256(req.password.encode()).hexdigest()

    if not user or user["password"] != pw_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = _create_token(req.username)
    response = JSONResponse({
        "token": token,
        "user": {
            "username": req.username,
            "role": user["role"],
            "display_name": user["display_name"],
        },
    })
    # Set cookie so middleware can authenticate browser page navigations
    response.set_cookie(
        key="auth_token",
        value=token,
        max_age=_TOKEN_EXPIRY,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


@app.get("/api/v1/auth/me")
def auth_me(request: Request):
    """Return current user info from token."""
    token = _get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = _verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token expired")
    return {
        "username": data["username"],
        "role": data["role"],
        "display_name": data["display_name"],
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/v1/auth/change-password")
def auth_change_password(req: ChangePasswordRequest, request: Request):
    """Change the current user's password."""
    token = _get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    data = _verify_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="Token expired")

    username = data["username"]
    user = _USERS.get(username)
    cur_hash = hashlib.sha256(req.current_password.encode()).hexdigest()
    if not user or user["password"] != cur_hash:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user["password"] = hashlib.sha256(req.new_password.encode()).hexdigest()
    return {"status": "ok"}


@app.post("/api/v1/auth/logout")
def auth_logout(request: Request):
    """Invalidate the current token."""
    token = _get_token_from_request(request)
    if token:
        _active_tokens.pop(token, None)
    response = JSONResponse({"status": "ok"})
    response.delete_cookie("auth_token", path="/")
    return response


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


@app.get("/")
def serve_ui():
    """Serve the eligibility verification UI."""
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


# ── Lookup Data Endpoints ─────────────────────────────────────

import json as _json

_DATA_DIR = Path(__file__).parent / "eligibility" / "data"


@app.get("/api/v1/lookup/payers")
def lookup_payers(q: str = "", limit: int = 50) -> list[dict[str, str]]:
    """Search payers by name or ID. Returns [{id, name, type}]."""
    path = _DATA_DIR / "payer_directory.json"
    with open(path) as f:
        data: dict[str, Any] = _json.load(f)
    q_lower = q.lower()
    results = []
    for pid, info in data.items():
        name = info.get("name", "")
        if not q or q_lower in pid.lower() or q_lower in name.lower():
            results.append({"id": pid, "name": name, "type": info.get("type", "")})
            if len(results) >= limit:
                break
    return results


@app.get("/api/v1/lookup/service-types")
def lookup_service_types() -> list[dict[str, str]]:
    """Return all X12 service type codes."""
    path = _DATA_DIR / "service_types.json"
    with open(path) as f:
        data: dict[str, str] = _json.load(f)
    return [{"code": code, "name": name} for code, name in data.items()]


# ── Eligibility Check Endpoints ──────────────────────────────

@app.post("/api/v1/eligibility/check", response_model=EligibilityCheckResponse)
def eligibility_check(request: EligibilityCheckRequest) -> EligibilityCheckResponse:
    """Run an eligibility check with validation + clearinghouse call."""
    try:
        return run_eligibility_check(request)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/eligibility/checks", response_model=list[RecentCheckOut])
def list_eligibility_checks() -> list[RecentCheckOut]:
    """List recent eligibility checks."""
    return get_recent_checks()


@app.get("/api/v1/eligibility/checks/{check_id}")
def get_eligibility_check(check_id: str) -> dict[str, Any]:
    """Get full result for a specific eligibility check."""
    result = get_check_result(check_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Check not found")
    return result


# ── Prior Auth Endpoints ──────────────────────────────────────

from claim_validator.prior_auth_api import (
    PriorAuthRequest,
    PriorAuthResponse,
    submit_prior_auth,
    get_pa_result,
    get_recent_pa_checks,
)


@app.post("/api/v1/prior-auth/check", response_model=PriorAuthResponse)
def prior_auth_check(request: PriorAuthRequest) -> PriorAuthResponse:
    """Submit a prior authorization status inquiry."""
    try:
        return submit_prior_auth(request)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/v1/prior-auth/checks")
def list_pa_checks() -> list[dict[str, Any]]:
    """List recent PA checks."""
    return get_recent_pa_checks()


@app.get("/api/v1/prior-auth/checks/{pa_id}")
def get_pa_check(pa_id: str) -> dict[str, Any]:
    """Get full result for a PA check."""
    result = get_pa_result(pa_id)
    if result is None:
        raise HTTPException(status_code=404, detail="PA check not found")
    return result


@app.get("/api/v1/test-config")
def get_test_config() -> dict[str, Any]:
    """Return test environment configuration for pre-filling the UI form."""
    import os
    env = os.getenv("CLEARINGHOUSE_ENV", "production")
    return {
        "environment": env,
        "provider_npi": os.getenv("TEST_PROVIDER_NPI", ""),
        "provider_name": os.getenv("TEST_PROVIDER_NAME", ""),
        "payer_id": os.getenv("TEST_PAYER_ID", ""),
        "payer_name": os.getenv("TEST_PAYER_NAME", ""),
        "member_id": os.getenv("TEST_MEMBER_ID", ""),
        "patient_first": os.getenv("TEST_PATIENT_FIRST", ""),
        "patient_last": os.getenv("TEST_PATIENT_LAST", ""),
        "patient_dob": os.getenv("TEST_PATIENT_DOB", ""),
    }


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
