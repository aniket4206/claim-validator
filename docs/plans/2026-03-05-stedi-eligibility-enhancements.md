# Stedi Eligibility Enhancements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance the StediClient with full-fidelity real-time eligibility mapping (provider org name, external patient ID, multi-service types, dependents, encounter details) and add batch eligibility support (submit batch, poll status, retrieve results).

**Architecture:** Extend the existing `StediClient` with enhanced field mapping for real-time eligibility and three new batch methods. Batch uses a separate base URL (`manager.us.stedi.com`) and an async polling workflow. New Pydantic models for batch request/response. All new methods follow existing patterns (MockTransport tests, error handling, retry).

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, pytest with MockTransport

---

### Task 1: Enhance Real-Time Eligibility Request Mapping

The current `_to_stedi_eligibility()` only maps `payer_id`, `npi`, `subscriber_id`, `first_name`, `last_name`, `dob`, and a single `service_type`. The Stedi API supports many more fields that callers may want to pass through.

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:136-157`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write failing tests for enhanced request mapping**

Add to `TestEligibility` class in the test file:

```python
def test_eligibility_maps_organization_name(self) -> None:
    """provider.organizationName is included when present."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "organization_name": "ACME Health Services",
            "subscriber_id": "123456789",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1900-01-01",
            "service_type": "MH",
        }
    )
    body = json.loads(captured[0].content)
    assert body["provider"]["organizationName"] == "ACME Health Services"


def test_eligibility_maps_external_patient_id(self) -> None:
    """externalPatientId is included when present."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "subscriber_id": "123456789",
            "external_patient_id": "UAA111222333",
        }
    )
    body = json.loads(captured[0].content)
    assert body["externalPatientId"] == "UAA111222333"


def test_eligibility_maps_multiple_service_type_codes(self) -> None:
    """Multiple service type codes are sent as array."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "subscriber_id": "123456789",
            "service_types": ["MH", "78"],
        }
    )
    body = json.loads(captured[0].content)
    assert body["encounter"]["serviceTypeCodes"] == ["MH", "78"]


def test_eligibility_maps_dependent(self) -> None:
    """Dependent info is mapped when present."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "subscriber_id": "123456789",
            "dependent_first_name": "Bobby",
            "dependent_last_name": "Doe",
            "dependent_dob": "2010-05-15",
            "dependent_relationship": "19",
        }
    )
    body = json.loads(captured[0].content)
    assert len(body["dependents"]) == 1
    dep = body["dependents"][0]
    assert dep["firstName"] == "Bobby"
    assert dep["lastName"] == "Doe"
    assert dep["dateOfBirth"] == "20100515"
    assert dep["individualRelationshipCode"] == "19"


def test_eligibility_maps_encounter_date_of_service(self) -> None:
    """encounter.dateOfService is mapped when present."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "subscriber_id": "123456789",
            "service_type": "30",
            "date_of_service": "2026-03-15",
        }
    )
    body = json.loads(captured[0].content)
    assert body["encounter"]["dateOfService"] == "20260315"


def test_eligibility_maps_submitter_transaction_identifier(self) -> None:
    """submitterTransactionIdentifier is included when present."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"status": "active"})

    client = _make_client(handler)
    client.check_eligibility(
        {
            "payer_id": "AHS",
            "npi": "1999999984",
            "subscriber_id": "123456789",
            "submitter_transaction_id": "ABC123456789",
        }
    )
    body = json.loads(captured[0].content)
    assert body["submitterTransactionIdentifier"] == "ABC123456789"
```

**Step 2: Run tests to verify they fail**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestEligibility -v`
Expected: FAIL — new fields not mapped yet

**Step 3: Implement enhanced `_to_stedi_eligibility()`**

Replace the static method in `stedi.py:136-157`:

