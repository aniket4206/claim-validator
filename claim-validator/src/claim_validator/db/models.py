"""SQLAlchemy ORM models for the EligibilityAgent database."""

from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EligibilityCheck(Base):
    __tablename__ = "eligibility_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(String(20), unique=True, nullable=False, index=True)
    source = Column(String(10), nullable=False, default="single")  # single | batch

    # Patient info
    patient_first_name = Column(String(100), nullable=False)
    patient_last_name = Column(String(100), nullable=False)
    patient_name = Column(String(200), nullable=False)
    patient_dob = Column(String(20), nullable=True)
    member_id = Column(String(100), nullable=True)

    # Payer info
    payer_id = Column(String(50), nullable=True)
    payer_name = Column(String(200), nullable=True)

    # Provider info
    provider_npi = Column(String(20), nullable=True)
    provider_name = Column(String(200), nullable=True)
    service_type_code = Column(String(10), nullable=True, default="30")

    # Status
    status = Column(String(30), nullable=False, default="pending")  # eligible, not_eligible, inactive, pending, error

    # Financial summary
    annual_deductible = Column(Float, nullable=True)
    annual_deductible_max = Column(Float, nullable=True)
    out_of_pocket = Column(Float, nullable=True)
    out_of_pocket_max = Column(Float, nullable=True)
    copay = Column(Float, nullable=True)
    coinsurance = Column(Float, nullable=True)

    # Coverage details
    prior_auth_required = Column(Boolean, nullable=True)
    coverage_start = Column(String(20), nullable=True)
    coverage_end = Column(String(20), nullable=True)
    plan_name = Column(String(200), nullable=True)
    group_number = Column(String(50), nullable=True)
    plan_number = Column(String(50), nullable=True)

    # Payer / subscriber info from clearinghouse
    carrier_name = Column(String(200), nullable=True)
    subscriber_name = Column(String(200), nullable=True)
    patient_dob_from_payer = Column(String(20), nullable=True)
    patient_gender = Column(String(10), nullable=True)
    relationship = Column(String(50), nullable=True)
    coverage_status = Column(String(50), nullable=True)
    claims_address = Column(Text, nullable=True)

    # Findings (stored as JSON)
    findings = Column(JSON, nullable=True)
    total_errors = Column(Integer, nullable=False, default=0)
    total_warnings = Column(Integer, nullable=False, default=0)

    # AI summary
    ai_summary = Column(Text, nullable=True)
    execution_time = Column(Float, nullable=True, default=0.0)

    # Raw clearinghouse response
    raw_response = Column(JSON, nullable=True)

    # Timestamps
    run_date = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary (matching the old in-memory format)."""
        return {
            "check_id": self.check_id,
            "source": self.source,
            "status": self.status,
            "patient_name": self.patient_name,
            "patient_first_name": self.patient_first_name,
            "patient_last_name": self.patient_last_name,
            "patient_dob": self.patient_dob,
            "member_id": self.member_id,
            "payer_id": self.payer_id,
            "payer_name": self.payer_name,
            "provider_npi": self.provider_npi,
            "provider_name": self.provider_name,
            "service_type_code": self.service_type_code,
            "run_date": self.run_date,
            "annual_deductible": self.annual_deductible,
            "annual_deductible_max": self.annual_deductible_max,
            "out_of_pocket": self.out_of_pocket,
            "out_of_pocket_max": self.out_of_pocket_max,
            "copay": self.copay,
            "coinsurance": self.coinsurance,
            "prior_auth_required": self.prior_auth_required,
            "coverage_start": self.coverage_start,
            "coverage_end": self.coverage_end,
            "plan_name": self.plan_name,
            "group_number": self.group_number,
            "plan_number": self.plan_number,
            "carrier_name": self.carrier_name,
            "subscriber_name": self.subscriber_name,
            "patient_dob_from_payer": self.patient_dob_from_payer,
            "patient_gender": self.patient_gender,
            "relationship": self.relationship,
            "coverage_status": self.coverage_status,
            "claims_address": self.claims_address,
            "findings": self.findings or [],
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "ai_summary": self.ai_summary,
            "execution_time": self.execution_time,
            "raw_response": self.raw_response,
        }


class PriorAuthCheck(Base):
    __tablename__ = "prior_auth_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pa_id = Column(String(20), unique=True, nullable=False, index=True)

    # Patient info
    patient_first_name = Column(String(100), nullable=False)
    patient_last_name = Column(String(100), nullable=False)
    patient_name = Column(String(200), nullable=False)
    patient_dob = Column(String(20), nullable=True)
    member_id = Column(String(100), nullable=True)

    # Payer info
    payer_id = Column(String(50), nullable=True)
    payer_name = Column(String(200), nullable=True)

    # Provider info
    provider_npi = Column(String(20), nullable=True)
    provider_name = Column(String(200), nullable=True)

    # PA-specific
    service_type_code = Column(String(10), nullable=True, default="30")
    diagnosis_code = Column(String(20), nullable=True)
    procedure_code = Column(String(20), nullable=True)

    # Status
    status = Column(String(30), nullable=False, default="pending")  # submitted, pending, approved, denied, error

    # Response fields
    reference_id = Column(String(100), nullable=True)
    status_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    auth_number = Column(String(100), nullable=True)

    # Link to eligibility check
    eligibility_check_id = Column(String(20), nullable=True)

    execution_time = Column(Float, nullable=True, default=0.0)
    raw_response = Column(JSON, nullable=True)

    # Timestamps
    run_date = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary (matching the old in-memory format)."""
        return {
            "pa_id": self.pa_id,
            "status": self.status,
            "patient_name": self.patient_name,
            "payer_name": self.payer_name,
            "run_date": self.run_date,
            "reference_id": self.reference_id,
            "status_message": self.status_message,
            "error_message": self.error_message,
            "auth_number": self.auth_number,
            "eligibility_check_id": self.eligibility_check_id,
            "execution_time": self.execution_time,
            "raw_response": self.raw_response,
        }
