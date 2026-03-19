"""Change Healthcare clearinghouse client (Optum).

Implements OAuth2 client_credentials authentication, eligibility (270/271),
professional claims submission (837P), and claim status (276/277).
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
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)

# Change Healthcare API base URLs
_BASE_URL = "https://sandbox.apigw.changehealthcare.com"
_TOKEN_PATH = "/apip/auth/v2/token"
_ELIGIBILITY_PATH = "/medicalnetwork/eligibility/v3"
_CLAIMS_PATH = "/medicalnetwork/professionalclaims/v3/submission"
_CLAIM_STATUS_PATH = "/medicalnetwork/claimstatus/v2"

# Refresh token 5 minutes before expiry
_TOKEN_REFRESH_BUFFER_SECONDS = 300


class ChangeHealthcareClient(BaseClearinghouseClient):
    """Change Healthcare (Optum) clearinghouse client.

    Authenticates via OAuth2 ``client_credentials`` flow.  Tokens are cached
    and refreshed automatically 5 minutes before expiry.

    Args:
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        base_url: API base URL (defaults to sandbox).
        timeout: HTTP timeout in seconds.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = _BASE_URL,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        # BaseClearinghouseClient expects api_key — pass client_id
        super().__init__(api_key=client_id, base_url=base_url, timeout=timeout, **kwargs)
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "change"

    # ------------------------------------------------------------------
    # OAuth2 token management (private)
    # ------------------------------------------------------------------

    def _get_oauth_token(self) -> str:
        """Obtain or return a cached OAuth2 access token.

        Automatically refreshes the token if it is expired or about to
        expire (within 5 minutes of expiry).
        """
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
                f"Change Healthcare OAuth2 authentication failed: HTTP {resp.status_code}"
            )
        if resp.status_code >= 400:
            raise ClearinghouseError(
                f"Change Healthcare token request failed: HTTP {resp.status_code}"
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
        """Make an authenticated HTTP request, handling common errors."""
        token = self._get_oauth_token()
        headers = {"Authorization": f"Bearer {token}"}

        resp = self._client.request(method, path, json=json_body, headers=headers)

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "unknown")
            raise ClearinghouseError(
                f"Change Healthcare rate limited. Retry-After: {retry_after}"
            )
        if resp.status_code in (401, 403):
            raise ClearinghouseAuthError(
                f"Change Healthcare auth error: HTTP {resp.status_code}"
            )
        if resp.status_code >= 500:
            raise ClearinghouseServerError(
                f"Change Healthcare server error: HTTP {resp.status_code}"
            )
        if resp.status_code >= 400:
            raise ClearinghouseValidationError(
                f"Change Healthcare validation error: HTTP {resp.status_code}"
            )
        return resp

    # ------------------------------------------------------------------
    # Public API (BaseClearinghouseClient contract)
    # ------------------------------------------------------------------

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility via Change Healthcare (270/271).

        Posts JSON to the eligibility v3 endpoint.  Business rejections
        (AAA segments) are returned in the response, not raised as exceptions.
        """
        resp = self._authed_request("POST", _ELIGIBILITY_PATH, json_body=request)
        body = resp.json()

        errors: list[str] = []
        if "errors" in body:
            errors = [e.get("description", str(e)) for e in body["errors"]]

        benefits = body.get("benefitsInformation", [])
        plan_info = {"benefits": benefits} if isinstance(benefits, list) else benefits

        return ClearinghouseEligibilityResponse(
            status=body.get("status", "ok"),
            eligible=body.get("eligible"),
            reference_id=body.get("controlNumber"),
            plan_info=plan_info,
            raw_response=body,
            errors=errors,
        )

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a professional claim to Change Healthcare (837P).

        Posts JSON to the professional claims v3 endpoint.
        """
        resp = self._authed_request("POST", _CLAIMS_PATH, json_body=claim_data)
        body = resp.json()

        status = body.get("status", "unknown")
        accepted = status.lower() in ("accepted", "ok", "success")
        errors: list[str] = []
        if "errors" in body:
            errors = [e.get("description", str(e)) for e in body["errors"]]

        return SubmissionResult(
            status=status,
            accepted=accepted,
            reference_id=body.get("claimReference"),
            raw_response=body,
            errors=errors,
        )

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim status via Change Healthcare (276/277).

        Respects ``Retry-After`` headers if rate-limited (PFR8).
        """
        resp = self._authed_request(
            "POST", _CLAIM_STATUS_PATH, json_body={"claimReference": claim_ref}
        )
        body = resp.json()

        return ClaimStatusResponse(
            status=body.get("status", "unknown"),
            claim_status=body.get("claimStatus"),
            adjudication_date=body.get("adjudicationDate"),
            reference_id=body.get("claimReference"),
            raw_response=body,
        )
