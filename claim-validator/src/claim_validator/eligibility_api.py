"""Eligibility API — endpoints for the eligibility check UI.

Handles:
  - Running eligibility checks (validation + optional clearinghouse API call)
  - MySQL database storage via SQLAlchemy
  - Serving results with findings for denial prevention
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

from claim_validator.db.models import EligibilityCheck as EligibilityCheckDB
from claim_validator.db.session import SessionLocal

# Load .env from project root (one or two levels up from this file)
_this_dir = Path(__file__).resolve().parent
for _candidate in [_this_dir.parent.parent.parent, _this_dir.parent.parent]:
    _env = _candidate / ".env"
    if _env.is_file():
        load_dotenv(_env)
        break

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Check ID generation (DB-backed)
# ---------------------------------------------------------------------------

def _next_check_id(db: Session) -> str:
    """Generate next check ID based on the max numeric suffix in the database."""
    from sqlalchemy import func
    rows = db.query(EligibilityCheckDB.check_id).all()
    max_num = 1000
    for (cid,) in rows:
        if cid and cid.startswith("CHK-"):
            try:
                num = int(cid.split("-")[1])
                if num > max_num:
                    max_num = num
            except (IndexError, ValueError):
                pass
    return f"CHK-{max_num + 1}"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EligibilityCheckRequest(BaseModel):
    patient_first_name: str
    patient_last_name: str
    patient_dob: str  # YYYY-MM-DD
    member_id: str
    payer_id: str
    payer_name: str = ""
    provider_npi: str = ""
    provider_name: str = ""
    service_type_code: str = "30"
    source: str = "single"  # "single" or "batch"


class FindingOut(BaseModel):
    code: str
    message: str
    severity: str  # ERROR or WARNING
    field_name: str = ""
    suggestion: str = ""
    context: dict[str, Any] | None = None


class EligibilityCheckResponse(BaseModel):
    check_id: str
    status: str  # eligible, not_eligible, inactive, pending, error
    patient_name: str
    payer_name: str
    run_date: str
    # Financial summary
    annual_deductible: float | None = None
    annual_deductible_max: float | None = None
    out_of_pocket: float | None = None
    out_of_pocket_max: float | None = None
    # Coverage details
    copay: float | None = None
    coinsurance: float | None = None
    prior_auth_required: bool | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    plan_name: str | None = None
    group_number: str | None = None
    plan_number: str | None = None
    # Payer / subscriber info from Waystar
    carrier_name: str | None = None
    subscriber_name: str | None = None
    patient_dob_from_payer: str | None = None
    patient_gender: str | None = None
    relationship: str | None = None
    coverage_status: str | None = None
    claims_address: str | None = None
    # Findings (errors/warnings for denial prevention)
    findings: list[FindingOut] = []
    total_errors: int = 0
    total_warnings: int = 0
    # AI summary
    ai_summary: str | None = None
    execution_time: float = 0.0
    # Raw clearinghouse response (for debug)
    raw_response: dict[str, Any] | None = None


class RecentCheckOut(BaseModel):
    check_id: str
    patient_name: str
    payer_name: str
    run_date: str
    status: str
    source: str = "single"
    prior_auth_required: bool | None = None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _build_demo_response(
    check_id: str, req: EligibilityCheckRequest, run_date: str
) -> EligibilityCheckResponse:
    """Return a realistic mock eligibility response for demo purposes.

    Triggered when member_id starts with 'DEMO' (case-insensitive).
    """
    patient_name = f"{req.patient_first_name} {req.patient_last_name}"
    print(f"  [DEMO MODE] Returning mock eligibility data for {patient_name}")

    return EligibilityCheckResponse(
        check_id=check_id,
        status="eligible",
        patient_name=patient_name,
        payer_name=req.payer_name or req.payer_id,
        run_date=run_date,
        annual_deductible=850.00,
        annual_deductible_max=3000.00,
        out_of_pocket=1200.00,
        out_of_pocket_max=6500.00,
        copay=30.00,
        coinsurance=20.0,
        prior_auth_required=True,
        coverage_start="2025-01-01",
        coverage_end="2025-12-31",
        plan_name=f"{req.payer_name or 'Demo'} PPO Gold",
        group_number="GRP-88421",
        findings=[
            FindingOut(
                code="DEMO_MODE",
                message="This is simulated demo data — not a live payer response.",
                severity="warning",
                suggestion="Use a real member ID to query the payer.",
            ),
        ],
        total_errors=0,
        total_warnings=1,
        ai_summary=(
            "Patient is eligible with active PPO coverage. "
            "Individual deductible is $850 of $3,000 met. "
            "Prior authorization is required for this service type. "
            "Recommend verifying PA requirements before claim submission."
        ),
        execution_time=0.1,
        raw_response=None,
    )


def run_eligibility_check(req: EligibilityCheckRequest, db: Session | None = None) -> EligibilityCheckResponse:
    """Run eligibility check: validate inputs → call clearinghouse → interpret."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        return _run_eligibility_check_impl(req, db)
    finally:
        if own_session:
            db.close()


