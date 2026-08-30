from ..base import StandardLlmSettings
from .openai_compatible import OpenAiCompatibleAdapter


class DeepSeekSettings(StandardLlmSettings):
    pass


class DeepSeekAdapter(OpenAiCompatibleAdapter):
    provider_names = ("deepseek",)
    default_base_url = "https://api.deepseek.com/v1"
    settings_type = DeepSeekSettings