"""Shared pipeline engine — configurable multi-phase execution for all domains."""

from __future__ import annotations

from claim_validator.shared.pipeline.config import PipelineConfig
from claim_validator.shared.pipeline.context import ValidationContext
from claim_validator.shared.pipeline.engine import BasePipeline

__all__ = ["BasePipeline", "PipelineConfig", "ValidationContext"]
