# Story 5.2: StediClient — JSON REST Integration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer integrating with Stedi,
I want a `StediClient` implementing `BaseClearinghouseClient` with full Stedi API coverage,
so that I can submit claims, verify eligibility, check claim status, and retrieve ERA through the unified interface.

## Acceptance Criteria

1. **AC-1: StediClient implements BaseClearinghouseClient**
   - **Given** `StediClient` is instantiated with `api_key`
   - **When** inspected
   - **Then** `provider_name` returns `"stedi"`
   - **And** it is a concrete subclass of `BaseClearinghouseClient`
   - **And** it is importable from `claim_validator.clearinghouse.providers.stedi`

2. **AC-2: Eligibility check (270/271)**
   - **Given** `client.check_eligibility(request)` is called with patient/payer/provider data
   - **When** the request is processed
   - **Then** library fields are translated to Stedi's JSON format (tradingPartnerServiceId, provider.npi, subscriber.*, encounter.serviceTypeCodes)
   - **And** POSTs to `{base_url}/change/medicalnetwork/eligibility/v3`
   - **And** the response is normalized to `ClearinghouseEligibilityResponse`

3. **AC-3: Professional claims submission (837P)**
   - **Given** `client.submit_claim(claim_data)` is called with professional claim fields
   - **When** the claim is submitted
   - **Then** it translates to Stedi's 837P JSON format
   - **And** POSTs to `{base_url}/change/medicalnetwork/professionalclaims/v3/submission`
   - **And** includes `Idempotency-Key` header (UUID) for safe retries
   - **And** returns `SubmissionResult` with acknowledgment status and reference ID

4. **AC-4: Claim status check (276/277)**
   - **Given** `client.check_claim_status(claim_ref)` is called
   - **When** a valid claim reference is provided
   - **Then** POSTs to `{base_url}/change/medicalnetwork/claimstatus/v2`
   - **And** returns `ClaimStatusResponse` with claim status and adjudication info

5. **AC-5: Authentication**
   - **Given** `StediClient` is configured with an API key
   - **When** any API call is made
   - **Then** the `Authorization` header is set to the API key value
   - **And** `Content-Type: application/json` is set

6. **AC-6: Error handling**
   - **Given** Stedi API returns HTTP 401/403
   - **When** the error is handled
   - **Then** `ClearinghouseAuthError` is raised immediately (no retry)
   - **Given** Stedi API returns HTTP 5xx
   - **When** the error is handled
   - **Then** one retry with 1s backoff is attempted before raising `ClearinghouseServerError`
   - **Given** Stedi API returns HTTP 422 (validation error)
   - **When** the error is handled
   - **Then** `ClearinghouseValidationError` is raised with error details from response body
   - **And** no PHI appears in any error message (NFR29)

7. **AC-7: Unit tests with MockTransport**
   - **Given** unit tests use `httpx.MockTransport`
   - **When** all StediClient tests run
   - **Then** zero network calls are made
   - **And** all tests are deterministic (NFR30)

8. **AC-8: Cross-cutting quality**
   - **And** all source files pass mypy strict and ruff clean
   - **And** `from __future__ import annotations` on ALL new files
   - **And** all public methods have docstrings
   - **And** FR48, FR53, FR55 are satisfied

## Tasks / Subtasks

