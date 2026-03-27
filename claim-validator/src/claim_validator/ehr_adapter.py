"""EHR Adapter — connects to EHR systems and pulls appointment data.

ThinkAI connects TO the EHR (we pull, they don't push):
  1. Practice configures FHIR credentials on EHR Sync page
  2. Our agent polls their EHR on schedule (every 15min / hourly / daily)
  3. Pulls new/updated appointments
  4. Creates local appointment records
  5. Auto-runs eligibility + PA for each

Supported EHR connections:
  - FHIR R4 (Epic, Cerner, Athena, eClinicalWorks, AllScripts)
  - Custom REST API (for non-FHIR EHRs)
  - CSV import (manual fallback)

Each EHR has different:
  - Auth method (OAuth2, API key, SMART on FHIR)
  - FHIR resource structure
  - Patient/Coverage/Appointment field mapping
  - Rate limits and pagination
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, UTC
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base EHR Adapter (all EHRs implement this)
# ---------------------------------------------------------------------------

class BaseEHRAdapter(ABC):
    """Abstract base for all EHR connections."""

    def __init__(self, config: dict[str, str]) -> None:
        self.config = config
        self.ehr_name = "unknown"

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the EHR. Returns True if successful."""

    @abstractmethod
    def fetch_appointments(
        self, date_from: str, date_to: str
    ) -> list[dict[str, Any]]:
        """Pull appointments for a date range. Returns normalized appointment dicts."""

    @abstractmethod
    def fetch_patient_coverage(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """Pull insurance/coverage info for a patient."""

    def test_connection(self) -> dict[str, Any]:
        """Test the EHR connection. Returns status dict."""
        try:
            ok = self.authenticate()
            return {"status": "ok" if ok else "error", "ehr": self.ehr_name}
        except Exception as exc:
            return {"status": "error", "ehr": self.ehr_name, "message": str(exc)}


# ---------------------------------------------------------------------------
# FHIR R4 Adapter (Epic, Cerner, Athena, etc.)
# ---------------------------------------------------------------------------

class FHIRR4Adapter(BaseEHRAdapter):
    """Connect to any FHIR R4 EHR and pull appointments + coverage.

    Works with: Epic, Cerner, Athena, eClinicalWorks, AllScripts, etc.

    Auth flow (SMART Backend Services / Client Credentials):
      1. POST /oauth2/token with client_id + client_secret
      2. Get access_token
      3. Use token for all FHIR API calls

    Each EHR has slightly different:
      - Token endpoint URL
      - Scopes required
      - Resource field mappings
      - Pagination style
    """

    def __init__(self, config: dict[str, str]) -> None:
        super().__init__(config)
        self.ehr_name = config.get("ehr_name", "fhir")
        self.base_url = config.get("fhir_base_url", "").rstrip("/")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.tenant_id = config.get("tenant_id", "")
        self.scopes = config.get("scopes", "patient/*.read")
        self._token: str | None = None
        self._token_expires: float = 0
        self._client = httpx.Client(timeout=30)

    def authenticate(self) -> bool:
        """Get OAuth2 access token from the EHR."""
        if self._token and time.time() < self._token_expires:
            return True  # Token still valid

        # Common FHIR token endpoints
        token_url = self.config.get("token_url", "")
        if not token_url:
            # Auto-discover from .well-known or common patterns
            for path in ["/oauth2/token", "/auth/token", "/connect/token"]:
                token_url = f"{self.base_url}{path}"
                break

        print(f"  [FHIR] Authenticating with {self.ehr_name} at {token_url}")

        try:
            resp = self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scopes,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code == 200:
                data = resp.json()
                self._token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self._token_expires = time.time() + expires_in - 60
                print(f"  [FHIR] Authenticated successfully (expires in {expires_in}s)")
                return True
            else:
                print(f"  [FHIR] Auth failed: {resp.status_code} {resp.text[:200]}")
                return False

        except Exception as exc:
            print(f"  [FHIR] Auth error: {exc}")
            return False

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/fhir+json",
        }

    def fetch_appointments(
        self, date_from: str, date_to: str
    ) -> list[dict[str, Any]]:
        """Pull appointments from the FHIR Appointment endpoint.

        FHIR query: GET /Appointment?date=ge{from}&date=le{to}&_count=100
        """
        if not self.authenticate():
            raise ConnectionError("Failed to authenticate with EHR")

        url = f"{self.base_url}/Appointment"
        params = {
            "date": [f"ge{date_from}", f"le{date_to}"],
            "_count": "100",
            "_sort": "date",
        }

        print(f"  [FHIR] Fetching appointments from {date_from} to {date_to}")
        appointments = []

        try:
            resp = self._client.get(url, params=params, headers=self._headers())

            if resp.status_code != 200:
                print(f"  [FHIR] Appointment fetch failed: {resp.status_code}")
                return []

            bundle = resp.json()
            entries = bundle.get("entry", [])
            print(f"  [FHIR] Got {len(entries)} appointments")

            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Appointment":
                    appt = self._parse_fhir_appointment(resource)
                    appointments.append(appt)

            # Handle pagination (FHIR uses Bundle.link with rel=next)
            next_url = None
            for link in bundle.get("link", []):
                if link.get("relation") == "next":
                    next_url = link.get("url")
                    break

            while next_url:
                resp = self._client.get(next_url, headers=self._headers())
                if resp.status_code != 200:
                    break
                bundle = resp.json()
                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    if resource.get("resourceType") == "Appointment":
                        appointments.append(self._parse_fhir_appointment(resource))
                next_url = None
                for link in bundle.get("link", []):
                    if link.get("relation") == "next":
                        next_url = link.get("url")
                        break

        except Exception as exc:
            print(f"  [FHIR] Error fetching appointments: {exc}")

        return appointments

    def fetch_patient_coverage(
        self, patient_id: str
    ) -> dict[str, Any] | None:
        """Pull Coverage resource for a patient.

        FHIR query: GET /Coverage?patient={patient_id}&status=active
        Returns payer_id, member_id, group_number, etc.
        """
        if not self.authenticate():
            return None

        url = f"{self.base_url}/Coverage"
        params = {"patient": patient_id, "status": "active", "_count": "10"}

        try:
            resp = self._client.get(url, params=params, headers=self._headers())
            if resp.status_code != 200:
                return None

            bundle = resp.json()
            entries = bundle.get("entry", [])
            if not entries:
                return None

            coverage = entries[0].get("resource", {})
            return self._parse_fhir_coverage(coverage)

        except Exception as exc:
            print(f"  [FHIR] Error fetching coverage: {exc}")
            return None

    def _parse_fhir_appointment(self, resource: dict) -> dict[str, Any]:
        """Parse FHIR Appointment resource into our format."""
        result: dict[str, Any] = {
            "ehr_source": self.ehr_name,
            "ehr_appointment_id": resource.get("id", ""),
        }

        # Start date/time
        start = resource.get("start", "")
        if start:
            result["appointment_date"] = start[:10]
            result["appointment_time"] = start[11:16] if len(start) > 11 else ""

        # Appointment type
        for st in resource.get("serviceType", []):
            for coding in st.get("coding", []):
                result["appointment_type"] = coding.get("display", "")
                result["service_type_code"] = coding.get("code", "30")

        # Participants
        for participant in resource.get("participant", []):
            actor = participant.get("actor", {})
            ref = actor.get("reference", "")
            display = actor.get("display", "")

            if "Patient/" in ref:
                result["patient_ref"] = ref
                parts = display.replace(",", " ").split()
                if len(parts) >= 2:
                    result["patient_first_name"] = parts[0]
                    result["patient_last_name"] = parts[-1]
                else:
                    result["patient_first_name"] = display
                    result["patient_last_name"] = ""

            elif "Practitioner/" in ref:
                result["provider_name"] = display

        return result

    @staticmethod
    def _parse_fhir_coverage(resource: dict) -> dict[str, Any]:
        """Parse FHIR Coverage resource into payer/member info."""
        result: dict[str, Any] = {}

        # Payer
        for payor in resource.get("payor", []):
            result["payer_name"] = payor.get("display", "")
            ref = payor.get("reference", "")
            if "/" in ref:
                result["payer_ref"] = ref

        # Member ID
        for identifier in resource.get("identifier", []):
            result["member_id"] = identifier.get("value", "")
            break

        # Subscriber ID
        subscriber = resource.get("subscriber", {})
        result["subscriber_name"] = subscriber.get("display", "")

        # Group
        for cls in resource.get("class", []):
            if cls.get("type", {}).get("coding", [{}])[0].get("code") == "group":
                result["group_number"] = cls.get("value", "")

        result["coverage_status"] = resource.get("status", "")
        return result

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Custom REST Adapter (for non-FHIR EHRs)
# ---------------------------------------------------------------------------

