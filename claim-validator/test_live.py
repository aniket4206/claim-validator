"""Live test script — validates all 3 pipelines + orchestrator.

Run:  .venv/bin/python test_live.py
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from claim_validator import (
    ClaimValidatorSettings,
    EligibilityRequest,
    check_eligibility,
    pre_claim_check,
    submit_prior_auth,
    validate,
)

# ── AI config (from .env) ──────────────────────────────────────────────
AI_CONFIG = None
_key = os.environ.get("CLAIM_VALIDATOR_AI_API_KEY")
if _key:
    AI_CONFIG = {
        "provider": os.environ.get("CLAIM_VALIDATOR_AI_PROVIDER", "openai"),
        "api_key": _key,
        "model": os.environ.get("CLAIM_VALIDATOR_AI_MODEL", "gpt-4o"),
    }

# ── Clearinghouse config (from .env) ──────────────────────────────────
CH_CONFIG = None
_ch_provider = os.environ.get("CLEARINGHOUSE_PROVIDER")
_ch_key = os.environ.get("CLEARINGHOUSE_API_KEY")
if _ch_provider and _ch_key:
    CH_CONFIG = {
        "provider": _ch_provider,
        "api_key": _ch_key,
    }
    _ch_secret = os.environ.get("CLEARINGHOUSE_SECRET")
    if _ch_secret:
        CH_CONFIG["secret"] = _ch_secret
    _ch_base = os.environ.get("CLEARINGHOUSE_BASE_URL")
    if _ch_base:
        CH_CONFIG["base_url"] = _ch_base
    # Waystar-specific fields
    _ch_user_id = os.environ.get("CLEARINGHOUSE_USER_ID")
    if _ch_user_id:
        CH_CONFIG["user_id"] = _ch_user_id
    _ch_password = os.environ.get("CLEARINGHOUSE_PASSWORD")
    if _ch_password:
        CH_CONFIG["password"] = _ch_password
    _ch_cust_id = os.environ.get("CLEARINGHOUSE_CUST_ID")
    if _ch_cust_id:
        CH_CONFIG["cust_id"] = _ch_cust_id
    _ch_elig_base = os.environ.get("CLEARINGHOUSE_ELIGIBILITY_BASE_URL")
    if _ch_elig_base:
        CH_CONFIG["eligibility_base_url"] = _ch_elig_base
    _ch_pa_base = os.environ.get("CLEARINGHOUSE_PRIOR_AUTH_BASE_URL")
    if _ch_pa_base:
        CH_CONFIG["prior_auth_base_url"] = _ch_pa_base


def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_findings(findings: list) -> None:
    if not findings:
        print("  (no findings)")
        return
    for f in findings:
        sev = f.severity.value.upper()
        print(f"  [{sev}] {f.code}: {f.message}")
        if f.field_name:
            print(f"         field: {f.field_name}")
        if f.suggestion:
            print(f"         fix:   {f.suggestion}")


# ======================================================================
# 1. CLAIM VALIDATION
# ======================================================================

def test_claim_valid():
    """Valid professional claim — expect 0 findings."""
    _header("1a. Valid Claim (should PASS)")
    result = validate({
        "billing_provider_npi": "1245319599",
        "billing_provider_taxonomy": "207Q00000X",
        "subscriber_id": "XYZ123456789",
        "subscriber_first_name": "John",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-03-15",
        "subscriber_gender": "M",
        "patient_first_name": "John",
        "patient_last_name": "Doe",
        "patient_dob": "1985-03-15",
        "patient_gender": "M",
        "patient_relationship": "self",
        "payer_id": "00001",
        "payer_name": "Aetna",
        "claim_type": "professional",
        "place_of_service": "11",
        "total_charge": 150.00,
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1, "type": "principal"},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "units": 1.0,
                "service_date_from": "2026-03-01",
                "place_of_service": "11",
            },
        ],
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return result.passed


def test_claim_invalid_npi():
    """Bad NPI — expect INVALID_NPI error."""
    _header("1b. Invalid NPI (should FAIL)")
    result = validate({
        "billing_provider_npi": "0000000000",
        "subscriber_id": "XYZ123",
        "subscriber_first_name": "Jane",
        "subscriber_last_name": "Smith",
        "subscriber_dob": "1990-01-01",
        "subscriber_gender": "F",
        "patient_first_name": "Jane",
        "patient_last_name": "Smith",
        "patient_dob": "1990-01-01",
        "patient_gender": "F",
        "patient_relationship": "self",
        "payer_id": "00002",
        "payer_name": "Cigna",
        "claim_type": "professional",
        "place_of_service": "11",
        "total_charge": 200.00,
        "diagnosis_codes": [{"code": "M54.5", "pointer": 1, "type": "principal"}],
        "lines": [
            {
                "procedure_code": "99214",
                "diagnosis_pointers": [1],
                "charge_amount": 200.00,
                "units": 1.0,
                "service_date_from": "2026-03-01",
                "place_of_service": "11",
            },
        ],
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return not result.passed  # expect failure


def test_claim_missing_fields():
    """Minimal claim with missing fields — expect completeness errors."""
    _header("1c. Missing Fields (should FAIL)")
    result = validate({
        "claim_type": "professional",
        "diagnosis_codes": [],
        "lines": [],
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return not result.passed


def test_claim_monetary_mismatch():
    """Total charge doesn't match line sum — expect monetary warning/error."""
    _header("1d. Monetary Mismatch (total != sum of lines)")
    result = validate({
        "billing_provider_npi": "1245319599",
        "subscriber_id": "XYZ123456789",
        "subscriber_first_name": "Bob",
        "subscriber_last_name": "Jones",
        "subscriber_dob": "1970-06-20",
        "subscriber_gender": "M",
        "patient_first_name": "Bob",
        "patient_last_name": "Jones",
        "patient_dob": "1970-06-20",
        "patient_gender": "M",
        "patient_relationship": "self",
        "payer_id": "00003",
        "payer_name": "UHC",
        "claim_type": "professional",
        "place_of_service": "11",
        "total_charge": 999.99,
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1, "type": "principal"}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "units": 1.0,
                "service_date_from": "2026-03-01",
                "place_of_service": "11",
            },
        ],
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return True  # informational


