# Stedi Professional Claims (837P) Enhancement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance the Stedi `submit_claim()` and `_to_stedi_claim()` to fully map the Stedi Professional Claims JSON API, add missing fields (subscriber demographics, billing address, service line details, claim dates, usageIndicator), and create a live test script using the `STEDITEST` test payer.

**Architecture:** The existing `_to_stedi_claim()` at `stedi.py:314-353` maps only a subset of the Stedi 837P schema (billing NPI/taxonomy, subscriber memberId, basic claim info, service lines as flat dicts). The Stedi API expects a much richer structure: full billing provider with address/contactInfo/employerId, subscriber demographics (name, DOB, gender, address), properly nested `professionalService` objects in service lines, claim dates, filing codes, and a `usageIndicator` for test vs production. We enhance the mapper and add the `STEDITEST` payer test workflow.

**Tech Stack:** Python 3.12, Pydantic v2, httpx, pytest, Stedi Healthcare JSON API

---

## Current State Analysis

**What exists (`stedi.py:314-353`):**
- `billing.npi`, `billing.taxonomyCode`
- `subscriber.memberId` only (no name, DOB, gender, address)
- `claimInformation.claimChargeAmount`, `placeOfServiceCode`
- `healthCareCodeInformation` with all codes as `ABK` (bug: should be `ABK` first, then `ABF`)
- `serviceLines` as flat dicts `{procedureCode, chargeAmount, unitCount}` (wrong: Stedi expects nested `professionalService`)
- `tradingPartnerServiceId`

**What's missing:**
1. `usageIndicator` ("T" for test, "P" for production)
2. `tradingPartnerName` (e.g., "Stedi Test Payer")
3. `billing.employerId` / `billing.ssn` (tax ID — required by Stedi)
4. `billing.organizationName` / `billing.firstName` + `billing.lastName`
5. `billing.address` (required: address1, city, state, postalCode)
6. `billing.contactInformation`
7. `subscriber.firstName`, `lastName`, `dateOfBirth`, `gender`, `address`
8. `subscriber.paymentResponsibilityLevelCode`
9. `claimInformation.claimFilingCode`, `claimFrequencyCode`, `patientControlNumber`
10. `claimInformation.benefitsAssignmentCertificationIndicator`
11. `claimInformation.claimDateInformation`
12. `claimInformation.claimSupplementalInformation` (prior auth, referral)
13. `serviceLines[].professionalService` nested structure (procedureCode, lineItemChargeAmount, serviceDate, diagnosisCodeReferences, procedureModifiers)
14. `serviceLines[].serviceDate` at line level
15. Diagnosis codes: first = `ABK`, rest = `ABF`

**Test payer for live testing:**
- `tradingPartnerServiceId`: `"STEDITEST"`
- `tradingPartnerName`: `"Stedi Test Payer"`
- `usageIndicator`: `"T"`
- `subscriber.memberId`: `"U7777788888"`, `firstName`: `"John"`, `lastName`: `"Anon"`, `dateOfBirth`: `"20000101"`

---

## Task 1: Fix diagnosis code type mapping (ABK/ABF)

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:327-331`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write the failing test**

Add to `TestSubmitClaim` class in `test_stedi.py`:

```python
def test_diagnosis_codes_use_abk_then_abf(self) -> None:
    """First diagnosis should be ABK (principal), rest ABF (secondary)."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"status": "accepted", "controlNumber": "REF-1"}
        )

    client = _make_client(handler)
    client.submit_claim({
        "payer_id": "TEST",
        "diagnosis_codes": ["J06.9", "E11.65", "I10"],
    })

    body = json.loads(captured[0].content)
    codes = body["claimInformation"]["healthCareCodeInformation"]
    assert codes[0] == {"diagnosisTypeCode": "ABK", "diagnosisCode": "J06.9"}
    assert codes[1] == {"diagnosisTypeCode": "ABF", "diagnosisCode": "E11.65"}
    assert codes[2] == {"diagnosisTypeCode": "ABF", "diagnosisCode": "I10"}
```

**Step 2: Run test to verify it fails**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim::test_diagnosis_codes_use_abk_then_abf -v`
Expected: FAIL — all codes currently get `ABK`

**Step 3: Write minimal implementation**

Edit `stedi.py:327-331`, replace:

```python
if "diagnosis_codes" in claim_data:
    claim_info["healthCareCodeInformation"] = [
        {"diagnosisTypeCode": "ABK", "diagnosisCode": code}
        for code in claim_data["diagnosis_codes"]
    ]
```

With:

```python
if "diagnosis_codes" in claim_data:
    codes = claim_data["diagnosis_codes"]
    claim_info["healthCareCodeInformation"] = [
        {
            "diagnosisTypeCode": "ABK" if i == 0 else "ABF",
            "diagnosisCode": code,
        }
        for i, code in enumerate(codes)
    ]
```

**Step 4: Run test to verify it passes**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "fix: use ABK for principal diagnosis, ABF for secondary in claim mapping"
```

---

## Task 2: Restructure service lines to nested `professionalService` format

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:332-340`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write the failing test**

```python
def test_service_lines_nested_professional_service(self) -> None:
    """Service lines must use nested professionalService structure."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"status": "accepted", "controlNumber": "REF-1"}
        )

    client = _make_client(handler)
    client.submit_claim({
        "payer_id": "TEST",
        "lines": [
            {
                "cpt_code": "99213",
                "charge": 150.00,
                "units": 1,
                "service_date": "2024-01-15",
                "modifiers": ["25"],
                "diagnosis_pointers": ["1"],
            },
        ],
    })

    body = json.loads(captured[0].content)
    line = body["claimInformation"]["serviceLines"][0]
    ps = line["professionalService"]
    assert ps["procedureCode"] == "99213"
    assert ps["procedureIdentifier"] == "HC"
    assert ps["lineItemChargeAmount"] == "150.0"
    assert ps["measurementUnit"] == "UN"
    assert ps["serviceUnitCount"] == "1"
    assert ps["compositeDiagnosisCodePointers"] == {
        "diagnosisCodePointers": ["1"]
    }
    assert ps["procedureModifiers"] == ["25"]
    assert line["serviceDate"] == "20240115"
