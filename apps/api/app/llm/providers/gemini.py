from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from ..base import LlmAdapter, StandardLlmSettings


class GeminiSettings(StandardLlmSettings):
    pass


class GeminiAdapter(LlmAdapter):
    provider_names = ("gemini",)

    @classmethod
    def create(cls) -> BaseChatModel:
        settings = GeminiSettings()
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=settings.api_key,
            LLM_MODEL=settings.model,
        )
        return ChatGoogleGenerativeAI(
            model=settings.model,
            api_key=settings.api_key,
            streaming=True,
            retries=2,
        )