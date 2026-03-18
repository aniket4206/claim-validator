"""Tests for per-stage AI configuration and helper functions."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.exceptions import ConfigurationError
from claim_validator.models.results import Finding
from claim_validator.workflow.models import FullWorkflowResult, StageResult
from claim_validator.workflow.stages_v2 import _get_llm_client_from_config, _resolve_ai_config


# ---------------------------------------------------------------------------
# _resolve_ai_config
# ---------------------------------------------------------------------------


class TestResolveAiConfig:
    """Test per-stage > global AI config resolution."""

    def test_returns_none_when_no_settings(self) -> None:
        assert _resolve_ai_config(None, "ai_claim_analysis_config") is None

    def test_returns_global_when_no_per_stage(self) -> None:
        settings = ClaimValidatorSettings(
            ai_config={"provider": "groq", "api_key": "k", "model": "m"},
        )
        result = _resolve_ai_config(settings, "ai_claim_analysis_config")
        assert result == {"provider": "groq", "api_key": "k", "model": "m"}

    def test_per_stage_overrides_global(self) -> None:
        settings = ClaimValidatorSettings(
            ai_config={"provider": "groq", "api_key": "k1", "model": "m1"},
            ai_claim_analysis_config={"provider": "anthropic", "api_key": "k2", "model": "m2"},
        )
        result = _resolve_ai_config(settings, "ai_claim_analysis_config")
        assert result["provider"] == "anthropic"
        assert result["api_key"] == "k2"

    def test_returns_none_when_neither_set(self) -> None:
        settings = ClaimValidatorSettings()
        result = _resolve_ai_config(settings, "ai_claim_analysis_config")
        assert result is None

    def test_rejection_summary_config(self) -> None:
        settings = ClaimValidatorSettings(
            ai_rejection_summary_config={"provider": "groq", "api_key": "k", "model": "fast"},
        )
        result = _resolve_ai_config(settings, "ai_rejection_summary_config")
        assert result["model"] == "fast"

    def test_pre_submission_config(self) -> None:
        settings = ClaimValidatorSettings(
            ai_pre_submission_config={"provider": "openai", "api_key": "sk", "model": "gpt-4o"},
        )
        result = _resolve_ai_config(settings, "ai_pre_submission_config")
        assert result["provider"] == "openai"

    def test_unknown_attr_falls_back_to_global(self) -> None:
        settings = ClaimValidatorSettings(
            ai_config={"provider": "groq", "api_key": "k", "model": "m"},
        )
        result = _resolve_ai_config(settings, "nonexistent_config")
        assert result == {"provider": "groq", "api_key": "k", "model": "m"}


# ---------------------------------------------------------------------------
# _get_llm_client_from_config
# ---------------------------------------------------------------------------


class TestGetLlmClientFromConfig:
    """Test LLM client creation with validation."""

    def test_missing_provider_raises_config_error(self) -> None:
        with pytest.raises(ConfigurationError, match="provider"):
            _get_llm_client_from_config({"api_key": "k", "model": "m"})

    def test_missing_api_key_raises_config_error(self) -> None:
        with pytest.raises(ConfigurationError, match="api_key"):
            _get_llm_client_from_config({"provider": "groq", "model": "m"})

    def test_missing_model_raises_config_error(self) -> None:
        with pytest.raises(ConfigurationError, match="model"):
            _get_llm_client_from_config({"provider": "groq", "api_key": "k"})

    def test_missing_multiple_keys_lists_all(self) -> None:
        with pytest.raises(ConfigurationError, match="provider.*api_key.*model"):
            _get_llm_client_from_config({})

    def test_creates_client_with_valid_config(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.HTTPError = type("HTTPError", (Exception,), {})
        groq_mod = "claim_validator.llm.providers.groq"
        saved = sys.modules.pop(groq_mod, None)
        try:
            with patch.dict("sys.modules", {"groq": None, "httpx": mock_httpx}):
                client = _get_llm_client_from_config({
                    "provider": "groq",
                    "api_key": "gsk-test",
                    "model": "llama-3.3-70b",
                })
                assert client.provider_name == "groq"
                assert client.model == "llama-3.3-70b"
        finally:
            if saved is not None:
                sys.modules[groq_mod] = saved

    def test_extra_kwargs_passed_through(self) -> None:
        mock_httpx = MagicMock()
        mock_httpx.HTTPError = type("HTTPError", (Exception,), {})
        groq_mod = "claim_validator.llm.providers.groq"
        saved = sys.modules.pop(groq_mod, None)
        try:
            with patch.dict("sys.modules", {"groq": None, "httpx": mock_httpx}):
                client = _get_llm_client_from_config({
                    "provider": "groq",
                    "api_key": "k",
                    "model": "m",
                    "base_url": "http://custom:8080/v1",
                })
                assert client._base_url == "http://custom:8080/v1"
        finally:
            if saved is not None:
                sys.modules[groq_mod] = saved


# ---------------------------------------------------------------------------
# FullWorkflowResult properties
# ---------------------------------------------------------------------------


class TestFullWorkflowResultProperties:
    """Test FullWorkflowResult computed properties."""

    def test_passed_true_when_no_errors(self) -> None:
        result = FullWorkflowResult(
            findings=[
                Finding(code="INFO", message="ok", severity=Severity.WARNING, field_name="x"),
            ],
        )
        assert result.passed is True

    def test_passed_false_when_errors(self) -> None:
        result = FullWorkflowResult(
            findings=[
                Finding(code="ERR", message="bad", severity=Severity.ERROR, field_name="x"),
            ],
        )
        assert result.passed is False

    def test_passed_true_when_no_findings(self) -> None:
        result = FullWorkflowResult()
        assert result.passed is True

    def test_submitted_true_when_accepted(self) -> None:
        mock_sub = MagicMock()
        mock_sub.accepted = True
        result = FullWorkflowResult(submission=mock_sub)
        assert result.submitted is True

    def test_submitted_false_when_rejected(self) -> None:
        mock_sub = MagicMock()
        mock_sub.accepted = False
        result = FullWorkflowResult(submission=mock_sub)
        assert result.submitted is False

    def test_submitted_false_when_no_submission(self) -> None:
        result = FullWorkflowResult()
        assert result.submitted is False

    def test_stage_times(self) -> None:
        result = FullWorkflowResult(
            stage_results=[
                StageResult(stage_name="rule_based_claim", passed=True, execution_time=0.01),
                StageResult(stage_name="eligibility", passed=True, execution_time=0.5),
            ],
        )
        times = result.stage_times
        assert times["rule_based_claim"] == 0.01
        assert times["eligibility"] == 0.5


# ---------------------------------------------------------------------------
# Per-stage AI config in ClaimValidatorSettings
# ---------------------------------------------------------------------------


class TestPerStageAiConfigSettings:
    """Test per-stage AI config fields in ClaimValidatorSettings."""

    def test_default_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.ai_claim_analysis_config is None
        assert settings.ai_rejection_summary_config is None
        assert settings.ai_pre_submission_config is None

    def test_explicit_values(self) -> None:
        cfg = {"provider": "groq", "api_key": "k", "model": "m"}
        settings = ClaimValidatorSettings(
            ai_claim_analysis_config=cfg,
            ai_rejection_summary_config=cfg,
            ai_pre_submission_config=cfg,
        )
        assert settings.ai_claim_analysis_config == cfg
        assert settings.ai_rejection_summary_config == cfg
        assert settings.ai_pre_submission_config == cfg

    def test_frozen(self) -> None:
        import pydantic
        settings = ClaimValidatorSettings()
        with pytest.raises(pydantic.ValidationError):
            settings.ai_claim_analysis_config = {"provider": "x"}  # type: ignore[misc]
