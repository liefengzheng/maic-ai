from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from ..base import LlmAdapter, LlmModelConfig, StandardLlmSettings


class GeminiSettings(StandardLlmSettings):
    pass


class GeminiAdapter(LlmAdapter):
    provider_names = ("gemini",)

    @classmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        cls.require(
            cls.provider_names[0],
            LLM_API_KEY=config.api_key,
            LLM_MODEL=config.model,
        )
        return ChatGoogleGenerativeAI(
            model=config.model,
            api_key=config.api_key,
            streaming=True,
            retries=2,
        )