"""Automation Agent — auto-checks eligibility & PA for scheduled appointments.

This is the CORE differentiator from Waystar/manual workflows:
  1. Appointment created → auto eligibility check
  2. 24hrs before visit → auto re-check
  3. PA required → auto PA submission
  4. Results feed into Morning Brief & Appointments dashboard

The agent can be triggered:
  - Manually via API (Run Agent Now button)
  - On appointment creation (webhook from EHR)
  - Scheduled (cron job / background task)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy.orm import Session

from claim_validator.db.models import Appointment, AgentRun, EligibilityCheck
from claim_validator.db.session import SessionLocal
from claim_validator.eligibility_api import (
    EligibilityCheckRequest,
    run_eligibility_check,
)
from claim_validator.prior_auth_api import (
    PriorAuthRequest,
    submit_prior_auth,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Appointment management
# ---------------------------------------------------------------------------

def _next_appointment_id(db: Session) -> str:
    """Generate next appointment ID."""
    last = db.query(Appointment).order_by(Appointment.id.desc()).first()
    if last and last.appointment_id.startswith("APPT-"):
        try:
            num = int(last.appointment_id.split("-")[1])
            return f"APPT-{num + 1}"
        except (IndexError, ValueError):
            pass
    return "APPT-1001"


def create_appointment(data: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    """Create a new appointment and optionally auto-run eligibility.

    This is called when:
      - EHR sends a webhook (FHIR Subscription)
      - Staff manually creates an appointment
      - CSV batch import of appointments

    Args:
        data: Appointment fields (patient info, payer, provider, date, etc.)
        db: Optional DB session.

    Returns:
        Appointment dict with auto-check results.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        appt_id = _next_appointment_id(db)
        patient_name = f"{data.get('patient_first_name', '')} {data.get('patient_last_name', '')}".strip()

        appt = Appointment(
            appointment_id=appt_id,
            patient_first_name=data.get("patient_first_name", ""),
            patient_last_name=data.get("patient_last_name", ""),
            patient_name=patient_name,
            patient_dob=data.get("patient_dob", ""),
            patient_phone=data.get("patient_phone", ""),
            member_id=data.get("member_id", ""),
            payer_id=data.get("payer_id", ""),
            payer_name=data.get("payer_name", ""),
            provider_npi=data.get("provider_npi", ""),
            provider_name=data.get("provider_name", ""),
            appointment_date=data.get("appointment_date", ""),
            appointment_time=data.get("appointment_time", ""),
            appointment_type=data.get("appointment_type", ""),
            service_type_code=data.get("service_type_code", "30"),
            diagnosis_code=data.get("diagnosis_code", ""),
            procedure_code=data.get("procedure_code", ""),
            ehr_source=data.get("ehr_source", "manual"),
            ehr_appointment_id=data.get("ehr_appointment_id", ""),
            status="scheduled",
        )
        db.add(appt)
        db.commit()
        db.refresh(appt)

        # Auto-run eligibility check if we have enough data
        auto_check = data.get("auto_check", True)
        if auto_check and appt.member_id and appt.payer_id:
            print(f"\n[AUTO] Running eligibility check for {appt_id} ({patient_name})")
            _run_eligibility_for_appointment(appt, db)

        return appt.to_dict()

    finally:
        if own_session:
            db.close()


