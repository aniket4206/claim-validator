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
    """Convert ``YYYY-MM-DD`` to ``YYYYMMDD`` for Claim.MD date format."""
    parts = date_str.split("-")
    if len(parts) == 3:
        return f"{parts[0]}{parts[1]}{parts[2]}"
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
        """Translate library eligibility dict to Claim.MD form data.

        Claim.MD eligibility API field names (per official API docs):
          AccountKey, payerid, prov_npi, prov_taxid, ins_name_f, ins_name_l,
          pat_dob (YYYYMMDD), fdos (YYYYMMDD), stype, pat_rel.
        """
        form: dict[str, str] = {
            "AccountKey": self._account_key,
        }
        if "payer_id" in request:
            form["payerid"] = request["payer_id"]
        if "npi" in request:
            form["prov_npi"] = request["npi"]
        if request.get("provider_tax_id"):
            form["prov_taxid"] = request["provider_tax_id"]
        if "subscriber_id" in request:
            form["ins_number"] = request["subscriber_id"]
        if "first_name" in request:
            form["ins_name_f"] = request["first_name"]
        if "last_name" in request:
            form["ins_name_l"] = request["last_name"]
        if "dob" in request:
            form["pat_dob"] = _to_claimmd_date(request["dob"])
        if request.get("service_type"):
            form["stype"] = request["service_type"]
        if "service_date" in request:
            form["fdos"] = _to_claimmd_date(request["service_date"])
        # Default patient relationship to Self (18)
        form["pat_rel"] = request.get("pat_rel", "18")
        return form

    def _to_claimmd_upload(
        self, claim_data: dict[str, Any]
    ) -> dict[str, str]:
        """Translate library claim dict to Claim.MD upload form data.

        Ensures ``prior_auth`` (CMS-1500 Box 23) is included at the
        claim level if provided in the input data.
        """
        form: dict[str, str] = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
        }
        # Ensure prior_auth is at claim root level for Claim.MD
        upload_data = dict(claim_data)
        pa_number = (
            claim_data.get("prior_auth")
            or claim_data.get("prior_auth_number")
            or claim_data.get("authorization_number")
        )
        if pa_number:
            upload_data["prior_auth"] = pa_number

        # Send claim data as JSON in the File parameter
        form["File"] = json.dumps(upload_data)
        return form

    # -- Response parsing helpers --------------------------------------------

    @staticmethod
    def _parse_eligibility_response(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse Claim.MD eligibility response to library model.

        ClaimMD XML eligibility responses use benefit_coverage_code="1" with
        benefit_coverage_description="Active Coverage" to indicate active
        enrollment.
        """
        eligible: bool | None = None
        status = "unknown"
        errors: list[str] = []

        benefits = data.get("benefits", [])
        if benefits:
            # Check for Active Coverage (benefit_coverage_code="1")
            for b in benefits:
                desc = b.get("benefit_coverage_description", "").lower()
                code = b.get("benefit_coverage_code", "")
                if code == "1" or "active" in desc:
                    eligible = True
                    status = "active"
                    break
                if "inactive" in desc:
                    eligible = False
                    status = "inactive"
                    break
            if status == "unknown" and benefits:
                status = "response_received"
        else:
            # Fallback for JSON or flat-parsed responses
            status = data.get("status", "unknown")
            if status.lower() in ("active", "a"):
                eligible = True
            elif status.lower() in ("inactive", "i"):
                eligible = False

        # Use the full data as plan_info for financial extraction
        plan_info = data

        return ClearinghouseEligibilityResponse(
            status=status,
            eligible=eligible,
            reference_id=data.get("eligid"),
            plan_info=plan_info,
            raw_response=data,
            errors=errors,
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

        Claim.MD may return XML or JSON. XML responses typically contain
        error information. JSON responses may have body-level error status.
        """
        if response.status_code in (401, 403):
            raise ClearinghouseAuthError("Invalid AccountKey")
        if response.status_code >= 500:
            raise ClearinghouseServerError(f"HTTP {response.status_code}")

        body = response.text.strip()

        # Claim.MD often returns XML even when JSON is requested
        if body.startswith("<"):
            return self._parse_xml_response(body)

        try:
            data: dict[str, Any] = response.json()
        except Exception:
            raise ClearinghouseError(
                f"Unexpected response from Claim.MD: {body[:500]}"
            ) from None

        if response.status_code >= 400:
            error_msg = data.get("message", f"HTTP {response.status_code}")
            raise ClearinghouseValidationError(error_msg)

        # Check body-level error status
        if data.get("status") == "error":
            error_msg = data.get("message", "Unknown error")
            raise ClearinghouseValidationError(error_msg)

        return data

    @staticmethod
    def _parse_xml_response(xml_text: str) -> dict[str, Any]:
        """Parse Claim.MD XML response into a structured dict.

        Handles both error responses and eligibility data responses.
        The eligibility XML has structure: <result><elig ...><benefit .../>...</elig></result>
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            raise ClearinghouseError(
                f"Invalid XML from Claim.MD: {xml_text[:500]}"
            ) from None

        # Check for error elements
        errors: list[str] = []
        for err in root.iter("error"):
            code = err.get("error_code", "")
            msg = err.get("error_mesg", "")
            errors.append(f"[{code}] {msg}" if code else msg)

        if errors:
            raise ClearinghouseValidationError("; ".join(errors))

        # Parse <elig> element with its attributes (patient/plan info)
        elig = root.find("elig")
        if elig is None:
            # Fallback: flat parse for non-eligibility responses
            result: dict[str, Any] = {}
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    result[elem.tag] = elem.text.strip()
                for k, v in elem.attrib.items():
                    result[f"{elem.tag}_{k}"] = v
            return result

        # Build structured result from <elig> attributes
        result = dict(elig.attrib)

        # Parse all <benefit> elements into a list
        benefits: list[dict[str, Any]] = []
        for ben in elig.findall("benefit"):
            benefit_dict = dict(ben.attrib)
            # Capture nested <entity> elements
            entities: list[dict[str, str]] = []
            for entity in ben.findall("entity"):
                entities.append(dict(entity.attrib))
            if entities:
                benefit_dict["entities"] = entities
            benefits.append(benefit_dict)

        result["benefits"] = benefits
        return result

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
