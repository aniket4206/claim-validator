"""ValidatorRegistry — dotted-path lazy loading."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from claim_validator.exceptions import ConfigurationError

if TYPE_CHECKING:
    from claim_validator.llm.base import BaseLLMClient
    from claim_validator.validators.ai.base import BaseAIValidator
    from claim_validator.validators.base import BaseValidator


class ValidatorRegistry:
    """Loads validator classes from dotted path strings and instantiates them."""

    def __init__(self) -> None:
        self._cache: dict[str, type[BaseValidator]] = {}

    def load(self, dotted_path: str) -> type[BaseValidator]:
        """Import and return a validator class from a dotted path.

        Example: ``"claim_validator.validators.rule_based.npi.NPIValidator"``
        """
        if dotted_path in self._cache:
            return self._cache[dotted_path]

        try:
            module_path, class_name = dotted_path.rsplit(".", 1)
        except ValueError:
            raise ConfigurationError(
                f"Invalid validator path '{dotted_path}': "
                "must be a dotted path like 'module.ClassName'"
            )

        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            raise ConfigurationError(
                f"Cannot import module '{module_path}' "
                f"from validator path '{dotted_path}': {exc}"
            ) from exc

        try:
            cls = getattr(module, class_name)
        except AttributeError:
            raise ConfigurationError(
                f"Module '{module_path}' has no class '{class_name}' "
                f"(from path '{dotted_path}')"
            )

        from claim_validator.validators.base import BaseValidator

        if not (isinstance(cls, type) and issubclass(cls, BaseValidator)):
            raise ConfigurationError(
                f"Class '{dotted_path}' is not a BaseValidator subclass"
            )

        self._cache[dotted_path] = cls
        return cls

    def create_validators(self, paths: list[str]) -> list[BaseValidator]:
        """Load and instantiate all validators from a list of dotted paths."""
        validators: list[BaseValidator] = []
        for path in paths:
            cls = self.load(path)
            validators.append(cls())
        return validators

    def create_ai_validators(
        self,
        paths: list[str],
        *,
        llm_client: BaseLLMClient,
    ) -> list[BaseAIValidator]:
        """Load and instantiate AI validators with LLM client injection.

        Args:
            paths: Dotted class paths for AI validators.
            llm_client: Pre-configured LLM client to inject.

        Returns:
            List of instantiated AI validators.

        Raises:
            ConfigurationError: If class is not a BaseAIValidator.
        """
        from claim_validator.validators.ai.base import (
            BaseAIValidator,
        )

        validators: list[BaseAIValidator] = []
        for path in paths:
            cls = self.load(path)
            if not issubclass(cls, BaseAIValidator):
                raise ConfigurationError(
                    f"Class '{path}' is not a "
                    "BaseAIValidator subclass"
                )
            validators.append(cls(llm_client=llm_client))
        return validators
