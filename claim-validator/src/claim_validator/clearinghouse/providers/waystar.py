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

        Uses the Waystar claims submission endpoint with JSON body
        and UserID/Password authentication (same pattern as prior auth).

        Args:
            claim_data: Claim data dictionary (ClaimData-compatible fields).

        Returns:
            SubmissionResult with acceptance status and reference ID.
        """
        url = f"{self._claims_base_url}/2.0/v1/Claims/Submit"
        json_body: dict[str, Any] = {
            "UserID": self._user_id,
            "Password": self._password,
            "CustID": self._cust_id,
            "ClaimData": claim_data,
        }
        response = self._post_json_with_retry(url, json_body)
        self._handle_response(response)
        return self._parse_submission_response(response)

    def _parse_submission_response(self, response: httpx.Response) -> SubmissionResult:
        """Parse Waystar claim submission response."""
        try:
            data = response.json()
        except Exception:
            return SubmissionResult(
                status="unknown",
                accepted=False,
                raw_response={"raw_text": response.text},
                errors=["Could not parse submission response"],
            )

        status = data.get("Status", data.get("status", "unknown"))
        accepted = str(status).lower() in ("accepted", "received", "queued")
        ref_id = data.get("ReferenceId", data.get("referenceId"))
        error_msg = data.get("ErrorMessage", data.get("errorMessage", ""))
        errors = [error_msg] if error_msg else []

        return SubmissionResult(
            status=str(status),
            accepted=accepted,
            reference_id=str(ref_id) if ref_id else None,
            raw_response=data,
            errors=errors,
        )

    def check_claim_status(
        self,
        claim_ref: str,
        *,
        dos: str = "",
        response_type: str = "XML",
    ) -> ClaimStatusResponse:
        """Query claim history via Waystar Claim History API (v2.0).

        Uses HMAC-SHA256 signed query string for authentication.
        The API requires ``DOS`` (date of service) and ``ClaimNum``.

        Args:
            claim_ref: Patient control number (claim number).
            dos: Date of service in ``MM/DD/YYYY`` format. **Required**
                by the Waystar v2.0 API.
            response_type: ``"XML"`` or ``"HTML"`` (default ``"XML"``).
                Included in the GET request but **excluded** from the
                HMAC signature calculation per Waystar docs.

        Returns:
            Claim status response with raw data.
        """
        params = self._build_claim_history_params(claim_ref, dos=dos)
        signed_url = self._sign_claim_history_url(
            params, response_type=response_type
        )
        response = self._get_with_retry(signed_url)
        self._handle_response(response)
        return self._parse_claim_history_response(response)

    def check_claim_status_by_params(
        self,
        *,
        cust_id: str = "",
        dos: str = "",
        claim_num: str = "",
        response_type: str = "XML",
    ) -> ClaimStatusResponse:
        """Query claim history with explicit parameters.

        Args:
            cust_id: Customer ID override (defaults to ``self._cust_id``).
            dos: Date of service (``MM/DD/YYYY``). **Required** by v2.0.
            claim_num: Claim number to look up.
            response_type: ``"XML"`` or ``"HTML"`` (default ``"XML"``).

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
        params["ReqType"] = "CLMHIST"

        signed_url = self._sign_claim_history_url(
            params, response_type=response_type
        )
        response = self._get_with_retry(signed_url)
        self._handle_response(response)
        return self._parse_claim_history_response(response)

    def check_prior_auth_status(
        self,
        payload: str | dict[str, Any],
        payload_type: str = "1952",
    ) -> dict[str, Any]:
        """Submit a prior authorization status inquiry (step 1 of 2).

        This is an **asynchronous** API. The initial POST returns a
        ``ReferenceId`` and ``StatusMessage: "Received"``. Use
        ``get_prior_auth_result(reference_id)`` to poll for the final
        278 response.

        Args:
            payload: 278x215 EDI string **or** a dict of fields that
                will be converted to a 278 EDI transaction.
            payload_type: Waystar payload type (default ``"1952"`` for
                authorization status).

        Returns:
            Initial acknowledgment dict with ``ReferenceId``,
            ``StatusMessage``, ``ErrorMessage``, and ``PayloadType``.
        """
        url = f"{self._prior_auth_base_url}{PRIOR_AUTH_SUBMIT_PATH}"
        json_body = self._build_prior_auth_body(payload, payload_type)
        response = self._post_json_with_retry(url, json_body)
        self._handle_response(response)
        try:
            return response.json()  # type: ignore[no-any-return]
        except Exception:
            return {"raw_text": response.text}

    def get_prior_auth_result(
        self, reference_id: int | str
    ) -> dict[str, Any]:
        """Retrieve prior authorization result (step 2 of 2).

        After submitting via ``check_prior_auth_status()``, poll this
        method with the returned ``ReferenceId`` to get the final
        278x215 response.

        Possible ``StatusMessage`` values:
          - ``"Received"`` / ``"Waiting Response"`` — still processing
          - ``"Certified – in Total"`` — authorization found
          - ``"Not Found"`` — no authorization record
          - ``"Failed at Waystar"`` — validation failure

        Args:
            reference_id: The ``ReferenceId`` from the initial POST.

        Returns:
            Response dict with ``ReferenceId``, ``StatusMessage``,
            ``ErrorMessage``, ``Payload`` (278 EDI), ``PayloadType``.
        """
        url = f"{self._prior_auth_base_url}{PRIOR_AUTH_STATUS_PATH}"
        json_body: dict[str, Any] = {
            "Username": self._user_id,
            "Password": self._password,
            "CustID": self._cust_id,
            "ReferenceID": int(reference_id),
        }
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
        response_type = request.get("response_type", "FullJSON")

        form: dict[str, str] = {
            "UserID": self._user_id,
            "Password": self._password,
            "CustID": self._cust_id,
            "ResponseType": response_type,
        }

        # If raw X12 data is provided, use it directly
        if "x12_data" in request:
            form["DataFormat"] = "X12"
            form["Data"] = request["x12_data"]
        else:
            # Build X12 270 transaction from dict fields
            form["DataFormat"] = "X12"
            form["Data"] = self._build_x12_270(request)

        return form

    @staticmethod
    def _build_x12_270(request: dict[str, Any]) -> str:
        """Build an X12 270 eligibility inquiry from dict fields.

        Generates a minimal but valid ANSI X12 270 transaction that
        Waystar can process reliably (unlike the SF1 simplified format
        which has carrier-mapping issues).
        """
        now = datetime.now(UTC)
        date6 = now.strftime("%y%m%d")
        date8 = now.strftime("%Y%m%d")
        time4 = now.strftime("%H%M")

        npi = request.get("npi", "")
        payer_id = request.get("payer_id", "")
        subscriber_id = request.get("subscriber_id", "")
        first_name = request.get("first_name", "").upper()
        last_name = request.get("last_name", "").upper()

        # Support multiple service types via list or comma-separated string
        raw_st = request.get("service_types", request.get("service_type", "30"))
        if isinstance(raw_st, str):
            svc_types = [s.strip() for s in raw_st.split(",")]
        else:
            svc_types = list(raw_st)

        # Normalise DOB to YYYYMMDD
        dob_raw = request.get("dob", "")
        dob = dob_raw.replace("-", "")

        # Pad ISA fields to required widths
        sender_id = f"{npi:<15}" if npi else "SENDER         "

        segments = [
            f"ISA*00*          *00*          "
            f"*ZZ*{sender_id}*ZZ*ZIRMED         "
            f"*{date6}*{time4}*^*00501*000000001*0*P*:",
            f"GS*HS*SENDER*ZIRMED*{date8}*{time4}"
            f"*1*X*005010X279A1",
            f"ST*270*0001*005010X279A1",
            f"BHT*0022*13*REQ001*{date8}*{time4}",
            "HL*1**20*1",
            f"NM1*PR*2*{payer_id}*****PI*{payer_id}",
            "HL*2*1*21*1",
            f"NM1*1P*2******XX*{npi}",
            "HL*3*2*22*0",
            "TRN*1*REQ001*9SENDER",
            f"NM1*IL*1*{last_name}*{first_name}****MI*{subscriber_id}",
            f"DMG*D8*{dob}",
            f"DTP*291*D8*{date8}",
        ]
        for st in svc_types:
            segments.append(f"EQ*{st}")

        # SE count: ST through SE inclusive (exclude ISA/GS envelope)
        se_count = len(segments) - 2 + 1  # -2 for ISA/GS, +1 for SE itself
        segments.extend([
            f"SE*{se_count}*0001",
            "GE*1*1",
            "IEA*1*000000001",
            "",
        ])
        return "~".join(segments)

    def _build_claim_history_params(
        self, claim_ref: str, *, dos: str = ""
    ) -> dict[str, str]:
        """Build query params for Claim History GET request (v2.0).

        Per Waystar docs the new URI requires CustID, DOS, ClaimNum,
        and ReqType=CLMHIST.  Version and TimeStamp are added by the
        signing method.
        """
        params: dict[str, str] = {
            "CustID": self._cust_id,
        }
        if dos:
            params["DOS"] = dos
        params["ClaimNum"] = claim_ref
        params["ReqType"] = "CLMHIST"
        return params

    def _sign_claim_history_url(
        self,
        params: dict[str, str],
        *,
        response_type: str = "XML",
    ) -> str:
        """Build a signed URL for the Claim History endpoint (v2.0).

        Adds Version, TimeStamp, and HMAC-SHA256 Signature to params.
        Per Waystar docs:
          - ``ResponseType`` must be **excluded** from the signature
            calculation but **included** in the final GET request.
          - The query string is case-sensitive for both signature
            calculation and the final request.
          - The request must be sent within 5 minutes of the TimeStamp.
        """
        params["Version"] = "2.0"
        params["TimeStamp"] = _utc_timestamp()

        # Build query string to sign (all params except Signature and
        # ResponseType — per Waystar docs ResponseType is excluded from
        # signature but required in the final GET).
        query_parts = [f"{k}={v}" for k, v in params.items()]
        query_string = "&".join(query_parts)

        # HMAC-SHA256 sign the query string
        signature = hmac_mod.new(
            self._secret.encode(),
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        params["Signature"] = signature
        # Add ResponseType AFTER signing (excluded from signature)
        params["ResponseType"] = response_type
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
        """Build JSON body for Prior Auth API.

        If *payload* is a string it is assumed to be a raw 278 EDI
        transaction and sent as-is.  If it is a dict, a minimal X12 278
        inquiry is generated from its fields.

        Per Waystar docs, ``CustID`` is Integer and ``PayloadType`` is
        Integer.  ``Relationship`` is an optional alphanumeric field.
        """
        body: dict[str, Any] = {
            "Username": self._user_id,
            "Password": self._password,
            "CustID": int(self._cust_id) if self._cust_id.isdigit() else self._cust_id,
            "Relationship": "",
            "PayloadType": int(payload_type),
        }
        if isinstance(payload, str):
            body["Payload"] = payload
        else:
            body["Payload"] = self._build_x12_278(payload)
        return body

    @staticmethod
    def _build_x12_278(request: dict[str, Any]) -> str:
        """Build a minimal X12 278 authorization status inquiry.

        Waystar's PA Status API (PayloadType 1952) accepts a 278 with
        **only 3 HL levels**: payer (20), provider (21), subscriber (22).
        No UM/HI/SV1/DTP service-detail segments — Waystar looks up
        existing authorizations by subscriber identification.

        Adding HL level 4 or service segments causes "Invalid Payload".
        """
        now = datetime.now(UTC)
        date6 = now.strftime("%y%m%d")
        date8 = now.strftime("%Y%m%d")
        time4 = now.strftime("%H%M")

        npi = request.get("npi", "")
        payer_id = request.get("payer_id", "")
        subscriber_id = request.get("subscriber_id", "")
        first_name = request.get("first_name", "").upper()
        last_name = request.get("last_name", "").upper()
        dob_raw = request.get("dob", "")
        dob = dob_raw.replace("-", "")

        sender_id = f"{npi:<15}" if npi else "SENDER         "

        segments = [
            f"ISA*00*          *00*          "
            f"*ZZ*{sender_id}*ZZ*ZIRMED         "
            f"*{date6}*{time4}*^*00501*000000001*0*P*:",
            f"GS*HI*{npi or 'SENDER'}*ZIRMED*{date8}*{time4}"
            f"*1*X*005010X215",
            "ST*278*0001*005010X215",
            f"BHT*0007*13*REQ001*{date8}*{time4}",
            "HL*1**20*1",
            f"NM1*PR*2*{payer_id}*****PI*{payer_id}",
            "HL*2*1*21*1",
            f"NM1*1P*2******XX*{npi}",
            "HL*3*2*22*0",
            f"TRN*1*REQ001*9{npi or 'SENDER'}",
            f"NM1*IL*1*{last_name}*{first_name}****MI*{subscriber_id}",
            f"DMG*D8*{dob}",
            # SE count: ST through SE inclusive = 11 segments
            "SE*11*0001",
            "GE*1*1",
            "IEA*1*000000001",
            "",
        ]
        return "~".join(segments)

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