def _run_eligibility_check_impl(req: EligibilityCheckRequest, db: Session) -> EligibilityCheckResponse:
    start = time.perf_counter()
    check_id = _next_check_id(db)
    patient_name = f"{req.patient_first_name} {req.patient_last_name}"
    run_date = datetime.now(UTC).strftime("%Y-%m-%d %I:%M %p")

    # ── Demo mode: return mock data when member_id starts with DEMO ──
    if req.member_id.upper().startswith("DEMO"):
        result = _build_demo_response(check_id, req, run_date)
        _save_check_to_db(db, result, req)
        return result

    env = os.getenv("CLEARINGHOUSE_ENV", "production").upper()
    print("\n" + "=" * 70)
    print(f"  ELIGIBILITY CHECK {check_id}  [{env} ENVIRONMENT]")
    print("=" * 70)
    print(f"  Patient:      {patient_name}")
    print(f"  DOB:          {req.patient_dob}")
    print(f"  Member ID:    {req.member_id}")
    print(f"  Payer ID:     {req.payer_id} ({req.payer_name})")
    print(f"  Provider NPI: {req.provider_npi or '(not provided)'}")
    print(f"  Provider:     {req.provider_name or '(not provided)'}")
    print(f"  Service Type: {req.service_type_code}")
    print("-" * 70)

    all_findings: list[FindingOut] = []

    # ── Step 1: Rule-based validation of the request ──────────────
    print("\n[STEP 1] Running rule-based validation...")
    ai_summary: str | None = None
    try:
        from claim_validator.eligibility._api import check_eligibility

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        validation_result = check_eligibility(
            {
                "provider_npi": req.provider_npi or "0000000000",
                "payer_id": req.payer_id,
                "subscriber_id": req.member_id,
                "subscriber_first_name": req.patient_first_name,
                "subscriber_last_name": req.patient_last_name,
                "subscriber_dob": req.patient_dob,
                "service_type_code": req.service_type_code,
                "date_of_service": today,
            },
        )
        print(f"  Rule validation: {len(validation_result.findings)} findings")
        for f in validation_result.findings:
            print(f"    [{f.severity.value.upper()}] {f.code}: {f.message}")
            all_findings.append(FindingOut(
                code=f.code,
                message=f.message,
                severity=f.severity.value,
                field_name=f.field_name,
                suggestion=f.suggestion,
                context=f.context,
            ))
        if not validation_result.findings:
            print("  All rule-based checks passed!")
    except Exception as exc:
        logger.exception("Rule-based validation failed")
        print(f"  EXCEPTION: {exc}")
        all_findings.append(FindingOut(
            code="VALIDATION_ERROR",
            message=f"Validation engine error: {exc}",
            severity="error",
            suggestion="Check the input data and try again.",
        ))

    # ── Step 2: Call clearinghouse eligibility API ──────────────────
    ch_provider = os.getenv("CLEARINGHOUSE_PROVIDER", "unknown")
    clearinghouse_resp = None
    eligible = None
    plan_info: dict[str, Any] = {}

    # Block API call if there are validation errors
    validation_errors = [f for f in all_findings if f.severity == "error"]
    if validation_errors:
        print(f"\n[STEP 2] SKIPPED — {len(validation_errors)} validation error(s) found:")
        for f in validation_errors:
            print(f"    [{f.code}] {f.message}")
        print("  Fix the above errors before calling the clearinghouse API.")
    else:
        print(f"\n[STEP 2] Calling {ch_provider.upper()} eligibility API...")

    if not validation_errors:
        try:
            client = _get_clearinghouse_client()
            if client:
                print(f"  {ch_provider.upper()} client created:")
                print(f"    Provider:    {ch_provider}")
                print(f"    Base URL:    {os.getenv('CLEARINGHOUSE_BASE_URL', 'default')}")

                # Parse provider name into first/last for X12-based clearinghouses
                _prov_parts = req.provider_name.strip().split() if req.provider_name else []
                _prov_first = _prov_parts[0] if _prov_parts else ""
                _prov_last = " ".join(_prov_parts[1:]) if len(_prov_parts) > 1 else ""

                waystar_request = {
                    "npi": req.provider_npi or "0000000000",
                    "payer_id": req.payer_id,
                    "subscriber_id": req.member_id,
                    "first_name": req.patient_first_name,
                    "last_name": req.patient_last_name,
                    "dob": req.patient_dob,
                    "service_type": req.service_type_code,
                    "provider_first_name": _prov_first,
                    "provider_last_name": _prov_last,
                    "provider_name": req.provider_name or "",  # full name for JSON-based clearinghouses
                }
                print(f"  Sending to {ch_provider.upper()}: {waystar_request}")

                clearinghouse_resp = client.check_eligibility(waystar_request)

                print(f"\n  {ch_provider.upper()} response received:")
                print(f"    Status:     {clearinghouse_resp.status}")
                print(f"    Eligible:   {clearinghouse_resp.eligible}")
                print(f"    Ref ID:     {clearinghouse_resp.reference_id}")
                print(f"    Errors:     {clearinghouse_resp.errors}")
                if clearinghouse_resp.raw_response:
                    import json as _j
                    raw_str = _j.dumps(clearinghouse_resp.raw_response, indent=2, default=str)
                    # Print first 1000 chars of raw response
                    print(f"    Raw response (first 1000 chars):")
                    print(f"    {raw_str[:1000]}")

                eligible = clearinghouse_resp.eligible
                plan_info = clearinghouse_resp.plan_info or {}

                if clearinghouse_resp.errors:
                    for err in clearinghouse_resp.errors:
                        print(f"    [ERROR from payer] {err}")
                        all_findings.append(FindingOut(
                            code="CLEARINGHOUSE_ERROR",
                            message=err,
                            severity="error",
                            suggestion="Check payer ID and member ID, then retry.",
                        ))

                # Extract Waystar-specific fail reasons from parsed output
                parsed = plan_info
                fail_reason = parsed.get("FailReason", "")
                if fail_reason:
                    print(f"    [PAYER REJECTION] {fail_reason}")
                    all_findings.append(FindingOut(
                        code="PAYER_REJECTION",
                        message=fail_reason,
                        severity="error",
                        field_name="payer_id",
                        suggestion="Verify the payer ID is correct and the provider is enrolled with this payer.",
                    ))
            else:
                print("  WARNING: Clearinghouse client not created!")
                print(f"    CLEARINGHOUSE_PROVIDER = {ch_provider}")
                print(f"    CLEARINGHOUSE_API_KEY = {'set' if os.getenv('CLEARINGHOUSE_API_KEY') else '(not set)'}")
                print("  Skipping clearinghouse call — results are rule-based only.")
        except Exception as exc:
            logger.warning("%s API call failed: %s", ch_provider, exc)
            print(f"  EXCEPTION calling {ch_provider.upper()}: {type(exc).__name__}: {exc}")
            err_msg = str(exc)
            # Distinguish data/validation errors from connectivity issues
            from claim_validator.clearinghouse.exceptions import (
                ClearinghouseValidationError,
                ClearinghouseError,
            )
            if isinstance(exc, ClearinghouseValidationError):
                all_findings.append(FindingOut(
                    code="CLEARINGHOUSE_VALIDATION",
                    message=f"Clearinghouse rejected the request: {err_msg}",
                    severity="error",
                    suggestion="Check the member ID, payer ID, and patient details are correct.",
                ))
            elif isinstance(exc, ClearinghouseError) and "not found" in err_msg.lower():
                all_findings.append(FindingOut(
                    code="CLEARINGHOUSE_DATA_ERROR",
                    message=f"Payer/member combination not recognized: {err_msg}",
                    severity="error",
                    suggestion="Verify the Member ID and Payer ID match the patient's insurance card. "
                               "In test mode, use only pre-configured test data.",
                ))
            elif isinstance(exc, ClearinghouseError):
                all_findings.append(FindingOut(
                    code="CLEARINGHOUSE_ERROR",
                    message=f"Clearinghouse error: {err_msg}",
                    severity="error",
                    suggestion="Check the request data and try again.",
                ))
            else:
                all_findings.append(FindingOut(
                    code="CLEARINGHOUSE_UNAVAILABLE",
                    message=f"Could not reach clearinghouse: {err_msg}",
                    severity="warning",
                    suggestion="Results are based on rule validation only. "
                               "Retry to get live payer data.",
                ))

    # ── Step 3: Parse financial/coverage data from response ───────
    print("\n[STEP 3] Extracting financial/coverage data...")
    raw_resp = clearinghouse_resp.raw_response if clearinghouse_resp else None
    financial = _extract_financial(plan_info, raw_resp)
    print(f"  Financial data: {financial}")

    # Determine status using clearinghouse response
    errors = [f for f in all_findings if f.severity == "error"]
    warnings = [f for f in all_findings if f.severity == "warning"]

    file_status = financial.get("file_status")
    if eligible is True or file_status == 1:
        status = "eligible"
    elif file_status == 2:
        status = "inactive"
    elif eligible is False:
        status = "not_eligible"
    elif errors:
        status = "error"
    else:
        status = "pending"

    print(f"\n[RESULT] Status: {status}")
    print(f"  Errors: {len(errors)}, Warnings: {len(warnings)}")
    print(f"  Eligible (from {ch_provider}): {eligible}")
    print(f"  FileStatus: {file_status} ({financial.get('file_status_desc', '')})")
    print("=" * 70 + "\n")

    elapsed = time.perf_counter() - start

    result = EligibilityCheckResponse(
        check_id=check_id,
        status=status,
        patient_name=patient_name,
        payer_name=financial.get("carrier_name") or req.payer_name or req.payer_id,
        run_date=run_date,
        annual_deductible=financial.get("deductible"),
        annual_deductible_max=financial.get("deductible_max"),
        out_of_pocket=financial.get("oop"),
        out_of_pocket_max=financial.get("oop_max"),
        copay=financial.get("copay"),
        coinsurance=financial.get("coinsurance"),
        prior_auth_required=financial.get("prior_auth_required"),
        coverage_start=financial.get("coverage_start"),
        coverage_end=financial.get("coverage_end"),
        plan_name=financial.get("plan_name"),
        group_number=financial.get("group_number"),
        plan_number=financial.get("plan_number"),
        carrier_name=financial.get("carrier_name"),
        subscriber_name=financial.get("subscriber_name"),
        patient_dob_from_payer=financial.get("patient_dob"),
        patient_gender=financial.get("patient_gender"),
        relationship=financial.get("relationship"),
        coverage_status=financial.get("coverage_status"),
        claims_address=financial.get("claims_address"),
        findings=all_findings,
        total_errors=len(errors),
        total_warnings=len(warnings),
        ai_summary=ai_summary,
        execution_time=round(elapsed, 3),
        raw_response=clearinghouse_resp.raw_response
        if clearinghouse_resp
        else None,
    )

    # Store in database
    _save_check_to_db(db, result, req)
    return result


