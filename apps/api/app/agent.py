import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator
from uuid import UUID

from deepagents import create_deep_agent
from deepagents.middleware.filesystem import FilesystemPermission
from langchain.tools import ToolRuntime, tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .config import get_settings
from .database import get_engine
from .llm import create_chat_model


@dataclass
class AgentContext:
    user_id: str
    conversation_id: str


@tool
async def search_my_conversations(
    query: str,
    runtime: ToolRuntime[AgentContext],
) -> str:
    """Search the current user's previous chat messages for relevant context."""
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as db:
        rows = (await db.execute(text("""
            SELECT c.title, m.role, m.content, m.created_at
            FROM chat_messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.user_id = :user_id AND m.content ILIKE :query
            ORDER BY m.created_at DESC
            LIMIT 20
        """), {"user_id": UUID(runtime.context.user_id), "query": f"%{query}%"})).mappings()
        matches = [dict(row) for row in rows]
    return json.dumps(matches, ensure_ascii=False, default=str)


_agents: dict[str, Any] = {}
_agent_lock = asyncio.Lock()

TOOL_HANDLERS = {
    "search_my_conversations": search_my_conversations,
    "app.agent.search_my_conversations": search_my_conversations,
}


def _permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/**/.env", "/**/.env.*"],
            mode="deny",
        ),
    ]


async def _agent_tools(db: AsyncSession, agent_id: UUID) -> list[Any]:
    tools: list[Any] = []
    local_rows = (await db.execute(text("""
        SELECT tools.handler
        FROM agent_tools
        JOIN tools ON tools.id = agent_tools.tool_id
        WHERE agent_tools.agent_id = :agent_id AND tools.enabled
        ORDER BY tools.slug
    """), {"agent_id": agent_id})).mappings()
    for row in local_rows:
        handler = TOOL_HANDLERS.get(row["handler"])
        if handler is None:
            raise RuntimeError(f"Unsupported Agent tool handler: {row['handler']}")
        tools.append(handler)

    mcp_rows = (await db.execute(text("""
        SELECT mcp_servers.slug, mcp_servers.transport, mcp_servers.url, mcp_servers.config
        FROM agent_mcp_servers
        JOIN mcp_servers ON mcp_servers.id = agent_mcp_servers.mcp_server_id
        WHERE agent_mcp_servers.agent_id = :agent_id AND mcp_servers.enabled
        ORDER BY mcp_servers.slug
    """), {"agent_id": agent_id})).mappings().all()
    if mcp_rows:
        connections = {
            row["slug"]: {
                **(row["config"] or {}),
                "transport": row["transport"],
                "url": row["url"],
            }
            for row in mcp_rows
        }
        tools.extend(await MultiServerMCPClient(connections).get_tools())
    return tools


async def get_catalog_agent(
    db: AsyncSession,
    user_id: UUID,
    target_kind: str,
    target_id: UUID,
) -> Any:
    table = "agents" if target_kind == "agent" else "super_agents"
    definition = (await db.execute(text(f"""
        SELECT resource.*, users.tenant_id AS user_tenant_id
        FROM {table} resource
        JOIN users ON users.id = :user_id
        WHERE resource.id = :target_id
          AND resource.tenant_id = users.tenant_id
          AND resource.enabled
          AND (resource.owner_user_id = :user_id OR resource.visibility = 'tenant')
    """), {"target_id": target_id, "user_id": user_id})).mappings().first()
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
            graph = create_deep_agent(
                name=definition["slug"],
                model=model,
                context_schema=AgentContext,
                system_prompt=definition["system_prompt"],
                tools=await _agent_tools(db, target_id),
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
                subagents.append({
                    "name": member["slug"],
                    "description": member["description"] or member["name"],
                    "system_prompt": member["system_prompt"],
                    "tools": await _agent_tools(db, member["id"]),
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

        search_tools: list[Any] = []
        if settings.search_mcp_url:
            client = MultiServerMCPClient({
                "search": {
                    "transport": "http",
                    "url": settings.search_mcp_url,
                }
            })
            search_tools = await client.get_tools()

        model = create_chat_model(settings)
        agent = create_deep_agent(
            name="coordinator",
            model=model,
            context_schema=AgentContext,
            system_prompt=system_prompt or (
                "你是 MAIC AI 协调 Agent。直接回答简单问题。复杂研究任务委派给 researcher，"
                "需要查找用户历史对话时委派给 conversation-analyst，需要处理或生成文件时委派给 file-worker。"
                "不得猜测工具结果，不得泄露其他用户数据。最终使用用户的语言简洁汇总。"
            ),
            subagents=[
                {
                    "name": "researcher",
                    "description": "使用已配置的网页搜索 MCP 进行多步事实研究并给出来源。",
                    "system_prompt": "你是研究代理。仅根据搜索结果作答，标明来源；没有搜索工具时明确说明。返回精炼结论。",
                    "tools": search_tools,
                },
                {
                    "name": "conversation-analyst",
                    "description": "仅在需要回顾当前用户以往对话时使用。",
                    "system_prompt": "你是历史对话分析代理。只使用受控工具检索当前用户数据，返回相关摘要，不输出无关原文。",
                    "tools": [search_my_conversations],
                },
                {
                    "name": "file-worker",
                    "description": "在对话隔离的虚拟文件系统中整理、读取或生成文件。",
                    "system_prompt": "你是文件处理代理。仅操作虚拟工作区，不尝试访问宿主机、环境变量或凭据。返回文件路径和简要说明。",
                    "tools": [],
                },
            ],
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
) -> AsyncIterator[tuple[str, str]]:
    assistant_content: list[str] = []
    config = {"configurable": {"thread_id": str(conversation_id)}, "recursion_limit": 100}
    context = AgentContext(user_id=str(user_id), conversation_id=str(conversation_id))
    async for event in agent.astream_events(
        {"messages": messages},
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
                if agent_name == "coordinator":
                    assistant_content.append(text_delta)
                yield "token", _sse("token", {"content": text_delta, "agent": agent_name})
        elif event_name == "on_tool_start":
            yield "tool", _sse("tool", {"name": event.get("name"), "agent": agent_name, "status": "started"})
        elif event_name == "on_tool_end":
            yield "tool", _sse("tool", {"name": event.get("name"), "agent": agent_name, "status": "completed"})
    yield "done", _sse("done", {"content": "".join(assistant_content)})