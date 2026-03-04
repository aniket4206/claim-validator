# Story 5.3: ClaimMDClient — REST with AccountKey Auth

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer integrating with Claim.MD,
I want a `ClaimMDClient` implementing `BaseClearinghouseClient` with Claim.MD API coverage,
so that I can verify eligibility, upload claims, retrieve responses, and download ERA/835 reports.

## Acceptance Criteria

1. **AC-1: ClaimMDClient implements BaseClearinghouseClient**
   - **Given** `ClaimMDClient` is instantiated with `account_key`
   - **When** inspected
   - **Then** `provider_name` returns `"claimmd"`
   - **And** it is a concrete subclass of `BaseClearinghouseClient`
   - **And** it is importable from `claim_validator.clearinghouse.providers.claimmd`

2. **AC-2: Eligibility check (270/271)**
   - **Given** `client.check_eligibility(request)` is called with patient/payer/provider data
   - **When** the request is processed
   - **Then** library fields are translated to Claim.MD form data (PayerID, ProviderNPI, InsuredFirstName, InsuredLastName, InsuredDOB, InsuredID, ServiceDate, ResponseType=json)
   - **And** `AccountKey` is included in every request
   - **And** POSTs to `{base_url}/services/eligdata/`
   - **And** the response is normalized to `ClearinghouseEligibilityResponse`

3. **AC-3: Claims upload**
   - **Given** `client.submit_claim(claim_data)` is called
   - **When** the claim data is submitted
   - **Then** it translates to Claim.MD's upload format with `AccountKey` and `ResponseType=json`
   - **And** POSTs to `{base_url}/services/upload/`
   - **And** returns `SubmissionResult` with batch reference

4. **AC-4: Claim status / responses**
   - **Given** `client.check_claim_status(claim_ref)` is called
   - **When** a valid ResponseID is provided
   - **Then** POSTs to `{base_url}/services/response/` with the reference
   - **And** returns `ClaimStatusResponse` with claim status

5. **AC-5: Authentication**
   - **Given** `ClaimMDClient` is configured with an `account_key`
   - **When** any API call is made
   - **Then** `AccountKey` is included in the POST body (or as header per endpoint)

6. **AC-6: Error handling**
   - **Given** a Claim.MD API call returns an authentication error
   - **When** the error is handled
   - **Then** `ClearinghouseAuthError` is raised immediately (no retry)
   - **Given** a Claim.MD API call returns a server error
   - **When** the error is handled
   - **Then** one retry with 1s backoff before `ClearinghouseServerError`
   - **And** no PHI in any error message

7. **AC-7: Unit tests with MockTransport**
   - **Given** unit tests use `httpx.MockTransport`
   - **When** all ClaimMDClient tests run
   - **Then** zero network calls are made and all tests are deterministic

8. **AC-8: Cross-cutting quality**
   - **And** all source files pass mypy strict and ruff clean
   - **And** `from __future__ import annotations` on ALL new files
   - **And** FR49, FR53, FR55 are satisfied

## Tasks / Subtasks

