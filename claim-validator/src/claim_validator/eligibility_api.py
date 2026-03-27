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
    provider_tax_id: str = ""
    service_type_code: str = "30"
    source: str = "single"  # "single" or "batch"
    clearinghouse: str = ""  # "stedi", "waystar", "claimmd" — overrides env var


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
    clearinghouse_provider: str | None = None
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
    clearinghouse_provider: str | None = None
    carrier_name: str | None = None
    plan_name: str | None = None
    copay: float | None = None
    annual_deductible: float | None = None
    coverage_status: str | None = None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def run_eligibility_check(req: EligibilityCheckRequest, db: Session | None = None, user_id: int | None = None) -> EligibilityCheckResponse:
    """Run eligibility check: validate inputs → call clearinghouse → interpret."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        return _run_eligibility_check_impl(req, db, user_id=user_id)
    finally:
        if own_session:
            db.close()


def _run_eligibility_check_impl(req: EligibilityCheckRequest, db: Session, user_id: int | None = None) -> EligibilityCheckResponse:
    start = time.perf_counter()
    check_id = _next_check_id(db)
    patient_name = f"{req.patient_first_name} {req.patient_last_name}"
    run_date = datetime.now(UTC).strftime("%Y-%m-%d %I:%M %p")

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
    clearinghouse_resp = None
    eligible = None
    plan_info: dict[str, Any] = {}

    # Use per-request clearinghouse override if provided
    client, ch_provider = _get_clearinghouse_client(req.clearinghouse)
    if not ch_provider:
        ch_provider = "unknown"

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
            if client:
                print(f"  {ch_provider.upper()} client created:")
                print(f"    Provider:    {ch_provider}")
                print(f"    Base URL:    {os.getenv('CLEARINGHOUSE_BASE_URL', 'default')}")

                # Parse provider name into first/last for X12-based clearinghouses
                _prov_parts = req.provider_name.strip().split() if req.provider_name else []
                _prov_first = _prov_parts[0] if _prov_parts else ""
                _prov_last = " ".join(_prov_parts[1:]) if len(_prov_parts) > 1 else ""

                # Resolve provider_tax_id from request or env var
                _tax_id = req.provider_tax_id or os.getenv("PROVIDER_TAX_ID", "")

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
                    "provider_name": req.provider_name or "",
                    "provider_tax_id": _tax_id,
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
        clearinghouse_provider=ch_provider,
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
    _save_check_to_db(db, result, req, ch_provider, user_id=user_id)
    return result


def _save_check_to_db(
    db: Session,
    result: EligibilityCheckResponse,
    req: EligibilityCheckRequest,
    clearinghouse_provider: str = "",
    user_id: int | None = None,
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
        clearinghouse_provider=clearinghouse_provider or "",
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
        user_id=user_id,
    )
    db.add(row)
    db.commit()


def get_recent_checks(db: Session | None = None, user_id: int | None = None) -> list[RecentCheckOut]:
    """Return recent checks, newest first, filtered by user."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        query = db.query(EligibilityCheckDB)
        if user_id is not None:
            query = query.filter(EligibilityCheckDB.user_id == user_id)
        rows = (
            query
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
                clearinghouse_provider=r.clearinghouse_provider,
                carrier_name=r.carrier_name,
                plan_name=r.plan_name,
                copay=r.copay,
                annual_deductible=r.annual_deductible,
                coverage_status=r.coverage_status,
            )
            for r in rows
        ]
    finally:
        if own_session:
            db.close()


