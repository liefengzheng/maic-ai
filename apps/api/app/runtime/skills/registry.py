import asyncio
import importlib.util
import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool


HANDLER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,99}$")


class Skill:
    async def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class SkillDefinition:
    code: str
    name: str
    description: str
    handler: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = field(default_factory=dict)
    execution_config: dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parent
        self._skills: dict[str, Skill] = {}

    def list_handlers(self) -> list[str]:
        return sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_dir()
            and HANDLER_PATTERN.fullmatch(path.name)
            and (path / "skill.py").is_file()
        )

    def get(self, handler: str) -> Skill:
        self._validate_handler(handler)
        cached = self._skills.get(handler)
        if cached is not None:
            return cached

        skill_path = self.root / handler / "skill.py"
        if not skill_path.is_file():
            raise RuntimeError(f"Skill handler does not exist: {handler}")
        module_name = f"maic_runtime_skill_{handler}"
        spec = importlib.util.spec_from_file_location(module_name, skill_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load Skill handler: {handler}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        skill_class = getattr(module, "Skill", None)
        if not inspect.isclass(skill_class):
            raise RuntimeError(f"Skill handler must export a Skill class: {handler}")
        skill = skill_class()
        execute = getattr(skill, "execute", None)
        if execute is None or not inspect.iscoroutinefunction(execute):
            raise RuntimeError(f"Skill.execute must be async: {handler}")
        self._skills[handler] = skill
        return skill

    def as_langchain_tool(self, definition: SkillDefinition) -> StructuredTool:
        skill = self.get(definition.handler)

        async def execute_skill(**kwargs: Any) -> Any:
            timeout = definition.execution_config.get("timeout_seconds")
            result = skill.execute(**kwargs)
            if timeout is None:
                return await result
            return await asyncio.wait_for(result, timeout=float(timeout))

        return StructuredTool.from_function(
            coroutine=execute_skill,
            name=definition.code,
            description=definition.description,
            args_schema=definition.input_schema,
        )

    @staticmethod
    def _validate_handler(handler: str) -> None:
        if not HANDLER_PATTERN.fullmatch(handler):
            raise RuntimeError(f"Invalid Skill handler: {handler}")


registry = SkillRegistry()