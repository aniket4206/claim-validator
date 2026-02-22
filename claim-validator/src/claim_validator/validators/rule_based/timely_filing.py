"""TimelyFilingValidator -- date consistency and timely filing checks."""

from __future__ import annotations

import datetime

from claim_validator.code_tables.timely_filing import (
    get_filing_deadline,
)
from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class TimelyFilingValidator(BaseValidator):
    """Validates service date consistency and timely filing deadlines."""

    name = "TimelyFilingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_service_dates(claim, findings)
        self._check_timely_filing(claim, findings)

        return self._make_output(findings)

    def _check_service_dates(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        dob_date = self._parse_date(claim.patient_dob)
        today = datetime.date.today()

        for idx, line in enumerate(claim.lines, start=1):
            from_date = self._parse_date(
                line.service_date_from,
            )
            if from_date is None:
                continue

            if from_date > today:
                findings.append(
                    self._make_finding(
                        code="FUTURE_SERVICE_DATE",
                        message=(
                            "Date in 'service_date_from'"
                            " must not be in the future"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Verify the service date"
                            " (CMS-1500 Box 24.A)"
                        ),
                    )
                )

            if dob_date is not None and from_date < dob_date:
                findings.append(
                    self._make_finding(
                        code="SERVICE_BEFORE_DOB",
                        message=(
                            "Date in 'service_date_from'"
                            " is before 'patient_dob'"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Verify the service date"
                            " and patient date of"
                            " birth"
                        ),
                    )
                )

            to_date = self._parse_date(line.service_date_to)
            if to_date is not None and from_date > to_date:
                findings.append(
                    self._make_finding(
                        code="INVALID_DATE_RANGE",
                        message=(
                            "Date in 'service_date_from'"
                            " is after"
                            " 'service_date_to'"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_date_from",
                        line_number=idx,
                        suggestion=(
                            "Ensure service start date"
                            " is on or before end"
                            " date (CMS-1500"
                            " Box 24.A)"
                        ),
                    )
                )

    def _check_timely_filing(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return
        if not claim.payer_id or not claim.payer_id.strip():
            return

        deadline = get_filing_deadline(claim.payer_id)
        if deadline is None:
            return

        filing_date = self._parse_date(claim.filing_date)
        if filing_date is None:
            filing_date = datetime.date.today()

        earliest = self._earliest_service_date(claim)
        if earliest is None:
            return

        days_elapsed = (filing_date - earliest).days
        if days_elapsed > deadline:
            findings.append(
                self._make_finding(
                    code="TIMELY_FILING_EXCEEDED",
                    message=(
                        "Claim may exceed the"
                        " payer's timely filing"
                        " deadline"
                    ),
                    severity=Severity.ERROR,
                    field_name="service_date_from",
                    suggestion=(
                        "Check the payer's timely"
                        " filing limit and submit"
                        " promptly"
                    ),
                )
            )

    @staticmethod
    def _parse_date(
        value: str | None,
    ) -> datetime.date | None:
        if not value or not value.strip():
            return None
        try:
            return datetime.date.fromisoformat(
                value.strip(),
            )
        except ValueError:
            return None

    def _earliest_service_date(
        self, claim: ClaimData,
    ) -> datetime.date | None:
        earliest: datetime.date | None = None
        for line in claim.lines:
            d = self._parse_date(line.service_date_from)
            if d is not None:
                if earliest is None or d < earliest:
                    earliest = d
        return earliest
