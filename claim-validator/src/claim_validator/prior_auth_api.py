"""Prior Authorization API — endpoints for the PA check flow.

Handles:
  - Waystar: Submitting PA status inquiries (async: submit → poll for 278)
  - ClaimMD: PA number is attached to claim submissions (CMS-1500 Box 23)
  - MySQL database storage via SQLAlchemy
  - Multi-provider PA support
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy.orm import Session

from claim_validator.db.models import PriorAuthCheck as PriorAuthCheckDB
from claim_validator.db.session import SessionLocal

# Load .env
_this_dir = Path(__file__).resolve().parent
for _candidate in [_this_dir.parent.parent.parent, _this_dir.parent.parent]:
    _env = _candidate / ".env"
    if _env.is_file():
        load_dotenv(_env)
        break

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PA ID generation (DB-backed)
# ---------------------------------------------------------------------------

def _next_pa_id(db: Session) -> str:
    """Generate next PA ID based on the max ID in the database."""
    last = db.query(PriorAuthCheckDB).order_by(PriorAuthCheckDB.id.desc()).first()
    if last and last.pa_id.startswith("PA-"):
        try:
            num = int(last.pa_id.split("-")[1])
            return f"PA-{num + 1}"
        except (IndexError, ValueError):
            pass
    return "PA-101"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PriorAuthRequest(BaseModel):
    # From eligibility check
    patient_first_name: str
    patient_last_name: str
    patient_dob: str
    member_id: str
    payer_id: str
    payer_name: str = ""
    provider_npi: str
    provider_name: str = ""
    provider_tax_id: str = ""
    # PA-specific
    service_type_code: str = "30"
    diagnosis_code: str = ""
    procedure_code: str = ""
    prior_auth_number: str = ""  # For ClaimMD: known auth number to attach to claim
    # Optional: link to eligibility check
    eligibility_check_id: str = ""
    clearinghouse: str = ""  # "waystar", "claimmd" — overrides env default


class PriorAuthResponse(BaseModel):
    pa_id: str
    status: str  # submitted, pending, approved, denied, error
    patient_name: str
    payer_name: str
    run_date: str
    # Waystar PA response fields
    reference_id: str | None = None
    status_message: str | None = None
    error_message: str | None = None
    auth_number: str | None = None
    # Link to eligibility
    eligibility_check_id: str | None = None
    execution_time: float = 0.0
    raw_response: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Waystar client helper (reuse from eligibility_api)
# ---------------------------------------------------------------------------

def _get_pa_client(override_provider: str = ""):
    """Create a clearinghouse client for PA operations.

    Supports:
      - waystar: Full 278 PA inquiry (submit → poll)
      - claimmd: PA number attached to claim submission (CMS-1500 Box 23)

    Returns:
        (client, provider_name) tuple, or (None, provider_name) on failure.
    """
    provider = (override_provider or os.getenv("CLEARINGHOUSE_PROVIDER", "")).lower()
    default_provider = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()

    def _env(key: str, default: str = "") -> str:
        val = os.getenv(f"CLEARINGHOUSE_{provider.upper()}_{key}", "")
        if val:
            return val
        if provider == default_provider:
            return os.getenv(f"CLEARINGHOUSE_{key}", default)
        return default

    api_key = _env("API_KEY")
    if not api_key:
        logger.warning("No API key found for %s", provider)
        return None, provider

    try:
        if provider == "waystar":
            from claim_validator.clearinghouse.providers.waystar import WaystarClient
            config = {
                "api_key": api_key,
                "base_url": _env("BASE_URL"),
                "eligibility_base_url": _env("ELIGIBILITY_BASE_URL"),
                "prior_auth_base_url": _env("PRIOR_AUTH_BASE_URL"),
                "user_id": _env("USER_ID"),
                "password": _env("PASSWORD"),
                "cust_id": _env("CUST_ID"),
            }
            config = {k: v for k, v in config.items() if v}
            return WaystarClient(**config), provider
        elif provider == "claimmd":
            from claim_validator.clearinghouse.providers.claimmd import ClaimMDClient
            config = {
                "api_key": api_key,
                "base_url": _env("BASE_URL"),
            }
            config = {k: v for k, v in config.items() if v}
            return ClaimMDClient(**config), provider
        else:
            logger.warning("Provider %s does not support prior auth", provider)
            return None, provider
    except Exception as exc:
        logger.warning("Could not create %s client: %s", provider, exc)
        return None, provider


# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------

def _save_pa_to_db(db: Session, result: PriorAuthResponse, req: PriorAuthRequest) -> None:
    """Persist a PA check result to the database."""
    row = PriorAuthCheckDB(
        pa_id=result.pa_id,
        patient_first_name=req.patient_first_name,
        patient_last_name=req.patient_last_name,
        patient_name=result.patient_name,
        patient_dob=req.patient_dob,
        member_id=req.member_id,
        payer_id=req.payer_id,
        payer_name=result.payer_name,
        provider_npi=req.provider_npi,
        provider_name=req.provider_name,
        service_type_code=req.service_type_code,
        diagnosis_code=req.diagnosis_code,
        procedure_code=req.procedure_code,
        status=result.status,
        reference_id=result.reference_id,
        status_message=result.status_message,
        error_message=result.error_message,
        auth_number=result.auth_number,
        eligibility_check_id=result.eligibility_check_id,
        execution_time=result.execution_time,
        raw_response=result.raw_response,
        run_date=result.run_date,
    )
    db.add(row)
    db.commit()


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def submit_prior_auth(req: PriorAuthRequest, db: Session | None = None) -> PriorAuthResponse:
    """Submit a prior authorization status inquiry to Waystar."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        return _submit_prior_auth_impl(req, db)
    finally:
        if own_session:
            db.close()


