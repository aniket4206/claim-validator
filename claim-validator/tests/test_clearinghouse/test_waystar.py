"""Tests for WaystarClient clearinghouse provider."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from claim_validator.clearinghouse.auth import HMACAuth
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
from claim_validator.clearinghouse.providers.waystar import (
    DEFAULT_BASE_URL,
    WaystarClient,
)


def _make_client(handler: Any) -> WaystarClient:
    """Create a WaystarClient backed by httpx.MockTransport (zero network)."""
    transport = httpx.MockTransport(handler)
    client = WaystarClient(api_key="test-key", secret="test-secret")
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


# ---------------------------------------------------------------------------
# AC-1: WaystarClient implements BaseClearinghouseClient
# ---------------------------------------------------------------------------


class TestWaystarClientBasics:
    """Verify WaystarClient structure and ABC compliance."""

    def test_provider_name(self) -> None:
        client = _make_client(_ok_handler({}))
        assert client.provider_name == "waystar"

    def test_is_subclass(self) -> None:
        from claim_validator.clearinghouse.base import BaseClearinghouseClient

        assert issubclass(WaystarClient, BaseClearinghouseClient)

    def test_importable_from_providers(self) -> None:
        from claim_validator.clearinghouse.providers.waystar import (
            WaystarClient as WaystarImport,
        )

        assert WaystarImport is WaystarClient

    def test_default_base_url(self) -> None:
        assert DEFAULT_BASE_URL == "https://api.waystar.com"

    def test_secret_stored(self) -> None:
        client = WaystarClient(api_key="k", secret="s")
        assert client._secret == "s"
        client.close()


# ---------------------------------------------------------------------------
# AC-2: HMAC-SHA256 authentication
# ---------------------------------------------------------------------------


class TestHMACAuthentication:
    """Verify HMAC signing is wired into the client."""

    def test_client_uses_hmac_auth(self) -> None:
        """Fresh WaystarClient should have HMACAuth on its httpx client."""
        client = WaystarClient(api_key="test-key", secret="test-secret")
        assert isinstance(client._client._transport, httpx.HTTPTransport)
        assert client._client.auth is not None
        client.close()

    def test_hmac_signing_deterministic(self) -> None:
        """Given known inputs and fixed time, HMAC produces consistent signature."""
        auth = HMACAuth(api_key="test-key", secret="test-secret")
        request = httpx.Request(
            "POST",
            "https://api.waystar.com/api/v1/eligibility",
            content=b'{"payerId": "12345"}',
        )
        with patch("claim_validator.clearinghouse.auth.time") as mock_time:
            mock_time.time.return_value = 1709500000
            flow = auth.auth_flow(request)
            signed = next(flow)
            assert signed.headers["Authorization"].startswith("HMAC test-key:")
            assert signed.headers["X-Timestamp"] == "1709500000"

        # Run again with same inputs → same signature
        with patch("claim_validator.clearinghouse.auth.time") as mock_time:
            mock_time.time.return_value = 1709500000
            flow = auth.auth_flow(request)
            signed2 = next(flow)
            assert (
                signed2.headers["Authorization"]
                == signed.headers["Authorization"]
            )

    def test_hmac_headers_present_in_request(self) -> None:
        """Verify Authorization and X-Timestamp headers reach the server."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        # Use real HMAC auth (not mocked transport override)
        client = WaystarClient(api_key="test-key", secret="test-secret")
        client._client.close()
        client._client = httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url=DEFAULT_BASE_URL,
            auth=HMACAuth(api_key="test-key", secret="test-secret"),
        )
        client.check_eligibility({"payer_id": "12345", "npi": "9876543210"})

        assert len(captured) == 1
        assert "Authorization" in captured[0].headers
        assert captured[0].headers["Authorization"].startswith("HMAC test-key:")
        assert "X-Timestamp" in captured[0].headers


