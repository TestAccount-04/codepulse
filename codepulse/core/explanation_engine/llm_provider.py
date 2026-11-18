"""Configurable LLM provider interface with local offline rule-based default."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_explanation(self, prompt: str) -> str:
        pass


class LocalRuleBasedProvider(BaseLLMProvider):
    """Default privacy-preserving offline provider that uses deterministic rules."""

    @property
    def provider_name(self) -> str:
        return "local-rule-based"

    def generate_explanation(self, prompt: str) -> str:
        return "Generated via local deterministic rule engine."


class OptionalCloudLLMProvider(BaseLLMProvider):
    """Optional pluggable cloud LLM provider (disabled by default, requires user API key)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "default") -> None:
        self.api_key = api_key
        self.model = model

    @property
    def provider_name(self) -> str:
        return f"cloud-provider-{self.model}"

    def generate_explanation(self, prompt: str) -> str:
        if not self.api_key:
            return "Reason not available from observed evidence. (No cloud LLM API key configured)."
        # Keep sensitive source code local unless explicitly configured
        return "Cloud explanation stub (local-first mode active)."
