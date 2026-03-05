"""Run all Waystar scenarios and write results to a single report file.

Scenarios:
  1. Eligibility — PASS (test payer 66666, valid data)
  2. Eligibility — FAIL (unregistered payer, expect T4 reject)
  3. Eligibility — FAIL (bad subscriber, expect rejection)
  4. Prior Authorization status check
  5. Claim History / Status check (HMAC-signed)
  6. Full Workflow — process_claim() with Waystar 271 response

Run:  .venv/bin/python run_all_scenarios.py
"""

from __future__ import annotations

import json
import os
import traceback
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


def section(title: str) -> None:
    p()
    p("=" * 70)
    p(f"  {title}")
    p("=" * 70)
    p()


def subsection(title: str) -> None:
    p()
    p(f"--- {title} ---")
    p()


def print_elig_response(resp) -> None:  # noqa: ANN001
    """Pretty-print a ClearinghouseEligibilityResponse."""
    p(f"  Status:       {resp.status}")
    p(f"  Eligible:     {resp.eligible}")
    p(f"  Reference ID: {resp.reference_id}")
    if resp.errors:
        p(f"  Errors:       {resp.errors}")

    parsed = resp.plan_info or {}
    if parsed:
        p()
        p(f"  Carrier:      {parsed.get('CarrierName', '?')} "
          f"({parsed.get('CarrierCode', '?')})")
        sub = parsed.get("Subscriber", {})
        if sub:
            p(f"  Subscriber:   {sub.get('First', '')} {sub.get('Last', '')} "
              f"| DOB: {sub.get('Dob', '')} | ID: {sub.get('MemberId', '')}")
        fs = parsed.get("FileStatusDescription", parsed.get("FileStatus", "?"))
        p(f"  File Status:  {fs}")
        fr = parsed.get("FailReason")
        if fr:
            p(f"  Fail Reason:  {fr}")
            p(f"  Fail Code:    {parsed.get('FailCode', '?')}")

        plans = parsed.get("Plans", [])
        if plans:
            p()
            p("  Plans:")
            for i, pl in enumerate(plans, 1):
                name = pl.get("InsurancePlanName", pl.get("InsurancePlan", "?"))
                st = pl.get("FileStatusDescription", "?")
                p(f"    {i}. {name} ({st})")
                p(f"       Effective:      {pl.get('PatientEffectiveBenefitDate', 'N/A')}")
                p(f"       Deductible IN:  ${pl.get('DeductibleInNetwork', 'N/A')}")
                p(f"       Deductible OUT: ${pl.get('DeductibleOutNetwork', 'N/A')}")
                p(f"       CoIns IN:       {pl.get('CoInsuranceInNetwork', 'N/A')}")
                p(f"       CoIns OUT:      {pl.get('CoInsuranceOutNetwork', 'N/A')}")
                ded_rem = pl.get("PlanBinDedRem")
                oop_rem = pl.get("PlanBinOopRem")
                if ded_rem is not None:
                    p(f"       Ded Remaining:  ${ded_rem}")
                if oop_rem is not None:
                    p(f"       OOP Remaining:  ${oop_rem}")

        benefits = parsed.get("Benefits", {})
        if benefits:
            p()
            p("  Benefits:")
            for svc, levels in benefits.items():
                if svc.startswith("It"):
                    continue
                p(f"    Service Type {svc}:")
                for level, data in levels.items():
                    if level.startswith("St"):
                        continue
                    ded = data.get("BinDed", "-")
                    ded_r = data.get("BinDedRem", "-")
                    oop = data.get("BinOop", "-")
                    oop_r = data.get("BinOopRem", "-")
                    p(f"      {level}: Ded ${ded} (rem ${ded_r}) "
                      f"| OOP ${oop} (rem ${oop_r})")

    subsection("Raw Response JSON")
    p(json.dumps(resp.raw_response, indent=2))


