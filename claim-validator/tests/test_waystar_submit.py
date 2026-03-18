from unittest.mock import MagicMock, patch

import pytest

from claim_validator.clearinghouse.models import SubmissionResult
from claim_validator.clearinghouse.providers.waystar import WaystarClient


@pytest.fixture
def client():
    return WaystarClient(
        api_key="test-key",
        secret="test-secret",
        user_id="test-user",
        password="test-pass",
        cust_id="12345",
    )


def test_submit_claim_returns_submission_result(client):
    """submit_claim() should return a SubmissionResult, not raise."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Status": "Accepted",
        "ReferenceId": "REF-001",
        "ErrorMessage": "",
    }
    mock_response.text = '{"Status": "Accepted"}'
    mock_response.headers = {"content-type": "application/json"}

    with patch.object(client, "_post_json_with_retry", return_value=mock_response):
        result = client.submit_claim({
            "billing_provider_npi": "1245319599",
            "subscriber_id": "XYZ123",
            "payer_id": "00001",
            "claim_type": "professional",
            "diagnosis_codes": [{"code": "J06.9"}],
            "lines": [{"procedure_code": "99213", "charge_amount": 150.0}],
        })

    assert isinstance(result, SubmissionResult)
    assert result.accepted is True
    assert result.reference_id == "REF-001"


def test_submit_claim_handles_rejection(client):
    """submit_claim() handles rejection response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Status": "Rejected",
        "ReferenceId": "",
        "ErrorMessage": "Invalid payer ID",
    }
    mock_response.text = '{"Status": "Rejected"}'
    mock_response.headers = {"content-type": "application/json"}

    with patch.object(client, "_post_json_with_retry", return_value=mock_response):
        result = client.submit_claim({"billing_provider_npi": "1234567890"})

    assert isinstance(result, SubmissionResult)
    assert result.accepted is False
    assert "Invalid payer ID" in result.errors
