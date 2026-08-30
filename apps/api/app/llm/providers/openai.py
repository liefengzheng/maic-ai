from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..base import LlmAdapter, StandardLlmSettings


class OpenAiSettings(StandardLlmSettings):
    pass


class OpenAiAdapter(LlmAdapter):
    provider_names = ("openai",)

    @classmethod
    def create(cls) -> BaseChatModel:
        settings = OpenAiSettings()
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=settings.api_key,
            LLM_MODEL=settings.model,
        )
        return ChatOpenAI(
            model=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url or None,
            streaming=True,
            max_retries=2,
        )