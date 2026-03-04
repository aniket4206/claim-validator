"""Generate full workflow report: Waystar eligibility + process_claim()."""

from __future__ import annotations

import json
import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from claim_validator import (
    ClaimRequest,
    CoverageInfo,
    CoverageStatus,
    EligibilityResponse,
    build_clearinghouse_client,
    process_claim,
)

out: list[str] = []


def p(s: str = "") -> None:
    out.append(s)


def main() -> None:
    p("=" * 70)
    p("  CLAIM VALIDATOR — FULL WORKFLOW REPORT")
    p(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p("=" * 70)
    p()

    # ── Build Waystar client ─────────────────────────────────
    CH_CONFIG = {
        "provider": os.environ["CLEARINGHOUSE_PROVIDER"],
        "api_key": os.environ["CLEARINGHOUSE_API_KEY"],
        "user_id": os.environ.get("CLEARINGHOUSE_USER_ID", ""),
        "password": os.environ.get("CLEARINGHOUSE_PASSWORD", ""),
        "cust_id": os.environ.get("CLEARINGHOUSE_CUST_ID", ""),
        "base_url": os.environ.get("CLEARINGHOUSE_BASE_URL", ""),
        "eligibility_base_url": os.environ.get(
            "CLEARINGHOUSE_ELIGIBILITY_BASE_URL", ""
        ),
    }

    # ── Input Data ───────────────────────────────────────────
    elig_input = {
        "payer_id": "66666",
        "npi": "1245319599",
        "subscriber_id": "SUB987654321",
        "first_name": "Alice",
        "last_name": "Williams",
        "dob": "1980-07-22",
        "service_type": "30",
    }

    elig_request_data = {
        "provider_npi": "1245319599",
        "payer_id": "60054",
        "subscriber_id": "SUB987654321",
        "subscriber_first_name": "Alice",
        "subscriber_last_name": "Williams",
        "subscriber_dob": "1980-07-22",
        "date_of_service": "2026-03-04",
    }

    claim_data = {
        "claim_type": "professional",
        "billing_provider_npi": "1245319599",
        "payer_id": "60054",
        "subscriber_id": "SUB987654321",
        "patient_first_name": "Alice",
        "patient_last_name": "Williams",
        "patient_dob": "1980-07-22",
        "patient_gender": "F",
        "service_date": "2026-03-04",
        "diagnosis_codes": [{"code": "J06.9"}],
        "lines": [
            {
                "procedure_code": "99213",
                "charge_amount": 150.0,
                "units": 1.0,
                "diagnosis_pointers": [1],
                "service_date_from": "2026-03-04",
                "place_of_service": "11",
            },
        ],
    }

    p("INPUT DATA")
    p("-" * 70)
    p()
    p("Eligibility Request (Waystar 270):")
    p(json.dumps(elig_input, indent=2))
    p()
    p("Eligibility Request (Validation):")
    p(json.dumps(elig_request_data, indent=2))
    p()
    p("Claim Data:")
    p(json.dumps(claim_data, indent=2))
    p()

    # ── STEP 1: Waystar Eligibility ──────────────────────────
    p("=" * 70)
    p("  STEP 1: WAYSTAR ELIGIBILITY CHECK (270/271)")
    p("=" * 70)
    p()

    client = build_clearinghouse_client(CH_CONFIG)
    waystar_elig = client.check_eligibility(elig_input)
    client.close()

    p(f"Status:       {waystar_elig.status}")
    p(f"Eligible:     {waystar_elig.eligible}")
    p(f"Reference ID: {waystar_elig.reference_id}")
    p()

    parsed = waystar_elig.plan_info
    p(f"Carrier:      {parsed.get('CarrierName')} ({parsed.get('CarrierCode')})")
    p(
        f"Address:      {parsed.get('CarrierAddress1')}, "
        f"{parsed.get('CarrierCity')}, {parsed.get('CarrierState')} "
        f"{parsed.get('CarrierZip')}"
    )
    sub = parsed.get("Subscriber", {})
    p(
        f"Subscriber:   {sub.get('First')} {sub.get('Last')} | "
        f"DOB: {sub.get('Dob')} | ID: {sub.get('MemberId')}"
    )
    p(f"File Status:  {parsed.get('FileStatusDescription')}")
    p()

    plans = parsed.get("Plans", [])
    p("Plans:")
    for pi, pl in enumerate(plans, 1):
        name = pl.get("InsurancePlanName", pl.get("InsurancePlan", "?"))
        status = pl.get("FileStatusDescription", "?")
        p(f"  Plan {pi}: {name}")
        p(f"    Status:          {status}")
        p(f"    Effective:       {pl.get('PatientEffectiveBenefitDate', 'N/A')}")
        p(f"    Deductible IN:   ${pl.get('DeductibleInNetwork', 'N/A')}")
        p(f"    Deductible OUT:  ${pl.get('DeductibleOutNetwork', 'N/A')}")
        p(f"    CoInsurance IN:  {pl.get('CoInsuranceInNetwork', 'N/A')}")
        p(f"    CoInsurance OUT: {pl.get('CoInsuranceOutNetwork', 'N/A')}")
        ded_rem = pl.get("PlanBinDedRem")
        oop_rem = pl.get("PlanBinOopRem")
        if ded_rem is not None:
            p(f"    Ded Remaining:   ${ded_rem}")
        if oop_rem is not None:
            p(f"    OOP Remaining:   ${oop_rem}")
        p()

    benefits = parsed.get("Benefits", {})
    if benefits:
        p("Benefits Detail:")
        for svc_type, levels in benefits.items():
            if svc_type.startswith("It"):
                continue
            p(f"  Service Type {svc_type}:")
            for level, data in levels.items():
                if level.startswith("St"):
                    continue
                ded = data.get("BinDed", "-")
                ded_rem = data.get("BinDedRem", "-")
                oop = data.get("BinOop", "-")
                oop_rem = data.get("BinOopRem", "-")
                p(
                    f"    {level}: Deductible ${ded} (remaining ${ded_rem})"
                    f" | OOP ${oop} (remaining ${oop_rem})"
                )
        p()

    p("Waystar Raw Response (JSON):")
    p(json.dumps(waystar_elig.raw_response, indent=2))
    p()

    # ── STEP 2: Full Workflow ────────────────────────────────
    elig_271 = EligibilityResponse(
        coverage=CoverageInfo(
            status=CoverageStatus.ACTIVE,
            plan_name=(
                plans[0].get("InsurancePlanName", "Unknown") if plans else "Unknown"
            ),
        ),
        raw_response=waystar_elig.raw_response,
    )

    result = process_claim(
        ClaimRequest(
            eligibility_request=elig_request_data,
            claim_data=claim_data,
            eligibility_response=elig_271,
        ),
    )

    p("=" * 70)
    p("  STEP 2: WORKFLOW RESULT — process_claim()")
    p("=" * 70)
    p()
    p(f"Workflow Passed: {result.passed}")
    p(f"Stopped At:      {result.stopped_at or '(completed all stages)'}")
    p(f"Execution Time:  {result.execution_time:.4f}s")
    p(f"Total Findings:  {len(result.findings)}")
    p()

    p("-" * 70)
    p("STAGE RESULTS")
    p("-" * 70)
    for sr in result.stage_results:
        status = "SKIPPED" if sr.skipped else ("PASS" if sr.passed else "FAIL")
        reason = f" — {sr.skip_reason}" if sr.skip_reason else ""
        p(f"  [{status}] {sr.stage_name}{reason}  ({sr.execution_time:.4f}s)")
        for f in sr.findings:
            sev = f.severity.value.upper()
            p(f"         [{sev}] {f.code}: {f.message}")
            if f.field_name:
                p(f"                field: {f.field_name}")
            if f.suggestion:
                p(f"                fix:   {f.suggestion}")
    p()

    p("-" * 70)
    p("DOMAIN RESULTS")
    p("-" * 70)
    if result.eligibility:
        p(
            f"  Eligibility:      passed={result.eligibility.passed}"
            f"  findings={len(result.eligibility.findings)}"
        )
        p(f"    Time: {result.eligibility.execution_time:.4f}s")
    if result.pa_determination:
        p(f"  PA Determination: required={result.pa_determination.required}")
        p(f"    Reason: {result.pa_determination.reason}")
    if result.prior_auth:
        p(
            f"  Prior Auth:       passed={result.prior_auth.passed}"
            f"  findings={len(result.prior_auth.findings)}"
        )
    if result.claim_validation:
        p(
            f"  Claim Validation: passed={result.claim_validation.passed}"
            f"  findings={len(result.claim_validation.findings)}"
        )
        p(f"    Time: {result.claim_validation.execution_time:.4f}s")
    p()

    if result.findings:
        p("-" * 70)
        p("ALL FINDINGS (sorted by severity)")
        p("-" * 70)
        for f in result.findings:
            sev = f.severity.value.upper()
            p(f"  [{sev}] {f.code}: {f.message}")
            if f.field_name:
                p(f"         field: {f.field_name}")
            if f.suggestion:
                p(f"         fix:   {f.suggestion}")
        p()

    p("=" * 70)
    p("  END OF REPORT")
    p("=" * 70)

    text = "\n".join(out)
    with open("workflow_report.txt", "w") as fh:
        fh.write(text)
    print(text)
    print()
    print(">>> Saved to workflow_report.txt")


if __name__ == "__main__":
    main()
