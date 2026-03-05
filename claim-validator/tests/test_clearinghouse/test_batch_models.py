"""Tests for batch eligibility models."""

from __future__ import annotations

import pytest

from claim_validator.clearinghouse.models.batch_eligibility import (
    BatchEligibilityItem,
    BatchEligibilityRequest,
    BatchEligibilityResponse,
    BatchItemStatus,
)


class TestBatchEligibilityItem:
    def test_minimal_item(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS", npi="1234567891", subscriber_id="1234567890",
            first_name="Jane", last_name="Doe", dob="19000101",
        )
        assert item.payer_id == "AHS"
        assert item.npi == "1234567891"

    def test_item_with_service_types(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS", npi="1234567891", subscriber_id="1234567890",
            first_name="Jane", last_name="Doe", dob="19000101",
            service_types=["MH", "78"],
        )
        assert item.service_types == ["MH", "78"]

    def test_item_with_optional_fields(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS", npi="1234567891", subscriber_id="1234567890",
            first_name="Jane", last_name="Doe", dob="19000101",
            organization_name="ACME Health Services",
            submitter_transaction_id="ABC123456789",
        )
        assert item.organization_name == "ACME Health Services"
        assert item.submitter_transaction_id == "ABC123456789"


class TestBatchEligibilityRequest:
    def test_request_with_items(self) -> None:
        item = BatchEligibilityItem(
            payer_id="AHS", npi="1234567891", subscriber_id="1234567890",
            first_name="Jane", last_name="Doe", dob="19000101",
        )
        req = BatchEligibilityRequest(name="march-2026-batch", items=[item])
        assert req.name == "march-2026-batch"
        assert len(req.items) == 1

    def test_request_requires_name(self) -> None:
        with pytest.raises(Exception):
            BatchEligibilityRequest(items=[])  # type: ignore[call-arg]


class TestBatchEligibilityResponse:
    def test_response_fields(self) -> None:
        resp = BatchEligibilityResponse(
            batch_id="batch_123", status="processing",
            total_items=10, completed_items=3,
        )
        assert resp.batch_id == "batch_123"
        assert resp.status == "processing"
        assert resp.total_items == 10
        assert resp.completed_items == 3

    def test_response_defaults(self) -> None:
        resp = BatchEligibilityResponse(batch_id="batch_123", status="submitted")
        assert resp.total_items == 0
        assert resp.completed_items == 0
        assert resp.items == []


class TestBatchItemStatus:
    def test_completed_item(self) -> None:
        item = BatchItemStatus(
            submitter_transaction_id="ABC123", status="complete",
            eligibility_response={"statusCode": "active"},
        )
        assert item.status == "complete"
        assert item.eligibility_response is not None

    def test_pending_item(self) -> None:
        item = BatchItemStatus(submitter_transaction_id="ABC123", status="pending")
        assert item.eligibility_response is None
