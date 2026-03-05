"""ClaimDeidentifier — HIPAA Safe Harbor de-identification.

Delegates year extraction to ``BaseDeidentifier``.  Age computation
uses module-level ``datetime`` for test mockability.
"""

from __future__ import annotations

import datetime

from claim_validator.models.claim import ClaimData, ClaimLineData
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)
from claim_validator.shared.deidentifier import (
    CLAIM_DEID_CONFIG,
    BaseDeidentifier,
)

# Safe Harbor age cap: ages 90+ reported as 90
_SAFE_HARBOR_AGE_CAP = 90

_base = BaseDeidentifier(CLAIM_DEID_CONFIG)


class ClaimDeidentifier:
    """Strips all 18 HIPAA identifiers from a ClaimData instance.

    Stateless — safe for concurrent use, deterministic output.
    """

    @classmethod
    def deidentify(cls, claim: ClaimData) -> DeidentifiedClaim:
        """De-identify a claim for LLM consumption.

        Strips: names, dates (except year), subscriber ID.
        Retains: NPI, codes, charges, gender, payer ID, age.
        Ages 90+ capped to 90 per HIPAA Safe Harbor.
        """
        patient_age = cls._compute_age(claim.patient_dob)

        lines = [cls._deidentify_line(line) for line in claim.lines]

        diagnosis_codes: list[dict[str, str | int]] = [
            {"code": dx.code, "pointer": dx.pointer}
            for dx in claim.diagnosis_codes
        ]

        return DeidentifiedClaim(
            billing_provider_npi=claim.billing_provider_npi,
            billing_provider_taxonomy=claim.billing_provider_taxonomy,
            rendering_provider_npi=claim.rendering_provider_npi,
            patient_age=patient_age,
            patient_gender=claim.patient_gender,
            payer_id=claim.payer_id,
            payer_name=claim.payer_name,
            claim_type=claim.claim_type,
            place_of_service=claim.place_of_service,
            total_charge=claim.total_charge,
            diagnosis_codes=diagnosis_codes,
            lines=lines,
        )

    @classmethod
    def _deidentify_line(
        cls,
        line: ClaimLineData,
    ) -> DeidentifiedLineData:
        """Strip PHI from a single claim line."""
        service_year = _base.extract_year(line.service_date_from)
        return DeidentifiedLineData(
            procedure_code=line.procedure_code,
            modifiers=list(line.modifiers),
            diagnosis_pointers=list(line.diagnosis_pointers),
            charge_amount=line.charge_amount,
            units=line.units,
            place_of_service=line.place_of_service,
            rendering_provider_npi=line.rendering_provider_npi,
            service_year=service_year,
        )

    @staticmethod
    def _compute_age(dob_str: str | None) -> int | None:
        """Convert DOB string to age, capped at 90.

        Uses module-level ``datetime`` for test mock compatibility.
        """
        if not dob_str:
            return None
        try:
            dob = datetime.date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            return None
        today = datetime.date.today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
        return min(age, _SAFE_HARBOR_AGE_CAP)