```python
@staticmethod
def _to_stedi_eligibility(request: dict[str, Any]) -> dict[str, Any]:
    """Translate library eligibility dict to Stedi JSON format."""
    subscriber: dict[str, Any] = {
        "memberId": request.get("subscriber_id", ""),
    }
    if "first_name" in request:
        subscriber["firstName"] = request["first_name"]
    if "last_name" in request:
        subscriber["lastName"] = request["last_name"]
    if "dob" in request:
        subscriber["dateOfBirth"] = _strip_dashes(request["dob"])
    if "gender" in request:
        subscriber["gender"] = request["gender"]

    provider: dict[str, Any] = {"npi": request.get("npi", "")}
    if "organization_name" in request:
        provider["organizationName"] = request["organization_name"]
    if "provider_first_name" in request:
        provider["firstName"] = request["provider_first_name"]
    if "provider_last_name" in request:
        provider["lastName"] = request["provider_last_name"]
    if "tax_id" in request:
        provider["taxId"] = request["tax_id"]

    payload: dict[str, Any] = {
        "tradingPartnerServiceId": request.get("payer_id", ""),
        "provider": provider,
        "subscriber": subscriber,
    }

    # Encounter: service types + date of service
    encounter: dict[str, Any] = {}
    if "service_types" in request:
        encounter["serviceTypeCodes"] = request["service_types"]
    elif "service_type" in request:
        encounter["serviceTypeCodes"] = [request["service_type"]]
    if "date_of_service" in request:
        encounter["dateOfService"] = _strip_dashes(request["date_of_service"])
    if encounter:
        payload["encounter"] = encounter

    # Optional top-level fields
    if "external_patient_id" in request:
        payload["externalPatientId"] = request["external_patient_id"]
    if "submitter_transaction_id" in request:
        payload["submitterTransactionIdentifier"] = request[
            "submitter_transaction_id"
        ]
    if "trading_partner_name" in request:
        payload["tradingPartnerName"] = request["trading_partner_name"]

    # Dependent (max 1 per Stedi API)
    if "dependent_first_name" in request or "dependent_last_name" in request:
        dependent: dict[str, Any] = {}
        if "dependent_first_name" in request:
            dependent["firstName"] = request["dependent_first_name"]
        if "dependent_last_name" in request:
            dependent["lastName"] = request["dependent_last_name"]
        if "dependent_dob" in request:
            dependent["dateOfBirth"] = _strip_dashes(
                request["dependent_dob"]
            )
        if "dependent_relationship" in request:
            dependent["individualRelationshipCode"] = request[
                "dependent_relationship"
            ]
        payload["dependents"] = [dependent]

    return payload
```

**Step 4: Run tests to verify they pass**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestEligibility -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py \
       claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: enhance Stedi eligibility request mapping with org name, multi-STC, dependents"
```

---

### Task 2: Enhance Real-Time Eligibility Response Parsing

The current `_parse_eligibility_response()` extracts basic `status`/`eligible`/`plan_info`. The Stedi API returns rich `benefitsInformation`, `planDateInformation`, and `subscriberTraceNumbers` that should be captured in `plan_info` and the raw response.

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py:208-233`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write failing tests for enhanced response parsing**

```python
def test_eligibility_response_parses_benefits_information(self) -> None:
    """benefitsInformation is captured in plan_info."""
    stedi_response = {
        "statusCode": "active",
        "benefitsInformation": [
            {
                "code": "1",
                "coverageLevelCode": "IND",
                "serviceTypeCodes": ["30"],
            },
            {
                "code": "C",
                "coverageLevelCode": "IND",
                "serviceTypeCodes": ["30"],
                "benefitAmount": "1500.00",
            },
        ],
        "planDateInformation": {
            "eligibilityBegin": "20240101",
            "eligibilityEnd": "20241231",
        },
    }
    client = _make_client(_ok_handler(stedi_response))
    result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})

    assert result.eligible is True
    assert len(result.plan_info["benefitsInformation"]) == 2
    assert result.plan_info["planDateInformation"]["eligibilityBegin"] == "20240101"


def test_eligibility_response_parses_status_code_field(self) -> None:
    """Newer Stedi responses use statusCode instead of status."""
    stedi_response = {"statusCode": "active"}
    client = _make_client(_ok_handler(stedi_response))
    result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})

    assert result.status == "active"
    assert result.eligible is True


def test_eligibility_response_inactive_status_code(self) -> None:
    """statusCode=inactive means not eligible."""
    stedi_response = {"statusCode": "inactive"}
    client = _make_client(_ok_handler(stedi_response))
    result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})

    assert result.eligible is False


def test_eligibility_response_captures_control_number(self) -> None:
    """controlNumber from response is mapped to reference_id."""
    stedi_response = {
        "statusCode": "active",
        "controlNumber": "CTL-555",
        "id": "ec_550e8400-e29b-41d4-a716-446655440000",
    }
    client = _make_client(_ok_handler(stedi_response))
    result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})

    assert result.reference_id == "CTL-555"


def test_eligibility_response_captures_errors(self) -> None:
    """AAA errors from payer are captured in errors list."""
    stedi_response = {
        "statusCode": "unknown",
        "errors": [
            {"code": "72", "description": "Invalid/Missing Subscriber ID"},
        ],
    }
    client = _make_client(_ok_handler(stedi_response))
    result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})

    assert result.eligible is None
    assert len(result.errors) == 1
    assert "Invalid/Missing Subscriber ID" in result.errors[0]
```

