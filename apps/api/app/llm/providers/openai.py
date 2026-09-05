from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..base import LlmAdapter, LlmModelConfig, StandardLlmSettings


class OpenAiSettings(StandardLlmSettings):
    pass


class OpenAiAdapter(LlmAdapter):
    provider_names = ("openai",)

    @classmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=config.api_key,
            LLM_MODEL=config.model,
        )
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=config.connection("baseUrl") or None,
            streaming=True,
            max_retries=2,
        )