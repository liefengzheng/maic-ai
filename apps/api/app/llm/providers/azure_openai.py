from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI
from pydantic_settings import SettingsConfigDict

from ..base import LlmAdapter, LlmModelConfig, ProviderSettings


class AzureOpenAiSettings(ProviderSettings):
    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_")

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-10-21"
    deployment: str = ""


class AzureOpenAiAdapter(LlmAdapter):
    provider_names = ("azure_openai",)

    @classmethod
    def create(cls, config: LlmModelConfig) -> BaseChatModel:
        endpoint = config.connection("endpoint") or config.connection("baseUrl")
        deployment = config.connection("deployment") or config.model
        cls.require(
            cls.provider_names[0],
            AZURE_OPENAI_ENDPOINT=endpoint,
            AZURE_OPENAI_API_KEY=config.api_key,
            AZURE_OPENAI_DEPLOYMENT=deployment,
        )
        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=config.api_key,
            api_version=config.connection("apiVersion") or "2024-10-21",
            azure_deployment=deployment,
            streaming=True,
            max_retries=2,
        )