```

**Step 2: Run test to verify it fails**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim::test_service_lines_nested_professional_service -v`
Expected: FAIL — current code produces flat structure

**Step 3: Write minimal implementation**

Replace the service lines block in `_to_stedi_claim`:

```python
if "lines" in claim_data:
    service_lines = []
    for line in claim_data["lines"]:
        prof_service: dict[str, Any] = {
            "procedureCode": line.get("cpt_code", ""),
            "procedureIdentifier": "HC",
            "lineItemChargeAmount": str(line.get("charge", "")),
            "measurementUnit": "UN",
            "serviceUnitCount": str(line.get("units", "1")),
        }
        if "modifiers" in line:
            prof_service["procedureModifiers"] = line["modifiers"]
        if "diagnosis_pointers" in line:
            prof_service["compositeDiagnosisCodePointers"] = {
                "diagnosisCodePointers": line["diagnosis_pointers"]
            }
        svc_line: dict[str, Any] = {
            "professionalService": prof_service,
        }
        if "service_date" in line:
            svc_line["serviceDate"] = _strip_dashes(line["service_date"])
        service_lines.append(svc_line)
    claim_info["serviceLines"] = service_lines
```

**Step 4: Run tests**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim -v`
Expected: ALL PASS (update existing `test_claim_request_mapping` if assertion on flat `serviceLines[0]["procedureCode"]` now fails — it should check `serviceLines[0]["professionalService"]["procedureCode"]` instead)

**Step 5: Update existing test assertion**

In `test_claim_request_mapping`, change line:
```python
assert body["claimInformation"]["serviceLines"][0]["procedureCode"] == "99213"
```
to:
```python
assert body["claimInformation"]["serviceLines"][0]["professionalService"]["procedureCode"] == "99213"
```

**Step 6: Run full test suite**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: restructure claim service lines to nested professionalService format"
```

---

