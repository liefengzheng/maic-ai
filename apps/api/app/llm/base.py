from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..config import API_ROOT


class ProviderSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=API_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class StandardLlmSettings(ProviderSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_")

    model: str = ""
    api_key: str = ""
    base_url: str = ""


@dataclass(frozen=True)
class LlmModelConfig:
    provider: str
    model: str
    api_key: str
    connection_config: dict[str, str] = field(default_factory=dict)

    def connection(self, key: str) -> str:
        return self.connection_config.get(key, "")


def normalize_provider(provider: str) -> str:
    return provider.strip().lower().replace("-", "_")


class LlmAdapter(ABC):
    provider_names: ClassVar[tuple[str, ...]] = ()
    _registry: ClassVar[dict[str, type["LlmAdapter"]]] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for provider in cls.provider_names:
            normalized = normalize_provider(provider)
            existing = cls._registry.get(normalized)
            if existing is not None and existing is not cls:
                raise RuntimeError(f"Duplicate LLM adapter for provider '{provider}'")
            cls._registry[normalized] = cls

    @classmethod
    def require(cls, provider: str, **values: str) -> None:
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(
                f"Missing {provider} LLM settings: {', '.join(missing)}"
            )

    @classmethod
    @abstractmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        """Create a LangChain chat model for this provider."""

    @classmethod
    def for_provider(cls, provider: str) -> type["LlmAdapter"]:
        normalized = normalize_provider(provider)
        adapter = cls._registry.get(normalized)
        if adapter is None:
            supported = ", ".join(sorted(cls._registry))
            raise RuntimeError(
                f"Unsupported LLM_PROVIDER '{provider}'. Supported: {supported}"
            )
        return adapter