"""Tests for PriorAuthPipeline."""

from __future__ import annotations

import time
from datetime import date, timedelta

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)
from claim_validator.prior_auth.pipeline import PriorAuthPipeline


def _valid_request() -> PriorAuthRequest:
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=["J06.9"],
        service_lines=[
            ServiceLine(
                cpt_code="99213",
                from_date=date.today() + timedelta(days=10),
            ),
        ],
    )


class TestPriorAuthPipelineBasic:
    """AC6, AC9: Pipeline executes phase 1, returns PriorAuthResult."""

    def test_valid_request_passes(self) -> None:
        pipeline = PriorAuthPipeline.from_settings()
        result = pipeline.run(_valid_request())
        assert result.passed is True
        assert len(result.findings) == 0
        assert result.approved is None
        assert result.response is None
        assert result.ai_summary is None

    def test_execution_time_tracked(self) -> None:
        pipeline = PriorAuthPipeline.from_settings()
        result = pipeline.run(_valid_request())
        assert result.execution_time > 0

    def test_from_settings_default(self) -> None:
        pipeline = PriorAuthPipeline.from_settings()
        assert len(pipeline._rule_validators) == 7

    def test_from_settings_explicit(self) -> None:
        settings = ClaimValidatorSettings()
        pipeline = PriorAuthPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 7


class TestPriorAuthPipelineAllValidators:
    """AC7: All 7 validators run, findings aggregated."""

    def test_multiple_issues_aggregated(self) -> None:
        """Request with NPI issue + missing diagnosis → multiple findings."""
        req = PriorAuthRequest(
            requester_npi="1234567890",  # Invalid Luhn
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            diagnosis_codes=[],  # Empty diagnosis
            service_lines=[
                ServiceLine(
                    cpt_code="99213",
                    from_date=date.today() + timedelta(days=10),
                ),
            ],
        )
        pipeline = PriorAuthPipeline.from_settings()
        result = pipeline.run(req)
        assert result.passed is False
        # Should have at least NPI error + dx mismatch warning
        codes = [f.code for f in result.findings]
        assert "PA_INVALID_NPI" in codes
        assert "PA_DX_PROCEDURE_MISMATCH" in codes

    def test_passed_false_on_errors(self) -> None:
        """passed=False when any ERROR-severity finding exists."""
        req = PriorAuthRequest(
            requester_npi="1234567890",  # Invalid Luhn
            subscriber=SubscriberInfo(
                member_id="MEM001",
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
            diagnosis_codes=["J06.9"],
            service_lines=[
                ServiceLine(
                    cpt_code="99213",
                    from_date=date.today() + timedelta(days=10),
                ),
            ],
        )
        pipeline = PriorAuthPipeline.from_settings()
        result = pipeline.run(req)
        assert result.passed is False


class TestPriorAuthPipelineSkipValidators:
    """AC10: Custom validator config excludes specific validators."""

    def test_custom_validators(self) -> None:
        """Only NPI validator → only NPI findings."""
        settings = ClaimValidatorSettings(
            pa_rule_validators=[
                "claim_validator.prior_auth.validators.rule_based.npi.PANPIValidator",
            ]
        )
        pipeline = PriorAuthPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 1

        req = PriorAuthRequest(
            requester_npi="1234567890",  # Invalid Luhn
            subscriber=SubscriberInfo(
                member_id="",  # Empty — but member_id validator not loaded
                first_name="Jane",
                last_name="Doe",
                dob=date(1985, 3, 15),
            ),
        )
        result = pipeline.run(req)
        codes = [f.code for f in result.findings]
        assert "PA_INVALID_NPI" in codes
        assert "PA_MISSING_MEMBER_ID" not in codes


class TestPriorAuthPipelinePerformance:
    """AC12: All 7 validators < 100ms."""

    def test_under_100ms(self) -> None:
        pipeline = PriorAuthPipeline.from_settings()
        req = _valid_request()
        # Warm up
        pipeline.run(req)
        # Timed run
        start = time.perf_counter()
        for _ in range(100):
            pipeline.run(req)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms < 100, (
            f"Pipeline took {elapsed_ms:.1f}ms (limit: 100ms)"
        )