def get_check_result(check_id: str, db: Session | None = None, user_id: int | None = None) -> dict[str, Any] | None:
    """Return full result for a check ID, filtered by user."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        query = db.query(EligibilityCheckDB).filter(EligibilityCheckDB.check_id == check_id)
        if user_id is not None:
            query = query.filter(EligibilityCheckDB.user_id == user_id)
        row = query.first()
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


def _get_clearinghouse_client(override_provider: str = ""):
    """Create a clearinghouse client from env vars, or return None.

    Supports: waystar, stedi, claimmd — configured via provider-specific
    env vars (e.g. CLEARINGHOUSE_WAYSTAR_API_KEY) or generic CLEARINGHOUSE_
    vars only when the provider matches CLEARINGHOUSE_PROVIDER.
    """
    provider = (override_provider or os.getenv("CLEARINGHOUSE_PROVIDER", "")).lower()
    if not provider:
        return None, ""

    # Per-provider env var prefix: CLEARINGHOUSE_WAYSTAR_, CLEARINGHOUSE_STEDI_, etc.
    prefix = f"CLEARINGHOUSE_{provider.upper()}_"
    default_provider = os.getenv("CLEARINGHOUSE_PROVIDER", "").lower()

    def _env(key: str, default: str = "") -> str:
        # Always check provider-specific var first
        val = os.getenv(f"{prefix}{key}", "")
        if val:
            return val
        # Only fall back to generic CLEARINGHOUSE_ vars if this IS the default provider
        # (avoids e.g. waystar picking up stedi's generic CLEARINGHOUSE_API_KEY)
        if provider == default_provider:
            return os.getenv(f"CLEARINGHOUSE_{key}", default)
        return default

    api_key = _env("API_KEY")
    if not api_key:
        print(f"  WARNING: No API key found for {provider} "
              f"(checked {prefix}API_KEY)")
        return None, provider

    from claim_validator.clearinghouse.factory import get_clearinghouse_client

    config: dict[str, Any] = {
        "api_key": api_key,
        "base_url": _env("BASE_URL"),
    }

    if provider == "waystar":
        config.update({
            "secret": _env("SECRET"),
            "user_id": _env("USER_ID"),
            "password": _env("PASSWORD"),
            "cust_id": _env("CUST_ID"),
            "eligibility_base_url": _env("ELIGIBILITY_BASE_URL"),
            "prior_auth_base_url": _env("PRIOR_AUTH_BASE_URL"),
        })

    # Remove empty strings so defaults in client constructors are used
    config = {k: v for k, v in config.items() if v}

    print(f"  Creating {provider.upper()} client with config keys: {list(config.keys())}")
    try:
        return get_clearinghouse_client(provider, **config), provider
    except Exception as exc:
        print(f"  WARNING: Failed to create {provider} client: {exc}")
        return None, provider


def _extract_financial(plan_info: dict[str, Any], raw_response: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract financial/coverage fields from clearinghouse response.

    Supports Waystar FullJSON (ParsedOutput), Stedi JSON, and ClaimMD XML formats.
    """
    result: dict[str, Any] = {}

    if not plan_info and not raw_response:
        return result

    # Detect Stedi format (has planStatus, benefitsInformation, etc.)
    raw = raw_response or {}
    if raw.get("planStatus") or raw.get("benefitsInformation") or raw.get("planDateInformation"):
        return _extract_financial_stedi(raw)

    # Detect ClaimMD format (has "benefits" list from XML parse and "eligid")
    if raw.get("benefits") and isinstance(raw.get("benefits"), list) and raw.get("eligid"):
        return _extract_financial_claimmd(raw)

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
        if plan.get("InsurancePlanName"):
            result.setdefault("plan_name", plan["InsurancePlanName"])
        if plan.get("ActiveDate"):
            result.setdefault("coverage_start", plan["ActiveDate"])
        if plan.get("PatientTerminationBenefitDate"):
            result["termination_date"] = plan["PatientTerminationBenefitDate"]
        # Pick up plan-level deductible/copay/coinsurance if present
        # Waystar uses DeductibleInNetwork / DeductibleOutNetwork
        for ded_key in ("Deductible", "DeductibleInNetwork", "PlanBinDed"):
            if plan.get(ded_key) is not None:
                result.setdefault("deductible", _to_float(plan[ded_key]))
                break
        for ded_max_key in ("DeductibleMax", "DeductibleOutNetwork", "PlanBonDed"):
            if plan.get(ded_max_key) is not None:
                result.setdefault("deductible_max", _to_float(plan[ded_max_key]))
                break
        for ded_rem_key in ("PlanBinDedRem",):
            if plan.get(ded_rem_key) is not None:
                result.setdefault("deductible_remaining", _to_float(plan[ded_rem_key]))
                break
        if plan.get("Copay") is not None:
            result.setdefault("copay", _to_float(plan["Copay"]))
        for coins_key in ("Coinsurance", "CoInsuranceInNetwork"):
            if plan.get(coins_key) is not None:
                result.setdefault("coinsurance", _to_float(plan[coins_key]))
                break
        if plan.get("OutOfPocket") is not None:
            result.setdefault("oop", _to_float(plan["OutOfPocket"]))
        if plan.get("OutOfPocketMax") is not None:
            result.setdefault("oop_max", _to_float(plan["OutOfPocketMax"]))
        for oop_rem_key in ("PlaoncenBinOopRem", "PlanBinOopRem"):
            if plan.get(oop_rem_key) is not None:
                result.setdefault("oop_remaining", _to_float(plan[oop_rem_key]))
                break

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
                # Waystar uses BinDed/BinDedRem/BinOop/BinOopRem
                for dk in ("Deductible", "BinDed"):
                    if ind.get(dk) is not None:
                        result.setdefault("deductible", _to_float(ind[dk]))
                        break
                for drk in ("DeductibleRemaining", "BinDedRem"):
                    if ind.get(drk) is not None:
                        result.setdefault("deductible_remaining", _to_float(ind[drk]))
                        break
                for ck in ("Copay", "BinCopay1"):
                    if ind.get(ck) is not None:
                        result.setdefault("copay", _to_float(ind[ck]))
                        break
                for cik in ("Coinsurance", "BinCovgPerc"):
                    if ind.get(cik) is not None:
                        result.setdefault("coinsurance", ind[cik])
                        break
                for ok in ("OutOfPocket", "BinOop"):
                    if ind.get(ok) is not None:
                        result.setdefault("oop", _to_float(ind[ok]))
                        break
                for ork in ("OutOfPocketRemaining", "BinOopRem"):
                    if ind.get(ork) is not None:
                        result.setdefault("oop_remaining", _to_float(ind[ork]))
                        break

            # Family benefits
            fam = svc_data.get("FAM", {})
            if isinstance(fam, dict):
                for fdk in ("Deductible", "BinDed"):
                    if fam.get(fdk) is not None:
                        result.setdefault("family_deductible", _to_float(fam[fdk]))
                        break
                for fok in ("OutOfPocket", "BinOop"):
                    if fam.get(fok) is not None:
                        result.setdefault("family_oop", _to_float(fam[fok]))
                        break

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


