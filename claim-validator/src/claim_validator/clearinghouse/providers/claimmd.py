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
_PRIOR_AUTH_PATH = "/services/preauth/"


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

    def submit_prior_auth(
        self, request: dict[str, Any]
    ) -> SubmissionResult:
        """Submit a prior authorization request via Claim.MD (278).

        Args:
            request: Prior auth request with keys ``payer_id``, ``npi``,
                ``subscriber_id``, ``first_name``, ``last_name``, ``dob``,
                ``diagnosis_codes``, ``service_lines``, etc.

        Returns:
            Submission result with Claim.MD batch reference.
        """
        form_data = self._to_claimmd_prior_auth(request)
        response = self._post_form_with_retry(_PRIOR_AUTH_PATH, form_data)
        data = self._handle_response(response)
        return self._parse_prior_auth_response(data)

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
        """Translate library eligibility dict to Claim.MD eligdata form data.

        Uses ClaimMD's native field names: ``prov_npi``, ``prov_taxid``,
        ``payerid``, ``ins_number``, ``pat_name_f``, ``pat_name_l``,
        ``ins_dob``, ``fdos``.
        """
        form: dict[str, str] = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
        }
        if "payer_id" in request:
            form["payerid"] = request["payer_id"]
        if "npi" in request:
            form["prov_npi"] = request["npi"]
        if "tax_id" in request:
            form["prov_taxid"] = request["tax_id"]
        if "subscriber_id" in request:
            form["ins_number"] = request["subscriber_id"]
        if "first_name" in request:
            form["pat_name_f"] = request["first_name"]
        if "last_name" in request:
            form["pat_name_l"] = request["last_name"]
        if "dob" in request:
            form["ins_dob"] = _to_claimmd_date(request["dob"])
        if "service_date" in request:
            form["fdos"] = _to_claimmd_date(request["service_date"])
        return form

    def _to_claimmd_prior_auth(
        self, request: dict[str, Any]
    ) -> dict[str, str]:
        """Translate library PA request dict to Claim.MD form data."""
        form: dict[str, str] = {
            "AccountKey": self._account_key,
            "ResponseType": "json",
        }
        if "payer_id" in request:
            form["PayerID"] = request["payer_id"]
        if "npi" in request or "requester_npi" in request:
            form["ProviderNPI"] = request.get("npi") or request.get(
                "requester_npi", ""
            )
        if "tax_id" in request:
            form["ProviderTaxID"] = request["tax_id"]
        if "subscriber_id" in request:
            form["InsuredID"] = request["subscriber_id"]
        elif "subscriber" in request and isinstance(request["subscriber"], dict):
            form["InsuredID"] = request["subscriber"].get("member_id", "")
        if "first_name" in request:
            form["InsuredFirstName"] = request["first_name"]
        elif "subscriber" in request and isinstance(request["subscriber"], dict):
            form["InsuredFirstName"] = request["subscriber"].get(
                "first_name", ""
            )
        if "last_name" in request:
            form["InsuredLastName"] = request["last_name"]
        elif "subscriber" in request and isinstance(request["subscriber"], dict):
            form["InsuredLastName"] = request["subscriber"].get(
                "last_name", ""
            )
        if "dob" in request:
            form["InsuredDOB"] = _to_claimmd_date(request["dob"])
        elif "subscriber" in request and isinstance(request["subscriber"], dict):
            dob = request["subscriber"].get("dob", "")
            if dob:
                form["InsuredDOB"] = _to_claimmd_date(str(dob))
        # Diagnosis codes
        diag_codes = request.get("diagnosis_codes", [])
        for i, code in enumerate(diag_codes[:4], start=1):
            form[f"DiagnosisCode{i}"] = str(code)
        # Service lines
        service_lines = request.get("service_lines", [])
        for i, line in enumerate(service_lines[:6], start=1):
            if isinstance(line, dict):
                if "cpt_code" in line:
                    form[f"ProcedureCode{i}"] = line["cpt_code"]
                if "from_date" in line and line["from_date"]:
                    form[f"ServiceDate{i}"] = _to_claimmd_date(
                        str(line["from_date"])
                    )
                if "quantity" in line:
                    form[f"Quantity{i}"] = str(line["quantity"])
        return form

    @staticmethod
    def _parse_prior_auth_response(data: dict[str, Any]) -> SubmissionResult:
        """Parse Claim.MD prior auth response to library model."""
        status = data.get("status", "unknown")
        accepted = status.lower() in (
            "ok", "accepted", "success", "approved", "certified",
        )
        return SubmissionResult(
            status=status,
            accepted=accepted,
            reference_id=(
                data.get("authorizationNumber")
                or data.get("batchID")
                or data.get("responseID")
            ),
            raw_response=data,
            errors=data.get("errors", []),
        )

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

        Claim.MD may return XML error responses even when JSON is
        requested, so the parser handles both content types.
        """
        if response.status_code in (401, 403):
            raise ClearinghouseAuthError("Invalid AccountKey")
        if response.status_code >= 500:
            raise ClearinghouseServerError(f"HTTP {response.status_code}")

        content_type = response.headers.get("content-type", "")
        body_text = response.text

        # Claim.MD sometimes returns XML errors despite ResponseType=json
        if "xml" in content_type or body_text.lstrip().startswith("<"):
            data = self._parse_xml_response(body_text)
        else:
            try:
                data = response.json()
            except Exception:
                msg = f"HTTP {response.status_code}: unparseable response"
                raise ClearinghouseError(msg) from None

        if response.status_code >= 400:
            error_msg = data.get("message", f"HTTP {response.status_code}")
            raise ClearinghouseValidationError(error_msg)

        # Check body-level error status
        if data.get("status") == "error":
            error_msg = data.get("message", "Unknown error")
            raise ClearinghouseValidationError(error_msg)

        return data

    @staticmethod
    def _parse_xml_response(body: str) -> dict[str, Any]:
        """Parse Claim.MD XML response into a dict.

        Handles:
        - Error format: ``<result><error error_code="..." error_mesg="..." /></result>``
        - Eligibility format: ``<result><elig ... benefit_coverage_code="1" ...>``
        """
        import re

        # Check for errors first
        errors: list[str] = []
        for match in re.finditer(
            r'error_code="([^"]*)"[^>]*error_mesg="([^"]*)"', body,
        ):
            code, msg = match.group(1), match.group(2)
            errors.append(f"{code}: {msg}")

        if errors:
            return {
                "status": "error",
                "message": "; ".join(errors),
                "errors": errors,
                "raw_xml": body,
            }

        # Check for eligibility response
        elig_match = re.search(r"<elig\s+([^>]+)>", body)
        if elig_match:
            attrs: dict[str, str] = dict(
                re.findall(r'(\w+)="([^"]*)"', elig_match.group(1))
            )
            # Extract coverage status from benefit elements
            coverage_code = None
            for bmatch in re.finditer(
                r'benefit_coverage_code="([^"]*)"', body,
            ):
                coverage_code = bmatch.group(1)
                break  # first benefit is primary

            status = "active" if coverage_code == "1" else (
                "inactive" if coverage_code == "6" else attrs.get("status", "unknown")
            )
            return {
                "status": status,
                "responseID": attrs.get("eligid"),
                "plan": {
                    "group_number": attrs.get("group_number"),
                    "plan_number": attrs.get("plan_number"),
                    "plan_begin_date": attrs.get("plan_begin_date"),
                },
                "subscriber": {
                    "ins_number": attrs.get("ins_number"),
                    "ins_dob": attrs.get("ins_dob"),
                    "ins_sex": attrs.get("ins_sex"),
                },
                "raw_xml": body,
            }

        return {"status": "unknown", "raw_xml": body}

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
