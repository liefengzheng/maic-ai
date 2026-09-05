import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from app.llm import LlmAdapter, LlmModelConfig, create_chat_model


class LlmAdapterTests(unittest.TestCase):
    def config(self, provider: str, **overrides: object) -> LlmModelConfig:
        values: dict[str, object] = {"model": "test-model", "api_key": "test-key"}
        values.update(overrides)
        return LlmModelConfig(provider=provider, **values)

    def test_native_providers(self) -> None:
        self.assertIsInstance(create_chat_model(self.config("openai")), ChatOpenAI)
        self.assertIsInstance(create_chat_model(self.config("anthropic")), ChatAnthropic)
        self.assertIsInstance(create_chat_model(self.config("gemini")), ChatGoogleGenerativeAI)

    def test_azure_openai_uses_existing_settings(self) -> None:
        model = create_chat_model(self.config("azure_openai", model="test-deployment", connection_config={"endpoint": "https://example.openai.azure.com/"}))
        self.assertIsInstance(model, AzureChatOpenAI)

    def test_openai_compatible_providers(self) -> None:
        for provider in ("deepseek", "kimi", "minimax", "minmax"):
            with self.subTest(provider=provider):
                self.assertIsInstance(create_chat_model(self.config(provider)), ChatOpenAI)

        generic = create_chat_model(self.config("openai_compatible", connection_config={"baseUrl": "https://llm.example/v1"}))
        self.assertIsInstance(generic, ChatOpenAI)

    def test_missing_settings_are_reported(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "LLM_API_KEY, LLM_MODEL"):
            create_chat_model(self.config("openai", api_key="", model=""))

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported LLM_PROVIDER"):
            create_chat_model(self.config("unknown"))

    def test_new_adapter_registers_without_factory_changes(self) -> None:
        class CustomAdapter(LlmAdapter):
            provider_names = ("custom-test",)

            @classmethod
            def create(cls, config: LlmModelConfig) -> ChatOpenAI:
                return ChatOpenAI(
                    model=config.model,
                    api_key=config.api_key,
                )

        model = create_chat_model(self.config("custom_test"))
        self.assertIsInstance(model, ChatOpenAI)


if __name__ == "__main__":
    unittest.main()