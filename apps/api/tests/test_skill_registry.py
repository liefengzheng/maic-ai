import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.runtime.skills import SkillDefinition, SkillRegistry


SKILL_SOURCE = """
class Skill:
    async def execute(self, **kwargs):
        return {"city": kwargs["city"]}
"""


class SkillRegistryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        weather = self.root / "weather"
        weather.mkdir()
        (weather / "skill.py").write_text(SKILL_SOURCE, encoding="utf-8")
        (self.root / "ignored").mkdir()
        self.registry = SkillRegistry(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lists_directories_that_contain_a_skill_module(self) -> None:
        self.assertEqual(self.registry.list_handlers(), ["weather"])

    async def test_loads_and_executes_a_skill_by_handler_name(self) -> None:
        result = await self.registry.get("weather").execute(city="北京")

        self.assertEqual(result, {"city": "北京"})

    async def test_builds_langchain_adapter_from_database_metadata(self) -> None:
        adapter = self.registry.as_langchain_tool(SkillDefinition(
            code="city_weather",
            name="城市天气",
            description="获取城市天气",
            handler="weather",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ))

        self.assertEqual(adapter.name, "city_weather")
        self.assertEqual(adapter.args["city"]["type"], "string")
        self.assertEqual(await adapter.ainvoke({"city": "北京"}), {"city": "北京"})

    def test_rejects_unsafe_handler_names(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Invalid Skill handler"):
            self.registry.get("../weather")


if __name__ == "__main__":
    unittest.main()