"""Tests for ChangeHealthcareClient."""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseServerError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.clearinghouse.providers.change_healthcare import (
    ChangeHealthcareClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token_response(token: str = "tok-123", expires_in: int = 3600) -> httpx.Response:
    """Build a mock OAuth2 token response."""
    return httpx.Response(
        200,
        json={"access_token": token, "expires_in": expires_in, "token_type": "bearer"},
    )


def _make_client(handler: Any) -> ChangeHealthcareClient:
    """Create a ChangeHealthcareClient with a mock HTTP transport."""
    transport = httpx.MockTransport(handler)
    client = ChangeHealthcareClient(
        client_id="test-id",
        client_secret="test-secret",
    )
    client._client.close()
    client._client = httpx.Client(
        transport=transport,
        base_url="https://sandbox.apigw.changehealthcare.com",
    )
    return client


# ---------------------------------------------------------------------------
# OAuth2 Authentication Tests (PE-2.1)
# ---------------------------------------------------------------------------

class TestOAuth2Authentication:
    """Tests for OAuth2 client_credentials flow."""

    def test_provider_name(self) -> None:
        client = ChangeHealthcareClient(client_id="id", client_secret="secret")
        assert client.provider_name == "change"
        client.close()

    def test_obtains_token_on_first_call(self) -> None:
        """First API call triggers OAuth2 token fetch."""
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        assert call_count["n"] >= 2  # token + API call
        client.close()

    def test_caches_token(self) -> None:
        """Second API call reuses cached token."""
        token_calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                token_calls["n"] += 1
                return _token_response()
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        client.check_eligibility({"payer_id": "test"})
        assert token_calls["n"] == 1  # Only one token request
        client.close()

    def test_refreshes_expired_token(self) -> None:
        """Token is refreshed when near expiry."""
        token_calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                token_calls["n"] += 1
                return _token_response(expires_in=1)  # Expires in 1s
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        # Force token to appear expired
        client._token_expiry = time.time() - 10
        client.check_eligibility({"payer_id": "test"})
        assert token_calls["n"] == 2  # Token refreshed
        client.close()

    def test_auth_failure_raises(self) -> None:
        """401 from token endpoint raises ClearinghouseAuthError."""

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return httpx.Response(401, json={"error": "invalid_client"})
            return httpx.Response(200, json={})

        client = _make_client(handler)
        with pytest.raises(ClearinghouseAuthError):
            client.check_eligibility({"payer_id": "test"})
        client.close()

    def test_token_set_in_authorization_header(self) -> None:
        """API calls include Bearer token in Authorization header."""
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response(token="my-bearer-token")
            captured_headers.update(dict(request.headers))
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        assert "authorization" in captured_headers
        assert captured_headers["authorization"] == "Bearer my-bearer-token"
        client.close()


# ---------------------------------------------------------------------------
# Eligibility Tests (PE-2.2)
# ---------------------------------------------------------------------------

class TestCheckEligibility:
    """Tests for ChangeHealthcareClient.check_eligibility()."""

    def test_returns_eligibility_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(200, json={
                "controlNumber": "123",
                "tradingPartnerServiceId": "test",
                "provider": {},
                "subscriber": {},
                "benefitsInformation": [],
            })

        client = _make_client(handler)
        result = client.check_eligibility({"payer_id": "60054"})
        assert isinstance(result, ClearinghouseEligibilityResponse)
        client.close()

    def test_posts_to_eligibility_endpoint(self) -> None:
        captured_url = {"url": ""}

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            captured_url["url"] = str(request.url)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        assert "eligibility" in captured_url["url"].lower()
        client.close()

    def test_server_error_raises(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(500, json={"error": "internal"})

        client = _make_client(handler)
        with pytest.raises(ClearinghouseError):
            client.check_eligibility({"payer_id": "test"})
        client.close()


# ---------------------------------------------------------------------------
# Claims Submission Tests (PE-2.3)
# ---------------------------------------------------------------------------

class TestSubmitClaim:
    """Tests for ChangeHealthcareClient.submit_claim()."""

    def test_returns_submission_result(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(200, json={
                "status": "accepted",
                "claimReference": "CHC-REF-001",
            })

        client = _make_client(handler)
        result = client.submit_claim({"npi": "1234567893"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True
        assert result.reference_id == "CHC-REF-001"
        client.close()

    def test_posts_to_claims_endpoint(self) -> None:
        captured_url = {"url": ""}

        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            captured_url["url"] = str(request.url)
            return httpx.Response(200, json={"status": "accepted", "claimReference": "X"})

        client = _make_client(handler)
        client.submit_claim({"npi": "1234567893"})
        assert "claim" in captured_url["url"].lower()
        client.close()

    def test_rejection_returns_not_accepted(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(200, json={
                "status": "rejected",
                "errors": [{"description": "Invalid NPI"}],
            })

        client = _make_client(handler)
        result = client.submit_claim({"npi": "bad"})
        assert result.accepted is False
        client.close()


# ---------------------------------------------------------------------------
# Claim Status Tests (PE-2.4)
# ---------------------------------------------------------------------------

class TestCheckClaimStatus:
    """Tests for ChangeHealthcareClient.check_claim_status()."""

    def test_returns_status_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(200, json={
                "status": "completed",
                "claimStatus": "paid",
                "claimReference": "CHC-REF-001",
            })

        client = _make_client(handler)
        result = client.check_claim_status("CHC-REF-001")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"
        client.close()

    def test_respects_retry_after(self) -> None:
        """429 with Retry-After should raise ClearinghouseError."""
        def handler(request: httpx.Request) -> httpx.Response:
            if "/token" in str(request.url):
                return _token_response()
            return httpx.Response(
                429,
                headers={"Retry-After": "30"},
                json={"error": "rate_limited"},
            )

        client = _make_client(handler)
        with pytest.raises(ClearinghouseError):
            client.check_claim_status("CHC-REF-001")
        client.close()


# ---------------------------------------------------------------------------
# Factory Registration Tests (PE-2.3)
# ---------------------------------------------------------------------------

class TestFactoryRegistration:
    """Test that 'change' is registered in the clearinghouse factory."""

    def test_factory_creates_change_client(self) -> None:
        from claim_validator.clearinghouse.factory import get_clearinghouse_client

        client = get_clearinghouse_client(
            "change",
            client_id="test-id",
            client_secret="test-secret",
        )
        assert isinstance(client, ChangeHealthcareClient)
        assert client.provider_name == "change"
        client.close()
