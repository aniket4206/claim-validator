"""Tests for DemographicsValidator — patient demographics consistency."""

from __future__ import annotations

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.rule_based.demographics import DemographicsValidator


def _valid_claim_dict() -> dict:
    """Minimal claim dict with valid demographics."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "payer_id": "BCBS001",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ],
    }


# --- Valid demographics ---


class TestDemographicsValidatorValid:
    """Tests for valid demographics producing zero findings."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_valid_demographics_zero_findings(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert result.findings == []

    def test_validator_name(self) -> None:
        assert self.validator.name == "DemographicsValidator"

    def test_valid_dob_1990(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "1990-01-15"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert dob_findings == []

    def test_valid_dob_2000(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "2000-12-31"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert dob_findings == []


# --- DOB validation ---


class TestDemographicsValidatorDOB:
    """Tests for date of birth validation."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_future_dob_produces_finding(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "2099-01-01"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "FUTURE_DOB"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "patient_dob"

    def test_invalid_dob_format_not_a_date(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "not-a-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_DOB_FORMAT"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "patient_dob"

    def test_invalid_dob_format_wrong_order(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "13/01/1990"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_DOB_FORMAT"]
        assert len(findings) == 1

    def test_invalid_dob_format_mm_dd_yyyy(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "01-15-1990"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_DOB_FORMAT"]
        assert len(findings) == 1

    def test_none_patient_dob_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert dob_findings == []

    def test_empty_patient_dob_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = ""
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert dob_findings == []

    def test_whitespace_patient_dob_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "   "
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert dob_findings == []

    def test_invalid_format_does_not_also_produce_future_dob(self) -> None:
        """Format check short-circuits — no future check if format is wrong."""
        data = _valid_claim_dict()
        data["patient_dob"] = "not-a-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        dob_findings = [
            f for f in result.findings if f.code in ("INVALID_DOB_FORMAT", "FUTURE_DOB")
        ]
        assert len(dob_findings) == 1
        assert dob_findings[0].code == "INVALID_DOB_FORMAT"

    def test_dob_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "not-a-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_DOB_FORMAT"]
        assert findings[0].suggestion != ""


# --- Gender validation ---


class TestDemographicsValidatorGender:
    """Tests for patient gender validation."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_valid_gender_m(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "M"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_valid_gender_f(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "F"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_valid_gender_u(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "U"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_valid_gender_lowercase_m(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "m"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_valid_gender_lowercase_f(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "f"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_valid_gender_lowercase_u(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "u"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_invalid_gender_x(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "X"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].field_name == "patient_gender"

    def test_invalid_gender_male(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "male"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert len(findings) == 1

    def test_none_patient_gender_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_empty_patient_gender_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = ""
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        gender_findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert gender_findings == []

    def test_gender_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "X"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [f for f in result.findings if f.code == "INVALID_GENDER"]
        assert findings[0].suggestion != ""


# --- Self-relationship validation ---


class TestDemographicsValidatorRelationship:
    """Tests for self-relationship name consistency."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_self_relationship_matching_names_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "Jane"
        data["subscriber_last_name"] = "Doe"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_self_relationship_matching_names_case_insensitive(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "JANE"
        data["subscriber_last_name"] = "DOE"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_self_relationship_differing_names_produces_warning(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].field_name == "patient_relationship"

    def test_self_relationship_differing_first_name_only(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Doe"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert len(findings) == 1

    def test_self_relationship_no_subscriber_names_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        # No subscriber names provided — can't compare
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_self_relationship_no_patient_names_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "Jane"
        data["subscriber_last_name"] = "Doe"
        data["patient_first_name"] = None
        data["patient_last_name"] = None
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_non_self_relationship_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "spouse"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_none_relationship_no_findings(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = None
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        rel_findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert rel_findings == []

    def test_self_relationship_case_insensitive_keyword(self) -> None:
        """'Self' (capitalized) should also trigger the check."""
        data = _valid_claim_dict()
        data["patient_relationship"] = "Self"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert len(findings) == 1

    def test_relationship_suggestion_present(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        findings = [
            f for f in result.findings if f.code == "SELF_RELATIONSHIP_MISMATCH"
        ]
        assert findings[0].suggestion != ""


# --- Finding quality ---


class TestDemographicsValidatorFindings:
    """Tests for finding quality — no PHI, correct fields."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_no_phi_in_dob_messages(self) -> None:
        data = _valid_claim_dict()
        data["patient_dob"] = "not-a-date"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "not-a-date" not in finding.message
            assert "not-a-date" not in finding.suggestion

    def test_no_phi_in_gender_messages(self) -> None:
        data = _valid_claim_dict()
        data["patient_gender"] = "male"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "male" not in finding.message.lower()

    def test_no_phi_in_relationship_messages(self) -> None:
        data = _valid_claim_dict()
        data["patient_relationship"] = "self"
        data["subscriber_first_name"] = "John"
        data["subscriber_last_name"] = "Smith"
        claim = ClaimData(**data)
        result = self.validator.validate(claim)
        for finding in result.findings:
            assert "Jane" not in finding.message
            assert "Doe" not in finding.message
            assert "John" not in finding.message
            assert "Smith" not in finding.message


# --- Statelessness ---


class TestDemographicsValidatorStatelessness:
    """Tests for stateless validator behavior."""

    def setup_method(self) -> None:
        self.validator = DemographicsValidator()

    def test_multiple_calls_independent(self) -> None:
        good = ClaimData(**_valid_claim_dict())
        bad_data = _valid_claim_dict()
        bad_data["patient_dob"] = "not-a-date"
        bad = ClaimData(**bad_data)

        r1 = self.validator.validate(good)
        r2 = self.validator.validate(bad)
        r3 = self.validator.validate(good)

        assert r1.findings == []
        assert len(r2.findings) >= 1
        assert r3.findings == []

    def test_returns_validator_output(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = self.validator.validate(claim)
        assert isinstance(result, ValidatorOutput)
        assert result.validator_name == "DemographicsValidator"

    def test_claim_not_modified(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        self.validator.validate(claim)
        assert claim.patient_dob == "1990-01-15"
        assert claim.patient_gender == "F"