class CustomRESTAdapter(BaseEHRAdapter):
    """Connect to custom EHR REST APIs.

    For EHRs that don't support FHIR but have their own REST API.
    Practice configures: base_url, api_key, endpoint mappings.
    """

    def __init__(self, config: dict[str, str]) -> None:
        super().__init__(config)
        self.ehr_name = config.get("ehr_name", "custom")
        self.base_url = config.get("base_url", "").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.auth_header = config.get("auth_header", "Authorization")
        self.auth_prefix = config.get("auth_prefix", "Bearer")
        # Endpoint mappings (configurable per EHR)
        self.appointments_endpoint = config.get("appointments_endpoint", "/api/appointments")
        self.patient_endpoint = config.get("patient_endpoint", "/api/patients")
        self._client = httpx.Client(timeout=30)

    def authenticate(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            self.auth_header: f"{self.auth_prefix} {self.api_key}",
            "Accept": "application/json",
        }

    def fetch_appointments(
        self, date_from: str, date_to: str
    ) -> list[dict[str, Any]]:
        """Fetch appointments from custom REST API."""
        url = f"{self.base_url}{self.appointments_endpoint}"
        params = {"date_from": date_from, "date_to": date_to}

        try:
            resp = self._client.get(url, params=params, headers=self._headers())
            if resp.status_code != 200:
                return []

            data = resp.json()
            # Handle different response formats
            appointments = data if isinstance(data, list) else data.get("appointments", data.get("data", []))

            # Map to our format (field names are configurable)
            field_map = {
                "patient_first_name": self.config.get("map_first_name", "patient_first_name"),
                "patient_last_name": self.config.get("map_last_name", "patient_last_name"),
                "patient_dob": self.config.get("map_dob", "patient_dob"),
                "member_id": self.config.get("map_member_id", "member_id"),
                "payer_id": self.config.get("map_payer_id", "payer_id"),
                "appointment_date": self.config.get("map_appt_date", "appointment_date"),
                "appointment_time": self.config.get("map_appt_time", "appointment_time"),
            }

            result = []
            for appt in appointments:
                mapped = {"ehr_source": self.ehr_name}
                for our_field, their_field in field_map.items():
                    mapped[our_field] = appt.get(their_field, "")
                mapped["ehr_appointment_id"] = str(appt.get("id", appt.get("appointment_id", "")))
                result.append(mapped)

            return result

        except Exception as exc:
            print(f"  [Custom EHR] Error: {exc}")
            return []

    def fetch_patient_coverage(self, patient_id: str) -> dict[str, Any] | None:
        return None  # Custom EHRs usually don't expose coverage data

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# EHR Adapter Factory
# ---------------------------------------------------------------------------

