from ..base import StandardLlmSettings
from .openai_compatible import OpenAiCompatibleAdapter


class KimiSettings(StandardLlmSettings):
    pass


class KimiAdapter(OpenAiCompatibleAdapter):
    provider_names = ("kimi",)
    default_base_url = "https://api.moonshot.cn/v1"
    settings_type = KimiSettings