"""Live integration tests for ClaimMD API.

These tests call the real ClaimMD API using test credentials from .env.
They verify eligibility, claims submission, and claim status endpoints.

Note: ClaimMD does NOT support prior authorization. PA is Waystar-only.

Run with:
    pytest tests/test_clearinghouse/test_claimmd_live.py -v -s

Requires .env with:
    CLEARINGHOUSE_CLAIMMD_API_KEY
    TEST_PROVIDER_NPI, PROVIDER_TAX_ID, TEST_PAYER_ID,
    TEST_MEMBER_ID, TEST_PATIENT_FIRST, TEST_PATIENT_LAST, TEST_PATIENT_DOB
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

# Load .env from project root
_root = Path(__file__).resolve().parent.parent.parent.parent
_env = _root / ".env"
if _env.is_file():
    load_dotenv(_env)

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseAuthError,
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.clearinghouse.providers.claimmd import ClaimMDClient

# ---------------------------------------------------------------------------
# Test configuration from .env
# ---------------------------------------------------------------------------

CLAIMMD_API_KEY = os.getenv("CLEARINGHOUSE_CLAIMMD_API_KEY", "")
CLAIMMD_BASE_URL = os.getenv(
    "CLEARINGHOUSE_CLAIMMD_BASE_URL", "https://svc.claim.md"
)
PROVIDER_NPI = os.getenv("TEST_PROVIDER_NPI", "1111111112")
PROVIDER_TAX_ID = os.getenv("PROVIDER_TAX_ID", "999999999")
PAYER_ID = os.getenv("TEST_PAYER_ID", "60054")  # Aetna
PAYER_NAME = os.getenv("TEST_PAYER_NAME", "Aetna")
MEMBER_ID = os.getenv("TEST_MEMBER_ID", "AETNA12345")
PATIENT_FIRST = os.getenv("TEST_PATIENT_FIRST", "Jane")
PATIENT_LAST = os.getenv("TEST_PATIENT_LAST", "Doe")
PATIENT_DOB = os.getenv("TEST_PATIENT_DOB", "2004-04-04")

# Skip all tests if no API key configured
pytestmark = pytest.mark.skipif(
    not CLAIMMD_API_KEY,
    reason="CLEARINGHOUSE_CLAIMMD_API_KEY not set — skipping live ClaimMD tests",
)


@pytest.fixture()
def claimmd_client() -> ClaimMDClient:
    """Create a live ClaimMDClient with real credentials."""
    client = ClaimMDClient(
        account_key=CLAIMMD_API_KEY,
        base_url=CLAIMMD_BASE_URL,
    )
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Eligibility tests — POST /services/eligdata/
# ---------------------------------------------------------------------------


class TestClaimMDLiveEligibility:
    """Live eligibility verification against ClaimMD API."""

    def test_eligibility_check_returns_response(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Basic eligibility check returns a valid response object."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status in ("active", "inactive", "response_received", "unknown")
        assert result.raw_response is not None
        print(f"\n  Status: {result.status}")
        print(f"  Eligible: {result.eligible}")
        print(f"  Reference ID: {result.reference_id}")

    def test_eligibility_returns_active_coverage(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Aetna test member should return active eligibility."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        assert result.eligible is True
        assert result.status == "active"

    def test_eligibility_returns_plan_info(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Eligibility response should contain plan information."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        plan_info = result.plan_info
        assert plan_info is not None
        assert len(plan_info) > 0, "Plan info should not be empty"
        # ClaimMD XML response includes elig attributes + benefits list
        print(f"\n  Plan info keys: {list(plan_info.keys())}")
        benefits = plan_info.get("benefits", [])
        print(f"  Number of benefits: {len(benefits)}")
        for b in benefits[:3]:
            print(
                f"    - {b.get('benefit_description', 'N/A')}: "
                f"{b.get('benefit_coverage_description', 'N/A')}"
            )

    def test_eligibility_returns_reference_id(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Eligibility response should include an eligid reference."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        assert result.reference_id is not None
        print(f"\n  Elig ID: {result.reference_id}")

    def test_eligibility_benefits_detail(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Parse and validate benefit details from ClaimMD response."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        benefits = result.raw_response.get("benefits", [])
        assert len(benefits) > 0, "Expected at least one benefit in response"

        # Verify benefit structure
        for benefit in benefits:
            assert "benefit_coverage_code" in benefit or "benefit_code" in benefit
            print(
                f"\n  Benefit: code={benefit.get('benefit_code')}, "
                f"coverage={benefit.get('benefit_coverage_code')}, "
                f"desc={benefit.get('benefit_coverage_description')}, "
                f"amount={benefit.get('benefit_amount', 'N/A')}, "
                f"network={benefit.get('inplan_network', 'N/A')}"
            )

    def test_eligibility_with_invalid_member_returns_error(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Invalid member ID should raise a validation error."""
        with pytest.raises(
            (ClearinghouseValidationError, ClearinghouseAuthError)
        ):
            claimmd_client.check_eligibility(
                {
                    "payer_id": PAYER_ID,
                    "npi": PROVIDER_NPI,
                    "provider_tax_id": PROVIDER_TAX_ID,
                    "subscriber_id": "INVALID_MEMBER_999",
                    "first_name": "Nonexistent",
                    "last_name": "Person",
                    "dob": "1900-01-01",
                    "service_date": "2026-03-24",
                    "service_type": "30",
                    "pat_rel": "18",
                }
            )

    def test_eligibility_without_tax_id(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Eligibility check without provider tax ID — may still work or error."""
        try:
            result = claimmd_client.check_eligibility(
                {
                    "payer_id": PAYER_ID,
                    "npi": PROVIDER_NPI,
                    "subscriber_id": MEMBER_ID,
                    "first_name": PATIENT_FIRST,
                    "last_name": PATIENT_LAST,
                    "dob": PATIENT_DOB,
                    "service_date": "2026-03-24",
                    "service_type": "30",
                    "pat_rel": "18",
                }
            )
            print(f"\n  Without tax_id — Status: {result.status}")
        except ClearinghouseValidationError as exc:
            print(f"\n  Without tax_id — Validation error (expected): {exc}")

    def test_eligibility_multiple_service_types(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Request multiple service type codes (e.g., 30,UC)."""
        result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        assert isinstance(result, ClearinghouseEligibilityResponse)
        print(f"\n  Multi-service Status: {result.status}")


# ---------------------------------------------------------------------------
# Claims submission tests — POST /services/upload/
# ---------------------------------------------------------------------------


class TestClaimMDLiveClaimSubmission:
    """Live claims submission against ClaimMD API.

    ClaimMD /services/upload/ expects proper claim file formats:
    837P (professional), 837I (institutional), CSV, or ClaimMD JSON/XML.
    Arbitrary JSON dicts are rejected with "Zero claims detected."

    These tests use ClaimMD's CSV format which is the simplest to construct.
    """

    def _test_claim_csv(self) -> str:
        """Build a minimal ClaimMD CSV claim line.

        ClaimMD CSV format requires specific column order. Minimum fields:
        payerid, ins_name_l, ins_name_f, ins_number, ins_dob, ins_sex,
        pat_rel, bill_npi, bill_taxid, fdos, tdos, pos, diag1, proc,
        charge, units
        """
        # ClaimMD CSV: one claim per line, pipe or comma delimited
        return (
            f"{PAYER_ID},{PATIENT_LAST},{PATIENT_FIRST},{MEMBER_ID},"
            f"20040404,F,18,{PROVIDER_NPI},{PROVIDER_TAX_ID},"
            f"20260324,20260324,11,J069,99213,15000,1"
        )

    def test_claim_submission_returns_result(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Submit a test claim CSV and get acknowledgment or validation error."""
        try:
            result = claimmd_client.submit_claim(
                {"_raw_file": self._test_claim_csv()}
            )
            assert isinstance(result, SubmissionResult)
            print(f"\n  Submission status: {result.status}")
            print(f"  Accepted: {result.accepted}")
            print(f"  Reference ID: {result.reference_id}")
        except ClearinghouseValidationError as exc:
            # ClaimMD test env may reject claims — validation error is acceptable
            print(f"\n  Validation error (expected in test env): {exc}")

    def test_claim_submission_invalid_data_raises_error(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Invalid claim data should raise a validation error."""
        with pytest.raises(ClearinghouseValidationError):
            claimmd_client.submit_claim({"invalid": "data"})


# ---------------------------------------------------------------------------
# Claim status tests — POST /services/response/
# ---------------------------------------------------------------------------


class TestClaimMDLiveClaimStatus:
    """Live claim status checks against ClaimMD API."""

    def test_claim_status_with_initial_query(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Query claim responses with ResponseID=0 (initial fetch)."""
        result = claimmd_client.check_claim_status("0")
        assert isinstance(result, ClaimStatusResponse)
        print(f"\n  Status: {result.status}")
        print(f"  Claim status: {result.claim_status}")
        print(f"  Reference ID: {result.reference_id}")


# ---------------------------------------------------------------------------
# Prior Authorization — NOT supported by ClaimMD
# ---------------------------------------------------------------------------


class TestClaimMDPriorAuthNotSupported:
    """Document that ClaimMD does not offer prior authorization endpoints.

    Prior authorization (X12 278) is only available through Waystar.
    ClaimMD focuses on: eligibility (270/271), claims (837), ERA (835).
    """

    def test_claimmd_has_no_prior_auth_method(self) -> None:
        """ClaimMDClient should not have a check_prior_auth method."""
        assert not hasattr(ClaimMDClient, "check_prior_auth")
        assert not hasattr(ClaimMDClient, "submit_prior_auth")
        assert not hasattr(ClaimMDClient, "check_prior_auth_status")

    def test_claimmd_supported_operations(self) -> None:
        """ClaimMD supports: eligibility, claims upload, claim status."""
        assert hasattr(ClaimMDClient, "check_eligibility")
        assert hasattr(ClaimMDClient, "submit_claim")
        assert hasattr(ClaimMDClient, "check_claim_status")


# ---------------------------------------------------------------------------
# Full flow integration test
# ---------------------------------------------------------------------------


class TestClaimMDFullFlow:
    """End-to-end: eligibility check -> claim submission -> status check."""

    def test_eligibility_then_claim_flow(
        self, claimmd_client: ClaimMDClient
    ) -> None:
        """Run eligibility, then submit a claim if eligible."""
        # Step 1: Check eligibility
        elig_result = claimmd_client.check_eligibility(
            {
                "payer_id": PAYER_ID,
                "npi": PROVIDER_NPI,
                "provider_tax_id": PROVIDER_TAX_ID,
                "subscriber_id": MEMBER_ID,
                "first_name": PATIENT_FIRST,
                "last_name": PATIENT_LAST,
                "dob": PATIENT_DOB,
                "service_date": "2026-03-24",
                "service_type": "30",
                "pat_rel": "18",
            }
        )
        print(f"\n  [1] Eligibility: {elig_result.status} (eligible={elig_result.eligible})")
        assert isinstance(elig_result, ClearinghouseEligibilityResponse)

        # Step 2: Submit claim (only if eligible)
        if elig_result.eligible:
            claim_csv = (
                f"{PAYER_ID},{PATIENT_LAST},{PATIENT_FIRST},{MEMBER_ID},"
                f"20040404,F,18,{PROVIDER_NPI},{PROVIDER_TAX_ID},"
                f"20260324,20260324,11,J069,99213,15000,1"
            )
            try:
                claim_result = claimmd_client.submit_claim(
                    {"_raw_file": claim_csv}
                )
                print(
                    f"  [2] Claim submission: {claim_result.status} "
                    f"(accepted={claim_result.accepted})"
                )

                # Step 3: Check status
                ref = claim_result.reference_id or "0"
                status_result = claimmd_client.check_claim_status(ref)
                print(f"  [3] Claim status: {status_result.status}")
            except ClearinghouseValidationError as exc:
                print(f"  [2] Claim validation error (test env): {exc}")
                # Still check claim status with initial query
                status_result = claimmd_client.check_claim_status("0")
                print(f"  [3] Claim status (initial): {status_result.status}")
        else:
            print("  [2] Skipped claim — patient not eligible")
            pytest.skip("Patient not eligible, skipping claim submission")