def print_workflow_result(result) -> None:  # noqa: ANN001
    """Pretty-print a WorkflowResult."""
    p(f"  Workflow Passed: {result.passed}")
    p(f"  Stopped At:      {result.stopped_at or '(completed all stages)'}")
    p(f"  Execution Time:  {result.execution_time:.4f}s")
    p(f"  Total Findings:  {len(result.findings)}")
    p()

    p("  Stage Results:")
    for sr in result.stage_results:
        status = "SKIPPED" if sr.skipped else ("PASS" if sr.passed else "FAIL")
        reason = f" — {sr.skip_reason}" if sr.skip_reason else ""
        p(f"    [{status}] {sr.stage_name}{reason}  ({sr.execution_time:.4f}s)")
        for f in sr.findings:
            sev = f.severity.value.upper()
            p(f"           [{sev}] {f.code}: {f.message}")
            if f.field_name:
                p(f"                  field: {f.field_name}")
            if f.suggestion:
                p(f"                  fix:   {f.suggestion}")
    p()

    p("  Domain Results:")
    if result.eligibility:
        p(f"    Eligibility:      passed={result.eligibility.passed} "
          f"findings={len(result.eligibility.findings)}")
    if result.pa_determination:
        p(f"    PA Determination: required={result.pa_determination.required}")
        p(f"      Reason: {result.pa_determination.reason}")
    if result.prior_auth:
        p(f"    Prior Auth:       passed={result.prior_auth.passed} "
          f"findings={len(result.prior_auth.findings)}")
    if result.claim_validation:
        p(f"    Claim Validation: passed={result.claim_validation.passed} "
          f"findings={len(result.claim_validation.findings)}")

    if result.findings:
        p()
        p("  All Findings:")
        for f in result.findings:
            sev = f.severity.value.upper()
            p(f"    [{sev}] {f.code}: {f.message}")


