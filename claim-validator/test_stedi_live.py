"""Live Stedi eligibility test — exercises all cases against the real API.

Uses Stedi mock requests (test API key + exact mock data).
See: https://www.stedi.com/docs/api-reference/healthcare/mock-requests-eligibility-checks
"""

from __future__ import annotations

import json
import traceback
from datetime import date
from typing import Any

from claim_validator.clearinghouse.providers.stedi import StediClient

API_KEY = "test_9gz3t4N.OTvDx3SK4PoJ96L4t3jHI29Y"
OUTPUT_FILE = "test_stedi_live_output.txt"


def fmt(obj: Any) -> str:
    """Pretty-print a Pydantic model or dict."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), indent=2, default=str)
    if isinstance(obj, list):
        return json.dumps(
            [o.model_dump() if hasattr(o, "model_dump") else o for o in obj],
            indent=2,
            default=str,
        )
    return json.dumps(obj, indent=2, default=str)


def run_case(name: str, fn, results: list[str]) -> None:
    """Run a test case, capture output or error."""
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
    results.append("STEDI LIVE ELIGIBILITY TEST — MOCK REQUESTS")
    results.append(f"Date: {date.today()}")
    results.append(f"API Key: {API_KEY[:15]}... (test key)")

    client = StediClient(api_key=API_KEY)

    # ── Case 1: Aetna subscriber-only — active coverage ──
    run_case(
        "1. Aetna subscriber-only — active coverage",
        lambda: client.check_eligibility({
            "payer_id": "60054",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "AETNA12345",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "2004-04-04",
            "service_type": "30",
        }),
        results,
    )

    # ── Case 2: Cigna subscriber — active coverage ──
    run_case(
        "2. Cigna subscriber — active coverage (Rolando Arrojo)",
        lambda: client.check_eligibility({
            "payer_id": "62308",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "5643296",
            "first_name": "Rolando",
            "last_name": "Arrojo",
            "dob": "1971-01-02",
            "service_type": "30",
        }),
        results,
    )

    # ── Case 3: Ambetter subscriber — active coverage ──
    run_case(
        "3. Ambetter subscriber — active coverage",
        lambda: client.check_eligibility({
            "payer_id": "68069",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "AMBETTER123",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1994-04-04",
            "service_type": "30",
        }),
        results,
    )

    # ── Case 4: UHC subscriber — active coverage ──
    run_case(
        "4. UHC subscriber — active coverage (Jane Doe)",
        lambda: client.check_eligibility({
            "payer_id": "87726",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "UHC123456",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1971-01-01",
            "service_type": "30",
        }),
        results,
    )

    # ── Case 5: UHC inactive coverage ──
    run_case(
        "5. UHC subscriber — INACTIVE coverage",
        lambda: client.check_eligibility({
            "payer_id": "87726",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "UHCINACTIVE",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1971-01-01",
            "service_type": "30",
        }),
        results,
    )

    # ── Case 6: With externalPatientId ──
    run_case(
        "6. Aetna with externalPatientId tracking",
        lambda: client.check_eligibility({
            "payer_id": "60054",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "AETNA12345",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "2004-04-04",
            "service_type": "30",
            "external_patient_id": "PATIENT-UAA111",
        }),
        results,
    )

    # ── Case 7: With submitterTransactionIdentifier ──
    run_case(
        "7. Aetna with submitterTransactionIdentifier",
        lambda: client.check_eligibility({
            "payer_id": "60054",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "AETNA12345",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "2004-04-04",
            "service_type": "30",
            "submitter_transaction_id": "TXN-LIVE-001",
        }),
        results,
    )

    # ── Case 8: AAA Error 72 — Invalid Subscriber ID ──
    run_case(
        "8. AAA Error 72 — Invalid/Missing Subscriber ID (mock)",
        lambda: client.check_eligibility({
            "payer_id": "87726",
            "npi": "1234567891",
            "organization_name": "ACME Health Services",
            "subscriber_id": "UHCAAA72",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "service_type": "30",
        }),
        results,
    )

    # ── Write output ──
    output = "\n".join(results)
    with open(OUTPUT_FILE, "w") as f:
        f.write(output)
    print(output)
    print(f"\n{'=' * 70}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