# ---------------------------------------------------------------------------
# AC-3: Eligibility check
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
                "service_type": "30",
            }
        )

        import json

        body = json.loads(captured[0].content)
        assert body["payerId"] == "00520"
        assert body["providerNpi"] == "1245319599"
        assert body["subscriber"]["memberId"] == "SUB123"
        assert body["subscriber"]["firstName"] == "Alice"
        assert body["subscriber"]["lastName"] == "Williams"
        assert body["subscriber"]["dateOfBirth"] == "1980-07-22"
        assert body["serviceTypeCode"] == "30"

    def test_eligibility_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert captured[0].url.path == "/api/v1/eligibility"

    def test_eligibility_response_active(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "active",
                    "referenceId": "REF-123",
                    "planInfo": {"planName": "BCBS PPO"},
                }
            )
        )
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})

        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status == "active"
        assert result.eligible is True
        assert result.reference_id == "REF-123"
        assert result.plan_info["planName"] == "BCBS PPO"

    def test_eligibility_response_inactive(self) -> None:
        client = _make_client(_ok_handler({"status": "inactive"}))
        result = client.check_eligibility({"payer_id": "00520", "npi": "123"})
        assert result.eligible is False

    def test_eligibility_minimal_request(self) -> None:
        """Request with only required fields should still work."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "unknown"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})

        import json

        body = json.loads(captured[0].content)
        assert body["payerId"] == "00520"
        assert body["providerNpi"] == "123"
        assert "subscriber" not in body


# ---------------------------------------------------------------------------
# AC-4: Claims submission
# ---------------------------------------------------------------------------


class TestSubmitClaim:
    """Verify claim submission and response parsing."""

    def test_claim_request_mapping(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "accepted"})

        client = _make_client(handler)
        client.submit_claim(
            {
                "payer_id": "00520",
                "billing_npi": "1234567890",
                "subscriber_id": "SUB-1",
                "total_charge": 250.00,
                "diagnosis_codes": ["J06.9"],
                "lines": [
                    {"cpt_code": "99213", "charge": 150.00, "units": 1},
                    {"cpt_code": "87081", "charge": 100.00, "units": 1},
                ],
            }
        )

        import json

        body = json.loads(captured[0].content)
        assert body["payerId"] == "00520"
        assert body["billingNpi"] == "1234567890"
        assert body["subscriberId"] == "SUB-1"
        assert body["totalCharge"] == "250.0"
        assert body["diagnosisCodes"] == ["J06.9"]
        assert len(body["serviceLines"]) == 2
        assert body["serviceLines"][0]["procedureCode"] == "99213"

    def test_claim_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "accepted"})

        client = _make_client(handler)
        client.submit_claim({"payer_id": "00520"})
        assert captured[0].url.path == "/api/v1/claims"

    def test_submission_response_accepted(self) -> None:
        client = _make_client(
            _ok_handler(
                {"status": "accepted", "referenceId": "CLAIM-456"}
            )
        )
        result = client.submit_claim({"payer_id": "00520"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True
        assert result.reference_id == "CLAIM-456"

    def test_submission_response_rejected(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "rejected",
                    "errors": ["Invalid diagnosis code"],
                }
            )
        )
        result = client.submit_claim({"payer_id": "00520"})
        assert result.accepted is False
        assert result.errors == ["Invalid diagnosis code"]


# ---------------------------------------------------------------------------
# AC-5: Claim status
# ---------------------------------------------------------------------------


class TestCheckClaimStatus:
    """Verify claim status request and response parsing."""

    def test_status_request(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("REF-789")

        import json

        body = json.loads(captured[0].content)
        assert body["claimReference"] == "REF-789"

    def test_status_posts_to_correct_path(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("REF-789")
        assert captured[0].url.path == "/api/v1/claims/status"

    def test_status_response_parsing(self) -> None:
        client = _make_client(
            _ok_handler(
                {
                    "status": "found",
                    "claimStatus": "paid",
                    "adjudicationDate": "2026-03-01",
                    "referenceId": "REF-789",
                }
            )
        )
        result = client.check_claim_status("REF-789")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"
        assert result.adjudication_date == "2026-03-01"
        assert result.reference_id == "REF-789"


# ---------------------------------------------------------------------------
# AC-6: Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify error mapping to clearinghouse exceptions."""

    def test_401_raises_auth_error(self) -> None:
        client = _make_client(_error_handler(401))
        with pytest.raises(ClearinghouseAuthError):
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
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_500_retries_then_raises(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"message": "Server error"})

        client = _make_client(handler)
        with patch(
            "claim_validator.clearinghouse.providers.waystar.time.sleep"
        ):
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
        with patch(
            "claim_validator.clearinghouse.providers.waystar.time.sleep"
        ):
            result = client.check_eligibility(
                {"payer_id": "00520", "npi": "123"}
            )
        assert result.status == "active"

    def test_timeout_raises_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Connection timed out")

        client = _make_client(handler)
        with pytest.raises(ClearinghouseTimeoutError, match="timed out"):
            client.check_eligibility({"payer_id": "00520", "npi": "123"})

    def test_no_phi_in_error_messages(self) -> None:
        """Error messages should reference field names, not actual patient data."""
        client = _make_client(_error_handler(422, {"message": "Invalid NPI"}))
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
    """Verify WaystarClient works through the factory."""

    def test_factory_returns_waystar_client(self) -> None:
        from claim_validator.clearinghouse.factory import (
            get_clearinghouse_client,
        )

        fake_mod = types.ModuleType(
            "claim_validator.clearinghouse.providers.waystar"
        )
        fake_mod.WaystarClient = WaystarClient  # type: ignore[attr-defined]
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client(
                "waystar", api_key="test-key", secret="test-secret"
            )
            assert isinstance(client, WaystarClient)
            assert client.provider_name == "waystar"
