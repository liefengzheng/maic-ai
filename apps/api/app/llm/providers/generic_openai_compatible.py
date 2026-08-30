from ..base import StandardLlmSettings
from .openai_compatible import OpenAiCompatibleAdapter


class GenericOpenAiCompatibleSettings(StandardLlmSettings):
    pass


class GenericOpenAiCompatibleAdapter(OpenAiCompatibleAdapter):
    provider_names = ("openai_compatible",)
    settings_type = GenericOpenAiCompatibleSettings