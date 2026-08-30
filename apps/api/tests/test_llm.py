import sys
import unittest
from os import environ
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from app.config import Settings
from app.llm import LlmAdapter, create_chat_model


class LlmAdapterTests(unittest.TestCase):
    def settings(self, provider: str) -> Settings:
        return Settings(_env_file=None, llm_provider=provider)

    def llm_environment(self, **overrides: str):
        values = {
            "LLM_MODEL": "test-model",
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "",
        }
        values.update(overrides)
        return patch.dict(environ, values)

    def test_native_providers(self) -> None:
        with self.llm_environment():
            self.assertIsInstance(create_chat_model(self.settings("openai")), ChatOpenAI)
            self.assertIsInstance(create_chat_model(self.settings("anthropic")), ChatAnthropic)
            self.assertIsInstance(create_chat_model(self.settings("gemini")), ChatGoogleGenerativeAI)

    def test_azure_openai_uses_existing_settings(self) -> None:
        values = {
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_OPENAI_DEPLOYMENT": "test-deployment",
        }
        with patch.dict(environ, values):
            model = create_chat_model(self.settings("azure_openai"))
        self.assertIsInstance(model, AzureChatOpenAI)

    def test_openai_compatible_providers(self) -> None:
        with self.llm_environment():
            for provider in ("deepseek", "kimi", "minimax", "minmax"):
                with self.subTest(provider=provider):
                    self.assertIsInstance(create_chat_model(self.settings(provider)), ChatOpenAI)

        with self.llm_environment(LLM_BASE_URL="https://llm.example/v1"):
            generic = create_chat_model(self.settings("openai_compatible"))
        self.assertIsInstance(generic, ChatOpenAI)

    def test_missing_settings_are_reported(self) -> None:
        with self.llm_environment(LLM_API_KEY="", LLM_MODEL=""):
            with self.assertRaisesRegex(RuntimeError, "LLM_API_KEY, LLM_MODEL"):
                create_chat_model(self.settings("openai"))

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported LLM_PROVIDER"):
            create_chat_model(self.settings("unknown"))

    def test_new_adapter_registers_without_factory_changes(self) -> None:
        class CustomAdapter(LlmAdapter):
            provider_names = ("custom-test",)

            @classmethod
            def create(cls) -> ChatOpenAI:
                return ChatOpenAI(
                    model="test-model",
                    api_key="test-key",
                )

        model = create_chat_model(self.settings("custom_test"))
        self.assertIsInstance(model, ChatOpenAI)


if __name__ == "__main__":
    unittest.main()