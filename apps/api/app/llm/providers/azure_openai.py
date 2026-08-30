from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI
from pydantic_settings import SettingsConfigDict

from ..base import LlmAdapter, ProviderSettings


class AzureOpenAiSettings(ProviderSettings):
    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_")

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-10-21"
    deployment: str = ""


class AzureOpenAiAdapter(LlmAdapter):
    provider_names = ("azure_openai",)

    @classmethod
    def create(cls) -> BaseChatModel:
        settings = AzureOpenAiSettings()
        cls.require(
            cls.provider_names[0],
            AZURE_OPENAI_ENDPOINT=settings.endpoint,
            AZURE_OPENAI_API_KEY=settings.api_key,
            AZURE_OPENAI_DEPLOYMENT=settings.deployment,
        )
        return AzureChatOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            azure_deployment=settings.deployment,
            streaming=True,
            max_retries=2,
        )