from ..base import StandardLlmSettings
from .openai_compatible import OpenAiCompatibleAdapter


class MiniMaxSettings(StandardLlmSettings):
    pass


class MiniMaxAdapter(OpenAiCompatibleAdapter):
    provider_names = ("minimax", "minmax")
    default_base_url = "https://api.minimax.io/v1"
    settings_type = MiniMaxSettings