- [ ] Task 1: Create StediClient (AC: #1, #5)
  - [ ] 1.1: Create `src/claim_validator/clearinghouse/providers/stedi.py`
  - [ ] 1.2: Implement constructor: `__init__(*, api_key, base_url=DEFAULT_BASE_URL, **kwargs)`
  - [ ] 1.3: Set default base_url to `https://healthcare.us.stedi.com/2024-04-01`
  - [ ] 1.4: Configure httpx.Client with API key auth header
- [ ] Task 2: Implement check_eligibility (AC: #2)
  - [ ] 2.1: Implement `_to_stedi_eligibility(request: dict) -> dict` — field mapping
  - [ ] 2.2: Implement `check_eligibility()` — POST, parse response to ClearinghouseEligibilityResponse
- [ ] Task 3: Implement submit_claim (AC: #3)
  - [ ] 3.1: Implement `_to_stedi_claim(claim_data: dict) -> dict` — field mapping for 837P
  - [ ] 3.2: Implement `submit_claim()` — POST with Idempotency-Key, parse response to SubmissionResult
- [ ] Task 4: Implement check_claim_status (AC: #4)
  - [ ] 4.1: Implement `_to_stedi_status_request(claim_ref: str) -> dict` — field mapping
  - [ ] 4.2: Implement `check_claim_status()` — POST, parse response to ClaimStatusResponse
- [ ] Task 5: Implement error handling (AC: #6)
  - [ ] 5.1: Create `_handle_response()` method — maps HTTP status codes to exceptions
  - [ ] 5.2: Implement retry logic for 5xx (one retry, 1s backoff)
  - [ ] 5.3: PHI scrubbing from error messages
- [ ] Task 6: Register in factory (AC: #1)
  - [ ] 6.1: Update `clearinghouse/factory.py` — add "stedi" case with lazy import
- [ ] Task 7: Tests (AC: #7, #8)
  - [ ] 7.1: Create `tests/test_clearinghouse/test_stedi.py`
  - [ ] 7.2: Test eligibility request mapping and response parsing
  - [ ] 7.3: Test claim submission mapping, idempotency key, response parsing
  - [ ] 7.4: Test claim status mapping and response parsing
  - [ ] 7.5: Test error handling — 401, 422, 500, timeout
  - [ ] 7.6: Test retry on 5xx
  - [ ] 7.7: Test no PHI in error messages
- [ ] Task 8: Quality verification (AC: #8)
  - [ ] 8.1: Run ruff check on all new files
  - [ ] 8.2: Run pytest on new tests — all pass
  - [ ] 8.3: Run full pytest — zero regressions

## Dev Notes

### Stedi API Reference

**Base URL:** `https://healthcare.us.stedi.com/2024-04-01`

**Authentication:** API key in `Authorization` header (no prefix needed):
```
Authorization: Jclcke.ZHqS3demo4dS16XZ1KeyBY7
```

**Key Endpoints:**

| Transaction | Endpoint | Method |
|-------------|----------|--------|
| Eligibility (270/271) | `/change/medicalnetwork/eligibility/v3` | POST |
| Professional Claims (837P) | `/change/medicalnetwork/professionalclaims/v3/submission` | POST |
| Institutional Claims (837I) | `/change/medicalnetwork/institutionalclaims/v1/submission` | POST |
| Claim Status (276/277) | `/change/medicalnetwork/claimstatus/v2` | POST |
| ERA Reports (835) | `/change/medicalnetwork/reports/v2/{txnId}/835` | GET |

### Data Mapping — Library Models to Stedi JSON

**Eligibility Request Mapping:**
```python
# Library dict → Stedi JSON
{
    "payer_id": "00520",        → "tradingPartnerServiceId": "00520"
    "npi": "1245319599",        → "provider": {"npi": "1245319599"}
    "subscriber_id": "SUB123",  → "subscriber": {"memberId": "SUB123", ...}
    "first_name": "Alice",      → "subscriber": {"firstName": "Alice", ...}
    "last_name": "Williams",    → "subscriber": {"lastName": "Williams", ...}
    "dob": "1980-07-22",        → "subscriber": {"dateOfBirth": "19800722"}  # YYYYMMDD!
    "service_type": "30",       → "encounter": {"serviceTypeCodes": ["30"]}
}
```

**Professional Claim (837P) Mapping:**
```python
# Library dict → Stedi JSON
{
    "payer_id"          → "tradingPartnerServiceId"
    "billing_npi"       → "billing": {"npi": ...}
    "taxonomy_code"     → "billing": {"taxonomyCode": ...}
    "subscriber_id"     → "subscriber": {"memberId": ...}
    "diagnosis_codes"   → "claimInformation": {"healthCareCodeInformation": [...]}
    "lines"             → "claimInformation": {"serviceLines": [...]}
    "total_charge"      → "claimInformation": {"claimChargeAmount": ...}
    "place_of_service"  → "claimInformation": {"placeOfServiceCode": ...}
}
```

**Date format:** Stedi uses `YYYYMMDD` (no dashes). Library uses `YYYY-MM-DD`. StediClient must convert.

**Idempotency:** Include `Idempotency-Key: {uuid4}` header on claim submissions.

### Error Handling Pattern

```python
def _handle_response(self, response: httpx.Response) -> None:
    if response.status_code == 200:
        return
    # Extract error body safely (no PHI)
    try:
        body = response.json()
        error_msg = body.get("message", f"HTTP {response.status_code}")
    except Exception:
        error_msg = f"HTTP {response.status_code}"

    if response.status_code in (401, 403):
        raise ClearinghouseAuthError(error_msg)
    if response.status_code == 422:
        raise ClearinghouseValidationError(error_msg)
    if response.status_code >= 500:
        raise ClearinghouseServerError(error_msg)
    raise ClearinghouseError(error_msg)
```

### Retry Pattern (5xx only)

```python
import time

def _post_with_retry(self, path: str, json: dict, **kwargs) -> httpx.Response:
    try:
        response = self._client.post(path, json=json, **kwargs)
        if response.status_code >= 500:
            time.sleep(1)
            response = self._client.post(path, json=json, **kwargs)
        return response
    except httpx.TimeoutException as exc:
        raise ClearinghouseTimeoutError(str(exc)) from exc
```

### Testing with httpx.MockTransport

```python
def make_mock_client(handler):
    transport = httpx.MockTransport(handler)
    client = StediClient(api_key="test-key")
    client._client = httpx.Client(transport=transport, base_url=StediClient.DEFAULT_BASE_URL)
    return client
```

### Existing Patterns to Follow

- **LLM provider pattern**: `llm/providers/openai.py` — constructor, method implementation, error handling
- **Factory registration**: `llm/factory.py` — lazy import in if/elif chain
- **No PHI in errors**: Reference field names only, never values

### Previous Story Intelligence

**Story 5.1 (prerequisite):**
- BaseClearinghouseClient ABC with submit_claim, check_eligibility, check_claim_status
- Response models: SubmissionResult, ClearinghouseEligibilityResponse, ClaimStatusResponse
- ClearinghouseError hierarchy for error mapping
- Factory already has "stedi" case (lazy import)

### Project Structure Notes

- New file: `src/claim_validator/clearinghouse/providers/stedi.py`
- New file: `tests/test_clearinghouse/test_stedi.py`
- Modify: `clearinghouse/factory.py` (add stedi lazy import if not already there from 5.1)

### References

- [Source: research/technical-clearinghouse-api-integration-research-2026-03-04.md — Stedi API endpoints, auth, request/response formats]
- [Source: Stedi API Reference — https://www.stedi.com/docs/healthcare/api-reference]
- [Source: Stedi Submit Professional Claims — https://www.stedi.com/docs/healthcare/submit-professional-claims]
- [Source: epics.md — FR48: StediClient implementation]
- [Source: llm/providers/openai.py — Provider implementation pattern]
- [Source: 5-1-base-client-abc-factory-config-exceptions-models.md — Prerequisite story]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
