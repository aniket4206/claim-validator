"""Tests for StediClient clearinghouse provider."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.clearinghouse.providers.stedi import (
    DEFAULT_BASE_URL,
    StediClient,
)


def _make_client(handler: Any) -> StediClient:
    """Create a StediClient backed by httpx.MockTransport (zero network)."""
    transport = httpx.MockTransport(handler)
    client = StediClient(api_key="test-key")
    client._client.close()
    client._client = httpx.Client(
        transport=transport,
        base_url=DEFAULT_BASE_URL,
        headers={
            "Authorization": "test-key",
            "Content-Type": "application/json",
        },
    )
    return client


def _ok_handler(data: dict[str, Any]) -> Any:
    """Return a handler that responds 200 with the given JSON data."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    return handler


def _error_handler(status_code: int, body: dict[str, Any] | None = None) -> Any:
    """Return a handler that responds with the given error status."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code, json=body or {"message": f"HTTP {status_code}"}
        )

    return handler


# ---------------------------------------------------------------------------
# AC-1: StediClient implements BaseClearinghouseClient
# ---------------------------------------------------------------------------


class TestStediClientBasics:
    """Verify StediClient structure and ABC compliance."""

    def test_provider_name(self) -> None:
        client = _make_client(_ok_handler({}))
        assert client.provider_name == "stedi"

    def test_is_subclass(self) -> None:
        from claim_validator.clearinghouse.base import BaseClearinghouseClient

        assert issubclass(StediClient, BaseClearinghouseClient)

    def test_importable_from_providers(self) -> None:
        from claim_validator.clearinghouse.providers.stedi import (
            StediClient as StediClientImport,
        )

        assert StediClientImport is StediClient

    def test_default_base_url(self) -> None:
        assert DEFAULT_BASE_URL == "https://healthcare.us.stedi.com/2024-04-01"


# ---------------------------------------------------------------------------
# AC-2: Eligibility check (270/271)
# ---------------------------------------------------------------------------


class TestEligibility:
    """Verify eligibility request mapping and response parsing."""

    def test_eligibility_request_mapping(self) -> None:
        """Library dict fields are translated to Stedi JSON format."""
        captured_requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility(
            {
                "payer_id": "00520",
                "npi": "1245319599",
                "subscriber_id": "SUB123",
                "first_name": "Alice",
                "last_name": "Williams",
                "dob": "1980-07-22",
                "service_type": "30",
            }
        )

        assert len(captured_requests) == 1
        body = json.loads(captured_requests[0].content)
        assert body["tradingPartnerServiceId"] == "00520"
        assert body["provider"]["npi"] == "1245319599"
        assert body["subscriber"]["memberId"] == "SUB123"
        assert body["subscriber"]["firstName"] == "Alice"
        assert body["subscriber"]["lastName"] == "Williams"
        assert body["subscriber"]["dateOfBirth"] == "19800722"  # No dashes
        assert body["encounter"]["serviceTypeCodes"] == ["30"]

    def test_eligibility_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert captured[0].url.path == "/2024-04-01/change/medicalnetwork/eligibility/v3"

    def test_eligibility_response_parsing(self) -> None:
        stedi_response = {
            "status": "active",
            "planStatus": "Active - Full",
            "controlNumber": "CTL-123",
            "planInformation": {"planName": "BCBS PPO"},
        }
        client = _make_client(_ok_handler(stedi_response))
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})

        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status == "active"
        assert result.eligible is True
        assert result.reference_id == "CTL-123"
        assert result.plan_info["planInformation"]["planName"] == "BCBS PPO"

    def test_eligibility_inactive(self) -> None:
        client = _make_client(
            _ok_handler({"status": "inactive", "planStatus": "Inactive"})
        )
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert result.eligible is False

    def test_eligibility_maps_organization_name(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "organization_name": "ACME Health Services",
            "subscriber_id": "123456789", "first_name": "Jane",
            "last_name": "Doe", "dob": "1900-01-01", "service_type": "MH",
        })
        body = json.loads(captured[0].content)
        assert body["provider"]["organizationName"] == "ACME Health Services"

    def test_eligibility_maps_external_patient_id(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "subscriber_id": "123456789", "external_patient_id": "UAA111222333",
        })
        body = json.loads(captured[0].content)
        assert body["externalPatientId"] == "UAA111222333"

    def test_eligibility_maps_multiple_service_type_codes(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "subscriber_id": "123456789", "service_types": ["MH", "78"],
        })
        body = json.loads(captured[0].content)
        assert body["encounter"]["serviceTypeCodes"] == ["MH", "78"]

    def test_eligibility_maps_dependent(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "subscriber_id": "123456789",
            "dependent_first_name": "Bobby", "dependent_last_name": "Doe",
            "dependent_dob": "2010-05-15", "dependent_relationship": "19",
        })
        body = json.loads(captured[0].content)
        assert len(body["dependents"]) == 1
        dep = body["dependents"][0]
        assert dep["firstName"] == "Bobby"
        assert dep["lastName"] == "Doe"
        assert dep["dateOfBirth"] == "20100515"
        assert dep["individualRelationshipCode"] == "19"

    def test_eligibility_maps_all_optional_provider_and_subscriber_fields(self) -> None:
        """All optional provider/subscriber fields are mapped correctly."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS",
            "npi": "1999999984",
            "organization_name": "ACME Health",
            "provider_first_name": "Dr",
            "provider_last_name": "Smith",
            "tax_id": "123456789",
            "subscriber_id": "MBR123",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": "1990-01-01",
            "gender": "F",
            "trading_partner_name": "Aetna",
        })
        body = json.loads(captured[0].content)
        assert body["provider"]["organizationName"] == "ACME Health"
        assert body["provider"]["firstName"] == "Dr"
        assert body["provider"]["lastName"] == "Smith"
        assert body["provider"]["taxId"] == "123456789"
        assert body["subscriber"]["gender"] == "F"
        assert body["tradingPartnerName"] == "Aetna"

    def test_eligibility_maps_encounter_date_of_service(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "subscriber_id": "123456789", "service_type": "30",
            "date_of_service": "2026-03-15",
        })
        body = json.loads(captured[0].content)
        assert body["encounter"]["dateOfService"] == "20260315"

    def test_eligibility_response_parses_benefits_information(self) -> None:
        """benefitsInformation is captured in plan_info."""
        stedi_response = {
            "statusCode": "active",
            "benefitsInformation": [
                {"code": "1", "coverageLevelCode": "IND", "serviceTypeCodes": ["30"]},
                {"code": "C", "coverageLevelCode": "IND", "serviceTypeCodes": ["30"], "benefitAmount": "1500.00"},
            ],
            "planDateInformation": {"eligibilityBegin": "20240101", "eligibilityEnd": "20241231"},
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
        stedi_response = {"statusCode": "active", "controlNumber": "CTL-555"}
        client = _make_client(_ok_handler(stedi_response))
        result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})
        assert result.reference_id == "CTL-555"

    def test_eligibility_response_captures_errors(self) -> None:
        """AAA errors from payer are captured in errors list."""
        stedi_response = {
            "statusCode": "unknown",
            "errors": [{"code": "72", "description": "Invalid/Missing Subscriber ID"}],
        }
        client = _make_client(_ok_handler(stedi_response))
        result = client.check_eligibility({"payer_id": "AHS", "npi": "123"})
        assert result.eligible is None
        assert len(result.errors) == 1
        assert "Invalid/Missing Subscriber ID" in result.errors[0]

    def test_eligibility_maps_submitter_transaction_identifier(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "AHS", "npi": "1999999984",
            "subscriber_id": "123456789",
            "submitter_transaction_id": "ABC123456789",
        })
        body = json.loads(captured[0].content)
        assert body["submitterTransactionIdentifier"] == "ABC123456789"


