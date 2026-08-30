from typing import ClassVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..base import LlmAdapter, StandardLlmSettings


class OpenAiCompatibleAdapter(LlmAdapter):
    default_base_url: ClassVar[str] = ""
    settings_type: ClassVar[type[StandardLlmSettings]] = StandardLlmSettings

    @classmethod
    def create(cls) -> BaseChatModel:
        settings = cls.settings_type()
        base_url = settings.base_url or cls.default_base_url
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=settings.api_key,
            LLM_MODEL=settings.model,
            LLM_BASE_URL=base_url,
        )
        return ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            base_url=base_url,
            streaming=True,
            max_retries=2,
        )