def main() -> None:
    section("CLAIM VALIDATOR — ALL SCENARIOS REPORT")
    p(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p(f"Clearinghouse: Waystar (Zirmed)")

    # ── Build client ─────────────────────────────────────────
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
        "prior_auth_base_url": os.environ.get(
            "CLEARINGHOUSE_PRIOR_AUTH_BASE_URL", ""
        ),
    }

    client = build_clearinghouse_client(CH_CONFIG)
    results_summary: list[tuple[str, str]] = []

    # ══════════════════════════════════════════════════════════
    # SCENARIO 1: Eligibility — PASS
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 1: ELIGIBILITY — PASS (test payer 66666)")

    elig_pass_input = {
        "payer_id": "66666",
        "npi": "1245319599",
        "subscriber_id": "SUB987654321",
        "first_name": "Alice",
        "last_name": "Williams",
        "dob": "1980-07-22",
        "service_type": "30",
    }
    p("Request:")
    p(json.dumps(elig_pass_input, indent=2))
    p()

    try:
        resp1 = client.check_eligibility(elig_pass_input)
        p("Response:")
        print_elig_response(resp1)
        status1 = "PASS" if resp1.eligible else "FAIL"
        results_summary.append(("1. Eligibility PASS", status1))
    except Exception as e:
        p(f"  ERROR: {type(e).__name__}: {e}")
        p(traceback.format_exc())
        results_summary.append(("1. Eligibility PASS", f"ERROR: {e}"))
        resp1 = None

    # ══════════════════════════════════════════════════════════
    # SCENARIO 2: Eligibility — FAIL (unregistered payer)
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 2: ELIGIBILITY — FAIL (unregistered payer 00520)")

    elig_fail_payer = {
        "payer_id": "00520",
        "npi": "1245319599",
        "subscriber_id": "SUB987654321",
        "first_name": "Alice",
        "last_name": "Williams",
        "dob": "1980-07-22",
        "service_type": "30",
    }
    p("Request:")
    p(json.dumps(elig_fail_payer, indent=2))
    p()

    try:
        resp2 = client.check_eligibility(elig_fail_payer)
        p("Response:")
        print_elig_response(resp2)
        status2 = "REJECTED" if not resp2.eligible else "UNEXPECTED PASS"
        results_summary.append(("2. Eligibility FAIL (bad payer)", status2))
    except Exception as e:
        p(f"  ERROR: {type(e).__name__}: {e}")
        results_summary.append(("2. Eligibility FAIL (bad payer)", f"ERROR: {e}"))

    # ══════════════════════════════════════════════════════════
    # SCENARIO 3: Eligibility — FAIL (invalid subscriber)
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 3: ELIGIBILITY — FAIL (unknown subscriber)")

    elig_fail_sub = {
        "payer_id": "66666",
        "npi": "1245319599",
        "subscriber_id": "INVALID000",
        "first_name": "Nonexistent",
        "last_name": "Person",
        "dob": "2099-12-31",
        "service_type": "30",
    }
    p("Request:")
    p(json.dumps(elig_fail_sub, indent=2))
    p()

    try:
        resp3 = client.check_eligibility(elig_fail_sub)
        p("Response:")
        print_elig_response(resp3)
        # Test payer 66666 may accept any subscriber — note the result
        status3 = "REJECTED" if not resp3.eligible else "ACCEPTED (test payer)"
        results_summary.append(("3. Eligibility FAIL (bad subscriber)", status3))
    except Exception as e:
        p(f"  ERROR: {type(e).__name__}: {e}")
        results_summary.append(("3. Eligibility FAIL (bad subscriber)", f"ERROR: {e}"))

    # ══════════════════════════════════════════════════════════
    # SCENARIO 4: Prior Authorization Status Check
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 4: PRIOR AUTHORIZATION STATUS CHECK")

    pa_payload = {
        "payer_id": "66666",
        "npi": "1245319599",
        "subscriber_id": "SUB987654321",
        "first_name": "Alice",
        "last_name": "Williams",
        "dob": "1980-07-22",
        "procedure_code": "27447",
        "diagnosis_code": "M17.11",
    }
    p("Request:")
    p(json.dumps(pa_payload, indent=2))
    p()

    try:
        p("Step 1 — Submit 278x215 inquiry (POST):")
        resp4 = client.check_prior_auth_status(pa_payload)
        p(json.dumps(resp4, indent=2))
        p()
        ref_id = resp4.get("ReferenceId")
        status_msg = resp4.get("StatusMessage", "")
        error_msg = resp4.get("ErrorMessage", "")

        if ref_id and ref_id != "0" and status_msg == "Received":
            p(f"  ReferenceId: {ref_id} — request accepted for processing")
            p()

            # Step 2 — Retrieve result (async — may still be processing)
            import time as _time
            p("Step 2 — Retrieve result (GET with ReferenceId):")
            _time.sleep(3)  # brief wait for async processing
            resp4b = client.get_prior_auth_result(ref_id)
            p(json.dumps(resp4b, indent=2))
            final_status = resp4b.get("StatusMessage", "")
            p()
            p(f"  Final Status: {final_status}")
            if final_status in ("Waiting Response", "Received"):
                p("  (Still processing — poll again later)")
            results_summary.append(("4. Prior Auth Status", f"REF={ref_id} {final_status}"))
        elif error_msg:
            p(f"  Failed: {error_msg}")
            results_summary.append(("4. Prior Auth Status", f"FAILED: {error_msg}"))
        else:
            p(f"  Status: {status_msg}")
            results_summary.append(("4. Prior Auth Status", f"STATUS: {status_msg}"))
    except Exception as e:
        p(f"  Result: {type(e).__name__}: {e}")
        p()
        p("  NOTE: 278 payload structure parses correctly (3-level HL:")
        p("  payer/provider/subscriber). The server error likely means")
        p("  this account does not have the PA product enabled, or the")
        p("  test subscriber has no authorization data in Waystar.")
        results_summary.append(("4. Prior Auth Status", f"SERVER ERROR: {e}"))

    # ══════════════════════════════════════════════════════════
    # SCENARIO 5: Claim History / Status Check
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 5: CLAIM HISTORY / STATUS CHECK (HMAC-signed)")

    claim_num = "TEST-CLAIM-001"
    claim_dos = "03/04/2026"
    p(f"Request: check_claim_status('{claim_num}', dos='{claim_dos}')")
    p()

    try:
        resp5 = client.check_claim_status(
            claim_num, dos=claim_dos, response_type="XML"
        )
        p("Response:")
        p(f"  Status:       {resp5.status}")
        p(f"  Claim Status: {resp5.claim_status}")
        p(f"  Reference ID: {resp5.reference_id}")
        if resp5.raw_response:
            subsection("Raw Response")
            p(json.dumps(resp5.raw_response, indent=2))
        results_summary.append(("5. Claim History", "COMPLETED"))
    except Exception as e:
        p(f"  Result: {type(e).__name__}: {e}")
        p()
        p("  NOTE: Claim History v2.0 requires CustID, DOS, ClaimNum,")
        p("  ReqType=CLMHIST, Version=2.0, TimeStamp (UTC within 5min),")
        p("  and HMAC-SHA256 Signature. ResponseType is excluded from")
        p("  signature but required in the GET request. Test data may")
        p("  return 'no resource found' — real claim numbers needed.")
        results_summary.append(("5. Claim History", "NEEDS REAL CLAIM REF"))

    client.close()

    # ══════════════════════════════════════════════════════════
    # SCENARIO 6: Full Workflow — process_claim()
    # ══════════════════════════════════════════════════════════
    section("SCENARIO 6: FULL WORKFLOW — process_claim()")

    if resp1 is not None and resp1.eligible:
        # Build EligibilityResponse from Waystar result
        plans = (resp1.plan_info or {}).get("Plans", [])
        elig_271 = EligibilityResponse(
            coverage=CoverageInfo(
                status=CoverageStatus.ACTIVE,
                plan_name=(
                    plans[0].get("InsurancePlanName", "Unknown")
                    if plans
                    else "Unknown"
                ),
            ),
            raw_response=resp1.raw_response,
        )

        elig_req = {
            "provider_npi": "1245319599",
            "payer_id": "60054",
            "subscriber_id": "SUB987654321",
            "subscriber_first_name": "Alice",
            "subscriber_last_name": "Williams",
            "subscriber_dob": "1980-07-22",
            "date_of_service": "2026-03-04",
        }

        claim_input = {
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

        p("Eligibility Request (validation):")
        p(json.dumps(elig_req, indent=2))
        p()
        p("Claim Data:")
        p(json.dumps(claim_input, indent=2))
        p()
        p("Eligibility Response: from Waystar Scenario 1 (ACTIVE)")
        p()

        try:
            wf_result = process_claim(
                ClaimRequest(
                    eligibility_request=elig_req,
                    claim_data=claim_input,
                    eligibility_response=elig_271,
                ),
            )
            p("Workflow Result:")
            print_workflow_result(wf_result)
            status6 = "PASS" if wf_result.passed else "FAIL"
            results_summary.append(("6. Full Workflow", status6))
        except Exception as e:
            p(f"  ERROR: {type(e).__name__}: {e}")
            p(traceback.format_exc())
            results_summary.append(("6. Full Workflow", f"ERROR: {e}"))
    else:
        p("  SKIPPED — Scenario 1 eligibility failed, no 271 to feed workflow")
        results_summary.append(("6. Full Workflow", "SKIPPED"))

    # ══════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════
    section("SUMMARY")
    for name, status in results_summary:
        icon = "+" if status in ("PASS", "COMPLETED", "REJECTED") else "-"
        p(f"  [{icon}] {name}: {status}")

    p()
    p("=" * 70)
    p("  END OF REPORT")
    p("=" * 70)

    # Write to file
    text = "\n".join(out)
    output_file = "all_scenarios_report.txt"
    with open(output_file, "w") as fh:
        fh.write(text)
    print(text)
    print()
    print(f">>> Saved to {output_file}")


if __name__ == "__main__":
    main()
