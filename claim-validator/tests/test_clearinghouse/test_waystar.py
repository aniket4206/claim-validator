"""Tests for WaystarClient — real Waystar API integration."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import sys
import types
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseServerError,
    ClearinghouseTimeoutError,
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
)
from claim_validator.clearinghouse.providers.waystar import (
    CLAIM_HISTORY_PATH,
    DEFAULT_BASE_URL,
    DEFAULT_CLAIMS_BASE_URL,
    DEFAULT_ELIGIBILITY_BASE_URL,
    DEFAULT_PRIOR_AUTH_BASE_URL,
    ELIGIBILITY_PATH,
    WaystarClient,
    _utc_timestamp,
)


def _make_client(
    handler: Any,
    *,
    api_key: str = "test-key",
    secret: str = "test-secret",
    user_id: str = "test-user",
    password: str = "test-pass",
    cust_id: str = "12345",
) -> WaystarClient:
    """Create a WaystarClient backed by httpx.MockTransport (zero network)."""
    transport = httpx.MockTransport(handler)
    client = WaystarClient(
        api_key=api_key,
        secret=secret,
        user_id=user_id,
        password=password,
        cust_id=cust_id,
    )
    client._client.close()
    client._client = httpx.Client(transport=transport)
    return client


def _ok_json_handler(data: dict[str, Any]) -> Any:
    """Return a handler that responds 200 with JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    return handler