def _save_check_to_db(
    db: Session,
    result: EligibilityCheckResponse,
    req: EligibilityCheckRequest,
) -> None:
    """Persist an eligibility check result to the database."""
    # Serialize findings list to dicts for JSON column
    findings_data = [f.model_dump() if hasattr(f, "model_dump") else f for f in (result.findings or [])]

    row = EligibilityCheckDB(
        check_id=result.check_id,
        source=req.source,
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
        status=result.status,
        annual_deductible=result.annual_deductible,
        annual_deductible_max=result.annual_deductible_max,
        out_of_pocket=result.out_of_pocket,
        out_of_pocket_max=result.out_of_pocket_max,
        copay=result.copay,
        coinsurance=result.coinsurance,
        prior_auth_required=result.prior_auth_required,
        coverage_start=result.coverage_start,
        coverage_end=result.coverage_end,
        plan_name=result.plan_name,
        group_number=result.group_number,
        plan_number=result.plan_number,
        carrier_name=result.carrier_name,
        subscriber_name=result.subscriber_name,
        patient_dob_from_payer=result.patient_dob_from_payer,
        patient_gender=result.patient_gender,
        relationship=result.relationship,
        coverage_status=result.coverage_status,
        claims_address=result.claims_address,
        findings=findings_data,
        total_errors=result.total_errors,
        total_warnings=result.total_warnings,
        ai_summary=result.ai_summary,
        execution_time=result.execution_time,
        raw_response=result.raw_response,
        run_date=result.run_date,
    )
    db.add(row)
    db.commit()


