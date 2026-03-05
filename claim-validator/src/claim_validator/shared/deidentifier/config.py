"""De-identification configuration — specifies PHI field categories per domain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeidentificationConfig:
    """Immutable configuration specifying which fields contain PHI.

    Each field tuple lists the dict keys that should be stripped/transformed
    during de-identification.  The base class handles stripping; domain
    subclasses only set the config.

    Attributes:
        name_fields: Fields containing person names — set to None.
        date_fields: Fields containing dates — reduced to year-only int.
        id_fields: Fields containing identifiers (SSN, member ID, etc.) — set to None.
        address_fields: Fields containing address components — set to None.
        age_field: Field containing DOB string for age computation with 90+ cap.
                   Set to None if domain has no DOB field.
    """

    name_fields: tuple[str, ...] = ()
    date_fields: tuple[str, ...] = ()
    id_fields: tuple[str, ...] = ()
    address_fields: tuple[str, ...] = ()
    age_field: str | None = None

    def __post_init__(self) -> None:
        """Validate that age_field does not overlap with date_fields."""
        if self.age_field and self.age_field in self.date_fields:
            msg = (
                f"age_field '{self.age_field}' must not also appear in date_fields "
                f"— age computation requires the raw DOB value"
            )
            raise ValueError(msg)


# --- Domain Configs ---

CLAIM_DEID_CONFIG = DeidentificationConfig(
    name_fields=("patient_first_name", "patient_last_name"),
    date_fields=("service_date_from", "service_date_to"),
    id_fields=("subscriber_id",),
    address_fields=(
        "patient_address",
        "patient_city",
        "patient_state",
        "patient_zip",
    ),
    age_field="patient_dob",
)

ELIGIBILITY_DEID_CONFIG = DeidentificationConfig(
    name_fields=("subscriber_name",),
    date_fields=("effective_date", "termination_date"),
    id_fields=("member_id", "group_number"),
    address_fields=(),
    age_field=None,
)

PA_DEID_CONFIG = DeidentificationConfig(
    name_fields=("patient_name",),
    date_fields=("effective_date", "expiration_date"),
    id_fields=("authorization_number", "member_id"),
    address_fields=("patient_address",),
    age_field="patient_dob",
)
