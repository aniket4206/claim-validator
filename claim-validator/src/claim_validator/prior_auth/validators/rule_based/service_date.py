"""PAServiceDateValidator — service date validation for PA requests."""

from __future__ import annotations

from datetime import date, timedelta

from claim_validator.constants import Severity
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_MAX_FUTURE_DAYS = 365


class PAServiceDateValidator(BaseValidator):
    """Validates service dates on PA request service lines."""

    name = "PAServiceDateValidator"

    def validate(self, request) -> ValidatorOutput:  # type: ignore[override]
        findings: list[Finding] = []
        today = date.today()
        max_future = today + timedelta(days=_MAX_FUTURE_DAYS)

        for idx, line in enumerate(request.service_lines, start=1):
            # Check from_date
            if line.from_date is not None:
                if line.from_date < today:
                    findings.append(
                        self._make_finding(
                            code="PA_SERVICE_DATE_PAST",
                            message=(
                                "Service date in 'from_date' on service line "
                                f"{idx} must not be in the past"
                            ),
                            severity=Severity.ERROR,
                            field_name="service_lines[].from_date",
                            line_number=idx,
                            suggestion=(
                                "Prior authorization requests should have "
                                "future service dates"
                            ),
                        )
                    )
                elif line.from_date > max_future:
                    findings.append(
                        self._make_finding(
                            code="PA_SERVICE_DATE_FUTURE",
                            message=(
                                "Service date in 'from_date' on service line "
                                f"{idx} is more than 365 days in the future"
                            ),
                            severity=Severity.WARNING,
                            field_name="service_lines[].from_date",
                            line_number=idx,
                            suggestion=(
                                "Verify the service date is correct — most "
                                "PAs are requested within a year"
                            ),
                        )
                    )

            # Check to_date > from_date (range validity)
            if (
                line.from_date is not None
                and line.to_date is not None
                and line.to_date < line.from_date
            ):
                findings.append(
                    self._make_finding(
                        code="PA_SERVICE_DATE_RANGE_INVALID",
                        message=(
                            "Service date 'to_date' on service line "
                            f"{idx} must not be before 'from_date'"
                        ),
                        severity=Severity.ERROR,
                        field_name="service_lines[].to_date",
                        line_number=idx,
                        suggestion="Ensure to_date is on or after from_date",
                    )
                )

        return self._make_output(findings)