def get_recent_checks(db: Session | None = None) -> list[RecentCheckOut]:
    """Return recent checks, newest first."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        rows = (
            db.query(EligibilityCheckDB)
            .order_by(EligibilityCheckDB.id.desc())
            .limit(20)
            .all()
        )
        return [
            RecentCheckOut(
                check_id=r.check_id,
                patient_name=r.patient_name,
                payer_name=r.payer_name,
                run_date=r.run_date,
                status=r.status,
                source=r.source or "single",
                prior_auth_required=r.prior_auth_required,
            )
            for r in rows
        ]
    finally:
        if own_session:
            db.close()


def get_check_result(check_id: str, db: Session | None = None) -> dict[str, Any] | None:
    """Return full result for a check ID."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        row = db.query(EligibilityCheckDB).filter(EligibilityCheckDB.check_id == check_id).first()
        if row is None:
            return None
        return row.to_dict()
    finally:
        if own_session:
            db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ai_config() -> dict[str, Any] | None:
    provider = os.getenv("CLAIM_VALIDATOR_AI_PROVIDER")
    api_key = os.getenv("CLAIM_VALIDATOR_AI_API_KEY")
    model = os.getenv("CLAIM_VALIDATOR_AI_MODEL")
    if provider and api_key and model:
        return {"provider": provider, "api_key": api_key, "model": model}
    return None