def _run_eligibility_for_appointment(appt: Appointment, db: Session) -> None:
    """Run an eligibility check for a single appointment and update it."""
    try:
        req = EligibilityCheckRequest(
            patient_first_name=appt.patient_first_name,
            patient_last_name=appt.patient_last_name,
            patient_dob=appt.patient_dob or "",
            member_id=appt.member_id or "",
            payer_id=appt.payer_id or "",
            payer_name=appt.payer_name or "",
            provider_npi=appt.provider_npi or "",
            provider_name=appt.provider_name or "",
            service_type_code=appt.service_type_code or "30",
            source="auto",
        )
        result = run_eligibility_check(req, db)

        # Update appointment with results
        appt.eligibility_check_id = result.check_id
        appt.eligibility_status = result.status
        appt.copay = result.copay
        appt.deductible = result.annual_deductible
        appt.deductible_max = result.annual_deductible_max
        appt.last_checked_at = datetime.now(UTC)
        appt.check_count = (appt.check_count or 0) + 1

        if result.status == "eligible":
            if result.prior_auth_required:
                appt.status = "pa_required"
                appt.pa_status = "required"
            else:
                appt.status = "cleared"
                appt.pa_status = "not_required"
        elif result.status == "inactive":
            appt.status = "action_needed"
            appt.notes = "Coverage inactive — verify insurance"
        elif result.status == "error":
            appt.status = "action_needed"
            appt.notes = f"Eligibility check error: {result.total_errors} error(s)"
        else:
            appt.status = "elig_checked"

        db.commit()
        print(f"  [AUTO] {appt.appointment_id}: {result.status} (PA: {appt.pa_status})")

    except Exception as exc:
        logger.warning("Auto eligibility failed for %s: %s", appt.appointment_id, exc)
        appt.status = "action_needed"
        appt.notes = f"Auto-check failed: {exc}"
        appt.last_checked_at = datetime.now(UTC)
        db.commit()


def _run_pa_for_appointment(appt: Appointment, db: Session) -> None:
    """Auto-submit PA inquiry for an appointment that requires it."""
    try:
        req = PriorAuthRequest(
            patient_first_name=appt.patient_first_name,
            patient_last_name=appt.patient_last_name,
            patient_dob=appt.patient_dob or "",
            member_id=appt.member_id or "",
            payer_id=appt.payer_id or "",
            payer_name=appt.payer_name or "",
            provider_npi=appt.provider_npi or "",
            provider_name=appt.provider_name or "",
            service_type_code=appt.service_type_code or "30",
            diagnosis_code=appt.diagnosis_code or "",
            procedure_code=appt.procedure_code or "",
            eligibility_check_id=appt.eligibility_check_id or "",
        )
        result = submit_prior_auth(req, db)

        appt.pa_check_id = result.pa_id
        appt.pa_status = result.status
        if result.status == "approved":
            appt.status = "cleared"
        else:
            appt.status = "pa_submitted"

        db.commit()
        print(f"  [AUTO-PA] {appt.appointment_id}: PA {result.status}")

    except Exception as exc:
        logger.warning("Auto PA failed for %s: %s", appt.appointment_id, exc)
        appt.notes = f"Auto PA failed: {exc}"
        db.commit()


# ---------------------------------------------------------------------------
# Agent runner — processes all upcoming appointments
# ---------------------------------------------------------------------------