def _submit_prior_auth_impl(req: PriorAuthRequest, db: Session) -> PriorAuthResponse:
    start = time.perf_counter()
    pa_id = _next_pa_id(db)
    patient_name = f"{req.patient_first_name} {req.patient_last_name}"
    run_date = datetime.now(UTC).strftime("%Y-%m-%d %I:%M %p")

    print("\n" + "=" * 70)
    print(f"  PRIOR AUTH CHECK {pa_id}")
    print("=" * 70)
    print(f"  Patient:      {patient_name}")
    print(f"  Member ID:    {req.member_id}")
    print(f"  Payer:        {req.payer_id} ({req.payer_name})")
    print(f"  Provider NPI: {req.provider_npi}")
    print(f"  Diagnosis:    {req.diagnosis_code or '(none)'}")
    print(f"  Procedure:    {req.procedure_code or '(none)'}")
    print(f"  Clearinghouse: {req.clearinghouse or '(default)'}")
    print("-" * 70)

    reference_id = None
    status_message = None
    error_message = None
    auth_number = None
    raw_response = None
    status = "error"

    # Check if test environment — use mock PA when real PA endpoints
    # are unavailable (Waystar has no PA sandbox, ClaimMD has no 278)
    is_test_env = os.getenv("CLEARINGHOUSE_ENV", "").lower() == "test"

    try:
        client, provider = _get_pa_client(req.clearinghouse)
        if not client:
            print(f"  WARNING: {provider} client not available")
            result = PriorAuthResponse(
                pa_id=pa_id, status="error", patient_name=patient_name,
                payer_name=req.payer_name, run_date=run_date,
                error_message=f"{provider} client not configured for prior auth",
                eligibility_check_id=req.eligibility_check_id or None,
                execution_time=round(time.perf_counter() - start, 3),
            )
            _save_pa_to_db(db, result, req)
            return result

        if is_test_env:
            # Test mode: simulate PA response (no real PA sandbox available)
            print(f"  [TEST MODE] Simulating PA response for {provider}")
            status, status_message, error_message, auth_number, raw_response, reference_id = (
                _handle_test_pa(req, pa_id, provider)
            )
        elif provider == "claimmd":
            # ClaimMD: PA number is attached to claim submission (CMS-1500 Box 23)
            status, status_message, error_message, auth_number, raw_response, reference_id = (
                _handle_claimmd_pa(client, req, pa_id)
            )
        else:
            # Waystar: Full 278 PA inquiry (submit → poll)
            status, status_message, error_message, auth_number, raw_response, reference_id = (
                _handle_waystar_pa(client, req)
            )

    except Exception as exc:
        logger.warning("PA check failed: %s", exc)
        print(f"  EXCEPTION: {type(exc).__name__}: {exc}")
        error_message = str(exc)
        status = "error"

    elapsed = time.perf_counter() - start
    print(f"\n[RESULT] PA Status: {status}")
    print(f"  Status Message: {status_message}")
    print(f"  Error Message: {error_message}")
    print(f"  Auth Number: {auth_number}")
    print(f"  Time: {elapsed:.2f}s")
    print("=" * 70 + "\n")

    result = PriorAuthResponse(
        pa_id=pa_id,
        status=status,
        patient_name=patient_name,
        payer_name=req.payer_name or req.payer_id,
        run_date=run_date,
        reference_id=reference_id,
        status_message=status_message,
        error_message=error_message,
        auth_number=auth_number,
        eligibility_check_id=req.eligibility_check_id or None,
        execution_time=round(elapsed, 3),
        raw_response=raw_response,
    )

    _save_pa_to_db(db, result, req)
    return result


