from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel

from ..base import LlmAdapter, LlmModelConfig, StandardLlmSettings


class AnthropicSettings(StandardLlmSettings):
    pass


class AnthropicAdapter(LlmAdapter):
    provider_names = ("anthropic",)

    @classmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=config.api_key,
            LLM_MODEL=config.model,
        )
        return ChatAnthropic(
            model_name=config.model,
            api_key=config.api_key,
            base_url=config.connection("baseUrl") or None,
            streaming=True,
            max_retries=2,
        )