**Step 2: Run tests to verify they fail**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestEligibility -v -k "benefits_information or status_code or captures_control or captures_errors"`
Expected: FAIL

**Step 3: Implement enhanced `_parse_eligibility_response()`**

Replace `stedi.py:208-233`:

```python
@staticmethod
def _parse_eligibility_response(
    data: dict[str, Any],
) -> ClearinghouseEligibilityResponse:
    """Parse Stedi eligibility response to library model."""
    # Stedi uses "statusCode" in newer responses, "status" in legacy
    status = data.get("statusCode") or data.get("status", "unknown")

    # Determine eligibility from status or planStatus
    eligible: bool | None = None
    plan_status = data.get("planStatus")
    if plan_status:
        eligible = plan_status.lower() in ("active", "active - full")
    elif status.lower() == "active":
        eligible = True
    elif status.lower() in ("inactive", "terminated"):
        eligible = False

    # Build plan_info from structured response fields
    plan_info: dict[str, Any] = {}
    if "planInformation" in data:
        plan_info["planInformation"] = data["planInformation"]
    if "planDateInformation" in data:
        plan_info["planDateInformation"] = data["planDateInformation"]
    if "benefitsInformation" in data:
        plan_info["benefitsInformation"] = data["benefitsInformation"]
    if "planStatus" in data:
        plan_info["planStatus"] = data["planStatus"]

    # Extract errors from AAA rejections
    errors: list[str] = []
    for err in data.get("errors", []):
        desc = err.get("description") or err.get("message", "")
        code = err.get("code", "")
        errors.append(f"{code}: {desc}" if code else desc)

    return ClearinghouseEligibilityResponse(
        status=status,
        eligible=eligible,
        reference_id=data.get("controlNumber"),
        plan_info=plan_info,
        raw_response=data,
        errors=errors,
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestEligibility -v`
Expected: ALL PASS (both old and new tests)

**Step 5: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py \
       claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: enhance Stedi eligibility response parsing with benefits, plan dates, errors"
```

---

### Task 3: Add Batch Eligibility Models

The batch eligibility API uses a different base URL and returns batch-level metadata. We need models for the batch request items and batch status responses.

**Files:**
- Create: `claim-validator/src/claim_validator/clearinghouse/models/batch_eligibility.py`
- Modify: `claim-validator/src/claim_validator/clearinghouse/models/__init__.py`
- Test: `claim-validator/tests/test_clearinghouse/test_batch_models.py`

**Step 1: Check the models `__init__.py` for existing exports**

Read: `claim-validator/src/claim_validator/clearinghouse/models/__init__.py`

**Step 2: Write failing tests for batch models**

Create `tests/test_clearinghouse/test_batch_models.py`:

```python
"""Tests for batch eligibility models."""

from __future__ import annotations

import pytest

from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
    BatchItemStatus,
)


class TestBatchEligibilityItem:
    """Verify batch eligibility item model."""

    def test_minimal_item(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS",
            npi="1234567891",
            subscriber_id="1234567890",
            first_name="Jane",
            last_name="Doe",
            dob="19000101",
        )
        assert item.payer_id == "AHS"
        assert item.npi == "1234567891"

    def test_item_with_service_types(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS",
            npi="1234567891",
            subscriber_id="1234567890",
            first_name="Jane",
            last_name="Doe",
            dob="19000101",
            service_types=["MH", "78"],
        )
        assert item.service_types == ["MH", "78"]

    def test_item_with_optional_fields(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS",
            npi="1234567891",
            subscriber_id="1234567890",
            first_name="Jane",
            last_name="Doe",
            dob="19000101",
            organization_name="ACME Health Services",
            submitter_transaction_id="ABC123456789",
        )
        assert item.organization_name == "ACME Health Services"
        assert item.submitter_transaction_id == "ABC123456789"


class TestBatchEligibilityRequest:
    """Verify batch eligibility request model."""

    def test_request_with_items(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS",
            npi="1234567891",
            subscriber_id="1234567890",
            first_name="Jane",
            last_name="Doe",
            dob="19000101",
        )
        req = BatchEligibilityRequest(name="march-2026-batch", items=[item])
        assert req.name == "march-2026-batch"
        assert len(req.items) == 1

    def test_request_requires_name(self) -> None:
        with pytest.raises(Exception):
            BatchEligibilityRequest(items=[])  # type: ignore[call-arg]


class TestBatchEligibilityResponse:
    """Verify batch eligibility response model."""

    def test_response_fields(self) -> None:
        resp = BatchEligibilityResponse(
            batch_id="batch_123",
            status="processing",
            total_items=10,
            completed_items=3,
        )
        assert resp.batch_id == "batch_123"
        assert resp.status == "processing"
        assert resp.total_items == 10
        assert resp.completed_items == 3

    def test_response_defaults(self) -> None:
        resp = BatchEligibilityResponse(
            batch_id="batch_123",
            status="submitted",
        )
        assert resp.total_items == 0
        assert resp.completed_items == 0
        assert resp.items == []


class TestBatchItemStatus:
    """Verify individual batch item status model."""

    def test_completed_item(self) -> None:
        item = BatchItemStatus(
            submitter_transaction_id="ABC123",
            status="complete",
            eligibility_response={"statusCode": "active"},
        )
        assert item.status == "complete"
        assert item.eligibility_response is not None

    def test_pending_item(self) -> None:
        item = BatchItemStatus(
            submitter_transaction_id="ABC123",
            status="pending",
        )
        assert item.eligibility_response is None
```

**Step 3: Run tests to verify they fail**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_batch_models.py -v`
Expected: FAIL — module not found

**Step 4: Create the batch eligibility models**

Create `claim-validator/src/claim_validator/clearinghouse/models/batch_eligibility.py`:

```python
"""Batch eligibility request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class BatchEligibilityItem(BaseModel):
    """Single eligibility check item within a batch request."""

    model_config = ConfigDict(frozen=True)

    payer_id: str
    npi: str
    subscriber_id: str
    first_name: str
    last_name: str
    dob: str
    service_types: list[str] = []
    organization_name: str | None = None
    submitter_transaction_id: str | None = None
    external_patient_id: str | None = None
    gender: str | None = None
    date_of_service: str | None = None


class BatchEligibilityRequest(BaseModel):
    """Batch eligibility request — wraps multiple items."""

    model_config = ConfigDict(frozen=True)

    name: str
    items: list[BatchEligibilityItem]


class BatchItemStatus(BaseModel):
    """Status of a single item within a batch."""

    model_config = ConfigDict(frozen=True)

    submitter_transaction_id: str
    status: str
    eligibility_response: dict[str, Any] | None = None
    errors: list[str] = []


class BatchEligibilityResponse(BaseModel):
    """Response from batch eligibility submission or status poll."""

    model_config = ConfigDict(frozen=True)

    batch_id: str
    status: str
    total_items: int = 0
    completed_items: int = 0
    items: list[BatchItemStatus] = []
    raw_response: dict[str, Any] = {}
```

**Step 5: Update models `__init__.py`**

Add to the `__init__.py` exports:

```python
from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
    BatchItemStatus,
)
```

**Step 6: Run tests to verify they pass**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_batch_models.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/models/batch_eligibility.py \
       claim-validator/src/claim_validator/clearinghouse/models/__init__.py \
       claim-validator/tests/test_clearinghouse/test_batch_models.py
git commit -m "feat: add batch eligibility Pydantic models"
```

---

### Task 4: Implement Batch Eligibility Submit

Add `submit_eligibility_batch()` to `StediClient`. This uses the Stedi Manager API at `https://manager.us.stedi.com/2024-04-01/eligibility-manager/batch-eligibility`.

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write failing tests**

Add a new test class `TestBatchEligibility` in `test_stedi.py`:

```python
from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
)


MANAGER_BASE_URL = "https://manager.us.stedi.com/2024-04-01"


def _make_batch_client(handler: Any) -> StediClient:
    """Create a StediClient with mocked manager client for batch operations."""
    transport = httpx.MockTransport(handler)
    client = StediClient(api_key="test-key")
    # Replace the manager client with mock
    client._manager_client.close()
    client._manager_client = httpx.Client(
        transport=transport,
        base_url=MANAGER_BASE_URL,
        headers={
            "Authorization": "test-key",
            "Content-Type": "application/json",
        },
    )
    return client


class TestBatchEligibility:
    """Verify batch eligibility submission and status polling."""

    def test_submit_batch_request_mapping(self) -> None:
        """Batch items are translated to Stedi batch format."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"batchId": "batch_abc", "status": "processing"},
            )

        client = _make_batch_client(handler)
        req = BatchEligibilityRequest(
            name="march-2026-batch",
            items=[
                BatchEligibilityItem(
                    payer_id="AHS",
                    npi="1234567891",
                    subscriber_id="1234567890",
                    first_name="Jane",
                    last_name="Doe",
                    dob="19000101",
                    organization_name="ACME Health Services",
                    submitter_transaction_id="ABC123456789",
                    service_types=["MH"],
                ),
            ],
        )
        result = client.submit_eligibility_batch(req)

        assert len(captured) == 1
        body = json.loads(captured[0].content)
        assert body["name"] == "march-2026-batch"
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["tradingPartnerServiceId"] == "AHS"
        assert item["provider"]["npi"] == "1234567891"
        assert item["provider"]["organizationName"] == "ACME Health Services"
        assert item["subscriber"]["memberId"] == "1234567890"
        assert item["subscriber"]["firstName"] == "Jane"
        assert item["subscriber"]["lastName"] == "Doe"
        assert item["subscriber"]["dateOfBirth"] == "19000101"
        assert item["encounter"]["serviceTypeCodes"] == ["MH"]
        assert item["submitterTransactionIdentifier"] == "ABC123456789"

    def test_submit_batch_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"batchId": "batch_abc", "status": "processing"},
            )

        client = _make_batch_client(handler)
        req = BatchEligibilityRequest(
            name="test-batch",
            items=[
                BatchEligibilityItem(
                    payer_id="AHS",
                    npi="123",
                    subscriber_id="456",
                    first_name="J",
                    last_name="D",
                    dob="19000101",
                ),
            ],
        )
        client.submit_eligibility_batch(req)
        assert (
            captured[0].url.path
            == "/2024-04-01/eligibility-manager/batch-eligibility"
        )

    def test_submit_batch_response_parsing(self) -> None:
        stedi_resp = {
            "batchId": "batch_abc",
            "status": "processing",
            "totalChecks": 2,
        }
        client = _make_batch_client(_ok_handler(stedi_resp))
        req = BatchEligibilityRequest(
            name="test",
            items=[
                BatchEligibilityItem(
                    payer_id="AHS",
                    npi="123",
                    subscriber_id="456",
                    first_name="J",
                    last_name="D",
                    dob="19000101",
                ),
            ],
        )
        result = client.submit_eligibility_batch(req)

        assert isinstance(result, BatchEligibilityResponse)
        assert result.batch_id == "batch_abc"
        assert result.status == "processing"

    def test_submit_batch_multiple_items(self) -> None:
        """Multiple items are all included in the request."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"batchId": "batch_multi", "status": "processing"},
            )

        client = _make_batch_client(handler)
        items = [
            BatchEligibilityItem(
                payer_id="AHS",
                npi="1234567891",
                subscriber_id=f"MBR{i}",
                first_name=f"Patient{i}",
                last_name="Doe",
                dob="19000101",
                service_types=["MH"],
                submitter_transaction_id=f"TXN{i}",
            )
            for i in range(3)
        ]
        req = BatchEligibilityRequest(name="multi-batch", items=items)
        client.submit_eligibility_batch(req)

        body = json.loads(captured[0].content)
        assert len(body["items"]) == 3
        assert body["items"][1]["subscriber"]["memberId"] == "MBR1"

    def test_submit_batch_auth_error(self) -> None:
        client = _make_batch_client(
            _error_handler(401, {"message": "Invalid API key"})
        )
        req = BatchEligibilityRequest(
            name="test",
            items=[
                BatchEligibilityItem(
                    payer_id="AHS",
                    npi="123",
                    subscriber_id="456",
                    first_name="J",
                    last_name="D",
                    dob="19000101",
                ),
            ],
        )
        with pytest.raises(ClearinghouseAuthError):
            client.submit_eligibility_batch(req)
```

**Step 2: Run tests to verify they fail**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestBatchEligibility -v`
Expected: FAIL — `submit_eligibility_batch` not defined, `_manager_client` not defined

**Step 3: Implement batch submit**

Add to `stedi.py` — constants at top:

```python
DEFAULT_MANAGER_BASE_URL = "https://manager.us.stedi.com/2024-04-01"

_BATCH_ELIGIBILITY_PATH = "/eligibility-manager/batch-eligibility"
```

Add to `__init__` — create the manager client after the existing healthcare client:

```python
self._manager_client = httpx.Client(
    base_url=kwargs.pop("manager_base_url", DEFAULT_MANAGER_BASE_URL),
    timeout=httpx.Timeout(timeout, connect=10.0),
    headers={
        "Authorization": api_key,
        "Content-Type": "application/json",
    },
)
```

Add import at top:

```python
from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
)
```

Add public method after `check_claim_status()`:

```python
def submit_eligibility_batch(
    self, request: BatchEligibilityRequest
) -> BatchEligibilityResponse:
    """Submit a batch of eligibility checks.

    Uses the Stedi Manager API which processes checks asynchronously.
    Poll with ``get_batch_eligibility_status()`` to track progress.

    Args:
        request: Batch eligibility request with named items.

    Returns:
        Batch response with batch_id for status polling.
    """
    payload = self._to_stedi_batch(request)
    try:
        response = self._manager_client.post(
            _BATCH_ELIGIBILITY_PATH, json=payload
        )
    except httpx.TimeoutException as exc:
        raise ClearinghouseTimeoutError(
            f"Stedi batch request timed out: {_BATCH_ELIGIBILITY_PATH}"
        ) from exc
    self._handle_response(response)
    data = response.json()
    return self._parse_batch_response(data)
```

Add field mapping helper:

```python
@staticmethod
def _to_stedi_batch_item(item: BatchEligibilityItem) -> dict[str, Any]:
    """Translate a single batch item to Stedi JSON format."""
    subscriber: dict[str, Any] = {
        "memberId": item.subscriber_id,
        "firstName": item.first_name,
        "lastName": item.last_name,
        "dateOfBirth": item.dob,
    }
    if item.gender:
        subscriber["gender"] = item.gender

    provider: dict[str, Any] = {"npi": item.npi}
    if item.organization_name:
        provider["organizationName"] = item.organization_name

    stedi_item: dict[str, Any] = {
        "tradingPartnerServiceId": item.payer_id,
        "provider": provider,
        "subscriber": subscriber,
    }

    if item.service_types:
        stedi_item["encounter"] = {
            "serviceTypeCodes": item.service_types,
        }
    if item.date_of_service:
        stedi_item.setdefault("encounter", {})["dateOfService"] = (
            _strip_dashes(item.date_of_service)
        )
    if item.submitter_transaction_id:
        stedi_item["submitterTransactionIdentifier"] = (
            item.submitter_transaction_id
        )
    if item.external_patient_id:
        stedi_item["externalPatientId"] = item.external_patient_id

    return stedi_item

@staticmethod
def _to_stedi_batch(request: BatchEligibilityRequest) -> dict[str, Any]:
    """Translate batch request to Stedi batch JSON format."""
    return {
        "name": request.name,
        "items": [
            StediClient._to_stedi_batch_item(item)
            for item in request.items
        ],
    }
```

Add response parser:

```python
@staticmethod
def _parse_batch_response(data: dict[str, Any]) -> BatchEligibilityResponse:
    """Parse Stedi batch eligibility response."""
    return BatchEligibilityResponse(
        batch_id=data.get("batchId", ""),
        status=data.get("status", "unknown"),
        total_items=data.get("totalChecks", 0),
        raw_response=data,
    )
```

Update `close()` to also close the manager client — override in StediClient:

```python
def close(self) -> None:
    """Close both HTTP clients."""
    self._client.close()
    self._manager_client.close()
```

**Step 4: Run tests to verify they pass**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestBatchEligibility -v`
Expected: ALL PASS

**Step 5: Run full Stedi test suite for regression**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py \
       claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: add Stedi batch eligibility submission via Manager API"
```

---

### Task 5: Implement Batch Status Polling and Results Retrieval

Add `get_batch_eligibility_status()` to poll batch progress and retrieve completed results.

**Files:**
- Modify: `claim-validator/src/claim_validator/clearinghouse/providers/stedi.py`
- Test: `claim-validator/tests/test_clearinghouse/test_stedi.py`

**Step 1: Write failing tests**

Add to `TestBatchEligibility` class:

```python
def test_get_batch_status(self) -> None:
    """Poll batch status returns progress info."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "batchId": "batch_abc",
                "status": "processing",
                "totalChecks": 10,
                "completedChecks": 4,
            },
        )

    client = _make_batch_client(handler)
    result = client.get_batch_eligibility_status("batch_abc")

    assert isinstance(result, BatchEligibilityResponse)
    assert result.batch_id == "batch_abc"
    assert result.status == "processing"
    assert result.total_items == 10
    assert result.completed_items == 4

