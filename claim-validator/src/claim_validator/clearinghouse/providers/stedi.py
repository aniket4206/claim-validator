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
from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
    BatchItemStatus,
)

DEFAULT_BASE_URL = "https://healthcare.us.stedi.com/2024-04-01"

_ELIGIBILITY_PATH = "/change/medicalnetwork/eligibility/v3"
_PROFESSIONAL_CLAIMS_PATH = (
    "/change/medicalnetwork/professionalclaims/v3/submission"
)
_CLAIM_STATUS_PATH = "/change/medicalnetwork/claimstatus/v2"

DEFAULT_MANAGER_BASE_URL = "https://manager.us.stedi.com/2024-04-01"
_BATCH_ELIGIBILITY_PATH = "/eligibility-manager/batch-eligibility"
_BATCH_STATUS_PATH = "/eligibility-manager/batch/{batch_id}"
_BATCH_ITEMS_PATH = "/eligibility-manager/batch/{batch_id}/items"


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
        self._manager_client = httpx.Client(
            base_url=DEFAULT_MANAGER_BASE_URL,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        """Close both HTTP clients."""
        self._client.close()
        self._manager_client.close()

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

    def submit_eligibility_batch(
        self, request: BatchEligibilityRequest
    ) -> BatchEligibilityResponse:
        """Submit a batch of eligibility checks.

        Uses the Stedi Manager API which processes checks asynchronously.
        Poll with ``get_batch_eligibility_status()`` to track progress.

        Args:
            request: Batch eligibility request with named items.

        Returns:
            Batch response with batch_id for status polling.
        """
        payload = self._to_stedi_batch(request)
        try:
            response = self._manager_client.post(
                _BATCH_ELIGIBILITY_PATH, json=payload
            )
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Stedi batch request timed out: {_BATCH_ELIGIBILITY_PATH}"
            ) from exc
        self._handle_response(response)
        data = response.json()
        return self._parse_batch_response(data)

    def get_batch_eligibility_status(
        self, batch_id: str
    ) -> BatchEligibilityResponse:
        """Poll batch eligibility status.

        Args:
            batch_id: Batch identifier from ``submit_eligibility_batch()``.

        Returns:
            Batch status with progress counts.
        """
        path = _BATCH_STATUS_PATH.format(batch_id=batch_id)
        try:
            response = self._manager_client.get(path)
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Stedi batch status timed out: {path}"
            ) from exc
        self._handle_response(response)
        data = response.json()
        return BatchEligibilityResponse(
            batch_id=data.get("batchId", batch_id),
            status=data.get("status", "unknown"),
            total_items=data.get("totalChecks", 0),
            completed_items=data.get("completedChecks", 0),
            raw_response=data,
        )

    def get_batch_eligibility_results(
        self, batch_id: str
    ) -> list[BatchItemStatus]:
        """Retrieve individual eligibility results from a completed batch.

        Args:
            batch_id: Batch identifier from ``submit_eligibility_batch()``.

        Returns:
            List of per-item eligibility results.
        """
        path = _BATCH_ITEMS_PATH.format(batch_id=batch_id)
        try:
            response = self._manager_client.get(path)
        except httpx.TimeoutException as exc:
            raise ClearinghouseTimeoutError(
                f"Stedi batch results timed out: {path}"
            ) from exc
        self._handle_response(response)
        data = response.json()
        return self._parse_batch_items(data.get("items", []))

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
        if "billing_employer_id" in claim_data:
            billing["employerId"] = claim_data["billing_employer_id"]
        if "billing_ssn" in claim_data:
            billing["ssn"] = claim_data["billing_ssn"]
        if "billing_organization_name" in claim_data:
            billing["organizationName"] = claim_data["billing_organization_name"]
        if "billing_first_name" in claim_data:
            billing["firstName"] = claim_data["billing_first_name"]
        if "billing_last_name" in claim_data:
            billing["lastName"] = claim_data["billing_last_name"]
        if "billing_address" in claim_data:
            billing["address"] = claim_data["billing_address"]
        if "billing_contact_phone" in claim_data:
            contact: dict[str, str] = {
                "phoneNumber": claim_data["billing_contact_phone"]
            }
            if "billing_contact_fax" in claim_data:
                contact["faxNumber"] = claim_data["billing_contact_fax"]
            if "billing_contact_email" in claim_data:
                contact["email"] = claim_data["billing_contact_email"]
            billing["contactInformation"] = [contact]

        claim_info: dict[str, Any] = {}
        if "total_charge" in claim_data:
            claim_info["claimChargeAmount"] = str(claim_data["total_charge"])
        if "place_of_service" in claim_data:
            claim_info["placeOfServiceCode"] = claim_data["place_of_service"]
        if "diagnosis_codes" in claim_data:
            codes = claim_data["diagnosis_codes"]
            claim_info["healthCareCodeInformation"] = [
                {
                    "diagnosisTypeCode": "ABK" if i == 0 else "ABF",
                    "diagnosisCode": code,
                }
                for i, code in enumerate(codes)
            ]
        if "lines" in claim_data:
            service_lines = []
            for line in claim_data["lines"]:
                prof_service: dict[str, Any] = {
                    "procedureCode": line.get("cpt_code", ""),
                    "procedureIdentifier": "HC",
                    "lineItemChargeAmount": str(line.get("charge", "")),
                    "measurementUnit": "UN",
                    "serviceUnitCount": str(line.get("units", "1")),
                }
                if "modifiers" in line:
                    prof_service["procedureModifiers"] = line["modifiers"]
                if "diagnosis_pointers" in line:
                    prof_service["compositeDiagnosisCodePointers"] = {
                        "diagnosisCodePointers": line["diagnosis_pointers"]
                    }
                svc_line: dict[str, Any] = {
                    "professionalService": prof_service,
                }
                if "service_date" in line:
                    svc_line["serviceDate"] = _strip_dashes(
                        line["service_date"]
                    )
                service_lines.append(svc_line)
            claim_info["serviceLines"] = service_lines

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

    @staticmethod
    def _to_stedi_batch_item(item: BatchEligibilityItem) -> dict[str, Any]:
        """Translate a single batch item to Stedi JSON format."""
        subscriber: dict[str, Any] = {
            "memberId": item.subscriber_id,
            "firstName": item.first_name,
            "lastName": item.last_name,
            "dateOfBirth": item.dob,
        }
        if item.gender:
            subscriber["gender"] = item.gender

        provider: dict[str, Any] = {"npi": item.npi}
        if item.organization_name:
            provider["organizationName"] = item.organization_name

        stedi_item: dict[str, Any] = {
            "tradingPartnerServiceId": item.payer_id,
            "provider": provider,
            "subscriber": subscriber,
        }

        if item.service_types:
            stedi_item["encounter"] = {"serviceTypeCodes": item.service_types}
        if item.date_of_service:
            stedi_item.setdefault("encounter", {})["dateOfService"] = (
                _strip_dashes(item.date_of_service)
            )
        if item.submitter_transaction_id:
            stedi_item["submitterTransactionIdentifier"] = (
                item.submitter_transaction_id
            )
        if item.external_patient_id:
            stedi_item["externalPatientId"] = item.external_patient_id

        return stedi_item

    @staticmethod
    def _to_stedi_batch(request: BatchEligibilityRequest) -> dict[str, Any]:
        """Translate batch request to Stedi batch JSON format."""
        return {
            "name": request.name,
            "items": [
                StediClient._to_stedi_batch_item(item)
                for item in request.items
            ],
        }

    # -- Response parsing helpers --------------------------------------------

    @staticmethod
    def _parse_eligibility_response(
        data: dict[str, Any],
    ) -> ClearinghouseEligibilityResponse:
        """Parse Stedi eligibility response to library model."""
        # Stedi uses "statusCode" in newer responses, "status" in legacy
        status = data.get("statusCode") or data.get("status") or "unknown"

        # Determine eligibility from status or planStatus
        eligible: bool | None = None
        plan_status = data.get("planStatus")
        if plan_status:
            # planStatus can be a list of objects or a string
            if isinstance(plan_status, list):
                has_active = any(
                    ps.get("status", "").lower() in ("active coverage",)
                    or ps.get("statusCode") == "1"
                    for ps in plan_status
                )
                has_inactive = any(
                    ps.get("status", "").lower() in ("inactive",)
                    or ps.get("statusCode") == "6"
                    for ps in plan_status
                )
                eligible = has_active and not has_inactive
            elif isinstance(plan_status, str):
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

    @staticmethod
    def _parse_batch_response(data: dict[str, Any]) -> BatchEligibilityResponse:
        """Parse Stedi batch eligibility response."""
        return BatchEligibilityResponse(
            batch_id=data.get("batchId", ""),
            status=data.get("status", "unknown"),
            total_items=data.get("totalChecks", 0),
            raw_response=data,
        )

    @staticmethod
    def _parse_batch_items(items: list[dict[str, Any]]) -> list[BatchItemStatus]:
        """Parse batch item results from Stedi response."""
        results: list[BatchItemStatus] = []
        for item in items:
            errors: list[str] = [
                err.get("message", str(err))
                for err in item.get("errors", [])
            ]
            results.append(
                BatchItemStatus(
                    submitter_transaction_id=item.get(
                        "submitterTransactionIdentifier", ""
                    ),
                    status=item.get("status", "unknown"),
                    eligibility_response=item.get("eligibilityCheck"),
                    errors=errors,
                )
            )
        return results

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
