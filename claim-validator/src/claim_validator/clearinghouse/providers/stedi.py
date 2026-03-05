"""Stedi clearinghouse provider — JSON REST integration."""

from __future__ import annotations

import time
import uuid
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

DEFAULT_BASE_URL = "https://healthcare.us.stedi.com/2024-04-01"

_ELIGIBILITY_PATH = "/change/medicalnetwork/eligibility/v3"
_PROFESSIONAL_CLAIMS_PATH = (
    "/change/medicalnetwork/professionalclaims/v3/submission"
)
_CLAIM_STATUS_PATH = "/change/medicalnetwork/claimstatus/v2"


def _strip_dashes(date_str: str) -> str:
    """Convert ``YYYY-MM-DD`` to ``YYYYMMDD`` for Stedi date format."""
    return date_str.replace("-", "")


class StediClient(BaseClearinghouseClient):
    """Stedi clearinghouse client.

    Implements the ``BaseClearinghouseClient`` interface for the Stedi
    Healthcare API using their JSON REST endpoints.

    Args:
        api_key: Stedi API key for the ``Authorization`` header.
        base_url: Override the default Stedi base URL.
        timeout: HTTP request timeout in seconds.
        **kwargs: Passed to ``BaseClearinghouseClient``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key, base_url=base_url, timeout=timeout, **kwargs
        )
        # Replace the base httpx client with one that includes auth headers
        self._client.close()
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
        )

    @property
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        return "stedi"

    # -- Public API methods --------------------------------------------------

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility via Stedi (270/271).

        Args:
            request: Eligibility request with keys ``payer_id``, ``npi``,
                ``subscriber_id``, ``first_name``, ``last_name``, ``dob``,
                ``service_type``, etc.

        Returns:
            Normalized eligibility response.
        """
        payload = self._to_stedi_eligibility(request)
        response = self._post_with_retry(_ELIGIBILITY_PATH, payload)
        self._handle_response(response)
        data = response.json()
        return self._parse_eligibility_response(data)

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a professional claim (837P) to Stedi.

        Args:
            claim_data: Professional claim data dictionary.

        Returns:
            Submission acknowledgment result.
        """
        payload = self._to_stedi_claim(claim_data)
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        response = self._post_with_retry(
            _PROFESSIONAL_CLAIMS_PATH, payload, headers=headers
        )
        self._handle_response(response)
        data = response.json()
        return self._parse_submission_response(data)

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim status via Stedi (276/277).

        Args:
            claim_ref: Claim reference identifier.

        Returns:
            Claim status response.
        """
        payload = self._to_stedi_status_request(claim_ref)
        response = self._post_with_retry(_CLAIM_STATUS_PATH, payload)
        self._handle_response(response)
        data = response.json()
        return self._parse_status_response(data)

    # -- Field mapping helpers -----------------------------------------------

    @staticmethod
    def _to_stedi_eligibility(request: dict[str, Any]) -> dict[str, Any]:
        """Translate library eligibility dict to Stedi JSON format."""
        subscriber: dict[str, Any] = {
            "memberId": request.get("subscriber_id", ""),
        }
        if "first_name" in request:
            subscriber["firstName"] = request["first_name"]
        if "last_name" in request:
            subscriber["lastName"] = request["last_name"]
        if "dob" in request:
            subscriber["dateOfBirth"] = _strip_dashes(request["dob"])
        if "gender" in request:
            subscriber["gender"] = request["gender"]

        provider: dict[str, Any] = {"npi": request.get("npi", "")}
        if "organization_name" in request:
            provider["organizationName"] = request["organization_name"]
        if "provider_first_name" in request:
            provider["firstName"] = request["provider_first_name"]
        if "provider_last_name" in request:
            provider["lastName"] = request["provider_last_name"]
        if "tax_id" in request:
            provider["taxId"] = request["tax_id"]

        payload: dict[str, Any] = {
            "tradingPartnerServiceId": request.get("payer_id", ""),
            "provider": provider,
            "subscriber": subscriber,
        }

        # Encounter: service types + date of service
        encounter: dict[str, Any] = {}
        if "service_types" in request:
            stc = request["service_types"]
            encounter["serviceTypeCodes"] = stc if isinstance(stc, list) else [stc]
        elif "service_type" in request:
            encounter["serviceTypeCodes"] = [request["service_type"]]
        if "date_of_service" in request:
            encounter["dateOfService"] = _strip_dashes(
                request["date_of_service"]
            )
        if encounter:
            payload["encounter"] = encounter

        # Optional top-level fields
        if "external_patient_id" in request:
            payload["externalPatientId"] = request["external_patient_id"]
        if "submitter_transaction_id" in request:
            payload["submitterTransactionIdentifier"] = request[
                "submitter_transaction_id"
            ]
        if "trading_partner_name" in request:
            payload["tradingPartnerName"] = request["trading_partner_name"]

        # Dependent (max 1 per Stedi API)
        if (
            "dependent_first_name" in request
            or "dependent_last_name" in request
        ):
            dependent: dict[str, Any] = {}
            if "dependent_first_name" in request:
                dependent["firstName"] = request["dependent_first_name"]
            if "dependent_last_name" in request:
                dependent["lastName"] = request["dependent_last_name"]
            if "dependent_dob" in request:
                dependent["dateOfBirth"] = _strip_dashes(
                    request["dependent_dob"]
                )
            if "dependent_relationship" in request:
                dependent["individualRelationshipCode"] = request[
                    "dependent_relationship"
                ]
            payload["dependents"] = [dependent]

        return payload

    @staticmethod
    def _to_stedi_claim(claim_data: dict[str, Any]) -> dict[str, Any]:
        """Translate library claim dict to Stedi 837P JSON format."""
        billing: dict[str, Any] = {}
        if "billing_npi" in claim_data:
            billing["npi"] = claim_data["billing_npi"]
        if "taxonomy_code" in claim_data:
            billing["taxonomyCode"] = claim_data["taxonomy_code"]

        claim_info: dict[str, Any] = {}
        if "total_charge" in claim_data:
            claim_info["claimChargeAmount"] = str(claim_data["total_charge"])
        if "place_of_service" in claim_data:
            claim_info["placeOfServiceCode"] = claim_data["place_of_service"]
        if "diagnosis_codes" in claim_data:
            claim_info["healthCareCodeInformation"] = [
                {"diagnosisTypeCode": "ABK", "diagnosisCode": code}
                for code in claim_data["diagnosis_codes"]
            ]
        if "lines" in claim_data:
            claim_info["serviceLines"] = [
                {
                    "procedureCode": line.get("cpt_code", ""),
                    "chargeAmount": str(line.get("charge", "")),
                    "unitCount": str(line.get("units", "1")),
                }
                for line in claim_data["lines"]
            ]

        payload: dict[str, Any] = {
            "tradingPartnerServiceId": claim_data.get("payer_id", ""),
        }
        if billing:
            payload["billing"] = billing
        if "subscriber_id" in claim_data:
            payload["subscriber"] = {
                "memberId": claim_data["subscriber_id"],
            }
        if claim_info:
            payload["claimInformation"] = claim_info
        return payload

    @staticmethod
    def _to_stedi_status_request(claim_ref: str) -> dict[str, Any]:
        """Translate claim reference to Stedi status request JSON."""
        return {"claimReference": claim_ref}

    # -- Response parsing helpers --------------------------------------------

    @staticmethod
    def _parse_eligibility_response(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse Stedi eligibility response to library model."""
        # Stedi uses "statusCode" in newer responses, "status" in legacy
        status = data.get("statusCode") or data.get("status", "unknown")

        # Determine eligibility from status or planStatus
        eligible: bool | None = None
        plan_status = data.get("planStatus")
        if plan_status:
            eligible = plan_status.lower() in ("active", "active - full")
        elif status.lower() == "active":
            eligible = True
        elif status.lower() in ("inactive", "terminated"):
            eligible = False

        # Build plan_info from structured response fields
        plan_info: dict[str, Any] = {}
        if "planInformation" in data:
            plan_info["planInformation"] = data["planInformation"]
        if "planDateInformation" in data:
            plan_info["planDateInformation"] = data["planDateInformation"]
        if "benefitsInformation" in data:
            plan_info["benefitsInformation"] = data["benefitsInformation"]
        if "planStatus" in data:
            plan_info["planStatus"] = data["planStatus"]

        # Extract errors from AAA rejections
        errors: list[str] = []
        for err in data.get("errors", []):
            desc = err.get("description") or err.get("message", "")
            code = err.get("code", "")
            errors.append(f"{code}: {desc}" if code else desc)

        return ClearinghouseEligibilityResponse(
            status=status,
            eligible=eligible,
            reference_id=data.get("controlNumber"),
            plan_info=plan_info,
            raw_response=data,
            errors=errors,
        )

    @staticmethod
    def _parse_submission_response(data: dict[str, Any]) -> SubmissionResult:
        """Parse Stedi claim submission response to library model."""
        status = data.get("status", "unknown")
        accepted = status.lower() in ("accepted", "success")
        return SubmissionResult(
            status=status,
            accepted=accepted,
            reference_id=data.get("controlNumber"),
            raw_response=data,
            errors=data.get("errors", []),
        )

    @staticmethod
    def _parse_status_response(data: dict[str, Any]) -> ClaimStatusResponse:
        """Parse Stedi claim status response to library model."""
        return ClaimStatusResponse(
            status=data.get("status", "unknown"),
            claim_status=data.get("claimStatus"),
            adjudication_date=data.get("adjudicationDate"),
            reference_id=data.get("controlNumber"),
            raw_response=data,
        )

    # -- HTTP helpers --------------------------------------------------------

    def _handle_response(self, response: httpx.Response) -> None:
        """Map HTTP error codes to clearinghouse exceptions.

        Extracts error messages from response body without including PHI.
        """
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
        self,
        path: str,
        json: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """POST with one retry on 5xx and timeout wrapping."""
        try:
            response = self._client.post(path, json=json, headers=headers)
            if response.status_code >= 500:
                time.sleep(1)
                response = self._client.post(path, json=json, headers=headers)
            return response
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Stedi request timed out: {path}"
            ) from exc
