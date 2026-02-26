# Story 3.2: LLM Provider Abstraction & Factory

Status: review

## Story

As a **developer**,
I want to use any supported LLM provider for AI validation by changing configuration only,
so that I can switch between Anthropic, OpenAI, or self-hosted models without code changes.

## Acceptance Criteria

1. **Given** AI configuration with `provider="anthropic"`, `api_key`, and `model`, **When** I call `get_llm_client(provider="anthropic", api_key="sk-...", model="claude-sonnet-4-5-20241022")`, **Then** an `AnthropicClient` instance is returned using the Anthropic SDK's Messages API.

2. **Given** AI configuration with `provider="openai"`, **When** I call `get_llm_client(provider="openai", api_key="sk-...", model="gpt-4o")`, **Then** an `OpenAIClient` instance is returned using the OpenAI SDK's Chat Completions API.

3. **Given** AI configuration with `provider="openai_compatible"` and a custom `base_url`, **When** I call `get_llm_client(provider="openai_compatible", api_key="...", model="llama3", base_url="http://localhost:11434/v1")`, **Then** an `OpenAICompatibleClient` instance is returned using httpx to call the OpenAI-compatible endpoint.

4. **Given** the `BaseLLMClient` abstract base class, **When** a developer subclasses it and implements `send_messages(messages: list[Message]) -> str`, **Then** their custom provider integrates with the AI validation pipeline. **And** the factory can be extended to instantiate it.

5. **Given** the `[ai]` extra is not installed, **When** I attempt to import LLM classes, **Then** a clear `ImportError` is raised explaining which extra to install (`pip install claim-validator[ai]`).

6. **Given** provider-specific extras (`[anthropic]`, `[openai]`), **When** I install only `claim-validator[anthropic]`, **Then** only the Anthropic SDK is installed, and `AnthropicClient` works while `OpenAIClient` raises a clear import error.

## Tasks / Subtasks

