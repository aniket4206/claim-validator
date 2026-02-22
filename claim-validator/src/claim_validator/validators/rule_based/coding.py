"""CodingValidator — diagnosis/procedure code validation."""

from __future__ import annotations

import re

from claim_validator.code_tables import lookup_hcpcs, lookup_icd10
from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_ICD10_PATTERN = re.compile(r"^[A-Za-z]\d{2}(\.\d{1,4})?$")
_PROCEDURE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{5}$")
_MODIFIER_PATTERN = re.compile(r"^[A-Za-z0-9]{2}$")


class CodingValidator(BaseValidator):
    """Validates diagnosis codes, procedure codes, modifiers,
    and diagnosis pointer consistency."""

    name = "CodingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_diagnosis_codes(claim, findings)
        self._check_procedure_codes(claim, findings)
        self._check_modifiers(claim, findings)
        self._check_diagnosis_pointers(claim, findings)
        self._check_unreferenced_diagnoses(claim, findings)

        return self._make_output(findings)

    def _check_diagnosis_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes:
            return

        for i, dx in enumerate(claim.diagnosis_codes, start=1):
            code = dx.code.strip() if dx.code else ""
            if not code:
                continue

            if not _ICD10_PATTERN.match(code):
                findings.append(
                    self._make_finding(
                        code="INVALID_DIAGNOSIS_CODE_FORMAT",
                        message=(
                            f"Diagnosis code at position {i} in"
                            " 'diagnosis_codes' has invalid"
                            " format"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "ICD-10-CM codes must start with a"
                            " letter followed by 2+ digits"
                            " (e.g., J06.9)"
                        ),
                    )
                )
                continue

            if lookup_icd10(code) is None:
                findings.append(
                    self._make_finding(
                        code="INVALID_DIAGNOSIS_CODE",
                        message=(
                            f"Diagnosis code at position {i} in"
                            " 'diagnosis_codes' not found in"
                            " bundled ICD-10-CM table"
                        ),
                        severity=Severity.ERROR,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "Verify the ICD-10-CM code against"
                            " the current CMS code set"
                        ),
                    )
                )

    def _check_procedure_codes(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.lines:
            return

        for idx, line in enumerate(claim.lines, start=1):
            code = line.procedure_code.strip()
            if not code:
                continue

            if not _PROCEDURE_CODE_PATTERN.match(code):
                findings.append(
                    self._make_finding(
                        code="INVALID_PROCEDURE_CODE_FORMAT",
                        message=(
                            "Procedure code in"
                            " 'procedure_code' must be"
                            " exactly 5 alphanumeric"
                            " characters"
                        ),
                        severity=Severity.ERROR,
                        field_name="procedure_code",
                        line_number=idx,
                        suggestion=(
                            "CPT codes are 5 digits"
                            " (e.g., 99213). HCPCS codes"
                            " are letter + 4 digits"
                            " (e.g., J0120)"
                        ),
                    )
                )
                continue

            if lookup_hcpcs(code) is None:
                findings.append(
                    self._make_finding(
                        code="INVALID_PROCEDURE_CODE",
                        message=(
                            "Procedure code in"
                            " 'procedure_code' not found"
                            " in bundled CPT/HCPCS table"
                        ),
                        severity=Severity.ERROR,
                        field_name="procedure_code",
                        line_number=idx,
                        suggestion=(
                            "Verify the CPT/HCPCS code"
                            " against the current code set"
                        ),
                    )
                )

    def _check_modifiers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        for idx, line in enumerate(claim.lines, start=1):
            for mod in line.modifiers:
                mod_stripped = mod.strip() if mod else ""
                if not mod_stripped:
                    continue

                if not _MODIFIER_PATTERN.match(mod_stripped):
                    findings.append(
                        self._make_finding(
                            code="INVALID_MODIFIER_FORMAT",
                            message=(
                                "Modifier in 'modifiers' must"
                                " be exactly 2 alphanumeric"
                                " characters"
                            ),
                            severity=Severity.ERROR,
                            field_name="modifiers",
                            line_number=idx,
                            suggestion=(
                                "Modifiers are 2-character"
                                " codes (e.g., 25, 59, TC)"
                            ),
                        )
                    )

    def _check_diagnosis_pointers(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        valid_pointers = {
            dx.pointer for dx in claim.diagnosis_codes
        }

        for idx, line in enumerate(claim.lines, start=1):
            for ptr in line.diagnosis_pointers:
                if ptr not in valid_pointers:
                    findings.append(
                        self._make_finding(
                            code="INVALID_DIAGNOSIS_POINTER",
                            message=(
                                "Diagnosis pointer in"
                                " 'diagnosis_pointers'"
                                " references a non-existent"
                                " diagnosis position"
                            ),
                            severity=Severity.ERROR,
                            field_name="diagnosis_pointers",
                            line_number=idx,
                            suggestion=(
                                "Each diagnosis pointer must"
                                " reference a valid pointer"
                                " value in the claim's"
                                " diagnosis codes"
                            ),
                        )
                    )

    def _check_unreferenced_diagnoses(
        self, claim: ClaimData, findings: list[Finding],
    ) -> None:
        if not claim.diagnosis_codes or not claim.lines:
            return

        referenced_pointers: set[int] = set()
        for line in claim.lines:
            referenced_pointers.update(line.diagnosis_pointers)

        for dx in claim.diagnosis_codes:
            if dx.pointer not in referenced_pointers:
                findings.append(
                    self._make_finding(
                        code="UNREFERENCED_DIAGNOSIS",
                        message=(
                            "Diagnosis code in"
                            " 'diagnosis_codes' is not"
                            " referenced by any service"
                            " line"
                        ),
                        severity=Severity.WARNING,
                        field_name="diagnosis_codes",
                        suggestion=(
                            "Each diagnosis code should be"
                            " referenced by at least one"
                            " service line via"
                            " diagnosis_pointers"
                        ),
                    )
                )
