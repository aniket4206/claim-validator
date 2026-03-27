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
import os
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
)

# ── Authentication ─────────────────────────────────────────────
_AUTH_SECRET = secrets.token_hex(32)
_TOKEN_EXPIRY = 86400 * 7  # 7 days

# Default users (username -> {password_hash, role, display_name})
_USERS: dict[str, dict[str, str]] = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "Administrator",
        "display_name": "Dr. Sarah Portal",
        "email": "jyoti.varade@thinkitive.com",
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


# ── Clearinghouse Providers ───────────────────────────────────

_PROVIDER_META = {
    "stedi": {
        "name": "Stedi",
        "label": "Stedi Healthcare API",
        "supports": ["eligibility", "claims", "claim_status"],
        "fields": [
            {"key": "api_key", "label": "API Key", "required": True, "secret": True},
        ],
        "test_url": "https://healthcare.us.stedi.com/2024-04-01",
    },
    "waystar": {
        "name": "Waystar",
        "label": "Waystar / Zirmed",
        "supports": ["eligibility", "prior_auth", "claim_status"],
        "fields": [
            {"key": "api_key", "label": "API Key (HMAC)", "required": True, "secret": True},
            {"key": "user_id", "label": "User ID", "required": True, "secret": False},
            {"key": "password", "label": "Password", "required": True, "secret": True},
            {"key": "cust_id", "label": "Customer ID", "required": True, "secret": False},
            {"key": "eligibility_base_url", "label": "Eligibility URL", "required": False, "secret": False, "placeholder": "https://eligibilityapi.zirmed.com"},
            {"key": "prior_auth_base_url", "label": "Prior Auth URL", "required": False, "secret": False, "placeholder": "https://priorauthorizationapi.waystar.com"},
            {"key": "base_url", "label": "Claims API URL", "required": False, "secret": False, "placeholder": "https://claimsapi.zirmed.com"},
        ],
        "test_url": "https://eligibilityapi.zirmed.com",
    },
    "claimmd": {
        "name": "ClaimMD",
        "label": "Claim.MD",
        "supports": ["eligibility", "claims", "claim_status"],
        "fields": [
            {"key": "api_key", "label": "Account Key", "required": True, "secret": True},
        ],
        "test_url": "https://svc.claim.md",
    },
}


def _provider_env_key(provider_id: str, field: str) -> str:
    """Map provider + field to env var name."""
    return f"CLEARINGHOUSE_{provider_id.upper()}_{field.upper()}"


def _get_provider_config(provider_id: str) -> dict[str, str]:
    """Read current config for a provider from env vars."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        return {}
    default_provider = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()
    cfg: dict[str, str] = {}
    for f in meta["fields"]:
        # Check provider-specific env var first, then fall back to generic
        val = os.getenv(_provider_env_key(provider_id, f["key"]), "")
        if not val and provider_id == default_provider:
            val = os.getenv(f"CLEARINGHOUSE_{f['key'].upper()}", "")
        cfg[f["key"]] = val
    return cfg


@app.get("/api/v1/providers")
def list_providers() -> list[dict[str, Any]]:
    """List available clearinghouse providers with config status and field definitions."""
    default = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()
    providers = []
    for key, meta in _PROVIDER_META.items():
        cfg = _get_provider_config(key)
        has_key = bool(cfg.get("api_key"))
        providers.append({
            "id": key,
            "name": meta["name"],
            "label": meta["label"],
            "supports": meta["supports"],
            "fields": meta["fields"],
            "configured": has_key,
            "is_default": key == default,
        })
    return providers


@app.get("/api/v1/providers/{provider_id}")
def get_provider(provider_id: str) -> dict[str, Any]:
    """Get config for a specific provider (secrets masked)."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    cfg = _get_provider_config(provider_id)
    default = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()
    # Mask secret fields
    masked: dict[str, str] = {}
    for f in meta["fields"]:
        val = cfg.get(f["key"], "")
        if f.get("secret") and val:
            masked[f["key"]] = val[:4] + "••••" + val[-4:] if len(val) > 8 else "••••••"
        else:
            masked[f["key"]] = val
    return {
        "id": provider_id,
        "name": meta["name"],
        "label": meta["label"],
        "supports": meta["supports"],
        "fields": meta["fields"],
        "config": masked,
        "configured": bool(cfg.get("api_key")),
        "is_default": provider_id == default,
    }


class ProviderConfigRequest(BaseModel):
    config: dict[str, str] = {}
    set_default: bool = False