def test_get_batch_status_correct_path(self) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"batchId": "batch_abc", "status": "complete"},
        )

    client = _make_batch_client(handler)
    client.get_batch_eligibility_status("batch_abc")
    assert (
        captured[0].url.path
        == "/2024-04-01/eligibility-manager/batch/batch_abc"
    )

def test_get_batch_results(self) -> None:
    """Retrieve completed batch item results."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "submitterTransactionIdentifier": "TXN1",
                        "status": "complete",
                        "eligibilityCheck": {
                            "statusCode": "active",
                            "benefitsInformation": [],
                        },
                    },
                    {
                        "submitterTransactionIdentifier": "TXN2",
                        "status": "error",
                        "errors": [{"message": "Payer unavailable"}],
                    },
                ]
            },
        )

    client = _make_batch_client(handler)
    result = client.get_batch_eligibility_results("batch_abc")

    assert len(result) == 2
    assert result[0].submitter_transaction_id == "TXN1"
    assert result[0].status == "complete"
    assert result[0].eligibility_response["statusCode"] == "active"
    assert result[1].status == "error"
    assert "Payer unavailable" in result[1].errors[0]

def test_get_batch_results_correct_path(self) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"items": []})

    client = _make_batch_client(handler)
    client.get_batch_eligibility_results("batch_abc")
    assert (
        captured[0].url.path
        == "/2024-04-01/eligibility-manager/batch/batch_abc/items"
    )

def test_get_batch_status_auth_error(self) -> None:
    client = _make_batch_client(
        _error_handler(401, {"message": "Invalid API key"})
    )
    with pytest.raises(ClearinghouseAuthError):
        client.get_batch_eligibility_status("batch_abc")
```

**Step 2: Run tests to verify they fail**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestBatchEligibility -v -k "get_batch"`
Expected: FAIL — methods not defined

**Step 3: Implement batch status and results methods**

Add constants:

```python
_BATCH_STATUS_PATH = "/eligibility-manager/batch/{batch_id}"
_BATCH_ITEMS_PATH = "/eligibility-manager/batch/{batch_id}/items"
```

Add import for `BatchItemStatus`:

```python
from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
    BatchItemStatus,
)
```

Add public methods:

```python
def get_batch_eligibility_status(
    self, batch_id: str
) -> BatchEligibilityResponse:
    """Poll batch eligibility status.

    Args:
        batch_id: Batch identifier from ``submit_eligibility_batch()``.

    Returns:
        Batch status with progress counts.
    """
    path = _BATCH_STATUS_PATH.format(batch_id=batch_id)
    try:
        response = self._manager_client.get(path)
    except httpx.TimeoutException as exc:
        raise ClearinghouseTimeoutError(
            f"Stedi batch status timed out: {path}"
        ) from exc
    self._handle_response(response)
    data = response.json()
    return BatchEligibilityResponse(
        batch_id=data.get("batchId", batch_id),
        status=data.get("status", "unknown"),
        total_items=data.get("totalChecks", 0),
        completed_items=data.get("completedChecks", 0),
        raw_response=data,
    )

def get_batch_eligibility_results(
    self, batch_id: str
) -> list[BatchItemStatus]:
    """Retrieve individual eligibility results from a completed batch.

    Args:
        batch_id: Batch identifier from ``submit_eligibility_batch()``.

    Returns:
        List of per-item eligibility results.
    """
    path = _BATCH_ITEMS_PATH.format(batch_id=batch_id)
    try:
        response = self._manager_client.get(path)
    except httpx.TimeoutException as exc:
        raise ClearinghouseTimeoutError(
            f"Stedi batch results timed out: {path}"
        ) from exc
    self._handle_response(response)
    data = response.json()
    return self._parse_batch_items(data.get("items", []))

@staticmethod
def _parse_batch_items(items: list[dict[str, Any]]) -> list[BatchItemStatus]:
    """Parse batch item results from Stedi response."""
    results: list[BatchItemStatus] = []
    for item in items:
        errors: list[str] = [
            err.get("message", str(err))
            for err in item.get("errors", [])
        ]
        results.append(
            BatchItemStatus(
                submitter_transaction_id=item.get(
                    "submitterTransactionIdentifier", ""
                ),
                status=item.get("status", "unknown"),
                eligibility_response=item.get("eligibilityCheck"),
                errors=errors,
            )
        )
    return results
```

**Step 4: Run tests to verify they pass**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/test_stedi.py::TestBatchEligibility -v`
Expected: ALL PASS

**Step 5: Run full test suite for regression**

Run: `cd claim-validator && python -m pytest tests/test_clearinghouse/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add claim-validator/src/claim_validator/clearinghouse/providers/stedi.py \
       claim-validator/tests/test_clearinghouse/test_stedi.py
git commit -m "feat: add Stedi batch eligibility status polling and results retrieval"
```

---

### Task 6: Integration — Wire Batch Eligibility into EligibilityPipeline (Optional)

If the eligibility pipeline should support batch checks, wire it through `BasePipeline`. This task is optional — batch is typically used standalone rather than through the validation pipeline.

**Files:**
- Modify: `claim-validator/src/claim_validator/eligibility/_api.py`
- Test: `claim-validator/tests/test_eligibility/test_api.py`

**Step 1: Write failing test for top-level batch function**

```python
def test_check_eligibility_batch_delegates_to_client(self) -> None:
    """check_eligibility_batch() creates client and delegates."""
    from unittest.mock import MagicMock, patch

    mock_client = MagicMock()
    mock_client.submit_eligibility_batch.return_value = BatchEligibilityResponse(
        batch_id="batch_123",
        status="processing",
    )

    with patch(
        "claim_validator.eligibility._api.get_clearinghouse_client",
        return_value=mock_client,
    ):
        from claim_validator.eligibility._api import check_eligibility_batch

        result = check_eligibility_batch(
            name="test-batch",
            items=[{
                "payer_id": "AHS",
                "npi": "123",
                "subscriber_id": "456",
                "first_name": "J",
                "last_name": "D",
                "dob": "19000101",
            }],
            settings=ClaimValidatorSettings(
                clearinghouse_config={"provider": "stedi", "api_key": "test"}
            ),
        )

    assert result.batch_id == "batch_123"
```

**Step 2: Implement `check_eligibility_batch()` in `_api.py`**

```python
def check_eligibility_batch(
    *,
    name: str,
    items: list[dict[str, Any]],
    settings: ClaimValidatorSettings | None = None,
) -> BatchEligibilityResponse:
    """Submit a batch eligibility check via the configured clearinghouse.

    Args:
        name: Batch name for tracking.
        items: List of eligibility check items as dicts.
        settings: Optional settings override.

    Returns:
        Batch response with batch_id for polling.
    """
    if settings is None:
        settings = ClaimValidatorSettings()
    if not settings.clearinghouse_config:
        raise ValueError("clearinghouse_config is required for batch eligibility")

    from claim_validator.clearinghouse.factory import get_clearinghouse_client
    from claim_validator.clearinghouse.models.batch_eligibility import (
        BatchEligibilityItem,
        BatchEligibilityRequest,
        BatchEligibilityResponse,
    )

    ch_config = dict(settings.clearinghouse_config)
    provider = ch_config.pop("provider")
    client = get_clearinghouse_client(provider, **ch_config)

    batch_items = [BatchEligibilityItem(**item) for item in items]
    request = BatchEligibilityRequest(name=name, items=batch_items)
    return client.submit_eligibility_batch(request)
```

**Step 3: Run test to verify it passes**

Run: `cd claim-validator && python -m pytest tests/test_eligibility/test_api.py -v -k "batch"`
Expected: PASS

**Step 4: Commit**

```bash
git add claim-validator/src/claim_validator/eligibility/_api.py \
       claim-validator/tests/test_eligibility/test_api.py
git commit -m "feat: add check_eligibility_batch() top-level API function"
```

---

### Task 7: Final Regression and Cleanup

**Step 1: Run full test suite**

Run: `cd claim-validator && python -m pytest --tb=short -q`
Expected: ALL PASS, no regressions

**Step 2: Run linter**

Run: `cd claim-validator && ruff check src/ tests/`
Expected: No errors

**Step 3: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: cleanup after Stedi eligibility enhancements"
```
