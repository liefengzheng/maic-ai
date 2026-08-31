import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import _resolve_tool_handler, stream_agent, warm_catalog_agents


class DefinitionResult:
    def __init__(self, definitions: list[dict]) -> None:
        self.definitions = definitions

    def mappings(self) -> list[dict]:
        return self.definitions


class CatalogDb:
    def __init__(self, definitions: list[dict]) -> None:
        self.definitions = definitions

    async def execute(self, *_args, **_kwargs) -> DefinitionResult:
        return DefinitionResult(self.definitions)


class StreamingAgent:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chat_model_stream",
            "metadata": {"lc_agent_name": "custom-agent"},
            "data": {"chunk": SimpleNamespace(content="OK")},
        }


class AgentWarmupTests(unittest.IsolatedAsyncioTestCase):
    async def test_streams_custom_root_agent_as_final_content(self) -> None:
        events = [
            payload
            async for _, payload in stream_agent(
                StreamingAgent(),
                [{"role": "user", "content": "reply OK"}],
                uuid4(),
                uuid4(),
                root_agent_name="custom-agent",
            )
        ]

        self.assertIn('"root": true', events[0])
        self.assertIn('"content": "OK"', events[-1])

    def test_resolves_dotted_python_tool_handler(self) -> None:
        handler = lambda: None
        module = SimpleNamespace(user_filter=handler)

        with patch("app.agent.importlib.import_module", return_value=module) as import_module:
            resolved = _resolve_tool_handler("app.tools.user_filter")

        self.assertIs(resolved, handler)
        import_module.assert_called_once_with("app.tools")

    async def test_builds_all_catalog_graphs_and_counts_failures(self) -> None:
        agent_id = uuid4()
        super_agent_id = uuid4()
        db = CatalogDb([
            {"id": agent_id, "kind": "agent"},
            {"id": super_agent_id, "kind": "super_agent"},
        ])
        build = AsyncMock(side_effect=[object(), RuntimeError("invalid tool")])

        with (
            patch("app.agent.get_catalog_agent", build),
            self.assertLogs("app.agent", level="ERROR"),
        ):
            result = await warm_catalog_agents(db)  # type: ignore[arg-type]

        self.assertEqual(result, (1, 1))
        self.assertEqual(
            build.await_args_list,
            [
                unittest.mock.call(db, "agent", agent_id),
                unittest.mock.call(db, "super_agent", super_agent_id),
            ],
        )


if __name__ == "__main__":
    unittest.main()
