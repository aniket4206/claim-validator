"""Prior Authorization API — endpoints for the PA check flow.

Handles:
  - Submitting PA status inquiries to Waystar (async: submit → poll)
  - MySQL database storage via SQLAlchemy
  - Parsing 278 response data
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
    # PA-specific
    service_type_code: str = "30"
    diagnosis_code: str = ""
    procedure_code: str = ""
    # Optional: link to eligibility check
    eligibility_check_id: str = ""


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

def _get_waystar_client():
    """Create a WaystarClient from env vars."""
    provider = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()
    if provider != "waystar":
        return None

    try:
        from claim_validator.clearinghouse.providers.waystar import WaystarClient
        return WaystarClient(
            api_key=os.getenv("CLEARINGHOUSE_API_KEY", ""),
            base_url=os.getenv("CLEARINGHOUSE_BASE_URL", ""),
            eligibility_base_url=os.getenv("CLEARINGHOUSE_ELIGIBILITY_BASE_URL", ""),
            prior_auth_base_url=os.getenv("CLEARINGHOUSE_PRIOR_AUTH_BASE_URL", ""),
            user_id=os.getenv("CLEARINGHOUSE_USER_ID", ""),
            password=os.getenv("CLEARINGHOUSE_PASSWORD", ""),
            customer_id=os.getenv("CLEARINGHOUSE_CUST_ID", ""),
        )
    except Exception as exc:
        logger.warning("Could not create Waystar client: %s", exc)
        return None


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
    print("-" * 70)

    reference_id = None
    status_message = None
    error_message = None
    auth_number = None
    raw_response = None
    status = "error"

    try:
        client = _get_waystar_client()
        if not client:
            print("  WARNING: Waystar client not available")
            result = PriorAuthResponse(
                pa_id=pa_id, status="error", patient_name=patient_name,
                payer_name=req.payer_name, run_date=run_date,
                error_message="Waystar client not configured",
                eligibility_check_id=req.eligibility_check_id or None,
                execution_time=round(time.perf_counter() - start, 3),
            )
            _save_pa_to_db(db, result, req)
            return result

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
                time.sleep(2)  # Wait between polls
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