- [x] Task 1: Implement `BaseLLMClient` ABC and `Message` dataclass in `src/claim_validator/llm/base.py` (AC: #4)
  - [x] `Message` dataclass with `role: str` and `content: str`
  - [x] `BaseLLMClient` ABC with `send_messages(messages: list[Message]) -> str`
  - [x] `model` property (str) — the model identifier
  - [x] `provider_name` class attribute (str) — e.g., "anthropic", "openai"
  - [x] No optional dependencies — uses only stdlib + pydantic
- [x] Task 2: Implement `get_llm_client()` factory in `src/claim_validator/llm/factory.py` (AC: #1, #2, #3, #5, #6)
  - [x] `get_llm_client(provider, api_key, model, **kwargs) -> BaseLLMClient`
  - [x] Provider dispatch: "anthropic" → AnthropicClient, "openai" → OpenAIClient, "openai_compatible" → OpenAICompatibleClient
  - [x] Raise `ConfigurationError` for unknown provider name
  - [x] Import providers lazily — catch `ImportError` and raise helpful message with install command
- [x] Task 3: Implement `AnthropicClient` in `src/claim_validator/llm/providers/anthropic.py` (AC: #1, #5, #6)
  - [x] Subclass `BaseLLMClient`
  - [x] Use `anthropic.Anthropic` SDK for Messages API
  - [x] `send_messages()` → `client.messages.create()` → extract text response
  - [x] Guard import with try/except ImportError → raise clear error mentioning `pip install claim-validator[anthropic]`
  - [x] `provider_name = "anthropic"`
  - [x] Wrap SDK errors in `LLMError`
- [x] Task 4: Implement `OpenAIClient` in `src/claim_validator/llm/providers/openai.py` (AC: #2, #5, #6)
  - [x] Subclass `BaseLLMClient`
  - [x] Use `openai.OpenAI` SDK for Chat Completions API
  - [x] `send_messages()` → `client.chat.completions.create()` → extract text response
  - [x] Guard import with try/except ImportError → raise clear error mentioning `pip install claim-validator[openai]`
  - [x] `provider_name = "openai"`
  - [x] Wrap SDK errors in `LLMError`
- [x] Task 5: Implement `OpenAICompatibleClient` in `src/claim_validator/llm/providers/openai_compatible.py` (AC: #3)
  - [x] Subclass `BaseLLMClient`
  - [x] Use `httpx` for raw HTTP calls to OpenAI-compatible `/v1/chat/completions` endpoint
  - [x] Accept `base_url` parameter
  - [x] `send_messages()` → POST JSON to `/v1/chat/completions` → parse response
  - [x] Guard httpx import with try/except → raise clear error mentioning `pip install claim-validator[ai]`
  - [x] `provider_name = "openai_compatible"`
  - [x] Wrap httpx errors in `LLMError`
- [x] Task 6: Write tests in `tests/test_llm/test_base.py` (AC: #4)
  - [x] Test Message dataclass creation
  - [x] Test BaseLLMClient is ABC (cannot instantiate directly)
  - [x] Test subclassing BaseLLMClient with custom implementation
  - [x] Test provider_name attribute
  - [x] Test model property
- [x] Task 7: Write tests in `tests/test_llm/test_factory.py` (AC: #1, #2, #3, #5, #6)
  - [x] Test get_llm_client dispatches to correct provider class
  - [x] Test unknown provider raises ConfigurationError
  - [x] Test missing SDK raises clear ImportError (mock import failure)
  - [x] Test kwargs passed through (base_url for openai_compatible)
- [x] Task 8: Write tests in `tests/test_llm/test_providers/` (AC: #1, #2, #3)
  - [x] Test AnthropicClient.send_messages() with mocked SDK
  - [x] Test OpenAIClient.send_messages() with mocked SDK
  - [x] Test OpenAICompatibleClient.send_messages() with mocked httpx
  - [x] Test SDK errors wrapped in LLMError
  - [x] Test import error handling for missing SDKs
- [x] Task 9: Update `llm/__init__.py` re-exports
  - [x] Export `BaseLLMClient`, `Message`, `get_llm_client`
- [x] Task 10: Update top-level `__init__.py` re-exports
  - [x] Add `BaseLLMClient` import (lazy — via `__getattr__` or direct with guard)
  - [x] Add `get_llm_client` to `__all__`
- [x] Task 11: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors (40 source files)
  - [x] `uv run pytest` — 580 tests pass (521 existing + 59 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 3.1)

- ClaimDeidentifier and DeidentifiedClaim implemented (521 tests, 37 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- Line-length limit is 100 characters — wrap long strings with implicit concatenation
- Test pattern: class-based tests with `setup_method`, helper functions for test data
- ruff catches unused imports (F401), unsorted imports (I001), CamelCase aliases (N817)
- `head` and `tail` commands unavailable in sandbox — don't pipe to them
- Top-level `__init__.py` already exports: `ClaimDeidentifier`, `DeidentifiedClaim`, `LLMError`
- `conf.py` already has `ai_config: dict[str, Any] | None = None` for provider configuration
- `pyproject.toml` already defines `[ai]`, `[anthropic]`, `[openai]` extras

### Current State of Key Files

| File | Status | Notes |
|---|---|---|
| `llm/__init__.py` | **EMPTY** (0 bytes) | Needs `BaseLLMClient`, `Message`, `get_llm_client` re-exports |
| `llm/base.py` | **STUB** — only docstring | Needs `BaseLLMClient` ABC, `Message` dataclass |
| `llm/factory.py` | **STUB** — only docstring | Needs `get_llm_client()` factory function |
| `llm/providers/__init__.py` | **EMPTY** (0 bytes) | Package marker |
| `llm/providers/anthropic.py` | **DOES NOT EXIST** | Needs `AnthropicClient` |
| `llm/providers/openai.py` | **DOES NOT EXIST** | Needs `OpenAIClient` |
| `llm/providers/openai_compatible.py` | **DOES NOT EXIST** | Needs `OpenAICompatibleClient` |
| `tests/test_llm/__init__.py` | **EMPTY** | Package marker |
| `tests/test_llm/test_providers/__init__.py` | **EMPTY** | Package marker |
| `exceptions.py` | Complete | `LLMError(ClaimValidatorError)` already defined |
| `conf.py` | Complete | `ai_config`, `ai_validators`, `skip_ai_on_rule_failure` ready |
| `validators/pipeline.py` | Complete | Two-phase execution with AI gate logic |

### Implementation Spec

```python
# src/claim_validator/llm/base.py
"""BaseLLMClient abstract base class and Message dataclass."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """A single message in an LLM conversation."""

    role: str  # "system", "user", "assistant"
    content: str


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM provider clients.

    Subclass this to integrate a custom LLM provider.
    Implement ``send_messages()`` to transport messages
    to your provider and return the text response.
    """

    provider_name: str = ""  # Override in subclasses

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        self._model = model
        self._api_key = api_key

    @property
    def model(self) -> str:
        """The model identifier."""
        return self._model

    @abc.abstractmethod
    def send_messages(self, messages: list[Message]) -> str:
        """Send messages to the LLM and return the text response.

        Raises:
            LLMError: If the provider returns an error.
        """
```

```python
# src/claim_validator/llm/factory.py
"""LLM client factory — get_llm_client()."""

from __future__ import annotations

from typing import Any

from claim_validator.exceptions import ConfigurationError
from claim_validator.llm.base import BaseLLMClient


def get_llm_client(
    provider: str,
    *,
    api_key: str,
    model: str,
    **kwargs: Any,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: Provider name ("anthropic", "openai", "openai_compatible").
        api_key: API key for the provider.
        model: Model identifier (e.g., "claude-sonnet-4-5-20241022", "gpt-4o").
        **kwargs: Provider-specific options (e.g., base_url for openai_compatible).

    Returns:
        A configured BaseLLMClient instance.

    Raises:
        ConfigurationError: If provider name is unknown.
        ImportError: If required SDK is not installed.
    """
    if provider == "anthropic":
        from claim_validator.llm.providers.anthropic import AnthropicClient
        return AnthropicClient(model=model, api_key=api_key, **kwargs)
    if provider == "openai":
        from claim_validator.llm.providers.openai import OpenAIClient
        return OpenAIClient(model=model, api_key=api_key, **kwargs)
    if provider == "openai_compatible":
        from claim_validator.llm.providers.openai_compatible import (
            OpenAICompatibleClient,
        )
        return OpenAICompatibleClient(model=model, api_key=api_key, **kwargs)
    raise ConfigurationError(
        f"Unknown LLM provider: {provider!r}. "
        f"Supported: 'anthropic', 'openai', 'openai_compatible'."
    )
```

```python
# src/claim_validator/llm/providers/anthropic.py
"""AnthropicClient — Anthropic Messages API provider."""

from __future__ import annotations

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import anthropic
except ImportError as exc:
    raise ImportError(
        "AnthropicClient requires the anthropic SDK. "
        "Install it with: pip install claim-validator[anthropic]"
    ) from exc


class AnthropicClient(BaseLLMClient):
    """LLM client using the Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = anthropic.Anthropic(api_key=api_key)

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages via Anthropic Messages API."""
        # Split system message from conversation messages
        system_msg = ""
        api_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                api_messages.append(
                    {"role": msg.role, "content": msg.content}
                )
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system_msg,
                messages=api_messages,
            )
            return response.content[0].text
        except anthropic.APIError as exc:
            raise LLMError(
                f"Anthropic API error: {exc}"
            ) from exc
```

```python
# src/claim_validator/llm/providers/openai.py
"""OpenAIClient — OpenAI Chat Completions API provider."""

from __future__ import annotations

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import openai
except ImportError as exc:
    raise ImportError(
        "OpenAIClient requires the openai SDK. "
        "Install it with: pip install claim-validator[openai]"
    ) from exc


class OpenAIClient(BaseLLMClient):
    """LLM client using the OpenAI Chat Completions API."""

    provider_name = "openai"

    def __init__(self, *, model: str, api_key: str, **kwargs: object) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._client = openai.OpenAI(api_key=api_key)

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages via OpenAI Chat Completions API."""
        api_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=api_messages,
            )
            return response.choices[0].message.content or ""
        except openai.APIError as exc:
            raise LLMError(
                f"OpenAI API error: {exc}"
            ) from exc
```

```python
# src/claim_validator/llm/providers/openai_compatible.py
"""OpenAICompatibleClient — Generic OpenAI-compatible endpoint."""

from __future__ import annotations

from typing import Any

from claim_validator.exceptions import LLMError
from claim_validator.llm.base import BaseLLMClient, Message

try:
    import httpx
except ImportError as exc:
    raise ImportError(
        "OpenAICompatibleClient requires httpx. "
        "Install it with: pip install claim-validator[ai]"
    ) from exc


class OpenAICompatibleClient(BaseLLMClient):
    """LLM client for any OpenAI-compatible endpoint."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str = "http://localhost:11434/v1",
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, api_key=api_key, **kwargs)
        self._base_url = base_url.rstrip("/")
        self._http_client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    def send_messages(self, messages: list[Message]) -> str:
        """Send messages to an OpenAI-compatible endpoint."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ],
        }
        try:
            resp = self._http_client.post(
                "/chat/completions", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            raise LLMError(
                f"OpenAI-compatible endpoint error: {exc}"
            ) from exc
```

### Key Design Decisions

- **`BaseLLMClient` is an ABC** — enforces `send_messages()` contract on all providers
- **`Message` is a frozen dataclass** — lightweight, no Pydantic needed for internal LLM messaging
- **Factory uses lazy imports** — `from claim_validator.llm.providers.anthropic import ...` inside the function body, so SDKs are only imported when actually requested
- **Provider imports guard at module level** — `try: import anthropic except ImportError: raise ImportError(...)` at module top. This means importing the provider module without the SDK installed raises immediately with a clear message
- **`__init__` takes `api_key` as keyword-only** — prevents accidental positional argument mistakes, keeps API keys explicit
- **`send_messages()` returns `str`** — simplest contract; AI validators parse the response themselves (D9: hybrid parsing)
- **SDK errors wrapped in `LLMError`** — consistent exception hierarchy regardless of provider
- **`provider_name` is a class attribute** — identifies the provider for debugging/logging without exposing credentials
- **httpx for OpenAI-compatible** — no SDK needed, works with any endpoint (Ollama, vLLM, LiteLLM)
- **System message handling** — Anthropic API requires system message separate from conversation; AnthropicClient splits it out. OpenAI/compatible pass all messages directly.

### Anti-Patterns to Avoid

- **DO NOT** import provider SDKs at package level — they are optional dependencies
- **DO NOT** expose API keys in `__repr__`, `__str__`, logs, or error messages
- **DO NOT** make `BaseLLMClient` a Pydantic model — it's a client, not a data model
- **DO NOT** add retry logic in providers — let consumers handle retries (pipeline catches LLMError)
- **DO NOT** hardcode model names — accept any model string
- **DO NOT** add async methods yet — keep synchronous for MVP (async is Phase 2)
- **DO NOT** add `BaseLLMClient` as a direct top-level import (causes ImportError if SDKs not installed) — use `__getattr__` lazy import or import from subpackage only

### Testing Strategy

Tests should mock the actual SDK calls since we don't want real API calls in tests:

```python
# Mock Anthropic SDK
from unittest.mock import MagicMock, patch

# For AnthropicClient tests:
with patch("claim_validator.llm.providers.anthropic.anthropic") as mock_sdk:
    mock_client = MagicMock()
    mock_sdk.Anthropic.return_value = mock_client
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="AI response")]
    mock_client.messages.create.return_value = mock_response
    # ... test send_messages

# For import error tests:
# Mock the import to raise ImportError, test that it surfaces correctly
```

**IMPORTANT:** Since SDKs raise ImportError at module level, tests for providers need to either:
1. Have the SDK installed (via `[ai]` or `[dev]` extra), OR
2. Mock the import mechanism at the module level

The dev extra currently does NOT include the AI SDKs. Tests should use `unittest.mock.patch` to mock the SDK modules when testing provider behavior.

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **D7** | LLM client — Chat-based `send_messages(messages: list[Message]) -> str` |
| **D8** | Prompt management — Per-validator prompts as class constants (used by Story 3.4) |
| **D9** | Response parsing — Hybrid (structured JSON preferred, regex fallback) (used by Story 3.4) |
| **FR23** | Anthropic Claude provider support |
| **FR24** | OpenAI GPT provider support |
| **FR25** | OpenAI-compatible endpoint support (Ollama, vLLM, LiteLLM) |
| **FR26** | Switch providers via config, no code changes |
| **FR27** | Custom LLM provider adapters via subclassing |
| **FR47** | Install AI support via `pip install claim-validator[ai]` |
| **FR48** | Provider-specific extras (`[anthropic]`, `[openai]`) |
| **NFR12** | Secrets handling — API keys never in logs or outputs |

### Future Integration Points

The LLM abstraction will be consumed by:
- **Story 3.3** (`AI Validation Pipeline Integration`) — Pipeline creates LLM client from `ai_config` via `get_llm_client()`, injects into AI validators
- **Story 3.4** (`AI Clinical Validators`) — Each AI validator uses `self._llm_client.send_messages()` to get LLM responses
- **FR27** — Developers subclass `BaseLLMClient` for custom providers

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#LLM Provider Architecture — D7, D8, D9]
- [Source: _bmad-output/planning-artifacts/architecture.md#Optional extras design]
- [Source: _bmad-output/planning-artifacts/prd.md#FR23-FR27] — LLM provider support requirements
- [Source: _bmad-output/planning-artifacts/prd.md#FR47-FR48] — Optional dependency extras
- [Source: _bmad-output/planning-artifacts/prd.md#NFR12] — Secrets handling

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- RED phase: 5 test files fail with ImportError (expected — stub only)
- GREEN phase: 3 factory import-error tests initially failed due to module caching; fixed by clearing cached provider modules before patching sys.modules
- Ruff: 2 auto-fixed I001 (import sorting) in `__init__.py` and `test_base.py`
- Mypy: 1 `arg-type` error in `anthropic.py` for `messages` param; fixed with `type: ignore[arg-type]`

### Completion Notes List
- 580 tests pass (521 existing + 59 new), ruff clean, mypy clean (40 source files)
- Provider tests mock SDK imports via `sys.modules` + `importlib.import_module()` to avoid requiring actual SDKs
- `BaseLLMClient`, `Message`, `get_llm_client` exported at top-level — safe because they don't import optional dependencies

### File List
- `src/claim_validator/llm/base.py` — BaseLLMClient ABC, Message dataclass
- `src/claim_validator/llm/factory.py` — get_llm_client() factory with lazy provider imports
- `src/claim_validator/llm/providers/anthropic.py` — AnthropicClient (Anthropic Messages API)
- `src/claim_validator/llm/providers/openai.py` — OpenAIClient (OpenAI Chat Completions API)
- `src/claim_validator/llm/providers/openai_compatible.py` — OpenAICompatibleClient (httpx to any OpenAI-compatible endpoint)
- `src/claim_validator/llm/__init__.py` — Re-exports BaseLLMClient, Message, get_llm_client
- `src/claim_validator/__init__.py` — Added BaseLLMClient, Message, get_llm_client to top-level exports
- `tests/test_llm/test_base.py` — 14 tests for Message and BaseLLMClient
- `tests/test_llm/test_factory.py` — 13 tests for get_llm_client factory
- `tests/test_llm/test_providers/test_anthropic.py` — 10 tests for AnthropicClient
- `tests/test_llm/test_providers/test_openai.py` — 10 tests for OpenAIClient
- `tests/test_llm/test_providers/test_openai_compatible.py` — 12 tests for OpenAICompatibleClient

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-19 | All 11 tasks done, 580 tests pass |
