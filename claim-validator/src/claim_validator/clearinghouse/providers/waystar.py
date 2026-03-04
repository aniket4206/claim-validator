"""Waystar clearinghouse provider — real API integration.

Waystar uses three separate service endpoints with different auth:
  - Claim History:  GET  + HMAC-SHA256 query-string signing
  - Eligibility:    POST + UserID/Password form fields
  - Prior Auth:     POST + Username/Password in JSON body

NOTE: Endpoint paths verified against Waystar developer documentation
(March 2026). Always confirm against the Waystar developer portal
before production use.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

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

# -- Default base URLs per service ------------------------------------------
DEFAULT_CLAIMS_BASE_URL = "https://claimsapi.zirmed.com"
DEFAULT_ELIGIBILITY_BASE_URL = "https://eligibilityapi.zirmed.com"
DEFAULT_PRIOR_AUTH_BASE_URL = "https://priorauthorizationapi.waystar.com"

# Keep legacy alias for backwards compat with factory / tests
DEFAULT_BASE_URL = DEFAULT_CLAIMS_BASE_URL

# -- Endpoint paths ---------------------------------------------------------
CLAIM_HISTORY_PATH = "/2.0/v1/History/GetClaimHistory"
ELIGIBILITY_PATH = "/1.0/Rest/Gateway/GatewayAsync.ashx"
PRIOR_AUTH_SUBMIT_PATH = "/1.0/Rest/Request/Submit"
PRIOR_AUTH_STATUS_PATH = "/1.0/Rest/Request/Status"


def _utc_timestamp() -> str:
    """Return current UTC time in Waystar format: ``MM/DD/YYYY HH:MM:SS AM/PM``."""
    now = datetime.now(UTC)
    return now.strftime("%m/%d/%Y %I:%M:%S %p")


class WaystarClient(BaseClearinghouseClient):
    """Waystar clearinghouse client — real API integration.

    Supports three Waystar services:
      - **Eligibility** (270/271): POST with UserID/Password auth
      - **Claim History**: GET with HMAC-SHA256 query-string signing
      - **Prior Auth** (278): POST with Username/Password in JSON body

    Args:
        api_key: Waystar API key (used for HMAC signing on claim history).
        secret: HMAC secret for claim history signing. If empty, ``api_key``
            is used as the HMAC key.
        user_id: UserID for eligibility endpoint authentication.
        password: Password for eligibility and prior auth endpoints.
        cust_id: Waystar Customer ID (integer as string).
        base_url: Override claims service base URL.
        eligibility_base_url: Override eligibility service base URL.
        prior_auth_base_url: Override prior auth service base URL.
        timeout: HTTP request timeout in seconds.
        **kwargs: Passed to ``BaseClearinghouseClient``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret: str = "",
        user_id: str = "",
        password: str = "",
        cust_id: str = "",
        base_url: str = "",
        eligibility_base_url: str = "",
        prior_auth_base_url: str = "",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        effective_base = base_url or DEFAULT_CLAIMS_BASE_URL
        super().__init__(
            api_key=api_key,
            base_url=effective_base,
            timeout=timeout,
            **kwargs,
        )
        self._secret = secret or api_key
        self._user_id = user_id
        self._password = password
        self._cust_id = cust_id
        self._claims_base_url = effective_base
        self._eligibility_base_url = (
            eligibility_base_url or DEFAULT_ELIGIBILITY_BASE_URL
        )
        self._prior_auth_base_url = (
            prior_auth_base_url or DEFAULT_PRIOR_AUTH_BASE_URL
        )
        # Replace inherited client with a plain one (no base_url / auth)
        self._client.close()
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "waystar"

    # ── Public API methods ─────────────────────────────────────────────

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility via Waystar (270/271).

        The eligibility endpoint accepts X12 270 EDI data or a simplified
        dict which is converted to form fields.

        Args:
            request: Eligibility request dict. Supported keys:

                - ``payer_id``, ``npi``, ``subscriber_id``, ``first_name``,
                  ``last_name``, ``dob``, ``service_type`` — standard fields
                - ``x12_data`` — raw X12 270 string (bypasses field mapping)
                - ``data_format`` — ``"X12"`` or ``"SF1"`` (default ``"SF1"``)
                - ``response_type`` — ``"FullJSON"``, ``"JSON"``, ``"271"``,
                  ``"HTML"``, ``"TEXT"`` (default ``"FullJSON"``)

        Returns:
            Normalized eligibility response.
        """
        url = f"{self._eligibility_base_url}{ELIGIBILITY_PATH}"
        form_data = self._build_eligibility_form(request)
        response = self._post_form_with_retry(url, form_data)
        # Waystar may return 401 with a full 271 EDI body on auth failure.
        # Parse the body first to extract Waystar-specific error details.
        if response.status_code in (401, 403):
            try:
                data = response.json()
                alerts = data.get("WaystarAlerts", [])
                msg = "; ".join(alerts) if alerts else f"HTTP {response.status_code}"
            except Exception:
                msg = f"HTTP {response.status_code}"
            raise ClearinghouseAuthError(msg)
        self._handle_response(response)
        return self._parse_eligibility_response(response)

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a claim to Waystar.

        NOTE: The Waystar Claims submission endpoint documentation has not
        been verified yet. This method is a placeholder that raises
        ``ClearinghouseError`` until the real endpoint is confirmed.
        For claim *history/status*, use ``check_claim_status()``.

        Args:
            claim_data: Claim data dictionary.

        Returns:
            Submission acknowledgment result.

        Raises:
            ClearinghouseError: Always — endpoint not yet confirmed.
        """
        raise ClearinghouseError(
            "Waystar claim submission endpoint not yet configured. "
            "Use check_claim_status() for claim history queries."
        )

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Query claim history via Waystar Claim History API.

        Uses HMAC-SHA256 signed query string for authentication.

        Args:
            claim_ref: Claim number or date of service to look up.
                Interpreted as a claim number by default. Pass a date
                string (``YYYY-MM-DD``) and set ``req_type="DOS"`` in
                the dict overload to search by date of service.

        Returns:
            Claim status response with raw data.
        """
        params = self._build_claim_history_params(claim_ref)
        signed_url = self._sign_claim_history_url(params)
        response = self._get_with_retry(signed_url)
        self._handle_response(response)
        return self._parse_claim_history_response(response)

    def check_claim_status_by_params(
        self,
        *,
        cust_id: str = "",
        dos: str = "",
        claim_num: str = "",
        req_type: str = "",
    ) -> ClaimStatusResponse:
        """Query claim history with explicit parameters.

        Args:
            cust_id: Customer ID override (defaults to ``self._cust_id``).
            dos: Date of service (``YYYY-MM-DD`` or ``MM/DD/YYYY``).
            claim_num: Claim number to look up.
            req_type: Request type filter.

        Returns:
            Claim status response.
        """
        params: dict[str, str] = {
            "CustID": cust_id or self._cust_id,
        }
        if dos:
            params["DOS"] = dos
        if claim_num:
            params["ClaimNum"] = claim_num
        if req_type:
            params["ReqType"] = req_type

        signed_url = self._sign_claim_history_url(params)
        response = self._get_with_retry(signed_url)
        self._handle_response(response)
        return self._parse_claim_history_response(response)

    def check_prior_auth_status(
        self,
        payload: str | dict[str, Any],
        payload_type: str = "1952",
    ) -> dict[str, Any]:
        """Check prior authorization status via Waystar PA API.

        Args:
            payload: 278 EDI string or JSON dict for the PA request.
            payload_type: Waystar payload type (default ``"1952"`` for
                authorization status).

        Returns:
            Raw response dict from the PA API.
        """
        url = f"{self._prior_auth_base_url}{PRIOR_AUTH_SUBMIT_PATH}"
        json_body = self._build_prior_auth_body(payload, payload_type)
        response = self._post_json_with_retry(url, json_body)
        self._handle_response(response)
        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return {"raw_text": response.text}

    # ── Field mapping / request builders ───────────────────────────────

    def _build_eligibility_form(
        self, request: dict[str, Any]
    ) -> dict[str, str]:
        """Build POST form data for the eligibility endpoint."""
        data_format = request.get("data_format", "SF1")
        response_type = request.get("response_type", "FullJSON")

        form: dict[str, str] = {
            "UserID": self._user_id,
            "Password": self._password,
            "CustID": self._cust_id,
            "DataFormat": data_format,
            "ResponseType": response_type,
        }

        # If raw X12 data is provided, use it directly
        if "x12_data" in request:
            form["DataFormat"] = "X12"
            form["Data"] = request["x12_data"]
        elif data_format.upper() == "X12" and "data" in request:
            form["Data"] = request["data"]
        else:
            # Build simplified request data from dict fields
            form["Data"] = self._build_sf1_data(request)

        return form

    @staticmethod
    def _build_sf1_data(request: dict[str, Any]) -> str:
        """Build SF1 simplified eligibility data from dict fields.

        SF1 format uses pipe-delimited fields. This builds a minimal
        request that can be adjusted once exact SF1 spec is confirmed.
        """
        parts = [
            request.get("payer_id", ""),
            request.get("npi", ""),
            request.get("subscriber_id", ""),
            request.get("first_name", ""),
            request.get("last_name", ""),
            request.get("dob", ""),
            request.get("service_type", ""),
        ]
        return "|".join(parts)

    def _build_claim_history_params(
        self, claim_ref: str
    ) -> dict[str, str]:
        """Build query params for Claim History GET request."""
        return {
            "CustID": self._cust_id,
            "ClaimNum": claim_ref,
        }

    def _sign_claim_history_url(
        self, params: dict[str, str]
    ) -> str:
        """Build a signed URL for the Claim History endpoint.

        Adds Version, TimeStamp, and HMAC-SHA256 Signature to params.
        The signature is computed over the full query string (excluding
        the Signature param itself), case-sensitive.
        """
        params["Version"] = "2"
        params["TimeStamp"] = _utc_timestamp()

        # Build query string to sign (all params except Signature).
        # The HMAC is computed over the raw (unencoded) query string
        # per Waystar docs — case-sensitive.
        query_parts = [f"{k}={v}" for k, v in params.items()]
        query_string = "&".join(query_parts)

        # HMAC-SHA256 sign the query string
        signature = hmac_mod.new(
            self._secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["Signature"] = signature
        # URL-encode the final query string (spaces → %20, etc.)
        encoded_query = urlencode(params)
        return (
            f"{self._claims_base_url}{CLAIM_HISTORY_PATH}?{encoded_query}"
        )

    def _build_prior_auth_body(
        self,
        payload: str | dict[str, Any],
        payload_type: str,
    ) -> dict[str, Any]:
        """Build JSON body for Prior Auth API."""
        body: dict[str, Any] = {
            "Username": self._user_id,
            "Password": self._password,
            "CustID": self._cust_id,
            "PayloadType": payload_type,
        }
        if isinstance(payload, str):
            body["Payload"] = payload
        else:
            body["Payload"] = payload
        return body

    # ── Response parsing ───────────────────────────────────────────────

    def _parse_eligibility_response(
        self, response: httpx.Response
    ) -> ClearinghouseEligibilityResponse:
        """Parse eligibility response (JSON or raw text)."""
        try:
            data = response.json()
        except Exception:
            # Non-JSON response (HTML/TEXT/271)
            return ClearinghouseEligibilityResponse(
                status="received",
                eligible=None,
                raw_response={"raw_text": response.text},
            )

        if isinstance(data, dict):
            return self._parse_eligibility_json(data)

        # List or other JSON structure
        return ClearinghouseEligibilityResponse(
            status="received",
            eligible=None,
            raw_response={"data": data},
        )

    @staticmethod
    def _parse_eligibility_json(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse JSON eligibility response to library model.

        Handles Waystar's response format:
          - ``RawOutput``: raw X12 271 EDI string
          - ``ParsedOutput``: structured JSON with subscriber/patient/coverage
          - ``WaystarAlerts``: list of alert messages
          - ``InquiryId``: inquiry tracking ID
        """
        # Waystar-specific format
        parsed = data.get("ParsedOutput", {})
        alerts = data.get("WaystarAlerts", [])

        # Determine status from FileStatus or general status fields
        file_status = parsed.get("FileStatus")
        if file_status is not None:
            # Waystar FileStatus: 0=unknown, 1=success, 3=failure
            if file_status == 1:
                status = "active"
            elif file_status == 3:
                status = parsed.get("FailReason", "failed")
            else:
                status = "unknown"
        else:
            status = data.get("status", data.get("Status", "unknown"))

        # Determine eligibility
        eligible: bool | None = None
        if isinstance(status, str):
            lower = status.lower()
            if lower in ("active", "eligible", "1"):
                eligible = True
            elif lower in ("inactive", "ineligible", "6", "failed"):
                eligible = False

        # Extract plan info from ParsedOutput or generic keys
        plan_info: dict[str, Any] = {}
        if parsed:
            plan_info = parsed
        else:
            for key in (
                "planInfo", "PlanInfo", "benefitsInformation", "Benefits",
            ):
                if key in data:
                    val = data[key]
                    plan_info = (
                        val if isinstance(val, dict) else {"data": val}
                    )
                    break

        # Collect errors from WaystarAlerts or generic error fields
        errors: list[str] = [str(a) for a in alerts] if alerts else []
        if not errors:
            for key in ("errors", "Errors", "ErrorMessage"):
                if key in data and data[key]:
                    val = data[key]
                    if isinstance(val, list):
                        errors = [str(e) for e in val]
                    elif isinstance(val, str):
                        errors = [val]
                    break

        return ClearinghouseEligibilityResponse(
            status=str(status),
            eligible=eligible,
            reference_id=str(data.get("InquiryId", ""))
            if data.get("InquiryId")
            else data.get("referenceId", data.get("ReferenceId")),
            plan_info=plan_info,
            raw_response=data,
            errors=errors,
        )

    def _parse_claim_history_response(
        self, response: httpx.Response
    ) -> ClaimStatusResponse:
        """Parse Claim History response (may be XML, HTML, or JSON)."""
        content_type = response.headers.get("content-type", "")
        raw_text = response.text

        # Try JSON first
        try:
            data = response.json()
            if isinstance(data, dict):
                return ClaimStatusResponse(
                    status=data.get("status", data.get("Status", "received")),
                    claim_status=data.get(
                        "claimStatus", data.get("ClaimStatus")
                    ),
                    adjudication_date=data.get(
                        "adjudicationDate", data.get("AdjudicationDate")
                    ),
                    reference_id=data.get(
                        "referenceId", data.get("ReferenceId")
                    ),
                    raw_response=data,
                )
        except Exception:
            pass

        # XML/HTML response — return as raw_response for caller to parse
        return ClaimStatusResponse(
            status="received",
            raw_response={"raw_text": raw_text, "content_type": content_type},
        )

    # ── HTTP helpers ───────────────────────────────────────────────────

    def _handle_response(self, response: httpx.Response) -> None:
        """Map HTTP error codes to clearinghouse exceptions."""
        if 200 <= response.status_code < 300:
            return

        try:
            body = response.json()
            if isinstance(body, dict):
                error_msg = body.get(
                    "message",
                    body.get("Message", body.get("ErrorMessage", "")),
                )
            else:
                error_msg = ""
            if not error_msg:
                error_msg = f"HTTP {response.status_code}"
        except Exception:
            error_msg = f"HTTP {response.status_code}"

        if response.status_code in (401, 403):
            raise ClearinghouseAuthError(error_msg)
        if response.status_code == 422:
            raise ClearinghouseValidationError(error_msg)
        if response.status_code >= 500:
            raise ClearinghouseServerError(error_msg)
        raise ClearinghouseError(error_msg)

    def _post_form_with_retry(
        self, url: str, data: dict[str, str]
    ) -> httpx.Response:
        """POST form-encoded data with one retry on 5xx."""
        try:
            response = self._client.post(url, data=data)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.post(url, data=data)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Waystar eligibility request timed out: {url}"
            ) from exc

    def _post_json_with_retry(
        self, url: str, json_body: dict[str, Any]
    ) -> httpx.Response:
        """POST JSON data with one retry on 5xx."""
        try:
            response = self._client.post(url, json=json_body)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.post(url, json=json_body)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Waystar request timed out: {url}"
            ) from exc

    def _get_with_retry(self, url: str) -> httpx.Response:
        """GET with one retry on 5xx."""
        try:
            response = self._client.get(url)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.get(url)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Waystar claim history request timed out: {url}"
            ) from exc