## Task 3: Add full billing provider mapping

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:314-321`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write the failing test**

```python
def test_billing_provider_full_mapping(self) -> None:
    """Billing provider should include address, employerId, org name, contact."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"status": "accepted", "controlNumber": "REF-1"}
        )

    client = _make_client(handler)
    client.submit_claim({
        "payer_id": "TEST",
        "billing_npi": "1234567890",
        "taxonomy_code": "2084P0800X",
        "billing_employer_id": "123456789",
        "billing_organization_name": "Therapy Associates",
        "billing_address": {
            "address1": "123 Some St",
            "city": "A City",
            "state": "NY",
            "postalCode": "123450000",
        },
        "billing_contact_phone": "6175551234",
    })

    body = json.loads(captured[0].content)
    billing = body["billing"]
    assert billing["npi"] == "1234567890"
    assert billing["taxonomyCode"] == "2084P0800X"
    assert billing["employerId"] == "123456789"
    assert billing["organizationName"] == "Therapy Associates"
    assert billing["address"]["address1"] == "123 Some St"
    assert billing["address"]["city"] == "A City"
    assert billing["address"]["state"] == "NY"
    assert billing["address"]["postalCode"] == "123450000"
    assert billing["contactInformation"][0]["phoneNumber"] == "6175551234"
```

**Step 2: Run test to verify it fails**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim::test_billing_provider_full_mapping -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace the billing block in `_to_stedi_claim`:

```python
billing: dict[str, Any] = {}
if "billing_npi" in claim_data:
    billing["npi"] = claim_data["billing_npi"]
if "taxonomy_code" in claim_data:
    billing["taxonomyCode"] = claim_data["taxonomy_code"]
if "billing_employer_id" in claim_data:
    billing["employerId"] = claim_data["billing_employer_id"]
if "billing_ssn" in claim_data:
    billing["ssn"] = claim_data["billing_ssn"]
if "billing_organization_name" in claim_data:
    billing["organizationName"] = claim_data["billing_organization_name"]
if "billing_first_name" in claim_data:
    billing["firstName"] = claim_data["billing_first_name"]
if "billing_last_name" in claim_data:
    billing["lastName"] = claim_data["billing_last_name"]
if "billing_address" in claim_data:
    billing["address"] = claim_data["billing_address"]
if "billing_contact_phone" in claim_data:
    contact: dict[str, str] = {
        "phoneNumber": claim_data["billing_contact_phone"]
    }
    if "billing_contact_fax" in claim_data:
        contact["faxNumber"] = claim_data["billing_contact_fax"]
    if "billing_contact_email" in claim_data:
        contact["email"] = claim_data["billing_contact_email"]
    billing["contactInformation"] = [contact]
```

**Step 4: Run tests**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: add full billing provider mapping (address, employer ID, contact info)"
```

---

## Task 4: Add full subscriber mapping and claim metadata fields

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:347-353`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write the failing test**

```python
def test_subscriber_and_claim_metadata_mapping(self) -> None:
    """Subscriber should include demographics; claim should include filing codes."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"status": "accepted", "controlNumber": "REF-1"}
        )

    client = _make_client(handler)
    client.submit_claim({
        "payer_id": "STEDITEST",
        "trading_partner_name": "Stedi Test Payer",
        "usage_indicator": "T",
        "subscriber_id": "U7777788888",
        "first_name": "John",
        "last_name": "Anon",
        "dob": "2000-01-01",
        "gender": "M",
        "subscriber_address": {
            "address1": "456 Oak Ave",
            "city": "Cambridge",
            "state": "MA",
            "postalCode": "021381234",
        },
        "payment_responsibility": "P",
        "claim_filing_code": "12",
        "claim_frequency_code": "1",
        "patient_control_number": "CLM-001",
        "benefits_assignment": "Y",
        "prior_auth_number": "AUTH123",
        "claim_date_info": {"initialTreatmentDate": "20240115"},
    })

    body = json.loads(captured[0].content)

    # Top-level fields
    assert body["tradingPartnerServiceId"] == "STEDITEST"
    assert body["tradingPartnerName"] == "Stedi Test Payer"
    assert body["usageIndicator"] == "T"

    # Subscriber
    sub = body["subscriber"]
    assert sub["memberId"] == "U7777788888"
    assert sub["firstName"] == "John"
    assert sub["lastName"] == "Anon"
    assert sub["dateOfBirth"] == "20000101"
    assert sub["gender"] == "M"
    assert sub["address"]["address1"] == "456 Oak Ave"
    assert sub["paymentResponsibilityLevelCode"] == "P"

    # Claim metadata
    ci = body["claimInformation"]
    assert ci["claimFilingCode"] == "12"
    assert ci["claimFrequencyCode"] == "1"
    assert ci["patientControlNumber"] == "CLM-001"
    assert ci["benefitsAssignmentCertificationIndicator"] == "Y"
    assert ci["claimSupplementalInformation"]["priorAuthorizationNumber"] == "AUTH123"
    assert ci["claimDateInformation"]["initialTreatmentDate"] == "20240115"
```

**Step 2: Run test to verify it fails**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim::test_subscriber_and_claim_metadata_mapping -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace the subscriber/payload section of `_to_stedi_claim`:

```python
payload: dict[str, Any] = {
    "tradingPartnerServiceId": claim_data.get("payer_id", ""),
}
if "trading_partner_name" in claim_data:
    payload["tradingPartnerName"] = claim_data["trading_partner_name"]
if "usage_indicator" in claim_data:
    payload["usageIndicator"] = claim_data["usage_indicator"]

if billing:
    payload["billing"] = billing