def get_ehr_adapter(config: dict[str, str]) -> BaseEHRAdapter:
    """Create the appropriate EHR adapter based on config.

    Config must include 'ehr_type': fhir | custom | epic | cerner | athena
    """
    ehr_type = config.get("ehr_type", "fhir").lower()

    if ehr_type in ("fhir", "epic", "cerner", "athena", "eclinicalworks", "allscripts"):
        return FHIRR4Adapter(config)
    elif ehr_type in ("custom", "rest"):
        return CustomRESTAdapter(config)
    else:
        raise ValueError(f"Unsupported EHR type: {ehr_type}")


# ---------------------------------------------------------------------------
# EHR Sync Agent — polls EHR and creates appointments
# ---------------------------------------------------------------------------

def sync_ehr_appointments(
    config: dict[str, str],
    days_ahead: int = 7,
) -> dict[str, Any]:
    """Poll the configured EHR and sync appointments into ThinkAI.

    This is the main entry point for EHR sync. Called by:
      - Scheduled cron job (e.g., every 15 minutes)
      - "Run Now" button on EHR Sync page
      - Manual trigger via API

    Flow:
      1. Connect to EHR using configured adapter
      2. Pull appointments for next N days
      3. For each: pull Coverage if available
      4. Create appointment in our DB (skips duplicates)
      5. Auto-run eligibility + PA via automation agent

    Args:
        config: EHR connection config (from EHR Sync settings page).
        days_ahead: How many days ahead to sync.

    Returns:
        Sync summary with counts.
    """
    from claim_validator.automation_agent import create_appointment

    adapter = get_ehr_adapter(config)
    start = time.time()

    try:
        # Authenticate
        if not adapter.authenticate():
            return {"status": "error", "message": "Authentication failed"}

        # Pull appointments
        date_from = datetime.now(UTC).date().isoformat()
        date_to = (datetime.now(UTC).date() + timedelta(days=days_ahead)).isoformat()

        appointments = adapter.fetch_appointments(date_from, date_to)
        print(f"  [EHR Sync] Pulled {len(appointments)} appointments from {adapter.ehr_name}")

        created = 0
        skipped = 0
        errors = 0

        for appt_data in appointments:
            try:
                # Try to enrich with coverage data
                patient_ref = appt_data.get("patient_ref", "")
                if patient_ref and not appt_data.get("member_id"):
                    coverage = adapter.fetch_patient_coverage(patient_ref)
                    if coverage:
                        appt_data.update(coverage)

                # Create appointment (auto_check=True triggers eligibility)
                appt_data["auto_check"] = True
                create_appointment(appt_data)
                created += 1

            except Exception as exc:
                # Likely duplicate — skip
                if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                    skipped += 1
                else:
                    errors += 1
                    print(f"  [EHR Sync] Error creating appointment: {exc}")

        elapsed = round(time.time() - start, 1)
        return {
            "status": "ok",
            "ehr": adapter.ehr_name,
            "total_pulled": len(appointments),
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "execution_time": elapsed,
        }

    finally:
        adapter.close()
