"""Tests for PA validator re-exports, config, PHI safety, and performance."""

from __future__ import annotations

import time
from datetime import date, timedelta

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)

# ── Re-exports ────────────────────────────────────────────────


class TestReExports:
    """AC12: Validators importable from prior_auth.validators."""

    def test_import_from_rule_based(self) -> None:
        from claim_validator.prior_auth.validators.rule_based import (
            PACrossFieldValidator,
            PADateOfBirthValidator,
            PADiagnosisValidator,
            PAMemberIDValidator,
            PANPIValidator,
            PAProcedureValidator,
            PAServiceDateValidator,
        )

        assert all(
            callable(cls)
            for cls in [
                PACrossFieldValidator,
                PADateOfBirthValidator,
                PADiagnosisValidator,
                PAMemberIDValidator,
                PANPIValidator,
                PAProcedureValidator,
                PAServiceDateValidator,
            ]
        )

    def test_import_from_validators(self) -> None:
        from claim_validator.prior_auth.validators import (
            PACrossFieldValidator,
            PADateOfBirthValidator,
            PADiagnosisValidator,
            PAMemberIDValidator,
            PANPIValidator,
            PAProcedureValidator,
            PAServiceDateValidator,
        )

        assert all(
            callable(cls)
            for cls in [
                PACrossFieldValidator,
                PADateOfBirthValidator,
                PADiagnosisValidator,
                PAMemberIDValidator,
                PANPIValidator,
                PAProcedureValidator,
                PAServiceDateValidator,
            ]
        )

    def test_rule_based_all(self) -> None:
        import claim_validator.prior_auth.validators.rule_based as rb

        expected = {
            "PACrossFieldValidator",
            "PADateOfBirthValidator",
            "PADiagnosisValidator",
            "PAMemberIDValidator",
            "PANPIValidator",
            "PAProcedureValidator",
            "PAServiceDateValidator",
        }
        assert expected.issubset(set(rb.__all__))

    def test_validators_all(self) -> None:
        import claim_validator.prior_auth.validators as pv

        expected = {
            "PACrossFieldValidator",
            "PADateOfBirthValidator",
            "PADiagnosisValidator",
            "PAMemberIDValidator",
            "PANPIValidator",
            "PAProcedureValidator",
            "PAServiceDateValidator",
        }
        assert expected.issubset(set(pv.__all__))


# ── Default config ────────────────────────────────────────────


class TestDefaultConfig:
    """AC12: DEFAULT_PA_RULE_VALIDATORS contains all 7 validator paths."""

    def test_all_seven_validators_in_defaults(self) -> None:
        from claim_validator.conf import DEFAULT_PA_RULE_VALIDATORS

        assert len(DEFAULT_PA_RULE_VALIDATORS) == 7

    def test_each_path_present(self) -> None:
        from claim_validator.conf import DEFAULT_PA_RULE_VALIDATORS

        expected_names = [
            "PACrossFieldValidator",
            "PADateOfBirthValidator",
            "PADiagnosisValidator",
            "PAMemberIDValidator",
            "PANPIValidator",
            "PAProcedureValidator",
            "PAServiceDateValidator",
        ]
        for name in expected_names:
            assert any(name in path for path in DEFAULT_PA_RULE_VALIDATORS), (
                f"{name} not found in DEFAULT_PA_RULE_VALIDATORS"
            )

    def test_settings_uses_defaults(self) -> None:
        from claim_validator.conf import ClaimValidatorSettings

        settings = ClaimValidatorSettings()
        assert len(settings.pa_rule_validators) == 7


# ── PHI safety (cross-validator) ─────────────────────────────


class TestPHISafety:
    """AC11: No PHI values in any finding message across all validators."""

    def test_no_phi_in_npi_findings(self) -> None:
        from claim_validator.prior_auth.validators.rule_based.npi import PANPIValidator

        v = PANPIValidator()
        npi = "1234567890"
        req = PriorAuthRequest(
            requester_npi=npi,
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
        )
        result = v.validate(req)
        for f in result.findings:
            assert npi not in f.message

    def test_no_phi_in_member_id_findings(self) -> None:
        from claim_validator.prior_auth.validators.rule_based.member_id import (
            PAMemberIDValidator,
        )

        v = PAMemberIDValidator()
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=SubscriberInfo(
                member_id="",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
        )
        result = v.validate(req)
        for f in result.findings:
            assert "Jane" not in f.message
            assert "Doe" not in f.message

    def test_no_phi_in_dob_findings(self) -> None:
        from claim_validator.prior_auth.validators.rule_based.date_of_birth import (
            PADateOfBirthValidator,
        )

        v = PADateOfBirthValidator()
        future = date.today() + timedelta(days=30)
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=future,
            ),
        )
        result = v.validate(req)
        for f in result.findings:
            assert str(future) not in f.message

    def test_no_phi_in_diagnosis_findings(self) -> None:
        from claim_validator.prior_auth.validators.rule_based.diagnosis import (
            PADiagnosisValidator,
        )

        v = PADiagnosisValidator()
        bad_code = "ZZZZ"
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            diagnosis_codes=[bad_code],
        )
        result = v.validate(req)
        for f in result.findings:
            assert bad_code not in f.message

    def test_no_phi_in_procedure_findings(self) -> None:
        from claim_validator.prior_auth.validators.rule_based.procedure import (
            PAProcedureValidator,
        )

        v = PAProcedureValidator()
        bad_code = "XX"
        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            service_lines=[ServiceLine(cpt_code=bad_code)],
        )
        result = v.validate(req)
        for f in result.findings:
            assert bad_code not in f.message


# ── Performance (NFR1) ───────────────────────────────────────


class TestPerformance:
    """NFR1: All 7 validators combined < 100ms."""

    def test_all_validators_under_100ms(self) -> None:
        from claim_validator.prior_auth.validators.rule_based import (
            PACrossFieldValidator,
            PADateOfBirthValidator,
            PADiagnosisValidator,
            PAMemberIDValidator,
            PANPIValidator,
            PAProcedureValidator,
            PAServiceDateValidator,
        )

        req = PriorAuthRequest(
            requester_npi="1234567893",
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            diagnosis_codes=["J06.9", "E11.9"],
            service_lines=[
                ServiceLine(
                    cpt_code="99213",
                    from_date=date.today() + timedelta(days=10),
                ),
                ServiceLine(
                    cpt_code="99214",
                    from_date=date.today() + timedelta(days=20),
                ),
            ],
        )
        validators = [
            PACrossFieldValidator(),
            PADateOfBirthValidator(),
            PADiagnosisValidator(),
            PAMemberIDValidator(),
            PANPIValidator(),
            PAProcedureValidator(),
            PAServiceDateValidator(),
        ]
        # Warm up code table caches
        for v in validators:
            v.validate(req)
        # Timed run
        start = time.perf_counter()
        for _ in range(100):
            for v in validators:
                v.validate(req)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms < 100, (
            f"All 7 validators took {elapsed_ms:.1f}ms (limit: 100ms)"
        )
