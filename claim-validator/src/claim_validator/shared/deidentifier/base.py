"""BaseDeidentifier — HIPAA Safe Harbor de-identification engine."""

from __future__ import annotations

import datetime
from typing import Any

from claim_validator.shared.deidentifier.config import DeidentificationConfig

_SAFE_HARBOR_AGE_CAP = 90


class BaseDeidentifier:
    """Base de-identifier — strips 18 HIPAA identifiers per domain config.

    Subclasses set config in ``__init__()``, never override ``deidentify()``.
    """

    def __init__(self, config: DeidentificationConfig) -> None:
        self._config = config

    @property
    def config(self) -> DeidentificationConfig:
        """The de-identification configuration."""
        return self._config

    def deidentify(self, data: dict[str, Any]) -> dict[str, Any]:
        """Strip PHI from a data dict per config.

        Args:
            data: Input data dict (e.g. from ``model_dump()``).

        Returns:
            New dict with PHI fields stripped/transformed.
            Original dict is NOT mutated.
        """
        result = {**data}  # shallow copy — never mutate input

        self._strip_names(result, self._config.name_fields)
        self._strip_ids(result, self._config.id_fields)
        self._strip_addresses(result, self._config.address_fields)
        self._reduce_dates(result, self._config.date_fields)

        if self._config.age_field and self._config.age_field in result:
            self._cap_age(result, self._config.age_field)

        return result

    @staticmethod
    def _strip_names(data: dict[str, Any], fields: tuple[str, ...]) -> None:
        """Set name fields to None."""
        for field in fields:
            if field in data:
                data[field] = None

    @staticmethod
    def _strip_ids(data: dict[str, Any], fields: tuple[str, ...]) -> None:
        """Set identifier fields to None."""
        for field in fields:
            if field in data:
                data[field] = None

    @staticmethod
    def _strip_addresses(data: dict[str, Any], fields: tuple[str, ...]) -> None:
        """Set address fields to None."""
        for field in fields:
            if field in data:
                data[field] = None

    @staticmethod
    def _reduce_dates(data: dict[str, Any], fields: tuple[str, ...]) -> None:
        """Convert date fields to year-only int or None."""
        for field in fields:
            if field in data:
                data[field] = BaseDeidentifier.extract_year(data[field])

    @staticmethod
    def _cap_age(data: dict[str, Any], age_field: str) -> None:
        """Compute age from DOB string and cap at 90 per HIPAA Safe Harbor."""
        data[age_field] = BaseDeidentifier.compute_age(data[age_field])

    @staticmethod
    def extract_year(date_value: str | datetime.date | None) -> int | None:
        """Extract year from a date string or date object.

        Returns None if input is None or unparseable.
        """
        if date_value is None:
            return None
        if isinstance(date_value, datetime.date):
            return date_value.year
        try:
            return datetime.date.fromisoformat(date_value).year
        except (ValueError, TypeError):
            return None

    @staticmethod
    def compute_age(dob_str: str | None) -> int | None:
        """Compute age from DOB string, capped at 90 per HIPAA Safe Harbor.

        Returns None if input is None or unparseable.
        """
        if not dob_str:
            return None
        try:
            dob = datetime.date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            return None
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 0:
            return None
        return min(age, _SAFE_HARBOR_AGE_CAP)