- [x] Task 1: Create ClaimMDClient (AC: #1, #5)
  - [x] 1.1: Create `src/claim_validator/clearinghouse/providers/claimmd.py`
  - [x] 1.2: Implement constructor: `__init__(*, account_key, base_url=DEFAULT_BASE_URL, **kwargs)`
  - [x] 1.3: Set default base_url to `https://svc.claim.md`
  - [x] 1.4: Store account_key for inclusion in every request
- [x] Task 2: Implement check_eligibility (AC: #2)
  - [x] 2.1: Implement `_to_claimmd_eligibility(request: dict) -> dict` — field mapping
  - [x] 2.2: Implement `check_eligibility()` — POST form data, parse JSON response
- [x] Task 3: Implement submit_claim (AC: #3)
  - [x] 3.1: Implement `_to_claimmd_upload(claim_data: dict) -> dict` — field mapping
  - [x] 3.2: Implement `submit_claim()` — POST, parse response to SubmissionResult
- [x] Task 4: Implement check_claim_status (AC: #4)
  - [x] 4.1: Implement `check_claim_status()` — POST to /services/response/, parse response
- [x] Task 5: Error handling (AC: #6)
  - [x] 5.1: Create `_handle_response()` — map HTTP status AND body-level errors to exceptions
  - [x] 5.2: Retry logic for 5xx (one retry, 1s backoff)
  - [x] 5.3: PHI scrubbing from error messages
- [x] Task 6: Register in factory (AC: #1)
  - [x] 6.1: Factory already has "claimmd" lazy import from Story 5.1 — verified working
- [x] Task 7: Tests (AC: #7, #8)
  - [x] 7.1: Create `tests/test_clearinghouse/test_claimmd.py`
  - [x] 7.2: Test eligibility request mapping (AccountKey, MM/DD/YYYY dates) — 4 tests
  - [x] 7.3: Test claim upload and response parsing — 5 tests
  - [x] 7.4: Test claim status and response parsing — 3 tests
  - [x] 7.5: Test error handling — auth, server, body-level, timeout, retry — 7 tests
  - [x] 7.6: Test no PHI in error messages — 1 test
- [x] Task 8: Quality verification (AC: #8)
  - [x] 8.1: Ruff clean, 28 new tests pass, 2149 total pass (zero regressions)

## Dev Notes

### Claim.MD API Reference

**Base URL:** `https://svc.claim.md`

**Authentication:** `AccountKey` parameter included in every request body.

**Key Endpoints:**

| Transaction | Endpoint | Method | Format |
|-------------|----------|--------|--------|
| Eligibility | `/services/eligdata/` | POST | Form data |
| Claims Upload | `/services/upload/` | POST | Form data (ANSI 837, CSV, JSON, XML) |
| Claim Responses | `/services/response/` | POST | Form data |
| ERA List | `/services/eralist/` | POST | Form data |
| ERA/835 | `/services/era835/` | POST | Form data |

### Data Mapping — Library Models to Claim.MD

**Eligibility Request Mapping:**
```python
# Library dict → Claim.MD form data
{
    "payer_id": "00520",        → "PayerID": "00520"
    "npi": "1245319599",        → "ProviderNPI": "1245319599"
    "subscriber_id": "SUB123",  → "InsuredID": "SUB123"
    "first_name": "Alice",      → "InsuredFirstName": "Alice"
    "last_name": "Williams",    → "InsuredLastName": "Williams"
    "dob": "1980-07-22",        → "InsuredDOB": "07/22/1980"  # MM/DD/YYYY!
    "service_date": "2026-03-04" → "ServiceDate": "03/04/2026"  # MM/DD/YYYY!
}
# Always include: "AccountKey": self._account_key, "ResponseType": "json"
```

**Date format:** Claim.MD uses `MM/DD/YYYY`. Library uses `YYYY-MM-DD`. ClaimMDClient must convert.

**Claims Upload:**
- Claim.MD accepts ANSI 837, CSV, JSON, XML, XLS formats
- For JSON: send claims as JSON in the File parameter
- Up to 2000 claims per upload call
- Include `AccountKey` and `ResponseType=json`

### Error Handling

Claim.MD returns errors in the response body JSON rather than HTTP status codes in some cases. Check both HTTP status AND response body `status` field:

```python
def _handle_response(self, response: httpx.Response) -> dict:
    if response.status_code >= 500:
        raise ClearinghouseServerError(f"HTTP {response.status_code}")
    if response.status_code in (401, 403):
        raise ClearinghouseAuthError("Invalid AccountKey")
    data = response.json()
    if data.get("status") == "error":
        raise ClearinghouseValidationError(data.get("message", "Unknown error"))
    return data
```

### Testing Pattern

Same as StediClient — `httpx.MockTransport` for all tests. Verify AccountKey is included in every request body.

### Existing Patterns

- Follow StediClient implementation structure (Story 5.2)
- Same error handling hierarchy, same retry pattern
- Factory registration same pattern

### References

- [Source: research/technical-clearinghouse-api-integration-research-2026-03-04.md — Claim.MD API endpoints, auth, formats]
- [Source: Claim.MD API — https://api.claim.md/]
- [Source: Claim.MD GitHub Samples — https://github.com/Claim-MD/RestAPISamples]
- [Source: epics.md — FR49: ClaimMDClient implementation]
- [Source: 5-1-base-client-abc-factory-config-exceptions-models.md — ABC and models]
- [Source: 5-2-stedi-client.md — Provider implementation pattern]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- No issues encountered during implementation

### Completion Notes List

- All 8 tasks complete, all ACs satisfied
- ClaimMDClient with form-data POST API: eligibility, claims upload, status retrieval
- AccountKey included in every request body, ResponseType=json always set
- Date conversion: YYYY-MM-DD → MM/DD/YYYY for Claim.MD format
- Dual auth: accepts both account_key and api_key (factory compatibility)
- Body-level error detection: HTTP 200 with status=error handled correctly
- 28 tests using httpx.MockTransport — zero network calls
- 2149 total tests pass (zero regressions)

### File List

**New source files (1):**
- `src/claim_validator/clearinghouse/providers/claimmd.py` — ClaimMDClient implementation

**New test files (1):**
- `tests/test_clearinghouse/test_claimmd.py` — 28 tests
