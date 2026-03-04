"""Claim.MD clearinghouse provider — REST with AccountKey auth."""

from __future__ import annotations

import json
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

DEFAULT_BASE_URL = "https://svc.claim.md"

_ELIGIBILITY_PATH = "/services/eligdata/"
_UPLOAD_PATH = "/services/upload/"
_RESPONSE_PATH = "/services/response/"


def _to_claimmd_date(date_str: str) -> str:
    """Convert ``YYYY-MM-DD`` to ``MM/DD/YYYY`` for Claim.MD date format."""
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    return date_str


class ClaimMDClient(BaseClearinghouseClient):
    """Claim.MD clearinghouse client.

    Implements the ``BaseClearinghouseClient`` interface for the Claim.MD
    API using their REST endpoints with form-data payloads and AccountKey
    authentication.

    Args:
        account_key: Claim.MD AccountKey for authentication.
        api_key: Alias for account_key (for factory compatibility).
        base_url: Override the default Claim.MD base URL.
        timeout: HTTP request timeout in seconds.
        **kwargs: Passed to ``BaseClearinghouseClient``.
    """

    def __init__(
        self,
        *,
        account_key: str = "",
        api_key: str = "",
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        # Accept either account_key or api_key for factory compatibility
        resolved_key = account_key or api_key
        super().__init__(
            api_key=resolved_key, base_url=base_url, timeout=timeout, **kwargs
        )
        self._account_key = resolved_key

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "claimmd"

    # -- Public API methods --------------------------------------------------

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility via Claim.MD (270/271).

        Args:
            request: Eligibility request with keys ``payer_id``, ``npi``,
                ``subscriber_id``, ``first_name``, ``last_name``, ``dob``,
                ``service_date``, etc.

        Returns:
            Normalized eligibility response.
        """
        form_data = self._to_claimmd_eligibility(request)
        response = self._post_form_with_retry(_ELIGIBILITY_PATH, form_data)
        data = self._handle_response(response)
        return self._parse_eligibility_response(data)

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Upload a claim to Claim.MD.

        Args:
            claim_data: Claim data dictionary.

        Returns:
            Submission acknowledgment with batch reference.
        """
        form_data = self._to_claimmd_upload(claim_data)
        response = self._post_form_with_retry(_UPLOAD_PATH, form_data)
        data = self._handle_response(response)
        return self._parse_submission_response(data)

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim status / retrieve responses from Claim.MD.

        Args:
            claim_ref: Claim.MD ResponseID reference.

        Returns:
            Claim status response.
        """
        form_data = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
            "ResponseID": claim_ref,
        }
        response = self._post_form_with_retry(_RESPONSE_PATH, form_data)
        data = self._handle_response(response)
        return self._parse_status_response(data)

    # -- Field mapping helpers -----------------------------------------------

    def _to_claimmd_eligibility(
        self, request: dict[str, Any]
    ) -> dict[str, str]:
        """Translate library eligibility dict to Claim.MD form data."""
        form: dict[str, str] = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
        }
        if "payer_id" in request:
            form["PayerID"] = request["payer_id"]
        if "npi" in request:
            form["ProviderNPI"] = request["npi"]
        if "subscriber_id" in request:
            form["InsuredID"] = request["subscriber_id"]
        if "first_name" in request:
            form["InsuredFirstName"] = request["first_name"]
        if "last_name" in request:
            form["InsuredLastName"] = request["last_name"]
        if "dob" in request:
            form["InsuredDOB"] = _to_claimmd_date(request["dob"])
        if "service_date" in request:
            form["ServiceDate"] = _to_claimmd_date(request["service_date"])
        return form

    def _to_claimmd_upload(
        self, claim_data: dict[str, Any]
    ) -> dict[str, str]:
        """Translate library claim dict to Claim.MD upload form data."""
        form: dict[str, str] = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
        }
        # Send claim data as JSON in the File parameter
        form["File"] = json.dumps(claim_data)
        return form

    # -- Response parsing helpers --------------------------------------------

    @staticmethod
    def _parse_eligibility_response(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse Claim.MD eligibility response to library model."""
        status = data.get("status", "unknown")
        eligible: bool | None = None
        if status.lower() in ("active", "a"):
            eligible = True
        elif status.lower() in ("inactive", "i"):
            eligible = False

        plan_info: dict[str, Any] = {}
        if "plan" in data:
            plan_info = data["plan"]

        return ClearinghouseEligibilityResponse(
            status=status,
            eligible=eligible,
            reference_id=data.get("responseID"),
            plan_info=plan_info,
            raw_response=data,
            errors=data.get("errors", []),
        )

    @staticmethod
    def _parse_submission_response(data: dict[str, Any]) -> SubmissionResult:
        """Parse Claim.MD upload response to library model."""
        status = data.get("status", "unknown")
        accepted = status.lower() in ("ok", "accepted", "success")
        return SubmissionResult(
            status=status,
            accepted=accepted,
            reference_id=data.get("batchID") or data.get("responseID"),
            raw_response=data,
            errors=data.get("errors", []),
        )

    @staticmethod
    def _parse_status_response(data: dict[str, Any]) -> ClaimStatusResponse:
        """Parse Claim.MD response retrieval to library model."""
        return ClaimStatusResponse(
            status=data.get("status", "unknown"),
            claim_status=data.get("claimStatus"),
            adjudication_date=data.get("adjudicationDate"),
            reference_id=data.get("responseID"),
            raw_response=data,
        )

    # -- HTTP helpers --------------------------------------------------------

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Map HTTP errors and body-level errors to exceptions.

        Claim.MD may return errors in the response body JSON even with
        HTTP 200, so both HTTP status and body ``status`` field are checked.
        """
        if response.status_code in (401, 403):
            raise ClearinghouseAuthError("Invalid AccountKey")
        if response.status_code >= 500:
            raise ClearinghouseServerError(f"HTTP {response.status_code}")

        try:
            data: dict[str, Any] = response.json()
        except Exception:
            msg = f"HTTP {response.status_code}"
            raise ClearinghouseError(msg) from None

        if response.status_code >= 400:
            error_msg = data.get("message", f"HTTP {response.status_code}")
            raise ClearinghouseValidationError(error_msg)

        # Check body-level error status
        if data.get("status") == "error":
            error_msg = data.get("message", "Unknown error")
            raise ClearinghouseValidationError(error_msg)

        return data

    def _post_form_with_retry(
        self,
        path: str,
        form_data: dict[str, str],
    ) -> httpx.Response:
        """POST form data with one retry on 5xx and timeout wrapping."""
        try:
            response = self._client.post(path, data=form_data)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.post(path, data=form_data)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Claim.MD request timed out: {path}"
            ) from exc
