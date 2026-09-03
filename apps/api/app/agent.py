import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemPermission
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .llm import create_chat_model
from .runtime.skills import SkillDefinition, registry as skill_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    user_id: str
    conversation_id: str


_agents: dict[str, Any] = {}
_agent_lock = asyncio.Lock()
SKILLS_PLACEHOLDER = "{{Skills}}"


def _inject_skill_descriptions(
    system_prompt: str,
    skill_rows: list[dict[str, Any]],
) -> str:
    descriptions = "\n".join(
        f"{index}. {skill['handler']}：{skill['description']}"
        for index, skill in enumerate(skill_rows, start=1)
    )
    return system_prompt.replace(SKILLS_PLACEHOLDER, descriptions)


def _permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**/.env", "/**/.env.*"],
            mode="deny",
        ),
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="interrupt",
        ),
    ]


async def _agent_skills(
    db: AsyncSession,
    agent_id: UUID,
) -> tuple[list[Any], list[dict[str, Any]]]:
    skills: list[Any] = []
    skill_rows = list((await db.execute(text("""
        SELECT skill_registry.skill_code, skill_registry.skill_name,
               skill_registry.description, skill_registry.handler,
               skill_registry.input_schema, skill_registry.output_schema,
               skill_registry.execution_config
        FROM agent_skills
        JOIN skill_registry ON skill_registry.id = agent_skills.skill_id
        WHERE agent_skills.agent_id = :agent_id AND skill_registry.enabled
        ORDER BY skill_registry.skill_code
    """), {"agent_id": agent_id})).mappings())
    for row in skill_rows:
        skills.append(skill_registry.as_langchain_tool(SkillDefinition(
            code=row["skill_code"],
            name=row["skill_name"],
            description=row["description"],
            handler=row["handler"],
            input_schema=row["input_schema"],
            output_schema=row["output_schema"],
            execution_config=row["execution_config"],
        )))

    return skills, [dict(row) for row in skill_rows]


async def get_catalog_agent(
    db: AsyncSession,
    target_kind: str,
    target_id: UUID,
) -> Any:
    table = "agents" if target_kind == "agent" else "super_agents"
    definition = (await db.execute(text(f"""
                SELECT resource.*
        FROM {table} resource
        WHERE resource.id = :target_id
          AND resource.enabled
        """), {"target_id": target_id})).mappings().first()
    if definition is None:
        raise RuntimeError("Agent does not exist or is not available")

    cache_key = f"{target_kind}:{target_id}:{definition['updated_at'].isoformat()}"
    if cache_key in _agents:
        return _agents[cache_key]
    async with _agent_lock:
        if cache_key in _agents:
            return _agents[cache_key]
        model = create_chat_model(get_settings())
        if target_kind == "agent":
            skills, skill_rows = await _agent_skills(db, target_id)
            graph = create_deep_agent(
                name=definition["slug"],
                model=model,
                context_schema=AgentContext,
                system_prompt=_inject_skill_descriptions(
                    definition["system_prompt"], skill_rows
                ),
                tools=skills,
                permissions=_permissions(),
            )
        else:
            members = (await db.execute(text("""
                SELECT agents.id, agents.slug, agents.name, agents.description, agents.system_prompt
                FROM super_agent_members
                JOIN agents ON agents.id = super_agent_members.agent_id
                WHERE super_agent_members.super_agent_id = :super_agent_id AND agents.enabled
                ORDER BY super_agent_members.position
            """), {"super_agent_id": target_id})).mappings().all()
            if not members:
                raise RuntimeError("SuperAgent must contain at least one enabled Agent")
            subagents = []
            for member in members:
                skills, skill_rows = await _agent_skills(db, member["id"])
                subagents.append({
                    "name": member["slug"],
                    "description": member["description"] or member["name"],
                    "system_prompt": _inject_skill_descriptions(
                        member["system_prompt"], skill_rows
                    ),
                    "tools": skills,
                })
            graph = create_deep_agent(
                name=definition["slug"],
                model=model,
                context_schema=AgentContext,
                system_prompt=definition["system_prompt"],
                subagents=subagents,
                permissions=_permissions(),
            )
        _agents[cache_key] = graph
        return graph


async def warm_catalog_agents(db: AsyncSession) -> tuple[int, int]:
    definitions = (await db.execute(text("""
        SELECT id, 'agent' AS kind FROM agents WHERE enabled
        UNION ALL
        SELECT id, 'super_agent' AS kind FROM super_agents WHERE enabled
        ORDER BY kind, id
    """))).mappings()
    ready = 0
    failed = 0
    for definition in definitions:
        try:
            await asyncio.wait_for(
                get_catalog_agent(db, definition["kind"], definition["id"]),
                timeout=30,
            )
            ready += 1
        except Exception:
            failed += 1
            logger.exception(
                "Failed to build catalog Agent graph",
                extra={"agent_id": str(definition["id"]), "agent_kind": definition["kind"]},
            )
    return ready, failed


async def get_agent(
    cache_key: str = "default",
    system_prompt: str | None = None,
) -> Any:
    if cache_key in _agents:
        return _agents[cache_key]
    async with _agent_lock:
        if cache_key in _agents:
            return _agents[cache_key]
        settings = get_settings()

        model = create_chat_model(settings)
        agent = create_deep_agent(
            name="coordinator",
            model=model,
            context_schema=AgentContext,
            system_prompt=system_prompt or (
                "你是 MAIC AI 协调 Agent。直接回答用户问题。"
                "不得猜测工具结果，不得泄露其他用户数据。最终使用用户的语言简洁汇总。"
            ),
            permissions=_permissions(),
        )
        _agents[cache_key] = agent
        return agent


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") in {"text", "text-delta"}
        )
    return ""


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


async def stream_agent(
    agent: Any,
    messages: list[dict[str, str]],
    user_id: UUID,
    conversation_id: UUID,
    root_agent_name: str = "coordinator",
) -> AsyncIterator[tuple[str, str]]:
    assistant_content: list[str] = []
    started_at = time.monotonic()
    config = {"configurable": {"thread_id": str(conversation_id)}, "recursion_limit": 100}
    context = AgentContext(user_id=str(user_id), conversation_id=str(conversation_id))
    graph_input: Any = {"messages": messages}
    async for event in agent.astream_events(
        graph_input,
        config=config,
        context=context,
        version="v2",
    ):
        event_name = event.get("event", "")
        metadata = event.get("metadata") or {}
        agent_name = metadata.get("lc_agent_name", "coordinator")
        if event_name == "on_chat_model_stream":
            chunk = (event.get("data") or {}).get("chunk")
            text_delta = _text_from_content(getattr(chunk, "content", ""))
            if text_delta:
                is_root = agent_name == root_agent_name
                if is_root:
                    assistant_content.append(text_delta)
                    logger.info(
                        "Agent token chunk emitted",
                        extra={
                            "agent": agent_name,
                            "characters": len(text_delta),
                            "elapsed_seconds": round(time.monotonic() - started_at, 3),
                        },
                    )
                yield "token", _sse("token", {
                    "content": text_delta,
                    "agent": agent_name,
                    "root": is_root,
                })
        elif event_name == "on_tool_start":
            yield "skill", _sse("skill", {"name": event.get("name"), "agent": agent_name, "status": "started"})
        elif event_name == "on_tool_end":
            yield "skill", _sse("skill", {"name": event.get("name"), "agent": agent_name, "status": "completed"})
    yield "done", _sse("done", {"content": "".join(assistant_content)})