"""Tests for institutional validators (bill type, revenue code, admission, completeness)."""

from __future__ import annotations

from claim_validator.models.institutional import (
    InstitutionalClaimData,
    InstitutionalServiceLine,
)
from claim_validator.validators.institutional.admission import AdmissionValidator
from claim_validator.validators.institutional.bill_type import BillTypeValidator
from claim_validator.validators.institutional.completeness import (
    InstitutionalCompletenessValidator,
)
from claim_validator.validators.institutional.revenue_code import RevenueCodeValidator


# ---------------------------------------------------------------------------
# BillTypeValidator
# ---------------------------------------------------------------------------

class TestBillTypeValidator:
    def setup_method(self) -> None:
        self.v = BillTypeValidator()

    def test_valid_bill_type(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="111")
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_valid_bill_type_131(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="131")
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_invalid_length_too_short(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="11")
        result = self.v.validate(claim)
        assert len(result.findings) == 1
        assert result.findings[0].code == "INST_INVALID_BILL_TYPE"

    def test_invalid_length_too_long(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="1111")
        result = self.v.validate(claim)
        assert len(result.findings) == 1

    def test_invalid_facility_type_0(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="011")
        result = self.v.validate(claim)
        assert any(f.code == "INST_INVALID_BILL_TYPE" for f in result.findings)

    def test_invalid_facility_type_9(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="911")
        result = self.v.validate(claim)
        assert any(f.code == "INST_INVALID_BILL_TYPE" for f in result.findings)

    def test_invalid_classification_0(self) -> None:
        claim = InstitutionalClaimData(bill_type_code="101")
        result = self.v.validate(claim)
        assert any(f.code == "INST_INVALID_BILL_TYPE" for f in result.findings)

    def test_no_bill_type_skips(self) -> None:
        claim = InstitutionalClaimData()
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_non_institutional_claim_skips(self) -> None:
        """Professional claim (no bill_type_code attr) returns empty."""
        from claim_validator.models.claim import ClaimData
        claim = ClaimData(billing_provider_npi="1234567893")
        result = self.v.validate(claim)
        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# RevenueCodeValidator
# ---------------------------------------------------------------------------

class TestRevenueCodeValidator:
    def setup_method(self) -> None:
        self.v = RevenueCodeValidator()

    def test_valid_revenue_code(self) -> None:
        claim = InstitutionalClaimData(
            service_lines=[InstitutionalServiceLine(revenue_code="0120")]
        )
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_invalid_revenue_code(self) -> None:
        claim = InstitutionalClaimData(
            service_lines=[InstitutionalServiceLine(revenue_code="9999")]
        )
        result = self.v.validate(claim)
        assert len(result.findings) == 1
        assert result.findings[0].code == "INST_INVALID_REVENUE_CODE"

    def test_multiple_lines_mixed(self) -> None:
        claim = InstitutionalClaimData(
            service_lines=[
                InstitutionalServiceLine(revenue_code="0120"),  # valid
                InstitutionalServiceLine(revenue_code="9999"),  # invalid
            ]
        )
        result = self.v.validate(claim)
        assert len(result.findings) == 1

    def test_no_service_lines_skips(self) -> None:
        claim = InstitutionalClaimData()
        result = self.v.validate(claim)
        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# AdmissionValidator
# ---------------------------------------------------------------------------

class TestAdmissionValidator:
    def setup_method(self) -> None:
        self.v = AdmissionValidator()

    def test_valid_admission(self) -> None:
        claim = InstitutionalClaimData(
            admission_date="2026-01-10",
            discharge_date="2026-01-15",
            admission_type_code="1",
            admission_source_code="7",
            patient_status_code="01",
        )
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_admission_after_discharge(self) -> None:
        claim = InstitutionalClaimData(
            admission_date="2026-01-20",
            discharge_date="2026-01-15",
        )
        result = self.v.validate(claim)
        assert any(f.code == "INST_ADMISSION_DATE_ORDER" for f in result.findings)

    def test_invalid_admission_type(self) -> None:
        claim = InstitutionalClaimData(admission_type_code="X")
        result = self.v.validate(claim)
        assert any(f.code == "INST_ADMISSION_INVALID_TYPE" for f in result.findings)

    def test_invalid_admission_source(self) -> None:
        claim = InstitutionalClaimData(admission_source_code="Z")
        result = self.v.validate(claim)
        assert any(f.code == "INST_ADMISSION_INVALID_SOURCE" for f in result.findings)

    def test_invalid_patient_status(self) -> None:
        claim = InstitutionalClaimData(patient_status_code="99")
        result = self.v.validate(claim)
        assert any(f.code == "INST_ADMISSION_INVALID_STATUS" for f in result.findings)

    def test_no_admission_data_skips(self) -> None:
        claim = InstitutionalClaimData()
        result = self.v.validate(claim)
        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# InstitutionalCompletenessValidator
# ---------------------------------------------------------------------------

class TestInstitutionalCompletenessValidator:
    def setup_method(self) -> None:
        self.v = InstitutionalCompletenessValidator()

    def test_complete_claim(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            attending_physician_npi="9876543210",
            bill_type_code="111",
            subscriber_id="MEM123",
            service_lines=[InstitutionalServiceLine(revenue_code="0120")],
        )
        result = self.v.validate(claim)
        assert len(result.findings) == 0

    def test_missing_attending_npi(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            bill_type_code="111",
            subscriber_id="MEM123",
            service_lines=[InstitutionalServiceLine(revenue_code="0120")],
        )
        result = self.v.validate(claim)
        assert any(f.code == "INST_MISSING_ATTENDING_NPI" for f in result.findings)

    def test_missing_bill_type(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            attending_physician_npi="9876543210",
            subscriber_id="MEM123",
            service_lines=[InstitutionalServiceLine(revenue_code="0120")],
        )
        result = self.v.validate(claim)
        assert any(f.code == "INST_MISSING_BILL_TYPE" for f in result.findings)

    def test_missing_service_lines(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            attending_physician_npi="9876543210",
            bill_type_code="111",
            subscriber_id="MEM123",
        )
        result = self.v.validate(claim)
        assert any(f.code == "INST_MISSING_SERVICE_LINES" for f in result.findings)

    def test_empty_claim_all_missing(self) -> None:
        claim = InstitutionalClaimData()
        result = self.v.validate(claim)
        codes = {f.code for f in result.findings}
        assert "INST_MISSING_ATTENDING_NPI" in codes
        assert "INST_MISSING_BILL_TYPE" in codes
        assert "INST_MISSING_SERVICE_LINES" in codes
        assert "INST_MISSING_BILLING_NPI" in codes
        assert "INST_MISSING_SUBSCRIBER_ID" in codes

    def test_missing_subscriber_id(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            attending_physician_npi="9876543210",
            bill_type_code="111",
            service_lines=[InstitutionalServiceLine(revenue_code="0120")],
        )
        result = self.v.validate(claim)
        assert any(f.code == "INST_MISSING_SUBSCRIBER_ID" for f in result.findings)
