"""Tests for batch eligibility top-level API function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityResponse,
)
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.eligibility._api import check_eligibility_batch


class TestCheckEligibilityBatch:
    """Verify check_eligibility_batch() delegates to clearinghouse client."""

    def test_delegates_to_client(self) -> None:
        mock_client = MagicMock()
        mock_client.submit_eligibility_batch.return_value = (
            BatchEligibilityResponse(
                batch_id="batch_123", status="processing",
            )
        )

        with patch(
            "claim_validator.clearinghouse.factory.get_clearinghouse_client",
            return_value=mock_client,
        ):
            result = check_eligibility_batch(
                name="test-batch",
                items=[{
                    "payer_id": "AHS", "npi": "123",
                    "subscriber_id": "456", "first_name": "J",
                    "last_name": "D", "dob": "19000101",
                }],
                settings=ClaimValidatorSettings(
                    clearinghouse_config={"provider": "stedi", "api_key": "test"}
                ),
            )

        assert result.batch_id == "batch_123"
        assert result.status == "processing"
        mock_client.submit_eligibility_batch.assert_called_once()

    def test_raises_without_clearinghouse_config(self) -> None:
        with pytest.raises(ValueError, match="clearinghouse_config is required"):
            check_eligibility_batch(
                name="test-batch",
                items=[{
                    "payer_id": "AHS", "npi": "123",
                    "subscriber_id": "456", "first_name": "J",
                    "last_name": "D", "dob": "19000101",
                }],
                settings=ClaimValidatorSettings(),
            )

    def test_passes_multiple_items(self) -> None:
        mock_client = MagicMock()
        mock_client.submit_eligibility_batch.return_value = (
            BatchEligibilityResponse(
                batch_id="batch_multi", status="processing",
            )
        )

        with patch(
            "claim_validator.clearinghouse.factory.get_clearinghouse_client",
            return_value=mock_client,
        ):
            check_eligibility_batch(
                name="multi-batch",
                items=[
                    {"payer_id": "AHS", "npi": "123", "subscriber_id": f"MBR{i}",
                     "first_name": "J", "last_name": "D", "dob": "19000101"}
                    for i in range(3)
                ],
                settings=ClaimValidatorSettings(
                    clearinghouse_config={"provider": "stedi", "api_key": "test"}
                ),
            )

        call_args = mock_client.submit_eligibility_batch.call_args
        batch_request = call_args[0][0]
        assert len(batch_request.items) == 3