def _extract_financial_claimmd(data: dict[str, Any]) -> dict[str, Any]:
    """Extract financial/coverage fields from ClaimMD XML eligibility response.

    ClaimMD returns an <elig> element with patient/plan attributes and nested
    <benefit> elements with coverage codes:
      1=Active Coverage, C=Deductible, G=Out of Pocket, A=Co-Insurance, B=Co-Payment
    """
    result: dict[str, Any] = {}

    # Patient / plan info from <elig> attributes
    result["subscriber_name"] = f"{data.get('ins_name_f', '')} {data.get('ins_name_l', '')}".strip()
    result["patient_dob"] = _format_claimmd_date(data.get("ins_dob", ""))
    result["patient_gender"] = data.get("ins_sex", "")
    result["member_id"] = data.get("ins_number", "")
    result["group_number"] = data.get("group_number", "")
    result["plan_number"] = data.get("plan_number", "")

    # Coverage dates from plan_begin_date (format: YYYYMMDD-YYYYMMDD)
    plan_dates = data.get("plan_begin_date", "")
    if "-" in plan_dates:
        parts = plan_dates.split("-")
        result["coverage_start"] = _format_claimmd_date(parts[0])
        result["coverage_end"] = _format_claimmd_date(parts[1])
    elif plan_dates:
        result["coverage_start"] = _format_claimmd_date(plan_dates)

    benefits = data.get("benefits", [])
    has_active = False

    for b in benefits:
        coverage_code = b.get("benefit_coverage_code", "")
        coverage_desc = b.get("benefit_coverage_description", "").lower()
        level = b.get("benefit_level_code", "").upper()
        amount = _to_float(b.get("benefit_amount"))
        pct = _to_float(b.get("benefit_percent"))
        period = b.get("benefit_period_description", "").lower()
        network = b.get("inplan_network", "")  # Y=in-network, N=out, W=both

        # Active Coverage
        if coverage_code == "1" or "active" in coverage_desc:
            has_active = True
            # Extract plan name and carrier from the first active benefit
            if b.get("insurance_plan"):
                result.setdefault("plan_name", b["insurance_plan"])
            if b.get("insurance_type_description"):
                result.setdefault("insurance_type", b["insurance_type_description"])
            # Extract payer entity info
            for entity in b.get("entities", []):
                if entity.get("entity_code") == "PR":  # Payer
                    result.setdefault("carrier_name", entity.get("entity_name", ""))
                    addr_parts = [entity.get("entity_name", "")]
                    if entity.get("entity_addr_1"):
                        addr_parts.append(entity["entity_addr_1"])
                    city_st = f"{entity.get('entity_city', '')}, {entity.get('entity_state', '')} {entity.get('entity_zip', '')}"
                    addr_parts.append(city_st.strip())
                    result["claims_address"] = " | ".join(p for p in addr_parts if p)

        # Deductible (C) — prefer in-network, calendar year
        if coverage_code == "C" or "deductible" in coverage_desc:
            if amount is not None:
                if level == "IND":
                    if "remaining" in period:
                        result.setdefault("deductible", amount)
                    elif "calendar" in period:
                        if network == "Y" or network == "W":
                            result.setdefault("deductible_max", amount)
                        else:
                            result.setdefault("deductible_max_oon", amount)
                elif level == "FAM":
                    if "calendar" in period and (network == "Y" or network == "W"):
                        result.setdefault("family_deductible", amount)

        # Out of Pocket (G)
        if coverage_code == "G" or "out of pocket" in coverage_desc:
            if amount is not None:
                if level == "IND":
                    if "remaining" in period:
                        result.setdefault("oop", amount)
                    elif "calendar" in period:
                        if network == "Y" or network == "W":
                            result.setdefault("oop_max", amount)
                elif level == "FAM":
                    if "calendar" in period and (network == "Y" or network == "W"):
                        result.setdefault("family_oop", amount)

        # Co-Payment (B) — prefer in-network
        if coverage_code == "B" or "co-payment" in coverage_desc:
            if amount is not None and (network == "Y" or network == "W"):
                # Use the first in-network copay for general service type
                stype = b.get("benefit_code", "")
                if stype in ("30", "98"):  # Health Plan / Office Visit
                    result.setdefault("copay", amount)
                else:
                    result.setdefault("copay", amount)

        # Co-Insurance (A) — prefer in-network
        if coverage_code == "A" or "co-insurance" in coverage_desc:
            if pct is not None and (network == "Y" or network == "W"):
                result.setdefault("coinsurance", pct)

        # Prior Auth Required — benefit_coverage_code "CB" or description
        # contains "authorization" or "precertification"
        benefit_desc = b.get("benefit_description", "").lower()
        benefit_notes = b.get("benefit_notes", "").lower()
        if (
            "authorization" in coverage_desc
            or "precertification" in coverage_desc
            or "authorization" in benefit_desc
            or "precertification" in benefit_desc
            or "auth required" in benefit_notes
            or "prior auth" in benefit_notes
        ):
            result["prior_auth_required"] = True

    # File status
    if has_active:
        result["file_status"] = 1
        result["file_status_desc"] = "ACTIVE"
        result["coverage_status"] = "Active Coverage"
    else:
        result["file_status"] = 2
        result["file_status_desc"] = "INACTIVE"

    return result


def _format_claimmd_date(raw: str) -> str | None:
    """Convert YYYYMMDD to YYYY-MM-DD for ClaimMD dates."""
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw


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