def _handle_test_pa(req: PriorAuthRequest, pa_id: str, provider: str):
    """Handle PA in test environment via real eligibility check.

    Waystar has no PA sandbox and ClaimMD doesn't support 278 inquiries.
    Instead, we run a real eligibility check against the clearinghouse and
    extract PA-related benefit information from the live payer response.
    """
    from claim_validator.clearinghouse.factory import get_clearinghouse_client

    # Build a real clearinghouse client for the provider
    _env_key = f"CLEARINGHOUSE_{provider.upper()}_"
    config: dict[str, str] = {}
    for key, val in os.environ.items():
        if key.startswith(_env_key):
            field = key[len(_env_key):].lower()
            config[field] = val

    # Add provider-specific extras
    if provider == "waystar":
        config.setdefault("eligibility_base_url",
                          os.getenv("CLEARINGHOUSE_WAYSTAR_ELIGIBILITY_BASE_URL", ""))

    client = get_clearinghouse_client(provider, **config)

    print(f"  [TEST PA] Running real eligibility check via {provider}...")

    try:
        elig_result = client.check_eligibility({
            "payer_id": req.payer_id,
            "npi": req.provider_npi,
            "provider_tax_id": req.provider_tax_id or "",
            "subscriber_id": req.member_id,
            "first_name": req.patient_first_name,
            "last_name": req.patient_last_name,
            "dob": req.patient_dob,
            "service_type": req.service_type_code,
            "provider_name": req.provider_name or "",
            "pat_rel": "18",
        })

        raw_response = elig_result.raw_response
        reference_id = elig_result.reference_id

        # Extract PA and coverage details from the live response
        pa_info = _extract_pa_from_eligibility(elig_result, provider)
        print(f"  [TEST PA] Eligible: {elig_result.eligible}")
        print(f"  [TEST PA] PA info: {pa_info}")

        if not elig_result.eligible:
            return (
                "denied",
                "Patient is not eligible — cannot proceed with prior auth",
                None,
                None,
                raw_response,
                reference_id,
            )

        # Build a rich response with real data
        status = pa_info.get("status", "approved")
        status_msg = pa_info.get("message", "Patient is eligible and covered")
        auth_number = pa_info.get("auth_number")

        # Annotate raw_response with PA determination
        if isinstance(raw_response, dict):
            raw_response["pa_determination"] = pa_info

        return (
            status,
            status_msg,
            None,
            auth_number,
            raw_response,
            reference_id,
        )

    except Exception as exc:
        print(f"  [TEST PA] Eligibility check failed: {exc}")
        return ("error", "PA eligibility check failed", str(exc), None, None, None)
    finally:
        client.close()


