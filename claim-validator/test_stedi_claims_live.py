"""Live Stedi professional claims test using STEDITEST payer.

Uses test API key + usageIndicator="T" for test mode.
See: https://www.stedi.com/docs/healthcare/test-claims-workflow
"""

from __future__ import annotations

import json
import traceback
from datetime import date
from typing import Any

from claim_validator.clearinghouse.providers.stedi import StediClient

API_KEY = "test_9gz3t4N.OTvDx3SK4PoJ96L4t3jHI29Y"
OUTPUT_FILE = "test_stedi_claims_live_output.txt"


def fmt(obj: Any) -> str:
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), indent=2, default=str)
    return json.dumps(obj, indent=2, default=str)


def run_case(name: str, fn, results: list[str]) -> None:
    sep = "=" * 70
    results.append(f"\n{sep}")
    results.append(f"CASE: {name}")
    results.append(sep)
    try:
        result = fn()
        results.append("STATUS: SUCCESS")
        results.append(f"RESULT:\n{fmt(result)}")
    except Exception as e:
        results.append(f"STATUS: ERROR ({type(e).__name__})")
        results.append(f"MESSAGE: {e}")
        results.append(f"TRACEBACK:\n{traceback.format_exc()}")


def main() -> None:
    results: list[str] = []
    results.append("STEDI LIVE PROFESSIONAL CLAIMS TEST")
    results.append(f"Date: {date.today()}")
    results.append(f"API Key: {API_KEY[:15]}... (test key)")

    client = StediClient(api_key=API_KEY)

    # -- Case 1: Minimal professional claim (STEDITEST payer) --
    run_case(
        "1. Minimal professional claim — STEDITEST payer",
        lambda: client.submit_claim({
            "payer_id": "STEDITEST",
            "trading_partner_name": "Stedi Test Payer",
            "usage_indicator": "T",
            "billing_npi": "1234567891",
            "billing_employer_id": "123456789",
            "billing_organization_name": "Therapy Associates",
            "taxonomy_code": "2084P0800X",
            "billing_address": {
                "address1": "123 Some St",
                "city": "A City",
                "state": "NY",
                "postalCode": "123450000",
            },
            "subscriber_id": "U7777788888",
            "first_name": "John",
            "last_name": "Anon",
            "dob": "2000-01-01",
            "total_charge": 109.20,
            "patient_control_number": "TESTCLM-001",
            "claim_filing_code": "12",
            "claim_frequency_code": "1",
            "benefits_assignment": "Y",
            "diagnosis_codes": ["Z0000"],
            "lines": [
                {
                    "cpt_code": "90837",
                    "charge": 109.20,
                    "units": 1,
                    "service_date": "2024-01-01",
                },
            ],
        }),
        results,
    )

    # -- Case 2: Multi-line claim with modifiers --
    run_case(
        "2. Multi-line claim with modifiers and diagnosis pointers",
        lambda: client.submit_claim({
            "payer_id": "STEDITEST",
            "trading_partner_name": "Stedi Test Payer",
            "usage_indicator": "T",
            "billing_npi": "1234567891",
            "billing_employer_id": "123456789",
            "billing_organization_name": "Therapy Associates",
            "taxonomy_code": "2084P0800X",
            "billing_address": {
                "address1": "123 Some St",
                "city": "A City",
                "state": "NY",
                "postalCode": "123450000",
            },
            "subscriber_id": "U7777788888",
            "first_name": "John",
            "last_name": "Anon",
            "dob": "2000-01-01",
            "gender": "M",
            "payment_responsibility": "P",
            "total_charge": 350.00,
            "patient_control_number": "TESTCLM-002",
            "claim_filing_code": "12",
            "claim_frequency_code": "1",
            "benefits_assignment": "Y",
            "place_of_service": "11",
            "claim_date_info": {"initialTreatmentDate": "20240115"},
            "diagnosis_codes": ["J069", "E1165"],
            "lines": [
                {
                    "cpt_code": "99214",
                    "charge": 200.00,
                    "units": 1,
                    "service_date": "2024-01-15",
                    "modifiers": ["25"],
                    "diagnosis_pointers": ["1", "2"],
                },
                {
                    "cpt_code": "99395",
                    "charge": 150.00,
                    "units": 1,
                    "service_date": "2024-01-15",
                    "diagnosis_pointers": ["1"],
                },
            ],
        }),
        results,
    )

    # -- Case 3: Claim with prior authorization --
    run_case(
        "3. Claim with prior authorization number",
        lambda: client.submit_claim({
            "payer_id": "STEDITEST",
            "trading_partner_name": "Stedi Test Payer",
            "usage_indicator": "T",
            "billing_npi": "1234567891",
            "billing_employer_id": "123456789",
            "billing_organization_name": "Therapy Associates",
            "taxonomy_code": "2084P0800X",
            "billing_address": {
                "address1": "123 Some St",
                "city": "A City",
                "state": "NY",
                "postalCode": "123450000",
            },
            "subscriber_id": "U7777788888",
            "first_name": "John",
            "last_name": "Anon",
            "dob": "2000-01-01",
            "total_charge": 109.20,
            "patient_control_number": "TESTCLM-003",
            "claim_filing_code": "12",
            "claim_frequency_code": "1",
            "benefits_assignment": "Y",
            "prior_auth_number": "AUTH-MOCK-123",
            "diagnosis_codes": ["Z0000"],
            "lines": [
                {
                    "cpt_code": "90837",
                    "charge": 109.20,
                    "units": 1,
                    "service_date": "2024-01-01",
                },
            ],
        }),
        results,
    )

    # -- Write output --
    output = "\n".join(results)
    with open(OUTPUT_FILE, "w") as f:
        f.write(output)
    print(output)
    print(f"\n{'=' * 70}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