@app.post("/api/v1/providers/{provider_id}/save")
def save_provider_config(provider_id: str, req: ProviderConfigRequest) -> dict[str, Any]:
    """Save provider config to env vars (runtime) and .env file."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")

    valid_keys = {f["key"] for f in meta["fields"]}
    for k, v in req.config.items():
        if k not in valid_keys:
            continue
        # Skip masked values (user didn't change them)
        if "••••" in v:
            continue
        env_key = _provider_env_key(provider_id, k)
        os.environ[env_key] = v

    if req.set_default:
        os.environ["CLEARINGHOUSE_PROVIDER"] = provider_id
        # Also set generic vars for backward compatibility
        cfg = _get_provider_config(provider_id)
        for k, v in cfg.items():
            if v:
                os.environ[f"CLEARINGHOUSE_{k.upper()}"] = v

    # Persist to .env file
    _persist_provider_env(provider_id, req.config, req.set_default)

    return {"status": "ok", "message": f"{meta['name']} configuration saved"}


def _persist_provider_env(provider_id: str, config: dict[str, str], set_default: bool) -> None:
    """Append/update provider env vars in the .env file."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    lines = env_path.read_text().splitlines()
    meta = _PROVIDER_META.get(provider_id, {})
    valid_keys = {f["key"] for f in meta.get("fields", [])}

    updates: dict[str, str] = {}
    for k, v in config.items():
        if k not in valid_keys or "••••" in v:
            continue
        env_key = _provider_env_key(provider_id, k)
        updates[env_key] = v

    if set_default:
        updates["CLEARINGHOUSE_PROVIDER"] = provider_id

    # Update existing lines or append
    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.lstrip("# ").split("=", 1)[0].strip()
        if stripped in updates:
            new_lines.append(f"{stripped}={updates[stripped]}")
            updated_keys.add(stripped)
        else:
            new_lines.append(line)

    # Append any keys not already in the file
    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines) + "\n")


@app.post("/api/v1/providers/{provider_id}/test")
def test_provider_connection(provider_id: str) -> dict[str, Any]:
    """Test connection to a clearinghouse provider using saved credentials."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")

    cfg = _get_provider_config(provider_id)
    if not cfg.get("api_key"):
        return {"status": "error", "message": "No API key configured. Save credentials first."}

    try:
        from claim_validator.clearinghouse.factory import get_clearinghouse_client

        client_config: dict[str, Any] = {"api_key": cfg["api_key"]}
        if provider_id == "waystar":
            client_config.update({
                k: v for k, v in {
                    "user_id": cfg.get("user_id", ""),
                    "password": cfg.get("password", ""),
                    "cust_id": cfg.get("cust_id", ""),
                    "base_url": cfg.get("base_url", ""),
                    "eligibility_base_url": cfg.get("eligibility_base_url", ""),
                    "prior_auth_base_url": cfg.get("prior_auth_base_url", ""),
                }.items() if v
            })
        elif provider_id == "claimmd":
            if cfg.get("base_url"):
                client_config["base_url"] = cfg["base_url"]

        client = get_clearinghouse_client(provider_id, **client_config)

        # Quick health check — try a dummy eligibility with known-bad data
        # If we get an auth error, credentials are wrong; if we get a data error, connection works
        import httpx
        test_url = meta.get("test_url", "")
        if provider_id == "stedi":
            resp = httpx.post(
                f"{test_url}/change/medicalnetwork/eligibility/v3",
                headers={"Authorization": f"Key {cfg['api_key']}", "Content-Type": "application/json"},
                json={"tradingPartnerServiceId": "TEST", "provider": {"npi": "0000000000"}, "subscriber": {"memberId": "TEST"}},
                timeout=15.0,
            )
            if resp.status_code == 401:
                return {"status": "error", "message": "Authentication failed — invalid API key"}
            return {"status": "ok", "message": f"Connected to Stedi (HTTP {resp.status_code})"}

        elif provider_id == "waystar":
            resp = httpx.post(
                f"{cfg.get('eligibility_base_url', 'https://eligibilityapi.zirmed.com')}/1.0/Rest/Gateway/GatewayAsync.ashx",
                data={
                    "UserID": cfg.get("user_id", ""),
                    "Password": cfg.get("password", ""),
                    "CustID": cfg.get("cust_id", ""),
                    "DataFormat": "X12",
                    "ResponseType": "FullJSON",
                    "InputData": "TEST",
                },
                timeout=15.0,
            )
            body = resp.text.lower()
            if "unauthorized" in body or resp.status_code == 401:
                return {"status": "error", "message": "Authentication failed — check User ID/Password"}
            return {"status": "ok", "message": f"Connected to Waystar (HTTP {resp.status_code})"}

        elif provider_id == "claimmd":
            resp = httpx.post(
                f"{cfg.get('base_url', 'https://svc.claim.md')}/services/eligdata/",
                data={"AccountKey": cfg["api_key"], "ResponseType": "json", "PayerID": "TEST"},
                timeout=15.0,
            )
            if resp.status_code == 401 or "invalid account" in resp.text.lower():
                return {"status": "error", "message": "Authentication failed — invalid Account Key"}
            return {"status": "ok", "message": f"Connected to Claim.MD (HTTP {resp.status_code})"}

        return {"status": "ok", "message": "Client created successfully"}

    except Exception as exc:
        return {"status": "error", "message": f"Connection failed: {exc}"}


@app.post("/api/v1/providers/{provider_id}/set-default")
def set_default_provider(provider_id: str) -> dict[str, Any]:
    """Set a provider as the default clearinghouse."""
    meta = _PROVIDER_META.get(provider_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    os.environ["CLEARINGHOUSE_PROVIDER"] = provider_id
    # Also copy provider-specific vars to generic vars for backward compat
    cfg = _get_provider_config(provider_id)
    for k, v in cfg.items():
        if v:
            os.environ[f"CLEARINGHOUSE_{k.upper()}"] = v
    _persist_provider_env(provider_id, {}, True)
    return {"status": "ok", "message": f"{meta['name']} set as default"}


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


# ── Appointment & Automation Endpoints ────────────────────────

from claim_validator.automation_agent import (
    create_appointment,
    run_automation_agent,
    get_agent_status,
    get_appointments,
)


@app.post("/api/v1/appointments")
def create_appointment_endpoint(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new appointment. Auto-runs eligibility if data is complete.

    Called by:
      - EHR webhook (FHIR Subscription)
      - Manual creation from UI
      - CSV import
    """
    return create_appointment(data)