def run_automation_agent(
    trigger: str = "manual",
    days_ahead: int = 2,
    recheck_hours: int = 24,
    auto_pa: bool = True,
    db: Session | None = None,
) -> dict[str, Any]:
    """Run the automation agent for all upcoming appointments.

    This is the main entry point. It:
      1. Finds appointments for today + tomorrow (or days_ahead)
      2. Runs eligibility for unchecked appointments
      3. Re-checks stale ones (checked > recheck_hours ago)
      4. Auto-submits PA for flagged appointments
      5. Returns a summary

    Args:
        trigger: What triggered this run (manual, scheduled, webhook).
        days_ahead: How many days ahead to check (default 2 = today + tomorrow).
        recheck_hours: Re-check if last check was this many hours ago.
        auto_pa: Whether to auto-submit PA for flagged appointments.
        db: Optional DB session.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    start = time.perf_counter()
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"

    print("\n" + "=" * 70)
    print(f"  AUTOMATION AGENT — {run_id}")
    print(f"  Trigger: {trigger} | Days ahead: {days_ahead} | Recheck: {recheck_hours}h | Auto-PA: {auto_pa}")
    print("=" * 70)

    try:
        # Create agent run record
        agent_run = AgentRun(
            run_id=run_id,
            trigger=trigger,
            status="running",
        )
        db.add(agent_run)
        db.commit()

        # Find appointments to process
        today = datetime.now(UTC).date()
        cutoff_date = (today + timedelta(days=days_ahead)).isoformat()
        today_str = today.isoformat()

        appointments = (
            db.query(Appointment)
            .filter(Appointment.appointment_date >= today_str)
            .filter(Appointment.appointment_date <= cutoff_date)
            .order_by(Appointment.appointment_date, Appointment.appointment_time)
            .all()
        )

        agent_run.total_appointments = len(appointments)
        print(f"\n  Found {len(appointments)} appointments for {today_str} to {cutoff_date}")

        stale_cutoff = datetime.now(UTC) - timedelta(hours=recheck_hours)
        checked = 0
        eligible = 0
        inactive = 0
        pa_required = 0
        pa_submitted = 0
        errors = 0

        for appt in appointments:
            needs_check = False

            # Never checked
            if not appt.last_checked_at:
                needs_check = True
                print(f"\n  [{appt.appointment_id}] {appt.patient_name} — NEVER CHECKED")

            # Stale check (older than recheck_hours)
            elif appt.last_checked_at < stale_cutoff:
                needs_check = True
                print(f"\n  [{appt.appointment_id}] {appt.patient_name} — STALE (last: {appt.last_checked_at})")

            # Skip if recently checked
            else:
                print(f"\n  [{appt.appointment_id}] {appt.patient_name} — OK (last: {appt.last_checked_at})")

            if needs_check and appt.member_id and appt.payer_id:
                _run_eligibility_for_appointment(appt, db)
                checked += 1

                if appt.eligibility_status == "eligible":
                    eligible += 1
                elif appt.eligibility_status == "inactive":
                    inactive += 1
                elif appt.eligibility_status == "error":
                    errors += 1

                if appt.pa_status == "required" or appt.status == "pa_required":
                    pa_required += 1
            elif needs_check:
                print(f"  SKIP (missing member_id or payer_id)")

            # Auto-submit PA if needed
            if auto_pa and appt.status == "pa_required" and not appt.pa_check_id:
                _run_pa_for_appointment(appt, db)
                pa_submitted += 1

        # Update agent run record
        elapsed = round(time.perf_counter() - start, 1)
        agent_run.status = "completed"
        agent_run.checked = checked
        agent_run.eligible = eligible
        agent_run.inactive = inactive
        agent_run.pa_required = pa_required
        agent_run.pa_submitted = pa_submitted
        agent_run.errors = errors
        agent_run.execution_time = elapsed
        agent_run.completed_at = datetime.now(UTC)
        db.commit()

        summary = agent_run.to_dict()
        print(f"\n  DONE in {elapsed}s: {checked} checked, {eligible} eligible, "
              f"{inactive} inactive, {pa_required} PA required, {pa_submitted} PA submitted")
        print("=" * 70 + "\n")

        return summary

    except Exception as exc:
        logger.error("Agent run failed: %s", exc)
        try:
            agent_run.status = "failed"
            agent_run.execution_time = round(time.perf_counter() - start, 1)
            agent_run.completed_at = datetime.now(UTC)
            db.commit()
        except Exception:
            pass
        raise

    finally:
        if own_session:
            db.close()


def get_agent_status(db: Session | None = None) -> dict[str, Any] | None:
    """Get the most recent agent run."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        run = db.query(AgentRun).order_by(AgentRun.id.desc()).first()
        return run.to_dict() if run else None
    finally:
        if own_session:
            db.close()


def get_appointments(
    date_filter: str = "today",
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """Get appointments with optional date filter."""
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True
    try:
        today = datetime.now(UTC).date().isoformat()
        tomorrow = (datetime.now(UTC).date() + timedelta(days=1)).isoformat()
        week_end = (datetime.now(UTC).date() + timedelta(days=7)).isoformat()

        query = db.query(Appointment)

        if date_filter == "today":
            query = query.filter(Appointment.appointment_date == today)
        elif date_filter == "tomorrow":
            query = query.filter(Appointment.appointment_date == tomorrow)
        elif date_filter == "week":
            query = query.filter(
                Appointment.appointment_date >= today,
                Appointment.appointment_date <= week_end,
            )
        # else: return all

        appointments = (
            query.order_by(Appointment.appointment_date, Appointment.appointment_time)
            .limit(100)
            .all()
        )
        return [a.to_dict() for a in appointments]

    finally:
        if own_session:
            db.close()
