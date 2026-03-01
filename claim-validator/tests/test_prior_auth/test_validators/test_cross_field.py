"""Tests for PACrossFieldValidator."""

from __future__ import annotations

from datetime import date

from claim_validator.prior_auth.models.request import (
    PatientInfo,
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)
from claim_validator.prior_auth.validators.rule_based.cross_field import (
    PACrossFieldValidator,
)


def _make_request(
    diagnosis_codes: list[str] | None = None,
    cpt_codes: list[str] | None = None,
    gender: str | None = None,
    patient_dob: date | None = None,
    subscriber_dob: date = date(1985, 3, 15),
) -> PriorAuthRequest:
    patient = None
    if gender is not None or patient_dob is not None:
        patient = PatientInfo(
            first_name="Jane",
            last_name="Doe",
            dob=patient_dob or date(1985, 3, 15),
            gender=gender,
        )
    service_lines = [ServiceLine(cpt_code=c) for c in (cpt_codes or [])]
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=subscriber_dob,
        ),
        patient=patient,
        diagnosis_codes=diagnosis_codes or [],
        service_lines=service_lines,
    )


class TestPACrossFieldValidatorValid:
    """No mismatch cases → zero findings."""

    def test_no_findings_when_valid(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(diagnosis_codes=["J06.9"], cpt_codes=["99213"])
        )
        assert len(result.findings) == 0

    def test_no_findings_empty_service_lines(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(_make_request(diagnosis_codes=["J06.9"], cpt_codes=[]))
        assert len(result.findings) == 0

    def test_no_findings_no_patient(self) -> None:
        """No patient → gender/age checks skipped gracefully."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(diagnosis_codes=["J06.9"], cpt_codes=["99213"])
        )
        assert len(result.findings) == 0

    def test_validator_name(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(diagnosis_codes=["J06.9"], cpt_codes=["99213"])
        )
        assert result.validator_name == "PACrossFieldValidator"


class TestPACrossFieldValidatorDxProcedureMismatch:
    """AC4: No diagnosis with procedures → PA_DX_PROCEDURE_MISMATCH."""

    def test_procedures_without_diagnosis(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(_make_request(diagnosis_codes=[], cpt_codes=["99213"]))
        dx_findings = [
            f for f in result.findings if f.code == "PA_DX_PROCEDURE_MISMATCH"
        ]
        assert len(dx_findings) == 1
        assert dx_findings[0].severity.value == "warning"
        assert dx_findings[0].field_name == "diagnosis_codes"
        assert len(dx_findings[0].suggestion) > 0

    def test_has_diagnosis_no_mismatch(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(diagnosis_codes=["J06.9"], cpt_codes=["99213"])
        )
        dx_findings = [
            f for f in result.findings if f.code == "PA_DX_PROCEDURE_MISMATCH"
        ]
        assert len(dx_findings) == 0


class TestPACrossFieldValidatorGenderMismatch:
    """AC5: Gender incompatible with procedure → PA_DEMOGRAPHIC_PROCEDURE_MISMATCH."""

    def test_male_with_ob_procedure(self) -> None:
        """Male patient with OB/maternity CPT → mismatch."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["O80"],
                cpt_codes=["59400"],
                gender="M",
            )
        )
        gender_findings = [
            f for f in result.findings if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
        ]
        assert len(gender_findings) >= 1
        assert gender_findings[0].severity.value == "warning"
        assert gender_findings[0].field_name == "patient.gender"

    def test_female_with_prostate_procedure(self) -> None:
        """Female patient with prostate CPT → mismatch."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["N40.0"],
                cpt_codes=["55700"],
                gender="F",
            )
        )
        gender_findings = [
            f for f in result.findings if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
        ]
        assert len(gender_findings) >= 1

    def test_female_with_ob_procedure_no_mismatch(self) -> None:
        """Female patient with OB procedure → no gender mismatch."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["O80"],
                cpt_codes=["59400"],
                gender="F",
            )
        )
        gender_findings = [
            f
            for f in result.findings
            if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
            and "gender" in f.field_name
        ]
        assert len(gender_findings) == 0

    def test_no_gender_no_mismatch(self) -> None:
        """No gender specified → skip gender check."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["O80"],
                cpt_codes=["59400"],
                gender=None,
            )
        )
        gender_findings = [
            f
            for f in result.findings
            if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
            and "gender" in f.field_name
        ]
        assert len(gender_findings) == 0


class TestPACrossFieldValidatorAgeMismatch:
    """AC5: Age incompatible with procedure → PA_DEMOGRAPHIC_PROCEDURE_MISMATCH."""

    def test_adult_with_pediatric_code(self) -> None:
        """Adult (age 40) with pediatric well-visit code → mismatch."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["Z00.129"],
                cpt_codes=["99383"],
                subscriber_dob=date(1985, 1, 1),
            )
        )
        age_findings = [
            f
            for f in result.findings
            if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
            and "dob" in f.field_name
        ]
        assert len(age_findings) >= 1
        assert age_findings[0].severity.value == "warning"

    def test_child_with_pediatric_code_no_mismatch(self) -> None:
        """Child (age 10) with pediatric code → no mismatch."""
        v = PACrossFieldValidator()
        child_dob = date(date.today().year - 10, 1, 1)
        result = v.validate(
            _make_request(
                diagnosis_codes=["Z00.129"],
                cpt_codes=["99383"],
                subscriber_dob=child_dob,
            )
        )
        age_findings = [
            f
            for f in result.findings
            if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
            and "dob" in f.field_name
        ]
        assert len(age_findings) == 0

    def test_non_numeric_cpt_skipped(self) -> None:
        """Non-numeric CPT code (HCPCS letter prefix) skips age check."""
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["J06.9"],
                cpt_codes=["A4206"],
                subscriber_dob=date(1985, 1, 1),
            )
        )
        age_findings = [
            f
            for f in result.findings
            if f.code == "PA_DEMOGRAPHIC_PROCEDURE_MISMATCH"
            and "dob" in f.field_name
        ]
        assert len(age_findings) == 0


class TestPACrossFieldValidatorPHISafety:
    """AC15: No PHI in finding messages."""

    def test_no_phi_in_dx_mismatch(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(_make_request(diagnosis_codes=[], cpt_codes=["99213"]))
        for f in result.findings:
            assert "99213" not in f.message
            assert "Jane" not in f.message

    def test_no_phi_in_gender_mismatch(self) -> None:
        v = PACrossFieldValidator()
        result = v.validate(
            _make_request(
                diagnosis_codes=["O80"],
                cpt_codes=["59400"],
                gender="M",
            )
        )
        for f in result.findings:
            assert "59400" not in f.message
            assert "M" not in f.field_name or f.field_name == "patient.gender"