@app.get("/api/v1/appointments")
def list_appointments(date: str = "all") -> list[dict[str, Any]]:
    """List appointments. Filter: today, tomorrow, week, all."""
    return get_appointments(date_filter=date)


@app.post("/api/v1/appointments/run-agent")
def run_agent_endpoint(trigger: str = "manual") -> dict[str, Any]:
    """Run the automation agent for all upcoming appointments.

    This is the "Run Agent Now" button. It:
      1. Finds all appointments for today + tomorrow
      2. Runs eligibility checks for unchecked ones
      3. Re-checks stale ones (>24hrs old)
      4. Auto-submits PA for flagged appointments
    """
    return run_automation_agent(trigger=trigger)


@app.get("/api/v1/appointments/agent-status")
def agent_status_endpoint() -> dict[str, Any]:
    """Get the last agent run status."""
    status = get_agent_status()
    if not status:
        return {"status": "never_run", "message": "Agent has not been run yet."}
    return status


@app.post("/api/v1/webhooks/ehr/appointment")
def ehr_appointment_webhook(data: dict[str, Any]) -> dict[str, Any]:
    """Webhook endpoint for EHR systems to notify of new/updated appointments.

    Supports:
      - FHIR R4 Appointment resource
      - Custom JSON format
      - HL7 ADT/SIU parsed payload

    The EHR sends appointment data here, and we auto-create the appointment
    + run eligibility immediately.
    """
    # Detect FHIR format
    if data.get("resourceType") == "Appointment":
        appt_data = _parse_fhir_appointment(data)
    else:
        appt_data = data

    appt_data["ehr_source"] = data.get("ehr_source", "webhook")
    appt_data["auto_check"] = True
    return create_appointment(appt_data)


def _parse_fhir_appointment(fhir_data: dict[str, Any]) -> dict[str, Any]:
    """Parse FHIR R4 Appointment resource into our format.

    FHIR Appointment has: status, start, end, participant[], serviceType[], etc.
    """
    result: dict[str, Any] = {
        "ehr_source": "fhir",
        "ehr_appointment_id": fhir_data.get("id", ""),
    }

    # Parse start date/time
    start = fhir_data.get("start", "")
    if start:
        result["appointment_date"] = start[:10]  # YYYY-MM-DD
        result["appointment_time"] = start[11:16] if len(start) > 11 else ""

    # Parse participants (patient, practitioner)
    for participant in fhir_data.get("participant", []):
        actor = participant.get("actor", {})
        ref = actor.get("reference", "")
        display = actor.get("display", "")

        if "Patient/" in ref:
            # Parse patient name
            parts = display.split(",") if "," in display else display.split()
            if len(parts) >= 2:
                result["patient_last_name"] = parts[0].strip()
                result["patient_first_name"] = parts[1].strip()
            else:
                result["patient_first_name"] = display
                result["patient_last_name"] = ""

        elif "Practitioner/" in ref:
            result["provider_name"] = display

    # Parse service type
    for st in fhir_data.get("serviceType", []):
        for coding in st.get("coding", []):
            result["service_type_code"] = coding.get("code", "30")
            result["appointment_type"] = coding.get("display", "")

    return result


