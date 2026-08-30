from importlib import import_module
from pkgutil import iter_modules

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import Settings
from .base import LlmAdapter

_adapters_loaded = False


def _load_adapters() -> None:
    global _adapters_loaded
    if _adapters_loaded:
        return

    providers = import_module(f"{__package__}.providers")
    for module in iter_modules(providers.__path__):
        if not module.name.startswith("_"):
            import_module(f"{providers.__name__}.{module.name}")
    _adapters_loaded = True


def create_chat_model(settings: Settings) -> BaseChatModel:
    _load_adapters()
    adapter = LlmAdapter.for_provider(settings.llm_provider)
    return adapter.create()