from typing import ClassVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..base import LlmAdapter, LlmModelConfig, StandardLlmSettings


class OpenAiCompatibleAdapter(LlmAdapter):
    default_base_url: ClassVar[str] = ""
    settings_type: ClassVar[type[StandardLlmSettings]] = StandardLlmSettings

    @classmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        base_url = config.connection("baseUrl") or cls.default_base_url
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=config.api_key,
            LLM_MODEL=config.model,
            LLM_BASE_URL=base_url,
        )
        return ChatOpenAI(
            model=config.model,
            api_key=config.api_key,
            base_url=base_url,
            streaming=True,
            max_retries=2,
        )