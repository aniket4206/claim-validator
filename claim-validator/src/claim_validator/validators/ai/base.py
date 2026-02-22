"""BaseAIValidator — abstract base for AI-powered validators."""

from __future__ import annotations

import abc

from claim_validator.llm.base import BaseLLMClient, Message
from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import DeidentifiedClaim
from claim_validator.models.results import ValidatorOutput
from claim_validator.validators.base import BaseValidator


class BaseAIValidator(BaseValidator):
    """Abstract base class for AI-powered validators.

    AI validators receive a pre-configured LLM client via
    constructor injection and operate on de-identified claim data.
    The pipeline handles de-identification automatically.

    Subclass this, set ``name``, and implement
    ``validate_deidentified()``.
    """

    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm_client = llm_client

    @abc.abstractmethod
    def validate_deidentified(
        self,
        claim: DeidentifiedClaim,
    ) -> ValidatorOutput:
        """Validate a de-identified claim using LLM analysis.

        Args:
            claim: HIPAA-safe de-identified claim data.

        Returns:
            ValidatorOutput with any AI-detected findings.
        """

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        """Not used directly for AI validators.

        The pipeline calls ``validate_deidentified()`` with a
        ``DeidentifiedClaim``. This override exists for
        ``BaseValidator`` ABC compatibility.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "AI validators must be invoked via "
            "validate_deidentified(). The pipeline handles "
            "de-identification automatically."
        )

    def _send_to_llm(
        self, messages: list[Message],
    ) -> str:
        """Send messages to the configured LLM provider.

        Args:
            messages: Conversation messages to send.

        Returns:
            The LLM text response.

        Raises:
            LLMError: If the provider returns an error.
        """
        return self._llm_client.send_messages(messages)