# Subscriber with full demographics
if "subscriber_id" in claim_data:
    subscriber: dict[str, Any] = {
        "memberId": claim_data["subscriber_id"],
    }
    if "first_name" in claim_data:
        subscriber["firstName"] = claim_data["first_name"]
    if "last_name" in claim_data:
        subscriber["lastName"] = claim_data["last_name"]
    if "dob" in claim_data:
        subscriber["dateOfBirth"] = _strip_dashes(claim_data["dob"])
    if "gender" in claim_data:
        subscriber["gender"] = claim_data["gender"]
    if "subscriber_address" in claim_data:
        subscriber["address"] = claim_data["subscriber_address"]
    if "payment_responsibility" in claim_data:
        subscriber["paymentResponsibilityLevelCode"] = (
            claim_data["payment_responsibility"]
        )
    payload["subscriber"] = subscriber

# Claim metadata fields
if "claim_filing_code" in claim_data:
    claim_info["claimFilingCode"] = claim_data["claim_filing_code"]
if "claim_frequency_code" in claim_data:
    claim_info["claimFrequencyCode"] = claim_data["claim_frequency_code"]
if "patient_control_number" in claim_data:
    claim_info["patientControlNumber"] = claim_data["patient_control_number"]
if "benefits_assignment" in claim_data:
    claim_info["benefitsAssignmentCertificationIndicator"] = (
        claim_data["benefits_assignment"]
    )
if "claim_date_info" in claim_data:
    claim_info["claimDateInformation"] = claim_data["claim_date_info"]

# Supplemental info (prior auth, referral, etc.)
supplemental: dict[str, Any] = {}
if "prior_auth_number" in claim_data:
    supplemental["priorAuthorizationNumber"] = claim_data["prior_auth_number"]
if "referral_number" in claim_data:
    supplemental["referralNumber"] = claim_data["referral_number"]
if supplemental:
    claim_info["claimSupplementalInformation"] = supplemental

if claim_info:
    payload["claimInformation"] = claim_info
return payload
```

**Step 4: Run tests**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestSubmitClaim -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: add full subscriber demographics and claim metadata to claim mapping"
```

---

## Task 5: Create live claim test script with STEDITEST payer

**Files:**
- Create: `claim-validator/test_stedi_claims_live.py`

**Important context:** The Stedi test payer `STEDITEST` requires provider enrollment first. This script will attempt submission and capture whatever response comes back (success or enrollment-needed error). The test API key works for claim submission with `usageIndicator: "T"`.

**Step 1: Write the live test script**

```python
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
            "diagnosis_codes": ["J06.9", "E11.65"],
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
```

**Step 2: Run the live test**

Run: `cd claim-validator && python test_stedi_claims_live.py`
Expected: Cases may return enrollment-required errors (`403` or specific error message about provider enrollment with STEDITEST). This is expected — it confirms the API is being reached with correctly formatted data. A `422 Validation Error` means our payload structure needs fixing. A `200 accepted` means full success.

**Step 3: Commit**

```bash
git add claim-validator/test_stedi_claims_live.py
git commit -m "feat: add live claim test script with STEDITEST payer"
```

---

## Task 6: Run full test suite and lint check

**Step 1: Run all tests**

Run: `cd claim-validator && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS (2321+ tests)

**Step 2: Run lint**

Run: `cd claim-validator && python -m ruff check src/ tests/`
Expected: No errors

**Step 3: Fix any issues found**

Address any lint errors or test failures.

**Step 4: Final commit if any fixes needed**

```bash
git add -u
git commit -m "chore: fix lint and test issues from claims enhancement"
```

---

## Summary of Changes

| Task | What | Files |
|------|------|-------|
| 1 | Fix diagnosis code types (ABK first, ABF rest) | stedi.py, test_stedi.py |
| 2 | Restructure service lines to nested `professionalService` | stedi.py, test_stedi.py |
| 3 | Full billing provider mapping (address, employer ID, contact) | stedi.py, test_stedi.py |
| 4 | Full subscriber demographics + claim metadata fields | stedi.py, test_stedi.py |
| 5 | Live test script with STEDITEST payer (3 cases) | test_stedi_claims_live.py |
| 6 | Full suite verification + lint | all |

## Test Data Reference

**STEDITEST payer (for live testing):**
```json
{
  "tradingPartnerServiceId": "STEDITEST",
  "tradingPartnerName": "Stedi Test Payer",
  "usageIndicator": "T",
  "subscriber": {
    "memberId": "U7777788888",
    "firstName": "John",
    "lastName": "Anon",
    "dateOfBirth": "20000101"
  }
}
```

**Note:** Live claim submission to STEDITEST requires provider enrollment first (via Stedi portal: Enrollments > Create > select "835 Claim payment" for STEDITEST payer). Without enrollment, the API returns a 403 or enrollment-required error — this is expected and confirms the payload is correctly formatted.
