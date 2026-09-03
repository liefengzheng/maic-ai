import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import _inject_skill_descriptions, stream_agent, warm_catalog_agents


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
    def __init__(self) -> None:
        self.inputs = []

    async def astream_events(self, *_args, **_kwargs):
        self.inputs.append(_args[0])
        yield {
            "event": "on_chat_model_stream",
            "metadata": {"lc_agent_name": "custom-agent"},
            "data": {"chunk": SimpleNamespace(content="OK")},
        }

class AgentWarmupTests(unittest.IsolatedAsyncioTestCase):
    def test_injects_assigned_skill_descriptions_into_system_prompt(self) -> None:
        prompt = _inject_skill_descriptions(
            "可使用以下技能：\n{{Skills}}",
            [
                {"handler": "overdue_account", "description": "查询欠款客户信息"},
                {"handler": "weather", "description": "查询城市天气"},
            ],
        )

        self.assertEqual(
            prompt,
            "可使用以下技能：\n1. overdue_account：查询欠款客户信息\n2. weather：查询城市天气",
        )

    def test_replaces_skill_placeholder_with_empty_text_for_agent_without_skills(self) -> None:
        self.assertEqual(
            _inject_skill_descriptions("技能：{{Skills}}", []),
            "技能：",
        )

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

    async def test_passes_complete_message_history_without_reading_checkpoint_state(self) -> None:
        agent = StreamingAgent()
        messages = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {"role": "user", "content": "second"},
        ]

        _ = [
            event
            async for event in stream_agent(
                agent,
                messages,
                uuid4(),
                uuid4(),
            )
        ]

        self.assertEqual(agent.inputs[0], {"messages": messages})

    async def test_builds_all_catalog_graphs_and_counts_failures(self) -> None:
        agent_id = uuid4()
        super_agent_id = uuid4()
        db = CatalogDb([
            {"id": agent_id, "kind": "agent"},
            {"id": super_agent_id, "kind": "super_agent"},
        ])
        build = AsyncMock(side_effect=[object(), RuntimeError("invalid Skill")])

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
