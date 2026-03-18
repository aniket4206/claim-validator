"""Tests for ClaimMDClient clearinghouse provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs

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
from claim_validator.clearinghouse.providers.claimmd import (
    DEFAULT_BASE_URL,
    ClaimMDClient,
)


def _make_client(handler: Any) -> ClaimMDClient:
    """Create a ClaimMDClient backed by httpx.MockTransport (zero network)."""
    transport = httpx.MockTransport(handler)
    client = ClaimMDClient(account_key="test-account-key")
    client._client.close()
    client._client = httpx.Client(
        transport=transport, base_url=DEFAULT_BASE_URL
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


def _parse_form_body(request: httpx.Request) -> dict[str, str]:
    """Parse URL-encoded form data from request content."""
    raw = parse_qs(request.content.decode())
    return {k: v[0] for k, v in raw.items()}


# ---------------------------------------------------------------------------
# AC-1: ClaimMDClient implements BaseClearinghouseClient
# ---------------------------------------------------------------------------


class TestClaimMDClientBasics:
    """Verify ClaimMDClient structure and ABC compliance."""

    def test_provider_name(self) -> None:
        client = _make_client(_ok_handler({}))
        assert client.provider_name == "claimmd"

    def test_is_subclass(self) -> None:
        from claim_validator.clearinghouse.base import BaseClearinghouseClient

        assert issubclass(ClaimMDClient, BaseClearinghouseClient)

    def test_importable_from_providers(self) -> None:
        from claim_validator.clearinghouse.providers.claimmd import (
            ClaimMDClient as ClaimMDImport,
        )

        assert ClaimMDImport is ClaimMDClient

    def test_default_base_url(self) -> None:
        assert DEFAULT_BASE_URL == "https://svc.claim.md"

    def test_accepts_api_key_alias(self) -> None:
        """Factory passes api_key; ClaimMDClient should accept it."""
        client = ClaimMDClient(api_key="my-key")
        assert client._account_key == "my-key"
        client.close()


# ---------------------------------------------------------------------------
# AC-2: Eligibility check (270/271)
# ---------------------------------------------------------------------------


class TestEligibility:
    """Verify eligibility request mapping and response parsing."""

    def test_eligibility_request_mapping(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
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
                "service_date": "2026-03-04",
            }
        )

        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"
        assert form["ResponseType"] == "json"
        assert form["PayerID"] == "00520"
        assert form["ProviderNPI"] == "1245319599"
        assert form["InsuredID"] == "SUB123"
        assert form["InsuredFirstName"] == "Alice"
        assert form["InsuredLastName"] == "Williams"
        assert form["InsuredDOB"] == "07/22/1980"  # MM/DD/YYYY
        assert form["ServiceDate"] == "03/04/2026"  # MM/DD/YYYY

    def test_eligibility_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert captured[0].url.path == "/services/eligdata/"

    def test_eligibility_response_active(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "active",
                    "responseID": "RESP-123",
                    "plan": {"planName": "BCBS PPO"},
                }
            )
        )
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})

        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status == "active"
        assert result.eligible is True
        assert result.reference_id == "RESP-123"
        assert result.plan_info["planName"] == "BCBS PPO"

    def test_eligibility_response_inactive(self) -> None:
        client = _make_client(_ok_handler({"status": "inactive"}))
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert result.eligible is False


# ---------------------------------------------------------------------------
# AC-3: Claims upload
# ---------------------------------------------------------------------------


class TestSubmitClaim:
    """Verify claim upload and response parsing."""

    def test_upload_includes_account_key(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok", "batchID": "B-1"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"
        assert form["ResponseType"] == "json"

    def test_upload_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        assert captured[0].url.path == "/services/upload/"

    def test_upload_sends_claim_as_json_file(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520", "total_charge": 150})
        form = _parse_form_body(captured[0])
        assert "File" in form
        import json

        file_data = json.loads(form["File"])
        assert file_data["payer_id"] == "00520"

    def test_submission_response_parsing(self) -> None:
        client = _make_client(
            _ok_handler({"status": "ok", "batchID": "BATCH-456"})
        )
        result = client.submit_claim({"payer_id": "00520"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True
        assert result.reference_id == "BATCH-456"

    def test_submission_rejected(self) -> None:
        client = _make_client(
            _ok_handler(
                {"status": "rejected", "errors": ["Invalid claim format"]}
            )
        )
        result = client.submit_claim({"payer_id": "00520"})
        assert result.accepted is False
        assert result.errors == ["Invalid claim format"]


# ---------------------------------------------------------------------------
# AC-4: Claim status / responses
# ---------------------------------------------------------------------------


class TestCheckClaimStatus:
    """Verify claim status request and response parsing."""

    def test_status_request_includes_response_id(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("RESP-789")
        form = _parse_form_body(captured[0])
        assert form["ResponseID"] == "RESP-789"
        assert form["AccountKey"] == "test-account-key"

    def test_status_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("RESP-789")
        assert captured[0].url.path == "/services/response/"

    def test_status_response_parsing(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "found",
                    "claimStatus": "paid",
                    "adjudicationDate": "2026-03-01",
                    "responseID": "RESP-789",
                }
            )
        )
        result = client.check_claim_status("RESP-789")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"
        assert result.reference_id == "RESP-789"


# ---------------------------------------------------------------------------
# AC-4b: Prior Authorization (278)
# ---------------------------------------------------------------------------


class TestSubmitPriorAuth:
    """Verify prior auth submission and response parsing."""

    def test_prior_auth_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "approved"})

        client = _make_client(handler)
        client.submit_prior_auth({"payer_id": "00520", "requester_npi": "1234567893"})
        assert captured[0].url.path == "/services/preauth/"

    def test_prior_auth_includes_account_key(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "approved"})

        client = _make_client(handler)
        client.submit_prior_auth({"payer_id": "00520", "requester_npi": "123"})
        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"
        assert form["ResponseType"] == "json"

    def test_prior_auth_request_mapping_flat_keys(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "approved"})

        client = _make_client(handler)
        client.submit_prior_auth(
            {
                "payer_id": "00520",
                "npi": "1245319599",
                "subscriber_id": "SUB123",
                "first_name": "Alice",
                "last_name": "Williams",
                "dob": "1980-07-22",
                "diagnosis_codes": ["M79.3", "G89.29"],
                "service_lines": [
                    {"cpt_code": "72148", "from_date": "2026-04-01", "quantity": 1},
                ],
            }
        )

        form = _parse_form_body(captured[0])
        assert form["PayerID"] == "00520"
        assert form["ProviderNPI"] == "1245319599"
        assert form["InsuredID"] == "SUB123"
        assert form["InsuredFirstName"] == "Alice"
        assert form["InsuredLastName"] == "Williams"
        assert form["InsuredDOB"] == "07/22/1980"
        assert form["DiagnosisCode1"] == "M79.3"
        assert form["DiagnosisCode2"] == "G89.29"
        assert form["ProcedureCode1"] == "72148"
        assert form["ServiceDate1"] == "04/01/2026"
        assert form["Quantity1"] == "1"

    def test_prior_auth_request_mapping_nested_subscriber(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "approved"})

        client = _make_client(handler)
        client.submit_prior_auth(
            {
                "payer_id": "00520",
                "requester_npi": "1245319599",
                "subscriber": {
                    "member_id": "SUB456",
                    "first_name": "Bob",
                    "last_name": "Smith",
                    "dob": "1975-03-15",
                },
            }
        )

        form = _parse_form_body(captured[0])
        assert form["ProviderNPI"] == "1245319599"
        assert form["InsuredID"] == "SUB456"
        assert form["InsuredFirstName"] == "Bob"
        assert form["InsuredLastName"] == "Smith"
        assert form["InsuredDOB"] == "03/15/1975"

    def test_prior_auth_response_approved(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "approved",
                    "authorizationNumber": "AUTH-789",
                }
            )
        )
        result = client.submit_prior_auth({"payer_id": "00520", "npi": "123"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True
        assert result.reference_id == "AUTH-789"

    def test_prior_auth_response_denied(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "denied",
                    "errors": ["Service not covered"],
                }
            )
        )
        result = client.submit_prior_auth({"payer_id": "00520", "npi": "123"})
        assert result.accepted is False
        assert result.errors == ["Service not covered"]

    def test_prior_auth_response_certified(self) -> None:
        client = _make_client(
            _ok_handler({"status": "certified", "responseID": "R-100"})
        )
        result = client.submit_prior_auth({"payer_id": "00520", "npi": "123"})
        assert result.accepted is True
        assert result.reference_id == "R-100"

    def test_stedi_does_not_support_prior_auth(self) -> None:
        """Verify non-ClaimMD providers raise NotImplementedError."""
        from claim_validator.clearinghouse.providers.stedi import StediClient

        client = StediClient(api_key="test-key")
        with pytest.raises(NotImplementedError, match="does not support"):
            client.submit_prior_auth({"payer_id": "00520"})
        client.close()


# ---------------------------------------------------------------------------
# AC-5: Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    """Verify AccountKey is included in every request."""

    def test_account_key_in_eligibility(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"

    def test_account_key_in_upload(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"

    def test_account_key_in_status(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_claim_status("REF-1")
        form = _parse_form_body(captured[0])
        assert form["AccountKey"] == "test-account-key"


# ---------------------------------------------------------------------------
# AC-6: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify error mapping to clearinghouse exceptions."""

    def test_401_raises_auth_error(self) -> None:
        client = _make_client(_error_handler(401))
        with pytest.raises(ClearinghouseAuthError, match="AccountKey"):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_403_raises_auth_error(self) -> None:
        client = _make_client(_error_handler(403))
        with pytest.raises(ClearinghouseAuthError):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_500_retries_then_raises(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"message": "Server error"})

        client = _make_client(handler)
        with patch("claim_validator.clearinghouse.providers.claimmd.time.sleep"):
            with pytest.raises(ClearinghouseServerError):
                client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert call_count == 2  # Original + 1 retry

    def test_500_retry_succeeds(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(500, json={"message": "Temporary"})
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        with patch("claim_validator.clearinghouse.providers.claimmd.time.sleep"):
            result = client.check_eligibility(
                {"payer_id": "00520", "npi": "123"}
            )
        assert result.status == "active"

    def test_body_level_error(self) -> None:
        """Claim.MD returns HTTP 200 but body status=error."""
        client = _make_client(
            _ok_handler({"status": "error", "message": "Missing PayerID"})
        )
        with pytest.raises(
            ClearinghouseValidationError, match="Missing PayerID"
        ):
            client.check_eligibility({"npi": "123"})

    def test_timeout_raises_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Connection timed out")

        client = _make_client(handler)
        with pytest.raises(ClearinghouseTimeoutError, match="timed out"):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_no_phi_in_error_messages(self) -> None:
        client = _make_client(
            _ok_handler(
                {"status": "error", "message": "Missing InsuredID field"}
            )
        )
        with pytest.raises(ClearinghouseValidationError) as exc_info:
            client.check_eligibility(
                {
                    "payer_id": "00520",
                    "npi": "123",
                    "first_name": "SensitiveName",
                }
            )
        assert "SensitiveName" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-7: Factory integration
# ---------------------------------------------------------------------------


class TestFactoryIntegration:
    """Verify ClaimMDClient works through the factory."""

    def test_factory_returns_claimmd_client(self) -> None:
        import sys
        import types

        from claim_validator.clearinghouse.factory import (
            get_clearinghouse_client,
        )

        fake_mod = types.ModuleType(
            "claim_validator.clearinghouse.providers.claimmd"
        )
        fake_mod.ClaimMDClient = ClaimMDClient  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client("claimmd", api_key="test-key")
            assert isinstance(client, ClaimMDClient)
            assert client.provider_name == "claimmd"