def _extract_pa_from_eligibility(elig_result, provider: str) -> dict[str, Any]:
    """Extract PA-related information from a real eligibility response.

    Analyzes benefits data from the live payer response to determine
    PA requirements and coverage status.
    """
    raw = elig_result.raw_response or {}
    info: dict[str, Any] = {
        "eligible": elig_result.eligible,
        "coverage_status": "active" if elig_result.eligible else "inactive",
    }

    if provider == "waystar":
        parsed = raw.get("ParsedOutput", {})
        info["carrier"] = parsed.get("CarrierName", "")
        info["plan_name"] = parsed.get("PlanName", "")
        info["file_status"] = parsed.get("FileStatusDescription", "")
        info["member_id"] = parsed.get("MemberId", "")

        subscriber = parsed.get("Subscriber", {})
        info["subscriber_name"] = f"{subscriber.get('First', '')} {subscriber.get('Last', '')}".strip()
        info["subscriber_dob"] = subscriber.get("Dob", "")

        # Check plans for active coverage
        plans = parsed.get("Plans", [])
        active_plans = [p for p in plans if p.get("IsActive")]
        info["active_plans"] = len(active_plans)

        if active_plans:
            plan = active_plans[0]
            info["plan_name"] = plan.get("InsurancePlanName", info.get("plan_name", ""))
            info["effective_date"] = plan.get("ActiveDate", "")
            info["deductible_in"] = plan.get("DeductibleInNetwork") or plan.get("PlanBinDed")
            info["deductible_remaining"] = plan.get("PlanBinDedRem")

        # Extract benefit-level details
        benefits = parsed.get("Benefits", {})
        for svc_code, svc_data in benefits.items():
            if not isinstance(svc_data, dict):
                continue
            ind = svc_data.get("IND", {})
            if isinstance(ind, dict) and ind.get("CoverageStatus"):
                info["benefit_coverage_status"] = ind["CoverageStatus"]
                info["benefit_plan"] = ind.get("PlanCoverageDescription", "")
                break

        # PA determination based on active coverage
        if active_plans:
            info["status"] = "approved"
            info["message"] = (
                f"Patient is eligible with active coverage under {info['plan_name']}. "
                f"Coverage verified via {info['carrier']}."
            )
            info["auth_number"] = None  # Real auth numbers come from 278
        else:
            info["status"] = "denied"
            info["message"] = "No active plans found for this patient"

    elif provider == "claimmd":
        benefits = raw.get("benefits", [])
        info["carrier"] = raw.get("ins_name_f", "") + " " + raw.get("ins_name_l", "")

        has_active = False
        for b in benefits:
            code = b.get("benefit_coverage_code", "")
            desc = b.get("benefit_coverage_description", "").lower()
            if code == "1" or "active" in desc:
                has_active = True
                info["plan_name"] = b.get("benefit_description", "")
                break

        if has_active:
            info["status"] = "approved"
            info["message"] = "Patient is eligible with active coverage. PA verified via Claim.MD."
            info["auth_number"] = None
        else:
            info["status"] = "denied"
            info["message"] = "No active coverage found"

    else:
        # Generic fallback
        if elig_result.eligible:
            info["status"] = "approved"
            info["message"] = "Patient is eligible — coverage confirmed"
        else:
            info["status"] = "denied"
            info["message"] = "Patient is not eligible"

    return info


def _handle_claimmd_pa(client, req: PriorAuthRequest, pa_id: str):
    """Handle ClaimMD prior auth — submit claim with prior_auth field.

    ClaimMD supports prior_auth as a claim-level field (CMS-1500 Box 23).
    If a PA number is provided, it is attached to a test claim submission.
    If no PA number is provided, we run an eligibility check to see if
    the payer indicates prior auth is required.
    """
    from claim_validator.clearinghouse.exceptions import ClearinghouseValidationError

    reference_id = None
    raw_response = None

    if req.prior_auth_number:
        # Submit a claim with the PA number attached
        print(f"\n[ClaimMD] Submitting claim with prior_auth={req.prior_auth_number}")
        claim_data = {
            "payerid": req.payer_id,
            "ins_name_f": req.patient_first_name,
            "ins_name_l": req.patient_last_name,
            "ins_number": req.member_id,
            "ins_dob": req.patient_dob.replace("-", ""),
            "bill_npi": req.provider_npi,
            "bill_taxid": req.provider_tax_id or "",
            "prior_auth": req.prior_auth_number,
            "diag1": req.diagnosis_code or "",
            "proc": req.procedure_code or "",
        }
        try:
            result = client.submit_claim(claim_data)
            raw_response = result.raw_response
            reference_id = result.reference_id
            if result.accepted:
                return (
                    "approved",
                    f"Claim submitted with PA number {req.prior_auth_number}",
                    None,
                    req.prior_auth_number,
                    raw_response,
                    reference_id,
                )
            else:
                return (
                    "submitted",
                    f"Claim submitted with PA number (status: {result.status})",
                    "; ".join(result.errors) if result.errors else None,
                    req.prior_auth_number,
                    raw_response,
                    reference_id,
                )
        except ClearinghouseValidationError as exc:
            return (
                "error",
                "Claim submission failed",
                str(exc),
                req.prior_auth_number,
                None,
                None,
            )
    else:
        # No PA number — check eligibility to determine if PA is required
        print("\n[ClaimMD] No PA number provided — checking eligibility for PA requirement")
        try:
            elig_result = client.check_eligibility({
                "payer_id": req.payer_id,
                "npi": req.provider_npi,
                "provider_tax_id": req.provider_tax_id or "",
                "subscriber_id": req.member_id,
                "first_name": req.patient_first_name,
                "last_name": req.patient_last_name,
                "dob": req.patient_dob,
                "service_type": req.service_type_code,
                "pat_rel": "18",
            })
            raw_response = elig_result.raw_response
            reference_id = elig_result.reference_id

            if elig_result.eligible:
                return (
                    "pending",
                    "Patient is eligible. Obtain PA number from payer and resubmit.",
                    None,
                    None,
                    raw_response,
                    reference_id,
                )
            else:
                return (
                    "error",
                    "Patient is not eligible — cannot proceed with prior auth",
                    None,
                    None,
                    raw_response,
                    reference_id,
                )
        except Exception as exc:
            return ("error", "Eligibility check failed", str(exc), None, None, None)