def _get_clearinghouse_client():
    """Create a clearinghouse client from env vars, or return None.

    Supports: waystar, stedi, claimmd — configured via CLEARINGHOUSE_PROVIDER.
    """
    provider = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()
    if not provider:
        return None
    api_key = os.getenv("CLEARINGHOUSE_API_KEY", "")
    if not api_key:
        return None

    from claim_validator.clearinghouse.factory import get_clearinghouse_client

    config: dict[str, Any] = {
        "api_key": api_key,
        "base_url": os.getenv("CLEARINGHOUSE_BASE_URL", ""),
    }

    if provider == "waystar":
        config.update({
            "secret": os.getenv("CLEARINGHOUSE_SECRET", ""),
            "user_id": os.getenv("CLEARINGHOUSE_USER_ID", ""),
            "password": os.getenv("CLEARINGHOUSE_PASSWORD", ""),
            "cust_id": os.getenv("CLEARINGHOUSE_CUST_ID", ""),
            "eligibility_base_url": os.getenv("CLEARINGHOUSE_ELIGIBILITY_BASE_URL", ""),
            "prior_auth_base_url": os.getenv("CLEARINGHOUSE_PRIOR_AUTH_BASE_URL", ""),
        })

    # Remove empty strings so defaults in client constructors are used
    config = {k: v for k, v in config.items() if v}

    try:
        return get_clearinghouse_client(provider, **config)
    except Exception as exc:
        print(f"  WARNING: Failed to create {provider} client: {exc}")
        return None


