"""Tests for AvailityClient."""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseError,
    ClearinghouseTimeoutError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.clearinghouse.providers.availity import AvailityClient

_BASE = "https://api.availity.com"


def _token_response(token: str = "av-tok", expires_in: int = 3600) -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": token, "expires_in": expires_in, "token_type": "bearer"},
    )


def _make_client(handler: Any) -> AvailityClient:
    transport = httpx.MockTransport(handler)
    client = AvailityClient(client_id="test-id", client_secret="test-secret")
    client._client.close()
    client._client = httpx.Client(transport=transport, base_url=_BASE)
    return client


# ---------------------------------------------------------------------------
# OAuth2 (PE-3.1)
# ---------------------------------------------------------------------------

class TestAvailityOAuth2:
    def test_provider_name(self) -> None:
        client = AvailityClient(client_id="id", client_secret="s")
        assert client.provider_name == "availity"
        client.close()

    def test_obtains_token_on_first_call(self) -> None:
        token_calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                token_calls["n"] += 1
                return _token_response()
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "test"})
        assert token_calls["n"] == 1
        client.close()

    def test_caches_token(self) -> None:
        token_calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                token_calls["n"] += 1
                return _token_response()
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "t1"})
        client.check_eligibility({"payer_id": "t2"})
        assert token_calls["n"] == 1
        client.close()

    def test_refreshes_expired_token(self) -> None:
        token_calls = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                token_calls["n"] += 1
                return _token_response(expires_in=1)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "t"})
        client._token_expiry = time.time() - 10
        client.check_eligibility({"payer_id": "t"})
        assert token_calls["n"] == 2
        client.close()

    def test_auth_failure_raises(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return httpx.Response(401, json={"error": "invalid_client"})
            return httpx.Response(200, json={})

        client = _make_client(handler)
        with pytest.raises(ClearinghouseAuthError):
            client.check_eligibility({"payer_id": "t"})
        client.close()

    def test_bearer_token_in_header(self) -> None:
        captured: dict[str, str] = {}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response(token="my-av-token")
            captured.update(dict(req.headers))
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "t"})
        assert captured.get("authorization") == "Bearer my-av-token"
        client.close()


# ---------------------------------------------------------------------------
# Eligibility (PE-3.2)
# ---------------------------------------------------------------------------

class TestAvailityEligibility:
    def test_returns_eligibility_response(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            return httpx.Response(200, json={
                "requestId": "R1",
                "coverages": [{"status": "active"}],
            })

        client = _make_client(handler)
        result = client.check_eligibility({"payer_id": "BCBS01"})
        assert isinstance(result, ClearinghouseEligibilityResponse)
        client.close()

    def test_posts_to_coverages_endpoint(self) -> None:
        captured_url = {"url": ""}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            captured_url["url"] = str(req.url)
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client.check_eligibility({"payer_id": "t"})
        assert "coverages" in captured_url["url"].lower() or "eligibility" in captured_url["url"].lower()
        client.close()

    def test_server_error_raises(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            return httpx.Response(500, json={"error": "internal"})

        client = _make_client(handler)
        with pytest.raises(ClearinghouseError):
            client.check_eligibility({"payer_id": "t"})
        client.close()


# ---------------------------------------------------------------------------
# Claims Submission (PE-3.3)
# ---------------------------------------------------------------------------

class TestAvailitySubmitClaim:
    def test_returns_submission_result(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            return httpx.Response(200, json={
                "status": "accepted",
                "id": "AV-REF-001",
            })

        client = _make_client(handler)
        result = client.submit_claim({"npi": "1234567893"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True
        assert result.reference_id == "AV-REF-001"
        client.close()

    def test_posts_to_claims_endpoint(self) -> None:
        captured_url = {"url": ""}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            captured_url["url"] = str(req.url)
            return httpx.Response(200, json={"status": "accepted", "id": "X"})

        client = _make_client(handler)
        client.submit_claim({"npi": "1234567893"})
        assert "claim" in captured_url["url"].lower()
        client.close()


# ---------------------------------------------------------------------------
# Claim Status (PE-3.3 continued)
# ---------------------------------------------------------------------------

class TestAvailityClaimStatus:
    def test_returns_status_response(self) -> None:
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            return httpx.Response(200, json={
                "status": "complete",
                "claimStatus": "paid",
                "id": "AV-REF-001",
            })

        client = _make_client(handler)
        result = client.check_claim_status("AV-REF-001")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"
        client.close()


# ---------------------------------------------------------------------------
# Async Polling (PE-3.4)
# ---------------------------------------------------------------------------

class TestAvailityAsyncPolling:
    def test_sync_response_returned_immediately(self) -> None:
        """Non-async response returned without polling."""
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            return httpx.Response(200, json={"status": "complete", "id": "X"})

        client = _make_client(handler)
        result = client.submit_claim({"npi": "1234567893"})
        assert result.accepted is True
        client.close()

    def test_async_response_polls_until_complete(self) -> None:
        """Async response triggers polling."""
        call_count = {"n": 0}

        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            # First call: submit returns pending with status URL
            if "claims" in str(req.url).lower() and req.method == "POST":
                return httpx.Response(200, json={
                    "status": "pending",
                    "statusUrl": "/availity/v1/claims/status/POLL-1",
                    "id": "POLL-1",
                })
            # Poll calls: first returns pending, second returns complete
            if "status" in str(req.url).lower():
                call_count["n"] += 1
                if call_count["n"] < 2:
                    return httpx.Response(200, json={"status": "pending", "id": "POLL-1"})
                return httpx.Response(200, json={
                    "status": "complete",
                    "id": "POLL-1",
                })
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler)
        client._poll_interval = 0.01  # Speed up for test
        result = client.submit_claim({"npi": "1234567893"})
        assert result.accepted is True
        assert call_count["n"] >= 1
        client.close()

    def test_polling_exceeds_max_raises_timeout(self) -> None:
        """Polling that never completes raises ClearinghouseTimeoutError."""
        def handler(req: httpx.Request) -> httpx.Response:
            if "/token" in str(req.url):
                return _token_response()
            if "claims" in str(req.url).lower() and req.method == "POST":
                return httpx.Response(200, json={
                    "status": "pending",
                    "statusUrl": "/availity/v1/claims/status/POLL-X",
                    "id": "POLL-X",
                })
            # Always return pending
            return httpx.Response(200, json={"status": "pending", "id": "POLL-X"})

        client = _make_client(handler)
        client._poll_interval = 0.01
        client._max_poll_attempts = 2
        with pytest.raises(ClearinghouseTimeoutError, match="polling"):
            client.submit_claim({"npi": "1234567893"})
        client.close()


# ---------------------------------------------------------------------------
# Factory Registration
# ---------------------------------------------------------------------------

class TestAvailityFactory:
    def test_factory_creates_availity_client(self) -> None:
        from claim_validator.clearinghouse.factory import get_clearinghouse_client

        client = get_clearinghouse_client(
            "availity", client_id="id", client_secret="s",
        )
        assert isinstance(client, AvailityClient)
        assert client.provider_name == "availity"
        client.close()