def _error_handler(
    status_code: int, body: dict[str, Any] | None = None
) -> Any:
    """Return a handler that responds with the given error status."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code, json=body or {"message": f"HTTP {status_code}"}
        )

    return handler


# ---------------------------------------------------------------------------
# AC-1: WaystarClient basics
# ---------------------------------------------------------------------------


class TestWaystarClientBasics:
    """Verify WaystarClient structure and ABC compliance."""

    def test_provider_name(self) -> None:
        client = _make_client(_ok_json_handler({}))
        assert client.provider_name == "waystar"

    def test_is_subclass(self) -> None:
        from claim_validator.clearinghouse.base import BaseClearinghouseClient

        assert issubclass(WaystarClient, BaseClearinghouseClient)

    def test_default_base_urls(self) -> None:
        assert DEFAULT_CLAIMS_BASE_URL == "https://claimsapi.zirmed.com"
        assert (
            DEFAULT_ELIGIBILITY_BASE_URL
            == "https://eligibilityapi.zirmed.com"
        )
        assert (
            DEFAULT_PRIOR_AUTH_BASE_URL
            == "https://priorauthorizationapi.waystar.com"
        )
        assert DEFAULT_BASE_URL == DEFAULT_CLAIMS_BASE_URL

    def test_credentials_stored(self) -> None:
        client = WaystarClient(
            api_key="k",
            secret="s",
            user_id="u",
            password="p",
            cust_id="999",
        )
        assert client._secret == "s"
        assert client._user_id == "u"
        assert client._password == "p"
        assert client._cust_id == "999"
        client.close()

    def test_secret_defaults_to_api_key(self) -> None:
        client = WaystarClient(api_key="my-key")
        assert client._secret == "my-key"
        client.close()

    def test_custom_base_urls(self) -> None:
        client = WaystarClient(
            api_key="k",
            base_url="https://custom-claims.example.com",
            eligibility_base_url="https://custom-elig.example.com",
            prior_auth_base_url="https://custom-pa.example.com",
        )
        assert client._claims_base_url == "https://custom-claims.example.com"
        assert (
            client._eligibility_base_url
            == "https://custom-elig.example.com"
        )
        assert (
            client._prior_auth_base_url == "https://custom-pa.example.com"
        )
        client.close()


# ---------------------------------------------------------------------------
# AC-2: Eligibility (POST with UserID/Password form data)
# ---------------------------------------------------------------------------


class TestEligibility:
    """Verify eligibility request mapping and response parsing."""

    def test_eligibility_posts_form_data(self) -> None:
        """Eligibility sends POST with form-encoded UserID/Password."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200, json={"status": "active", "Status": "active"}
            )

        client = _make_client(handler)
        client.check_eligibility(
            {"payer_id": "00520", "npi": "1245319599"}
        )

        assert len(captured) == 1
        req = captured[0]
        assert req.method == "POST"
        assert ELIGIBILITY_PATH in str(req.url)

        # Verify form data includes auth fields
        body = req.content.decode()
        assert "UserID=test-user" in body
        assert "Password=test-pass" in body
        assert "CustID=12345" in body

    def test_eligibility_uses_eligibility_base_url(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "00520", "npi": "123"})

        url = str(captured[0].url)
        assert url.startswith(DEFAULT_ELIGIBILITY_BASE_URL)

    def test_eligibility_x12_270_from_fields(self) -> None:
        """Dict fields are converted to an X12 270 transaction."""
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

        body = captured[0].content.decode()
        assert "DataFormat=X12" in body
        assert "ResponseType=FullJSON" in body
        # Data field should contain X12 270 segments
        assert "Data=" in body
        assert "270" in body  # ST*270 segment
        assert "00520" in body  # payer_id in NM1*PR
        assert "1245319599" in body  # NPI in NM1*1P

    def test_eligibility_x12_raw_data(self) -> None:
        """When x12_data is provided, it is sent as-is with DataFormat=X12."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        x12_270 = "ISA*00*          *00*          *ZZ*SENDER*ZZ*RECEIVER*..."
        client.check_eligibility({"x12_data": x12_270})

        body = captured[0].content.decode()
        assert "DataFormat=X12" in body

    def test_eligibility_response_active(self) -> None:
        client = _make_client(
            _ok_json_handler(
                {
                    "status": "active",
                    "referenceId": "REF-123",
                    "planInfo": {"planName": "BCBS PPO"},
                }
            )
        )
        result = client.check_eligibility(
            {"payer_id": "00520", "npi": "123"}
        )

        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status == "active"
        assert result.eligible is True
        assert result.reference_id == "REF-123"
        assert result.plan_info.get("planName") == "BCBS PPO"

    def test_eligibility_response_inactive(self) -> None:
        client = _make_client(_ok_json_handler({"status": "inactive"}))
        result = client.check_eligibility(
            {"payer_id": "00520", "npi": "123"}
        )
        assert result.eligible is False

    def test_eligibility_non_json_response(self) -> None:
        """HTML/TEXT responses return raw_response with raw_text."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text="<html>Eligibility Report</html>",
                headers={"content-type": "text/html"},
            )

        client = _make_client(handler)
        result = client.check_eligibility(
            {"payer_id": "00520", "npi": "123"}
        )
        assert result.status == "received"
        assert "raw_text" in result.raw_response

    def test_eligibility_response_with_errors(self) -> None:
        client = _make_client(
            _ok_json_handler(
                {
                    "status": "error",
                    "ErrorMessage": "Invalid subscriber ID",
                }
            )
        )
        result = client.check_eligibility(
            {"payer_id": "00520", "npi": "123"}
        )
        assert result.errors == ["Invalid subscriber ID"]

    def test_eligibility_custom_response_type(self) -> None:
        """User can specify ResponseType=271 for raw X12 response."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, text="ISA*00*...*IEA*1*...")

        client = _make_client(handler)
        client.check_eligibility(
            {
                "payer_id": "00520",
                "npi": "123",
                "response_type": "271",
            }
        )
        body = captured[0].content.decode()
        assert "ResponseType=271" in body


# ---------------------------------------------------------------------------
# AC-3: Claim History (GET with HMAC query-string signing)
# ---------------------------------------------------------------------------


class TestClaimHistory:
    """Verify claim history request with HMAC signing."""

    def test_claim_history_uses_get(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("CLM-789")

        assert len(captured) == 1
        assert captured[0].method == "GET"

    def test_claim_history_uses_claims_base_url(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("CLM-789")

        url = str(captured[0].url)
        assert url.startswith(DEFAULT_CLAIMS_BASE_URL)
        assert CLAIM_HISTORY_PATH in url

    def test_claim_history_has_required_params(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status("CLM-789", dos="03/04/2026")

        url = str(captured[0].url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["CustID"] == ["12345"]
        assert params["ClaimNum"] == ["CLM-789"]
        assert params["DOS"] == ["03/04/2026"]
        assert params["ReqType"] == ["CLMHIST"]
        assert params["Version"] == ["2.0"]
        assert "TimeStamp" in params
        assert "Signature" in params
        # ResponseType excluded from signature but present in request
        assert params["ResponseType"] == ["XML"]

    def test_claim_history_hmac_signature(self) -> None:
        """HMAC signature is computed over query string (excl Signature and ResponseType)."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler, secret="test-hmac-secret")

        with patch(
            "claim_validator.clearinghouse.providers.waystar._utc_timestamp",
            return_value="03/04/2026 10:30:00 AM",
        ):
            client.check_claim_status("CLM-789", dos="05/01/2019")

        url = str(captured[0].url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Verify signature is present
        assert "Signature" in params
        sig = params["Signature"][0]
        assert len(sig) == 64  # SHA-256 hex digest

        # Verify signature is deterministic: recompute it
        # ResponseType is EXCLUDED from signature per Waystar docs
        query_to_sign = (
            "CustID=12345&DOS=05/01/2019&ClaimNum=CLM-789&"
            "ReqType=CLMHIST&"
            "Version=2.0&TimeStamp=03/04/2026 10:30:00 AM"
        )
        expected_sig = hmac_mod.new(
            b"test-hmac-secret",
            query_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()
        assert sig == expected_sig

        # Verify ResponseType is in the URL but was not signed
        assert params["ResponseType"] == ["XML"]

    def test_claim_history_hmac_deterministic(self) -> None:
        """Same inputs + same time → same signature."""
        results: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            results.append(params["Signature"][0])
            return httpx.Response(200, json={"status": "found"})

        with patch(
            "claim_validator.clearinghouse.providers.waystar._utc_timestamp",
            return_value="03/04/2026 10:30:00 AM",
        ):
            client1 = _make_client(handler)
            client1.check_claim_status("CLM-789", dos="03/04/2026")
            client2 = _make_client(handler)
            client2.check_claim_status("CLM-789", dos="03/04/2026")

        assert results[0] == results[1]

    def test_claim_history_by_params(self) -> None:
        """check_claim_status_by_params sends explicit fields."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "found"})

        client = _make_client(handler)
        client.check_claim_status_by_params(
            dos="03/01/2026", claim_num="CLM-100"
        )

        url = str(captured[0].url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        assert params["DOS"] == ["03/01/2026"]
        assert params["ClaimNum"] == ["CLM-100"]
        assert params["ReqType"] == ["CLMHIST"]
        assert params["ResponseType"] == ["XML"]

    def test_claim_history_json_response(self) -> None:
        client = _make_client(
            _ok_json_handler(
                {
                    "status": "found",
                    "ClaimStatus": "paid",
                    "AdjudicationDate": "2026-03-01",
                    "ReferenceId": "REF-789",
                }
            )
        )
        result = client.check_claim_status("CLM-789")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"
        assert result.adjudication_date == "2026-03-01"
        assert result.reference_id == "REF-789"

    def test_claim_history_xml_response(self) -> None:
        """XML/HTML responses return raw_response with raw_text."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                text="<ClaimHistory><Claim>...</Claim></ClaimHistory>",
                headers={"content-type": "text/xml"},
            )

        client = _make_client(handler)
        result = client.check_claim_status("CLM-789")
        assert result.status == "received"
        assert "raw_text" in result.raw_response
        assert "<ClaimHistory>" in result.raw_response["raw_text"]


# ---------------------------------------------------------------------------
# AC-4: Submit claim (placeholder)
# ---------------------------------------------------------------------------


class TestSubmitClaim:
    """Verify submit_claim raises until endpoint is confirmed."""

    def test_submit_claim_raises(self) -> None:
        client = _make_client(_ok_json_handler({}))
        with pytest.raises(ClearinghouseError, match="not yet configured"):
            client.submit_claim({"payer_id": "00520"})


# ---------------------------------------------------------------------------
# AC-5: Prior Auth
# ---------------------------------------------------------------------------


class TestPriorAuth:
    """Verify prior auth request structure."""

    def test_prior_auth_posts_json_with_credentials(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "received"})

        client = _make_client(handler)
        client.check_prior_auth_status("278*EDI*PAYLOAD*HERE~")

        assert len(captured) == 1
        req = captured[0]
        assert req.method == "POST"

        import json

        body = json.loads(req.content)
        assert body["Username"] == "test-user"
        assert body["Password"] == "test-pass"
        assert body["CustID"] == 12345
        assert body["PayloadType"] == 1952
        assert body["Relationship"] == ""
        assert body["Payload"] == "278*EDI*PAYLOAD*HERE~"

    def test_prior_auth_uses_prior_auth_base_url(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_prior_auth_status("test-payload")

        url = str(captured[0].url)
        assert url.startswith(DEFAULT_PRIOR_AUTH_BASE_URL)

    def test_prior_auth_dict_builds_278_x215(self) -> None:
        """Dict payload is converted to 278x215 EDI."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"ReferenceId": 123, "StatusMessage": "Received"},
            )

        client = _make_client(handler)
        client.check_prior_auth_status(
            {
                "payer_id": "66666",
                "npi": "1245319599",
                "subscriber_id": "SUB123",
                "first_name": "Alice",
                "last_name": "Williams",
                "dob": "1980-07-22",
                "procedure_code": "27447",
                "diagnosis_code": "M17.11",
            }
        )

        import json

        body = json.loads(captured[0].content)
        assert body["PayloadType"] == 1952
        # Payload should be a 278 EDI string with X215 version
        payload = body["Payload"]
        assert "ST*278" in payload
        assert "005010X215" in payload
        # Minimal 3-level HL: payer, provider, subscriber
        assert "HL*1**20*1" in payload
        assert "HL*2*1*21*1" in payload
        assert "HL*3*2*22*0" in payload
        assert "NM1*IL*1*WILLIAMS*ALICE" in payload

    def test_get_prior_auth_result(self) -> None:
        """Step 2: retrieve PA result by ReferenceId."""
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={
                    "ReferenceId": 1234567,
                    "StatusMessage": "Certified – in Total",
                    "ErrorMessage": "",
                    "Payload": "278x215 response EDI here",
                    "PayloadType": 1652,
                },
            )

        client = _make_client(handler)
        result = client.get_prior_auth_result(1234567)

        import json

        body = json.loads(captured[0].content)
        assert body["Username"] == "test-user"
        assert body["Password"] == "test-pass"
        assert body["CustID"] == "12345"
        assert body["ReferenceID"] == 1234567

        assert result["StatusMessage"] == "Certified – in Total"
        assert result["PayloadType"] == 1652


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
                client.check_eligibility(
                    {"payer_id": "00520", "npi": "123"}
                )
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

    def test_claim_history_timeout(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Connection timed out")

        client = _make_client(handler)
        with pytest.raises(
            ClearinghouseTimeoutError, match="claim history"
        ):
            client.check_claim_status("CLM-789")

    def test_no_phi_in_error_messages(self) -> None:
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
                "waystar",
                api_key="test-key",
                secret="test-secret",
                user_id="test-user",
                password="test-pass",
                cust_id="12345",
            )
            assert isinstance(client, WaystarClient)
            assert client.provider_name == "waystar"


# ---------------------------------------------------------------------------
# Utility function tests
# ---------------------------------------------------------------------------


class TestUtilities:
    """Verify helper functions."""

    def test_utc_timestamp_format(self) -> None:
        ts = _utc_timestamp()
        # Format: MM/DD/YYYY HH:MM:SS AM/PM
        assert "/" in ts
        assert ("AM" in ts) or ("PM" in ts)
        parts = ts.split(" ")
        assert len(parts) == 3  # date, time, AM/PM