def _extract_financial(plan_info: dict[str, Any], raw_response: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract financial/coverage fields from clearinghouse response.

    Supports both Waystar FullJSON (ParsedOutput) and Stedi JSON formats.
    """
    result: dict[str, Any] = {}

    if not plan_info and not raw_response:
        return result

    # Detect Stedi format (has planStatus, benefitsInformation, etc.)
    raw = raw_response or {}
    if raw.get("planStatus") or raw.get("benefitsInformation") or raw.get("planDateInformation"):
        return _extract_financial_stedi(raw)

    if not plan_info:
        return result

    # ── Plan-level info ──────────────────────────────────────────
    result["plan_name"] = plan_info.get("PlanName") or plan_info.get("CarrierName")
    result["group_number"] = plan_info.get("GroupNumber")
    result["plan_number"] = plan_info.get("PlanNumber")
    result["carrier_name"] = plan_info.get("CarrierName")
    result["member_id"] = plan_info.get("MemberId")

    # FileStatus: 1=ACTIVE, 2=INACTIVE, 3=ERROR/REJECTED
    file_status = plan_info.get("FileStatus")
    result["file_status"] = file_status
    result["file_status_desc"] = plan_info.get("FileStatusDescription", "")

    # ── Subscriber / Patient info ────────────────────────────────
    subscriber = plan_info.get("Subscriber", {})
    patient = plan_info.get("Patient", {})
    result["subscriber_name"] = f"{subscriber.get('First', '')} {subscriber.get('Last', '')}".strip()
    result["patient_name"] = f"{patient.get('First', '')} {patient.get('Last', '')}".strip()
    result["patient_dob"] = patient.get("Dob", "")
    result["patient_gender"] = patient.get("Sex") or patient.get("Gender", "")
    result["relationship"] = plan_info.get("SubscriberRelationship", "")

    # ── Claims mailing info ──────────────────────────────────────
    claims_info = plan_info.get("ClaimsInfo", {})
    if claims_info:
        addr_parts = [claims_info.get("Name", "")]
        if claims_info.get("Address1"):
            addr_parts.append(claims_info["Address1"])
        city_st = f"{claims_info.get('City', '')}, {claims_info.get('State', '')} {claims_info.get('Zip', '')}"
        addr_parts.append(city_st.strip())
        result["claims_address"] = " | ".join(p for p in addr_parts if p)

    # ── Coverage dates from Dtps ─────────────────────────────────
    for dtp in plan_info.get("Dtps", []):
        dtp_type = dtp.get("Type", "")
        dtp_date = dtp.get("Date", "")
        if dtp_type == "356":  # Eligibility begin
            result["coverage_start"] = _format_waystar_date(dtp_date)
        elif dtp_type == "291":  # Service period
            if "-" in dtp_date:
                parts = dtp_date.split("-")
                result.setdefault("coverage_start", _format_waystar_date(parts[0]))
                result["coverage_end"] = _format_waystar_date(parts[1])

    # ── Plans array ──────────────────────────────────────────────
    plans = plan_info.get("Plans", [])
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        is_active = plan.get("IsActive", False)
        result["is_active"] = is_active
        if plan.get("PatientTerminationBenefitDate"):
            result["termination_date"] = plan["PatientTerminationBenefitDate"]
        # Pick up plan-level deductible/copay/coinsurance if present
        if plan.get("Deductible") is not None:
            result.setdefault("deductible", _to_float(plan["Deductible"]))
        if plan.get("DeductibleMax") is not None:
            result.setdefault("deductible_max", _to_float(plan["DeductibleMax"]))
        if plan.get("Copay") is not None:
            result.setdefault("copay", _to_float(plan["Copay"]))
        if plan.get("Coinsurance") is not None:
            result.setdefault("coinsurance", _to_float(plan["Coinsurance"]))
        if plan.get("OutOfPocket") is not None:
            result.setdefault("oop", _to_float(plan["OutOfPocket"]))
        if plan.get("OutOfPocketMax") is not None:
            result.setdefault("oop_max", _to_float(plan["OutOfPocketMax"]))

    # ── Benefits dict (keyed by service type code) ───────────────
    benefits = plan_info.get("Benefits", {})
    if isinstance(benefits, dict):
        for _svc_code, svc_data in benefits.items():
            if not isinstance(svc_data, dict):
                continue
            # Individual benefits
            ind = svc_data.get("IND", {})
            if isinstance(ind, dict):
                result["coverage_status"] = ind.get("CoverageStatus", "")
                result.setdefault("plan_name", ind.get("PlanCoverageDescription"))
                if ind.get("Deductible") is not None:
                    result.setdefault("deductible", _to_float(ind["Deductible"]))
                if ind.get("DeductibleRemaining") is not None:
                    result["deductible_remaining"] = _to_float(ind["DeductibleRemaining"])
                if ind.get("Copay") is not None:
                    result.setdefault("copay", _to_float(ind["Copay"]))
                if ind.get("Coinsurance") is not None:
                    result.setdefault("coinsurance", _to_float(ind["Coinsurance"]))
                if ind.get("OutOfPocket") is not None:
                    result.setdefault("oop", _to_float(ind["OutOfPocket"]))
                if ind.get("OutOfPocketRemaining") is not None:
                    result["oop_remaining"] = _to_float(ind["OutOfPocketRemaining"])

            # Family benefits
            fam = svc_data.get("FAM", {})
            if isinstance(fam, dict):
                if fam.get("Deductible") is not None:
                    result["family_deductible"] = _to_float(fam["Deductible"])
                if fam.get("OutOfPocket") is not None:
                    result["family_oop"] = _to_float(fam["OutOfPocket"])

    # ── Prior auth ───────────────────────────────────────────────
    pa_required = plan_info.get("PriorAuthRequired") or plan_info.get("authOrCertIndicator")
    if pa_required is not None:
        if isinstance(pa_required, bool):
            result["prior_auth_required"] = pa_required
        elif str(pa_required).upper() in ("Y", "YES"):
            result["prior_auth_required"] = True
        elif str(pa_required).upper() in ("N", "NO"):
            result["prior_auth_required"] = False

    return result


def _extract_financial_stedi(data: dict[str, Any]) -> dict[str, Any]:
    """Extract financial/coverage fields from Stedi eligibility response."""
    result: dict[str, Any] = {}

    # Plan status — can be a string or list
    raw_plan_status = data.get("planStatus", "")
    if isinstance(raw_plan_status, list):
        plan_status = raw_plan_status[0] if raw_plan_status else ""
        if isinstance(plan_status, dict):
            plan_status = plan_status.get("status", "")
    else:
        plan_status = raw_plan_status or ""
    plan_status = str(plan_status)
    result["coverage_status"] = plan_status
    ps_lower = plan_status.lower()
    if "active" in ps_lower and "inactive" not in ps_lower:
        result["file_status"] = 1
        result["file_status_desc"] = "ACTIVE"
    elif "inactive" in ps_lower:
        result["file_status"] = 2
        result["file_status_desc"] = "INACTIVE"
    else:
        result["file_status"] = None
        result["file_status_desc"] = plan_status

    # Plan info
    plan_info = data.get("planInformation", {})
    result["plan_name"] = plan_info.get("planDescription") or data.get("planName", "")
    result["group_number"] = plan_info.get("groupNumber") or data.get("groupNumber", "")
    result["plan_number"] = plan_info.get("planNumber", "")

    # Subscriber / Patient
    subscriber = data.get("subscriber", {})
    result["subscriber_name"] = f"{subscriber.get('firstName', '')} {subscriber.get('lastName', '')}".strip()
    result["patient_dob"] = subscriber.get("dateOfBirth", "")
    result["patient_gender"] = subscriber.get("gender", "")
    result["member_id"] = subscriber.get("memberId", "")
    result["relationship"] = data.get("subscriberRelationship", "SUBSCRIBER")

    # Payer / source
    payer = data.get("payer", {}) or data.get("informationSource", {})
    result["carrier_name"] = payer.get("name", "") or data.get("tradingPartnerServiceId", "")

    # Plan dates
    date_info = data.get("planDateInformation", {})
    if date_info.get("eligibilityBegin"):
        result["coverage_start"] = _format_stedi_date(date_info["eligibilityBegin"])
    if date_info.get("eligibilityEnd"):
        result["coverage_end"] = _format_stedi_date(date_info["eligibilityEnd"])
    if date_info.get("planBegin"):
        result.setdefault("coverage_start", _format_stedi_date(date_info["planBegin"]))
    if date_info.get("planEnd"):
        result.setdefault("coverage_end", _format_stedi_date(date_info["planEnd"]))

    # Benefits information (array of benefit objects)
    benefits = data.get("benefitsInformation", [])
    for b in benefits:
        if not isinstance(b, dict):
            continue
        code = b.get("code", "")
        name = b.get("name", "").lower()
        coverage_level = b.get("coverageLevelCode", "").upper()
        amount = _to_float(b.get("benefitAmount"))
        pct = _to_float(b.get("benefitPercent"))

        # Deductible
        if code == "C" or "deductible" in name:
            if coverage_level in ("IND", ""):
                if amount is not None:
                    if "remaining" in name:
                        result["deductible"] = amount
                    else:
                        result.setdefault("deductible_max", amount)
            elif coverage_level == "FAM":
                if amount is not None:
                    result["family_deductible"] = amount

        # Out of pocket
        if code == "G" or "out of pocket" in name or "out-of-pocket" in name:
            if coverage_level in ("IND", ""):
                if amount is not None:
                    if "remaining" in name:
                        result["oop"] = amount
                    else:
                        result.setdefault("oop_max", amount)

        # Copay
        if code == "B" or "co-pay" in name or "copay" in name:
            if amount is not None:
                result.setdefault("copay", amount)

        # Coinsurance
        if code == "A" or "co-insurance" in name or "coinsurance" in name:
            if pct is not None:
                result.setdefault("coinsurance", pct)

        # Prior auth required
        if "authorization" in name or "auth" in name.split():
            result["prior_auth_required"] = True

    return result


def _format_stedi_date(raw: str) -> str | None:
    """Convert YYYYMMDD to YYYY-MM-DD for Stedi dates."""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def _format_waystar_date(raw: str) -> str | None:
    """Convert YYYYMMDD to YYYY-MM-DD, or return as-is if already formatted."""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


def _to_float(val: Any) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Seed demo data into database
# ---------------------------------------------------------------------------

def seed_demo_data() -> None:
    """Pre-populate demo checks into the database (if empty)."""
    db = SessionLocal()
    try:
        count = db.query(EligibilityCheckDB).count()
        if count > 0:
            return  # Already seeded

        demo_rows = [
            EligibilityCheckDB(
                check_id="CHK-1048", source="single", status="eligible",
                patient_first_name="Sarah", patient_last_name="Johnson",
                patient_name="Sarah Johnson", payer_name="Medicare",
                run_date="2026-03-02 09:15 AM",
                annual_deductible=850.0, annual_deductible_max=1500.0,
                out_of_pocket=1200.0, out_of_pocket_max=3500.0,
                copay=20.0, coinsurance=20.0, prior_auth_required=True,
                coverage_start="2026-01-01", coverage_end="2026-12-31",
                plan_name="Medicare Part B",
                findings=[], total_errors=0, total_warnings=0, execution_time=1.234,
            ),
            EligibilityCheckDB(
                check_id="CHK-1047", source="batch", status="eligible",
                patient_first_name="Michael", patient_last_name="Chen",
                patient_name="Michael Chen", payer_name="BlueCross BlueShield",
                run_date="2026-03-02 08:42 AM",
                annual_deductible=500.0, annual_deductible_max=1000.0,
                out_of_pocket=2000.0, out_of_pocket_max=5000.0,
                copay=30.0, coinsurance=15.0, prior_auth_required=False,
                coverage_start="2026-01-01", coverage_end="2026-12-31",
                plan_name="PPO Gold", group_number="GRP-44521",
                findings=[], total_errors=0, total_warnings=0, execution_time=0.987,
            ),
            EligibilityCheckDB(
                check_id="CHK-1046", source="batch", status="not_eligible",
                patient_first_name="Emily", patient_last_name="Rodriguez",
                patient_name="Emily Rodriguez", payer_name="Aetna",
                run_date="2026-03-02 07:30 AM",
                findings=[
                    {"code": "ELIG_COVERAGE_TERMINATED", "message": "Coverage terminated on 2025-12-31", "severity": "error", "field_name": "coverage", "suggestion": "Verify patient has active coverage or check alternate payer."},
                    {"code": "ELIG_MEMBER_ID_MISMATCH", "message": "Member ID does not match payer records", "severity": "error", "field_name": "member_id", "suggestion": "Double-check member ID on patient's insurance card."},
                ],
                total_errors=2, total_warnings=0, execution_time=1.456,
            ),
            EligibilityCheckDB(
                check_id="CHK-1045", source="single", status="eligible",
                patient_first_name="David", patient_last_name="Kim",
                patient_name="David Kim", payer_name="UnitedHealthcare",
                run_date="2026-03-01 04:15 PM",
                annual_deductible=1200.0, annual_deductible_max=2000.0,
                out_of_pocket=3000.0, out_of_pocket_max=6000.0,
                copay=40.0, coinsurance=25.0, prior_auth_required=True,
                coverage_start="2026-01-01", coverage_end="2026-12-31",
                plan_name="Choice Plus POS", group_number="GRP-77892",
                findings=[
                    {"code": "ELIG_PA_REQUIRED", "message": "Prior authorization required for requested service type", "severity": "warning", "field_name": "service_type", "suggestion": "Submit prior authorization before claim to avoid denial."},
                ],
                total_errors=0, total_warnings=1, execution_time=2.103,
            ),
            EligibilityCheckDB(
                check_id="CHK-1044", source="single", status="pending",
                patient_first_name="Jennifer", patient_last_name="Wilson",
                patient_name="Jennifer Wilson", payer_name="Cigna",
                run_date="2026-03-01 02:22 PM",
                findings=[
                    {"code": "CLEARINGHOUSE_TIMEOUT", "message": "Payer response pending — check back later", "severity": "warning", "field_name": "", "suggestion": "Retry eligibility check in a few minutes."},
                ],
                total_errors=0, total_warnings=1, execution_time=30.0,
            ),
        ]

        db.add_all(demo_rows)
        db.commit()
        print("[DB] Seeded 5 demo eligibility checks")
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to seed demo data: %s", exc)
    finally:
        db.close()
