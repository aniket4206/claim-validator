"""Tests for de-identified prior authorization models."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.models.deidentified import (
    DeidentifiedPriorAuthResponse,
)


class TestDeidentifiedPriorAuthResponse:
    def test_create_empty(self) -> None:
        resp = DeidentifiedPriorAuthResponse()
        assert resp.action_code is None
        assert resp.decision_reason_code is None
        assert resp.decision_reason_description is None
        assert resp.service_type_codes == []
        assert resp.cpt_codes == []
        assert resp.aaa_reject_codes == []
        assert resp.raw_safe_fields is None

    def test_create_with_all_fields(self) -> None:
        resp = DeidentifiedPriorAuthResponse(
            action_code=CertificationActionCode.CERTIFIED_IN_TOTAL,
            decision_reason_code="01",
            decision_reason_description="Approved",
            service_type_codes=["1", "2"],
            cpt_codes=["27447"],
            aaa_reject_codes=[],
            raw_safe_fields={"key": "value"},
        )
        assert resp.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert resp.decision_reason_code == "01"
        assert len(resp.service_type_codes) == 2
        assert resp.cpt_codes == ["27447"]
        assert resp.raw_safe_fields == {"key": "value"}

    def test_frozen(self) -> None:
        resp = DeidentifiedPriorAuthResponse()
        with pytest.raises(pydantic.ValidationError):
            resp.action_code = CertificationActionCode.NOT_CERTIFIED  # type: ignore[misc]

    def test_no_phi_fields(self) -> None:
        """Verify the stub model has no fields that could contain PHI."""
        phi_field_names = {
            "member_id",
            "subscriber_id",
            "first_name",
            "last_name",
            "dob",
            "date_of_birth",
            "ssn",
            "address",
            "phone",
            "authorization_number",
            "patient_name",
        }
        model_fields = set(DeidentifiedPriorAuthResponse.model_fields.keys())
        overlap = phi_field_names & model_fields
        assert overlap == set(), f"PHI fields found in deidentified model: {overlap}"