# ---------------------------------------------------------------------------
# AC-3: Professional claims submission (837P)
# ---------------------------------------------------------------------------


class TestSubmitClaim:
    """Verify claim submission mapping, idempotency, and response parsing."""

    def test_claim_request_mapping(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200, json={"status": "accepted", "controlNumber": "REF-456"}
            )

        client = _make_client(handler)
        client.submit_claim(
            {
                "payer_id": "00520",
                "billing_npi": "1234567890",
                "taxonomy_code": "207Q00000X",
                "subscriber_id": "MBR-999",
                "total_charge": 150.00,
                "place_of_service": "11",
                "diagnosis_codes": ["J06.9"],
                "lines": [
                    {"cpt_code": "99213", "charge": 150.00, "units": 1},
                ],
            }
        )

        body = json.loads(captured[0].content)
        assert body["tradingPartnerServiceId"] == "00520"
        assert body["billing"]["npi"] == "1234567890"
        assert body["billing"]["taxonomyCode"] == "207Q00000X"
        assert body["subscriber"]["memberId"] == "MBR-999"
        assert body["claimInformation"]["claimChargeAmount"] == "150.0"
        assert body["claimInformation"]["placeOfServiceCode"] == "11"
        assert body["claimInformation"]["healthCareCodeInformation"][0]["diagnosisCode"] == "J06.9"
        assert body["claimInformation"]["serviceLines"][0]["procedureCode"] == "99213"

    def test_claim_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "accepted"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        assert (
            captured[0].url.path
            == "/2024-04-01/change/medicalnetwork/professionalclaims/v3/submission"
        )

    def test_idempotency_key_header(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "accepted"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        assert "idempotency-key" in captured[0].headers

    def test_idempotency_key_is_uuid(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "accepted"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        import uuid

        key = captured[0].headers["idempotency-key"]
        uuid.UUID(key)  # Raises ValueError if not valid UUID

    def test_submission_response_parsing(self) -> None:
        stedi_response = {
            "status": "accepted",
            "controlNumber": "REF-456",
        }
        client = _make_client(_ok_handler(stedi_response))
        result = client.submit_claim({"payer_id": "00520"})

        assert isinstance(result, SubmissionResult)
        assert result.status == "accepted"
        assert result.accepted is True
        assert result.reference_id == "REF-456"

    def test_submission_rejected(self) -> None:
        client = _make_client(
            _ok_handler({"status": "rejected", "errors": ["Invalid NPI"]})
        )
        result = client.submit_claim({"payer_id": "00520"})
        assert result.accepted is False
        assert result.errors == ["Invalid NPI"]


# ---------------------------------------------------------------------------
# AC-4: Claim status check (276/277)
# ---------------------------------------------------------------------------


class TestCheckClaimStatus:
    """Verify claim status request mapping and response parsing."""

    def test_status_request_mapping(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("REF-789")
        body = json.loads(captured[0].content)
        assert body["claimReference"] == "REF-789"

    def test_status_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("REF-789")
        assert (
            captured[0].url.path
            == "/2024-04-01/change/medicalnetwork/claimstatus/v2"
        )

    def test_status_response_parsing(self) -> None:
        stedi_response = {
            "status": "found",
            "claimStatus": "paid",
            "adjudicationDate": "2026-03-01",
            "controlNumber": "CTL-999",
        }
        client = _make_client(_ok_handler(stedi_response))
        result = client.check_claim_status("REF-789")

        assert isinstance(result, ClaimStatusResponse)
        assert result.status == "found"
        assert result.claim_status == "paid"
        assert result.adjudication_date == "2026-03-01"
        assert result.reference_id == "CTL-999"


# ---------------------------------------------------------------------------
# AC-5: Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    """Verify API key auth header is set on requests."""

    def test_authorization_header(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert captured[0].headers["authorization"] == "test-key"

    def test_content_type_header(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert "application/json" in captured[0].headers["content-type"]


# ---------------------------------------------------------------------------
# AC-6: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify HTTP error mapping to clearinghouse exceptions."""

    def test_401_raises_auth_error(self) -> None:
        client = _make_client(
            _error_handler(401, {"message": "Invalid API key"})
        )
        with pytest.raises(ClearinghouseAuthError, match="Invalid API key"):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_403_raises_auth_error(self) -> None:
        client = _make_client(_error_handler(403))
        with pytest.raises(ClearinghouseAuthError):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_422_raises_validation_error(self) -> None:
        client = _make_client(
            _error_handler(422, {"message": "Missing required field"})
        )
        with pytest.raises(
            ClearinghouseValidationError, match="Missing required field"
        ):
            client.submit_claim({"payer_id": "00520"})

    def test_500_retries_then_raises_server_error(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"message": "Server error"})

        client = _make_client(handler)
        with patch("claim_validator.clearinghouse.providers.stedi.time.sleep"):
            with pytest.raises(ClearinghouseServerError, match="Server error"):
                client.check_eligibility({"payer_id": "00520", "npi": "123"})
        # Retried once (2 total calls)
        assert call_count == 2

    def test_500_retry_succeeds(self) -> None:
        """First call returns 500, retry returns 200."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500, json={"message": "Temporary"})
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        with patch("claim_validator.clearinghouse.providers.stedi.time.sleep"):
            result = client.check_eligibility(
                {"payer_id": "00520", "npi": "123"}
            )
        assert result.status == "active"
        assert call_count == 2

    def test_timeout_raises_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Connection timed out")

        client = _make_client(handler)
        with pytest.raises(ClearinghouseTimeoutError, match="timed out"):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_no_phi_in_error_messages(self) -> None:
        """Error messages must reference field names, not patient data."""
        client = _make_client(
            _error_handler(
                422,
                {"message": "Missing required field: subscriber.memberId"},
            )
        )
        with pytest.raises(ClearinghouseValidationError) as exc_info:
            client.check_eligibility(
                {
                    "payer_id": "00520",
                    "npi": "123",
                    "first_name": "SensitiveFirstName",
                    "last_name": "SensitiveLastName",
                }
            )
        error_msg = str(exc_info.value)
        assert "SensitiveFirstName" not in error_msg
        assert "SensitiveLastName" not in error_msg

    def test_error_response_without_json(self) -> None:
        """Handle error responses that don't have JSON body."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = _make_client(handler)
        with patch("claim_validator.clearinghouse.providers.stedi.time.sleep"):
            with pytest.raises(ClearinghouseServerError, match="HTTP 500"):
                client.check_eligibility({"payer_id": "00520", "npi": "123"})


# ---------------------------------------------------------------------------
# AC-7: Factory integration
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    """Verify StediClient works through the factory."""

    def test_factory_returns_stedi_client(self) -> None:
        import sys
        import types

        from claim_validator.clearinghouse.factory import (
            get_clearinghouse_client,
        )

        fake_mod = types.ModuleType(
            "claim_validator.clearinghouse.providers.stedi"
        )
        fake_mod.StediClient = StediClient  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client("stedi", api_key="test-key")
            assert isinstance(client, StediClient)
            assert client.provider_name == "stedi"
