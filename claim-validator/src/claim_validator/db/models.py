"""SQLAlchemy ORM models for the EligibilityAgent database."""

from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    """Application users for portal access."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="Staff")  # Administrator, Staff
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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
    clearinghouse_provider = Column(String(30), nullable=True)  # stedi, waystar, claimmd

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

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

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
            "clearinghouse_provider": self.clearinghouse_provider,
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


class Appointment(Base):
    """Appointments pulled from EHR or created manually."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(String(50), unique=True, nullable=False, index=True)

    # Patient info
    patient_first_name = Column(String(100), nullable=False)
    patient_last_name = Column(String(100), nullable=False)
    patient_name = Column(String(200), nullable=False)
    patient_dob = Column(String(20), nullable=True)
    patient_phone = Column(String(20), nullable=True)
    member_id = Column(String(100), nullable=True)

    # Payer info
    payer_id = Column(String(50), nullable=True)
    payer_name = Column(String(200), nullable=True)

    # Provider info
    provider_npi = Column(String(20), nullable=True)
    provider_name = Column(String(200), nullable=True)

    # Appointment details
    appointment_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    appointment_time = Column(String(10), nullable=True)    # HH:MM
    appointment_type = Column(String(100), nullable=True)   # Initial Eval, Follow-up, etc.
    service_type_code = Column(String(10), nullable=True, default="30")
    diagnosis_code = Column(String(20), nullable=True)
    procedure_code = Column(String(20), nullable=True)

    # Automation status
    status = Column(String(30), nullable=False, default="scheduled")
    # scheduled | elig_checked | pa_required | pa_submitted | cleared | action_needed | inactive

    # Links to automated checks
    eligibility_check_id = Column(String(20), nullable=True)
    eligibility_status = Column(String(30), nullable=True)  # eligible, inactive, error, pending
    pa_check_id = Column(String(20), nullable=True)
    pa_status = Column(String(30), nullable=True)  # approved, denied, pending, not_required

    # Financial (copied from eligibility check for quick access)
    copay = Column(Float, nullable=True)
    deductible = Column(Float, nullable=True)
    deductible_max = Column(Float, nullable=True)

    # EHR source
    ehr_source = Column(String(50), nullable=True)  # epic, cerner, athena, manual, fhir, csv
    ehr_appointment_id = Column(String(100), nullable=True)  # Original ID from EHR

    # Agent processing
    last_checked_at = Column(DateTime, nullable=True)
    check_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "appointment_id": self.appointment_id,
            "patient_name": self.patient_name,
            "patient_first_name": self.patient_first_name,
            "patient_last_name": self.patient_last_name,
            "patient_dob": self.patient_dob,
            "patient_phone": self.patient_phone,
            "member_id": self.member_id,
            "payer_id": self.payer_id,
            "payer_name": self.payer_name,
            "provider_npi": self.provider_npi,
            "provider_name": self.provider_name,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "appointment_type": self.appointment_type,
            "service_type_code": self.service_type_code,
            "diagnosis_code": self.diagnosis_code,
            "procedure_code": self.procedure_code,
            "status": self.status,
            "eligibility_check_id": self.eligibility_check_id,
            "eligibility_status": self.eligibility_status,
            "pa_check_id": self.pa_check_id,
            "pa_status": self.pa_status,
            "copay": self.copay,
            "deductible": self.deductible,
            "deductible_max": self.deductible_max,
            "ehr_source": self.ehr_source,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "check_count": self.check_count,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AgentRun(Base):
    """Tracks each automation agent run."""

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(50), unique=True, nullable=False)
    trigger = Column(String(30), nullable=False)  # manual, scheduled, webhook
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed
    total_appointments = Column(Integer, default=0)
    checked = Column(Integer, default=0)
    eligible = Column(Integer, default=0)
    inactive = Column(Integer, default=0)
    pa_required = Column(Integer, default=0)
    pa_submitted = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    execution_time = Column(Float, default=0.0)

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "trigger": self.trigger,
            "status": self.status,
            "total_appointments": self.total_appointments,
            "checked": self.checked,
            "eligible": self.eligible,
            "inactive": self.inactive,
            "pa_required": self.pa_required,
            "pa_submitted": self.pa_submitted,
            "errors": self.errors,
            "execution_time": self.execution_time,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
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

    # User ownership
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        """Convert to dictionary (matching the old in-memory format)."""
        return {
            "pa_id": self.pa_id,
            "status": self.status,
            "patient_name": self.patient_name,
            "patient_dob": self.patient_dob,
            "member_id": self.member_id,
            "payer_id": self.payer_id,
            "payer_name": self.payer_name,
            "provider_npi": self.provider_npi,
            "provider_name": self.provider_name,
            "service_type_code": self.service_type_code,
            "diagnosis_code": self.diagnosis_code,
            "procedure_code": self.procedure_code,
            "run_date": self.run_date,
            "reference_id": self.reference_id,
            "status_message": self.status_message,
            "error_message": self.error_message,
            "auth_number": self.auth_number,
            "eligibility_check_id": self.eligibility_check_id,
            "execution_time": self.execution_time,
            "raw_response": self.raw_response,
        }