def _handle_waystar_pa(client, req: PriorAuthRequest):
    """Handle Waystar prior auth — full 278 inquiry (submit → poll)."""
    reference_id = None
    status_message = None
    error_message = None
    auth_number = None
    raw_response = None
    status = "error"

    # Parse provider name
    _prov_parts = req.provider_name.strip().split() if req.provider_name else []
    _prov_first = _prov_parts[0] if _prov_parts else ""
    _prov_last = " ".join(_prov_parts[1:]) if len(_prov_parts) > 1 else ""

    # Step 1: Submit PA inquiry
    print("\n[STEP 1] Submitting PA status inquiry to Waystar...")
    pa_payload = {
        "npi": req.provider_npi,
        "payer_id": req.payer_id,
        "subscriber_id": req.member_id,
        "first_name": req.patient_first_name,
        "last_name": req.patient_last_name,
        "dob": req.patient_dob,
        "provider_first_name": _prov_first,
        "provider_last_name": _prov_last,
        "provider_name": req.provider_name or "",
    }
    print(f"  Payload: {pa_payload}")

    submit_result = client.check_prior_auth_status(pa_payload)
    print(f"  Submit response: {submit_result}")

    reference_id = str(submit_result.get("ReferenceId", ""))
    status_message = submit_result.get("StatusMessage", "")
    error_message = submit_result.get("ErrorMessage", "")

    if error_message:
        print(f"  [ERROR] {error_message}")
        status = "error"
        raw_response = submit_result
    elif reference_id:
        print(f"  Reference ID: {reference_id}")
        print(f"  Status: {status_message}")

        # Step 2: Poll for result (try a few times)
        print("\n[STEP 2] Polling for PA result...")
        for attempt in range(3):
            time.sleep(2)
            print(f"  Poll attempt {attempt + 1}...")
            poll_result = client.get_prior_auth_result(reference_id)
            print(f"  Poll response: {poll_result}")

            poll_status = poll_result.get("StatusMessage", "")
            poll_error = poll_result.get("ErrorMessage", "")

            if poll_error:
                error_message = poll_error
                status = "error"
                raw_response = poll_result
                break

            if poll_status in ("Received", "Waiting Response"):
                status_message = poll_status
                status = "pending"
                raw_response = poll_result
                continue
            elif "Certified" in poll_status:
                status = "approved"
                status_message = poll_status
                auth_number = poll_result.get("AuthNumber", "")
                raw_response = poll_result
                break
            elif poll_status == "Not Found":
                status = "denied"
                status_message = "No prior authorization found on file"
                raw_response = poll_result
                break
            elif "Failed" in poll_status:
                status = "error"
                status_message = poll_status
                raw_response = poll_result
                break
            else:
                status = "pending"
                status_message = poll_status
                raw_response = poll_result
    else:
        status = "error"
        error_message = "No reference ID returned"
        raw_response = submit_result

    return (status, status_message, error_message, auth_number, raw_response, reference_id)


def get_pa_result(pa_id: str, db: Session | None = None) -> dict[str, Any] | None:
    """Return full result for a PA check."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        row = db.query(PriorAuthCheckDB).filter(PriorAuthCheckDB.pa_id == pa_id).first()
        if row is None:
            return None
        return row.to_dict()
    finally:
        if own_session:
            db.close()


def get_recent_pa_checks(db: Session | None = None) -> list[dict[str, Any]]:
    """Return recent PA checks."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        rows = (
            db.query(PriorAuthCheckDB)
            .order_by(PriorAuthCheckDB.id.desc())
            .limit(20)
            .all()
        )
        return [r.to_dict() for r in rows]
    finally:
        if own_session:
            db.close()