@app.post("/api/v1/ehr/sync")
def ehr_sync_endpoint(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Trigger EHR sync — pull appointments from connected EHR.

    If no config provided, uses saved EHR settings from env.
    This is what the "Run Now" button on EHR Sync page calls.
    """
    from claim_validator.ehr_adapter import sync_ehr_appointments

    if not config:
        # Load from saved EHR config (env vars or DB)
        config = {
            "ehr_type": os.getenv("EHR_TYPE", "fhir"),
            "ehr_name": os.getenv("EHR_NAME", "fhir"),
            "fhir_base_url": os.getenv("EHR_FHIR_BASE_URL", ""),
            "client_id": os.getenv("EHR_CLIENT_ID", ""),
            "client_secret": os.getenv("EHR_CLIENT_SECRET", ""),
            "tenant_id": os.getenv("EHR_TENANT_ID", ""),
            "token_url": os.getenv("EHR_TOKEN_URL", ""),
            "scopes": os.getenv("EHR_SCOPES", "patient/*.read appointment.read coverage.read"),
        }

    if not config.get("fhir_base_url") and not config.get("base_url"):
        return {"status": "error", "message": "No EHR configured. Set up EHR connection on the EHR Sync page."}

    return sync_ehr_appointments(config)


@app.post("/api/v1/ehr/test-connection")
def ehr_test_connection(config: dict[str, Any]) -> dict[str, Any]:
    """Test EHR connection with provided credentials."""
    from claim_validator.ehr_adapter import get_ehr_adapter
    adapter = get_ehr_adapter(config)
    try:
        return adapter.test_connection()
    finally:
        adapter.close()


@app.get("/api/v1/stats")
def get_dashboard_stats() -> dict[str, Any]:
    """Return aggregated stats for dashboard, morning brief, reports, and appointments."""
    from claim_validator.db.session import SessionLocal
    from claim_validator.db.models import EligibilityCheck, PriorAuthCheck, Appointment, AgentRun
    from sqlalchemy import func
    from datetime import datetime, timedelta, UTC

    db = SessionLocal()
    try:
        # ── Eligibility checks ──
        all_checks = db.query(EligibilityCheck).order_by(EligibilityCheck.id.desc()).limit(200).all()
        total_checks = len(all_checks)
        eligible_count = sum(1 for c in all_checks if c.status == "eligible")
        inactive_count = sum(1 for c in all_checks if c.status == "inactive")
        error_count = sum(1 for c in all_checks if c.status == "error")
        pa_required_count = sum(1 for c in all_checks if c.prior_auth_required)
        avg_time = round(sum(c.execution_time or 0 for c in all_checks) / max(total_checks, 1), 1)
        elig_rate = round(eligible_count / max(total_checks, 1) * 100, 1)

        # Recent checks with full financial data (for morning brief)
        recent_checks = []
        for c in all_checks[:50]:
            recent_checks.append({
                "check_id": c.check_id,
                "patient_name": c.patient_name,
                "patient_first_name": c.patient_first_name,
                "patient_last_name": c.patient_last_name,
                "payer_name": c.payer_name,
                "payer_id": c.payer_id,
                "provider_npi": c.provider_npi,
                "provider_name": c.provider_name,
                "status": c.status,
                "source": c.source,
                "prior_auth_required": c.prior_auth_required,
                "copay": c.copay,
                "annual_deductible": c.annual_deductible,
                "annual_deductible_max": c.annual_deductible_max,
                "out_of_pocket": c.out_of_pocket,
                "out_of_pocket_max": c.out_of_pocket_max,
                "plan_name": c.plan_name,
                "carrier_name": c.carrier_name,
                "coverage_status": c.coverage_status,
                "subscriber_name": c.subscriber_name,
                "execution_time": c.execution_time,
                "run_date": c.run_date,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

        # ── PA checks ──
        all_pa = db.query(PriorAuthCheck).order_by(PriorAuthCheck.id.desc()).limit(100).all()
        pa_total = len(all_pa)
        pa_approved = sum(1 for p in all_pa if p.status == "approved")
        pa_denied = sum(1 for p in all_pa if p.status == "denied")
        pa_pending = sum(1 for p in all_pa if p.status in ("pending", "submitted"))
        pa_error = sum(1 for p in all_pa if p.status == "error")

        pa_checks = []
        for p in all_pa[:50]:
            pa_checks.append({
                "pa_id": p.pa_id,
                "patient_name": p.patient_name,
                "payer_name": p.payer_name,
                "payer_id": p.payer_id,
                "provider_name": p.provider_name,
                "status": p.status,
                "auth_number": p.auth_number,
                "reference_id": p.reference_id,
                "status_message": p.status_message,
                "diagnosis_code": p.diagnosis_code,
                "procedure_code": p.procedure_code,
                "service_type_code": p.service_type_code,
                "execution_time": p.execution_time,
                "run_date": p.run_date,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        # ── Denial/error analysis from findings ──
        denial_reasons = {}
        for c in all_checks:
            if c.findings and isinstance(c.findings, list):
                for f in c.findings:
                    if isinstance(f, dict) and f.get("severity") == "error":
                        code = f.get("code", "UNKNOWN")
                        denial_reasons[code] = denial_reasons.get(code, 0) + 1

        # Sort by count
        top_denials = sorted(denial_reasons.items(), key=lambda x: -x[1])[:10]

        # ── Payer breakdown ──
        payer_stats = {}
        for c in all_checks:
            payer = c.payer_name or c.payer_id or "Unknown"
            if payer not in payer_stats:
                payer_stats[payer] = {"total": 0, "eligible": 0, "inactive": 0, "error": 0, "pa_required": 0}
            payer_stats[payer]["total"] += 1
            if c.status == "eligible":
                payer_stats[payer]["eligible"] += 1
            elif c.status == "inactive":
                payer_stats[payer]["inactive"] += 1
            elif c.status == "error":
                payer_stats[payer]["error"] += 1
            if c.prior_auth_required:
                payer_stats[payer]["pa_required"] += 1

        return {
            "eligibility": {
                "total": total_checks,
                "eligible": eligible_count,
                "inactive": inactive_count,
                "error": error_count,
                "pa_required": pa_required_count,
                "avg_time": avg_time,
                "elig_rate": elig_rate,
            },
            "prior_auth": {
                "total": pa_total,
                "approved": pa_approved,
                "denied": pa_denied,
                "pending": pa_pending,
                "error": pa_error,
            },
            "recent_checks": recent_checks,
            "pa_checks": pa_checks,
            "top_denials": [{"code": code, "count": count} for code, count in top_denials],
            "payer_stats": payer_stats,
            "appointments": _get_appointments_summary(db),
            "agent_status": _get_agent_status_summary(db),
        }
    finally:
        db.close()


def _get_appointments_summary(db) -> dict[str, Any]:
    """Get appointment counts and recent appointments for stats."""
    from claim_validator.db.models import Appointment
    from datetime import datetime, timedelta, UTC

    today = datetime.now(UTC).date().isoformat()
    tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
    week_end = (datetime.now(UTC).date() + timedelta(days=7)).isoformat()

    all_appts = db.query(Appointment).filter(
        Appointment.appointment_date >= today,
        Appointment.appointment_date <= week_end,
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    today_appts = [a for a in all_appts if a.appointment_date == today]
    tomorrow_appts = [a for a in all_appts if a.appointment_date == tomorrow]

    return {
        "today_count": len(today_appts),
        "tomorrow_count": len(tomorrow_appts),
        "week_count": len(all_appts),
        "today": [a.to_dict() for a in today_appts],
        "tomorrow": [a.to_dict() for a in tomorrow_appts],
        "week": [a.to_dict() for a in all_appts],
        "stats": {
            "eligible": sum(1 for a in all_appts if a.eligibility_status == "eligible"),
            "inactive": sum(1 for a in all_appts if a.eligibility_status == "inactive"),
            "pa_required": sum(1 for a in all_appts if a.status == "pa_required"),
            "action_needed": sum(1 for a in all_appts if a.status == "action_needed"),
            "cleared": sum(1 for a in all_appts if a.status == "cleared"),
            "unchecked": sum(1 for a in all_appts if not a.last_checked_at),
        },
    }


def _get_agent_status_summary(db) -> dict[str, Any] | None:
    """Get the latest agent run info."""
    from claim_validator.db.models import AgentRun
    run = db.query(AgentRun).order_by(AgentRun.id.desc()).first()
    return run.to_dict() if run else None


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
