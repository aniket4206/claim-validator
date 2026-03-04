"""Waystar clearinghouse provider — HMAC-SHA256 authenticated REST."""

from __future__ import annotations

import time
from typing import Any

import httpx

from claim_validator.clearinghouse.auth import HMACAuth
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

DEFAULT_BASE_URL = "https://api.waystar.com"

# NOTE: These endpoint paths are provisional. Verify against
# Waystar developer portal documentation before production use.
ELIGIBILITY_PATH = "/api/v1/eligibility"
CLAIMS_PATH = "/api/v1/claims"
STATUS_PATH = "/api/v1/claims/status"


class WaystarClient(BaseClearinghouseClient):
    """Waystar clearinghouse client with HMAC-SHA256 authentication.

    Implements the ``BaseClearinghouseClient`` interface for the Waystar
    platform, using ``HMACAuth`` to sign every request.

    Note:
        Endpoint paths are provisional. Verify against Waystar developer
        portal documentation before production use.

    Args:
        api_key: Waystar API key for HMAC signing.
        secret: Waystar HMAC secret.
        base_url: Override the default Waystar base URL.
        timeout: HTTP request timeout in seconds.
        **kwargs: Passed to ``BaseClearinghouseClient``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret: str = "",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key, base_url=base_url, timeout=timeout, **kwargs
        )
        self._secret = secret
        # Replace the base httpx client with one using HMAC auth
        self._client.close()
        self._client = httpx.Client(
            base_url=base_url,
            auth=HMACAuth(api_key=api_key, secret=secret),
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"Content-Type": "application/json"},
        )

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "waystar"

    # -- Public API methods --------------------------------------------------

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility via Waystar (270/271).

        Args:
            request: Eligibility request with keys ``payer_id``, ``npi``,
                ``subscriber_id``, ``first_name``, ``last_name``, ``dob``,
                ``service_type``, etc.

        Returns:
            Normalized eligibility response.
        """
        payload = self._to_waystar_eligibility(request)
        response = self._post_with_retry(ELIGIBILITY_PATH, payload)
        self._handle_response(response)
        data = response.json()
        return self._parse_eligibility_response(data)

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a claim to Waystar.

        Args:
            claim_data: Claim data dictionary.

        Returns:
            Submission acknowledgment result.
        """
        payload = self._to_waystar_claim(claim_data)
        response = self._post_with_retry(CLAIMS_PATH, payload)
        self._handle_response(response)
        data = response.json()
        return self._parse_submission_response(data)

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim status via Waystar (276/277).

        Args:
            claim_ref: Claim reference identifier.

        Returns:
            Claim status response.
        """
        payload = {"claimReference": claim_ref}
        response = self._post_with_retry(STATUS_PATH, payload)
        self._handle_response(response)
        data = response.json()
        return self._parse_status_response(data)

    # -- Field mapping helpers -----------------------------------------------

    @staticmethod
    def _to_waystar_eligibility(request: dict[str, Any]) -> dict[str, Any]:
        """Translate library eligibility dict to Waystar JSON format."""
        payload: dict[str, Any] = {
            "payerId": request.get("payer_id", ""),
            "providerNpi": request.get("npi", ""),
        }
        subscriber: dict[str, Any] = {}
        if "subscriber_id" in request:
            subscriber["memberId"] = request["subscriber_id"]
        if "first_name" in request:
            subscriber["firstName"] = request["first_name"]
        if "last_name" in request:
            subscriber["lastName"] = request["last_name"]
        if "dob" in request:
            subscriber["dateOfBirth"] = request["dob"]
        if subscriber:
            payload["subscriber"] = subscriber
        if "service_type" in request:
            payload["serviceTypeCode"] = request["service_type"]
        return payload

    @staticmethod
    def _to_waystar_claim(claim_data: dict[str, Any]) -> dict[str, Any]:
        """Translate library claim dict to Waystar JSON format."""
        payload: dict[str, Any] = {
            "payerId": claim_data.get("payer_id", ""),
        }
        if "billing_npi" in claim_data:
            payload["billingNpi"] = claim_data["billing_npi"]
        if "subscriber_id" in claim_data:
            payload["subscriberId"] = claim_data["subscriber_id"]
        if "total_charge" in claim_data:
            payload["totalCharge"] = str(claim_data["total_charge"])
        if "diagnosis_codes" in claim_data:
            payload["diagnosisCodes"] = claim_data["diagnosis_codes"]
        if "lines" in claim_data:
            payload["serviceLines"] = [
                {
                    "procedureCode": line.get("cpt_code", ""),
                    "chargeAmount": str(line.get("charge", "")),
                    "units": str(line.get("units", "1")),
                }
                for line in claim_data["lines"]
            ]
        return payload

    # -- Response parsing helpers --------------------------------------------

    @staticmethod
    def _parse_eligibility_response(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse Waystar eligibility response to library model."""
        status = data.get("status", "unknown")
        eligible: bool | None = None
        if status.lower() in ("active", "eligible"):
            eligible = True
        elif status.lower() in ("inactive", "ineligible"):
            eligible = False

        return ClearinghouseEligibilityResponse(
            status=status,
            eligible=eligible,
            reference_id=data.get("referenceId"),
            plan_info=data.get("planInfo", {}),
            raw_response=data,
        )

    @staticmethod
    def _parse_submission_response(data: dict[str, Any]) -> SubmissionResult:
        """Parse Waystar claim submission response to library model."""
        status = data.get("status", "unknown")
        accepted = status.lower() in ("accepted", "success")
        return SubmissionResult(
            status=status,
            accepted=accepted,
            reference_id=data.get("referenceId"),
            raw_response=data,
            errors=data.get("errors", []),
        )

    @staticmethod
    def _parse_status_response(data: dict[str, Any]) -> ClaimStatusResponse:
        """Parse Waystar claim status response to library model."""
        return ClaimStatusResponse(
            status=data.get("status", "unknown"),
            claim_status=data.get("claimStatus"),
            adjudication_date=data.get("adjudicationDate"),
            reference_id=data.get("referenceId"),
            raw_response=data,
        )

    # -- HTTP helpers --------------------------------------------------------

    def _handle_response(self, response: httpx.Response) -> None:
        """Map HTTP error codes to clearinghouse exceptions."""
        if response.status_code == 200:
            return
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

    def _post_with_retry(
        self, path: str, json: dict[str, Any]
    ) -> httpx.Response:
        """POST with one retry on 5xx and timeout wrapping."""
        try:
            response = self._client.post(path, json=json)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.post(path, json=json)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Waystar request timed out: {path}"
            ) from exc