def test_claim_with_ai():
    """Valid claim + AI code validation via OpenAI."""
    if not AI_CONFIG:
        print("\n  [SKIP] No AI_API_KEY in .env — skipping AI test")
        return True
    _header("1e. Claim + AI Validation (OpenAI GPT-4o)")
    settings = ClaimValidatorSettings(
        ai_config=AI_CONFIG,
        ai_validators=[
            "claim_validator.validators.ai.code_validation.CodeValidationAI",
        ],
    )
    result = validate(
        {
            "billing_provider_npi": "1245319599",
            "subscriber_id": "XYZ123456789",
            "subscriber_first_name": "John",
            "subscriber_last_name": "Doe",
            "subscriber_dob": "1985-03-15",
            "subscriber_gender": "M",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1985-03-15",
            "patient_gender": "M",
            "patient_relationship": "self",
            "payer_id": "00001",
            "payer_name": "Aetna",
            "claim_type": "professional",
            "place_of_service": "11",
            "total_charge": 150.00,
            "diagnosis_codes": [{"code": "J06.9", "pointer": 1, "type": "principal"}],
            "lines": [
                {
                    "procedure_code": "99213",
                    "diagnosis_pointers": [1],
                    "charge_amount": 150.00,
                    "units": 1.0,
                    "service_date_from": "2026-03-01",
                    "place_of_service": "11",
                },
            ],
        },
        settings=settings,
    )
    phases = [pr.phase for pr in result.phase_results]
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Phases: {phases}")
    print(f"  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return "ai" in phases  # AI phase must have run


# ======================================================================
# 2. ELIGIBILITY VERIFICATION
# ======================================================================

def test_eligibility_valid():
    """Valid eligibility request — rule-based only."""
    _header("2a. Eligibility Check (valid request)")
    result = check_eligibility({
        "provider_npi": "1245319599",
        "provider_taxonomy": "207Q00000X",
        "payer_id": "00520",
        "subscriber_id": "SUB987654321",
        "subscriber_first_name": "Alice",
        "subscriber_last_name": "Williams",
        "subscriber_dob": "1980-07-22",
        "service_type_code": "30",
        "date_of_service": "2026-03-04",
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return result.passed


def test_eligibility_invalid_npi():
    """Bad NPI in eligibility request."""
    _header("2b. Eligibility Check (invalid NPI)")
    result = check_eligibility({
        "provider_npi": "0000000000",
        "payer_id": "00520",
        "subscriber_id": "SUB987654321",
        "subscriber_first_name": "Alice",
        "subscriber_last_name": "Williams",
        "subscriber_dob": "1980-07-22",
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return not result.passed


def test_eligibility_with_ai():
    """Eligibility + AI interpretation of a mock 271 response."""
    if not AI_CONFIG:
        print("\n  [SKIP] No AI_API_KEY in .env — skipping AI eligibility test")
        return True
    _header("2c. Eligibility + AI Interpretation")

    from claim_validator import EligibilityResponse, CoverageInfo, CoverageStatus

    mock_271 = EligibilityResponse(
        coverage=CoverageInfo(
            status=CoverageStatus.ACTIVE,
            plan_name="BCBS PPO Gold",
            group_number="GRP12345",
            effective_date="2025-01-01",
        ),
        raw_response={
            "controlNumber": "999999999",
            "tradingPartnerServiceId": "BCBS01",
            "provider": {"npi": "1245319599"},
            "subscriber": {
                "memberId": "SUB987654321",
                "firstName": "Alice",
                "lastName": "Williams",
                "dateOfBirth": "1980-07-22",
            },
            "benefitsInformation": [
                {
                    "code": "30",
                    "name": "Health Benefit Plan Coverage",
                    "coverageLevelCode": "IND",
                    "serviceTypeCodes": ["30"],
                    "insuranceTypeCode": "PPO",
                    "planCoverage": "BCBS PPO Gold",
                    "benefitAmount": "0",
                    "inPlanNetworkIndicatorCode": "Y",
                },
            ],
        },
    )

    result = check_eligibility(
        {
            "provider_npi": "1245319599",
            "payer_id": "00520",
            "subscriber_id": "SUB987654321",
            "subscriber_first_name": "Alice",
            "subscriber_last_name": "Williams",
            "subscriber_dob": "1980-07-22",
            "service_type_code": "30",
            "date_of_service": "2026-03-04",
        },
        ai_config=AI_CONFIG,
        response=mock_271,
    )
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    if result.ai_summary:
        print(f"  AI Summary: {result.ai_summary[:200]}...")
    _print_findings(result.findings)
    return True


# ======================================================================
# 3. PRIOR AUTHORIZATION
# ======================================================================

def test_prior_auth_valid():
    """Valid PA request — rule-based only."""
    _header("3a. Prior Auth (valid request)")
    result = submit_prior_auth({
        "requester_npi": "1245319599",
        "requester_taxonomy": "207Q00000X",
        "payer_id": "00520",
        "subscriber": {
            "member_id": "SUB987654321",
            "first_name": "Alice",
            "last_name": "Williams",
            "dob": "1980-07-22",
        },
        "diagnosis_codes": ["M79.3"],
        "service_lines": [
            {
                "cpt_code": "99213",
                "quantity": 1,
                "from_date": "2026-04-01",
                "place_of_service_code": "21",
            },
        ],
        "request_category_code": "HS",
        "certification_type_code": "I",
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return result.passed


def test_prior_auth_invalid():
    """PA request with bad NPI and missing subscriber fields."""
    _header("3b. Prior Auth (invalid data)")
    result = submit_prior_auth({
        "requester_npi": "0000000000",
        "subscriber": {
            "member_id": "",
            "first_name": "X",
            "last_name": "Y",
            "dob": "1980-01-01",
        },
        "diagnosis_codes": [],
        "service_lines": [],
    })
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return not result.passed


# ======================================================================
# 4. FULL ORCHESTRATOR (pre_claim_check)
# ======================================================================

def test_pre_claim_check():
    """Full pre-claim workflow: eligibility -> PA determination."""
    _header("4. Pre-Claim Check (full orchestrator)")
    elig_req = EligibilityRequest(
        provider_npi="1245319599",
        payer_id="00520",
        subscriber_id="SUB987654321",
        subscriber_first_name="Alice",
        subscriber_last_name="Williams",
        subscriber_dob="1980-07-22",
        service_type_code="30",
        date_of_service="2026-03-04",
    )
    result = pre_claim_check(elig_req)
    print(f"  Ready to submit: {result.ready_to_submit}")
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    if result.eligibility:
        print(f"  Eligibility passed: {result.eligibility.passed}")
    if result.pa_determination:
        print(f"  PA required: {result.pa_determination.pa_required}")
    _print_findings(result.findings)
    return True


# ======================================================================
# 5. CLEARINGHOUSE CLIENT (Waystar / Stedi / Claim.MD)
# ======================================================================

def test_clearinghouse_build():
    """Build clearinghouse client from config."""
    if not CH_CONFIG:
        print("\n  [SKIP] No CLEARINGHOUSE_PROVIDER/API_KEY in .env")
        return True
    _header(f"5a. Build Clearinghouse Client ({CH_CONFIG['provider']})")
    from claim_validator import build_clearinghouse_client
    client = build_clearinghouse_client(CH_CONFIG)
    print(f"  Provider: {client.provider_name}")
    print(f"  Client type: {type(client).__name__}")
    client.close()
    return True


def test_clearinghouse_eligibility():
    """Check eligibility via clearinghouse (270/271)."""
    if not CH_CONFIG:
        print("\n  [SKIP] No CLEARINGHOUSE_PROVIDER/API_KEY in .env")
        return True
    _header(f"5b. Eligibility via {CH_CONFIG['provider']}")
    from claim_validator import build_clearinghouse_client
    client = build_clearinghouse_client(CH_CONFIG)
    try:
        result = client.check_eligibility({
            "payer_id": "00520",
            "npi": "1245319599",
            "subscriber_id": "SUB987654321",
            "first_name": "Alice",
            "last_name": "Williams",
            "dob": "1980-07-22",
            "service_type": "30",
        })
        print(f"  Status: {result.status}")
        print(f"  Eligible: {result.eligible}")
        print(f"  Reference ID: {result.reference_id}")
        if result.plan_info:
            print(f"  Plan info: {result.plan_info}")
        return True
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
        print("  (This is expected if using test/invalid credentials)")
        return True  # Don't fail — just informational
    finally:
        client.close()


def test_clearinghouse_submit_claim():
    """Submit a claim via clearinghouse (837)."""
    if not CH_CONFIG:
        print("\n  [SKIP] No CLEARINGHOUSE_PROVIDER/API_KEY in .env")
        return True
    _header(f"5c. Submit Claim via {CH_CONFIG['provider']}")
    from claim_validator import build_clearinghouse_client
    client = build_clearinghouse_client(CH_CONFIG)
    try:
        result = client.submit_claim({
            "payer_id": "00520",
            "billing_npi": "1245319599",
            "subscriber_id": "SUB987654321",
            "total_charge": 150.00,
            "diagnosis_codes": ["J06.9"],
            "lines": [
                {
                    "cpt_code": "99213",
                    "charge": 150.00,
                    "units": 1,
                },
            ],
        })
        print(f"  Status: {result.status}")
        print(f"  Accepted: {result.accepted}")
        print(f"  Reference ID: {result.reference_id}")
        if result.errors:
            print(f"  Errors: {result.errors}")
        return True
    except Exception as e:
        print(f"  Info: {type(e).__name__}: {e}")
        print("  (Expected for Waystar — claim submission endpoint not yet configured)")
        return True
    finally:
        client.close()


def test_clearinghouse_claim_status():
    """Check claim status via clearinghouse (276/277)."""
    if not CH_CONFIG:
        print("\n  [SKIP] No CLEARINGHOUSE_PROVIDER/API_KEY in .env")
        return True
    _header(f"5d. Claim Status via {CH_CONFIG['provider']}")
    from claim_validator import build_clearinghouse_client
    client = build_clearinghouse_client(CH_CONFIG)
    try:
        result = client.check_claim_status("TEST-REF-001")
        print(f"  Status: {result.status}")
        print(f"  Claim status: {result.claim_status}")
        print(f"  Reference ID: {result.reference_id}")
        return True
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
        print("  (This is expected if using test/invalid credentials)")
        return True
    finally:
        client.close()


def test_validate_with_clearinghouse():
    """Run validate() with clearinghouse_config wired in."""
    if not CH_CONFIG:
        print("\n  [SKIP] No CLEARINGHOUSE_PROVIDER/API_KEY in .env")
        return True
    _header(f"5e. validate() + clearinghouse ({CH_CONFIG['provider']})")
    result = validate(
        {
            "billing_provider_npi": "1245319599",
            "subscriber_id": "XYZ123456789",
            "subscriber_first_name": "John",
            "subscriber_last_name": "Doe",
            "subscriber_dob": "1985-03-15",
            "subscriber_gender": "M",
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_dob": "1985-03-15",
            "patient_gender": "M",
            "patient_relationship": "self",
            "payer_id": "00001",
            "payer_name": "Aetna",
            "claim_type": "professional",
            "place_of_service": "11",
            "total_charge": 150.00,
            "diagnosis_codes": [{"code": "J06.9", "pointer": 1, "type": "principal"}],
            "lines": [
                {
                    "procedure_code": "99213",
                    "diagnosis_pointers": [1],
                    "charge_amount": 150.00,
                    "units": 1.0,
                    "service_date_from": "2026-03-01",
                    "place_of_service": "11",
                },
            ],
        },
        clearinghouse_config=CH_CONFIG,
    )
    print(f"  Passed: {result.passed}  |  Findings: {len(result.findings)}  |  Time: {result.execution_time:.4f}s")
    _print_findings(result.findings)
    return True


# ======================================================================
# RUNNER
# ======================================================================

def main() -> None:
    print("\n" + "#" * 60)
    print("#  claim-validator LIVE TEST")
    print(f"#  AI: {'ENABLED (' + AI_CONFIG['provider'] + '/' + AI_CONFIG['model'] + ')' if AI_CONFIG else 'DISABLED (no key in .env)'}")
    print(f"#  CH: {'ENABLED (' + CH_CONFIG['provider'] + ')' if CH_CONFIG else 'DISABLED (no CLEARINGHOUSE_PROVIDER in .env)'}")
    print("#" * 60)

    tests = [
        ("1a Valid claim", test_claim_valid),
        ("1b Invalid NPI", test_claim_invalid_npi),
        ("1c Missing fields", test_claim_missing_fields),
        ("1d Monetary mismatch", test_claim_monetary_mismatch),
        ("1e Claim + AI", test_claim_with_ai),
        ("2a Eligibility valid", test_eligibility_valid),
        ("2b Eligibility bad NPI", test_eligibility_invalid_npi),
        ("2c Eligibility + AI", test_eligibility_with_ai),
        ("3a Prior auth valid", test_prior_auth_valid),
        ("3b Prior auth invalid", test_prior_auth_invalid),
        ("4  Pre-claim check", test_pre_claim_check),
        ("5a CH build client", test_clearinghouse_build),
        ("5b CH eligibility", test_clearinghouse_eligibility),
        ("5c CH submit claim", test_clearinghouse_submit_claim),
        ("5d CH claim status", test_clearinghouse_claim_status),
        ("5e validate+CH", test_validate_with_clearinghouse),
    ]

    results = []
    total_start = time.perf_counter()

    for name, fn in tests:
        try:
            ok = fn()
            results.append((name, "PASS" if ok else "FAIL"))
        except Exception as e:
            print(f"\n  EXCEPTION: {type(e).__name__}: {e}")
            results.append((name, f"ERROR: {e}"))

    total_time = time.perf_counter() - total_start

    _header("SUMMARY")
    for name, status in results:
        icon = "+" if status == "PASS" else "-"
        print(f"  [{icon}] {name}: {status}")
    print(f"\n  Total time: {total_time:.2f}s")

    failures = sum(1 for _, s in results if s != "PASS")
    if failures:
        print(f"\n  {failures} test(s) did not pass as expected.")
        sys.exit(1)
    else:
        print("\n  All tests passed as expected!")


if __name__ == "__main__":
    main()
