"""De-identified claim model — DeidentifiedClaim."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeidentifiedLineData(BaseModel):
    """De-identified service line — dates replaced with year only."""

    model_config = ConfigDict(frozen=True, strict=False)

    procedure_code: str
    modifiers: list[str] = []
    diagnosis_pointers: list[int] = []
    charge_amount: float
    units: float = 1.0
    place_of_service: str | None = None
    rendering_provider_npi: str | None = None
    service_year: int | None = None


class DeidentifiedClaim(BaseModel):
    """HIPAA Safe Harbor de-identified claim.

    Contains only clinically relevant, non-PHI data
    suitable for LLM consumption. Created exclusively
    by ``ClaimDeidentifier.deidentify()``.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    # Provider (NPI is public, not PHI)
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    rendering_provider_npi: str | None = None

    # Demographics (de-identified)
    patient_age: int | None = None  # Capped at 90 per Safe Harbor
    patient_gender: str | None = None

    # Payer (organization identifier, not PHI)
    payer_id: str | None = None
    payer_name: str | None = None

    # Claim metadata
    claim_type: str = "professional"
    place_of_service: str | None = None
    total_charge: float | None = None

    # Clinical data (codes are not PHI)
    diagnosis_codes: list[dict[str, str | int]] = []
    lines: list[DeidentifiedLineData] = []

    @property
    def is_deidentified(self) -> Literal[True]:
        """Type-level marker that this claim is de-identified."""
        return True
