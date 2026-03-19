"""Availity clearinghouse client.

Implements OAuth2 client_credentials authentication, eligibility (coverages),
claims submission, claim status, and async response polling for payers
that return asynchronous results.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from claim_validator.clearinghouse.base import BaseClearinghouseClient
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
    SubmissionResult,
)

_BASE_URL = "https://api.availity.com"
_TOKEN_PATH = "/availity/v1/token"
_COVERAGES_PATH = "/availity/v1/coverages"
_CLAIMS_PATH = "/availity/v1/claims"
_CLAIM_STATUS_PATH = "/availity/v1/claim-statuses"

_TOKEN_REFRESH_BUFFER_SECONDS = 300
_DEFAULT_POLL_INTERVAL = 5.0
_DEFAULT_MAX_POLL_ATTEMPTS = 3


class AvailityClient(BaseClearinghouseClient):
    """Availity clearinghouse client for BCBS, Humana, Cigna payers.

    Authenticates via OAuth2 ``client_credentials``.  Handles async response
    patterns by polling the status endpoint for payers that return
    ``pending``/``processing`` responses.

    Args:
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        base_url: API base URL.
        timeout: HTTP timeout in seconds.
        poll_interval: Seconds between async poll attempts.
        max_poll_attempts: Maximum polling attempts before timeout.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = _BASE_URL,
        timeout: float = 60.0,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
        max_poll_attempts: int = _DEFAULT_MAX_POLL_ATTEMPTS,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key=client_id, base_url=base_url, timeout=timeout, **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expiry: float = 0.0
        self._poll_interval = poll_interval
        self._max_poll_attempts = max_poll_attempts

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "availity"

    # ------------------------------------------------------------------
    # OAuth2
    # ------------------------------------------------------------------

    def _get_oauth_token(self) -> str:
        """Obtain or return a cached OAuth2 access token."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        """Request a new OAuth2 token via client_credentials flow."""
        resp = self._client.post(
            _TOKEN_PATH,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        if resp.status_code in (401, 403):
            raise ClearinghouseAuthError(
                f"Availity OAuth2 authentication failed: HTTP {resp.status_code}"
            )
        if resp.status_code >= 400:
            raise ClearinghouseError(
                f"Availity token request failed: HTTP {resp.status_code}"
            )
        body = resp.json()
        self._access_token = body["access_token"]
        expires_in = body.get("expires_in", 3600)
        self._token_expiry = time.time() + expires_in - _TOKEN_REFRESH_BUFFER_SECONDS
        return self._access_token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Authenticated request helper
    # ------------------------------------------------------------------

    def _authed_request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an authenticated HTTP request."""
        token = self._get_oauth_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = self._client.request(method, path, json=json_body, headers=headers)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "unknown")
            raise ClearinghouseError(
                f"Availity rate limited. Retry-After: {retry_after}"
            )
        if resp.status_code in (401, 403):
            raise ClearinghouseAuthError(
                f"Availity auth error: HTTP {resp.status_code}"
            )
        if resp.status_code >= 500:
            raise ClearinghouseServerError(
                f"Availity server error: HTTP {resp.status_code}"
            )
        if resp.status_code >= 400:
            raise ClearinghouseValidationError(
                f"Availity validation error: HTTP {resp.status_code}"
            )
        return resp

    # ------------------------------------------------------------------
    # Async polling
    # ------------------------------------------------------------------

    def _poll_for_result(self, status_url: str) -> dict[str, Any]:
        """Poll a status URL until the response is no longer pending.

        Raises:
            ClearinghouseTimeoutError: If max poll attempts exceeded.
        """
        for _attempt in range(self._max_poll_attempts):
            time.sleep(self._poll_interval)
            resp = self._authed_request("GET", status_url)
            body = resp.json()
            status = body.get("status", "").lower()
            if status not in ("pending", "processing"):
                return body
        raise ClearinghouseTimeoutError(
            f"Availity async polling exceeded {self._max_poll_attempts} attempts"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Check patient eligibility via Availity coverages endpoint."""
        resp = self._authed_request("POST", _COVERAGES_PATH, json_body=request)
        body = resp.json()

        errors: list[str] = []
        if "errors" in body:
            errors = [e.get("message", str(e)) for e in body["errors"]]

        coverages = body.get("coverages", [])
        plan_info = {"coverages": coverages} if isinstance(coverages, list) else coverages

        return ClearinghouseEligibilityResponse(
            status=body.get("status", "ok"),
            eligible=body.get("eligible"),
            reference_id=body.get("requestId"),
            plan_info=plan_info,
            raw_response=body,
            errors=errors,
        )

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a claim through Availity.

        If the response indicates an async pattern (``status`` is ``pending``
        and ``statusUrl`` is present), polls until completion or timeout.
        """
        resp = self._authed_request("POST", _CLAIMS_PATH, json_body=claim_data)
        body = resp.json()

        # Handle async response pattern
        status = body.get("status", "unknown").lower()
        status_url = body.get("statusUrl")
        if status in ("pending", "processing") and status_url:
            body = self._poll_for_result(status_url)
            status = body.get("status", "unknown").lower()

        accepted = status in ("accepted", "complete", "ok", "success")
        errors: list[str] = []
        if "errors" in body:
            errors = [e.get("message", str(e)) for e in body["errors"]]

        return SubmissionResult(
            status=body.get("status", status),
            accepted=accepted,
            reference_id=body.get("id"),
            raw_response=body,
            errors=errors,
        )

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim status via Availity."""
        resp = self._authed_request(
            "GET", f"{_CLAIM_STATUS_PATH}/{claim_ref}"
        )
        body = resp.json()

        return ClaimStatusResponse(
            status=body.get("status", "unknown"),
            claim_status=body.get("claimStatus"),
            adjudication_date=body.get("adjudicationDate"),
            reference_id=body.get("id"),
            raw_response=body,
        )
