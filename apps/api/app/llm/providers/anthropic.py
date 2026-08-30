from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

from ..base import LlmAdapter, StandardLlmSettings


class AnthropicSettings(StandardLlmSettings):
    pass


class AnthropicAdapter(LlmAdapter):
    provider_names = ("anthropic",)

    @classmethod
    def create(cls) -> BaseChatModel:
        settings = AnthropicSettings()
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=settings.api_key,
            LLM_MODEL=settings.model,
        )
        return ChatAnthropic(
            model_name=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url or None,
            streaming=True,
            max_retries=2,
        )