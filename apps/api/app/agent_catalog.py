from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .agent import get_catalog_agent
from .database import get_db
from .schemas import (
    AgentCatalogOutput,
    AgentChoiceOutput,
    AgentGraphOutput,
    AgentInput,
    AgentOutput,
    McpServerInput,
    McpServerOutput,
    SuperAgentInput,
    SuperAgentOutput,
    ToolInput,
    ToolOutput,
)
from .security import require_admin_user_id, require_user_id

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/catalog", response_model=AgentCatalogOutput, response_model_by_alias=True)
async def get_agent_catalog(
    _admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentCatalogOutput:
    tools = (await db.execute(text("""
        SELECT id, name, slug, description, handler, enabled
        FROM tools ORDER BY name
    """))).mappings()
    mcp_servers = (await db.execute(text("""
        SELECT id, name, slug, description, transport, url, enabled
        FROM mcp_servers ORDER BY name
    """))).mappings()
    agents = (await db.execute(text("""
        SELECT agents.id, 'agent' AS kind, agents.name, agents.slug,
               agents.description, agents.system_prompt,
               agents.enabled, 'not_generated' AS graph_status,
               COALESCE(array_agg(DISTINCT agent_tools.tool_id)
                   FILTER (WHERE agent_tools.tool_id IS NOT NULL), '{}') AS tool_ids,
               COALESCE(array_agg(DISTINCT agent_mcp_servers.mcp_server_id)
                   FILTER (WHERE agent_mcp_servers.mcp_server_id IS NOT NULL), '{}') AS mcp_server_ids
        FROM agents
        LEFT JOIN agent_tools ON agent_tools.agent_id = agents.id
        LEFT JOIN agent_mcp_servers ON agent_mcp_servers.agent_id = agents.id
        GROUP BY agents.id ORDER BY agents.name
    """))).mappings()
    super_agents = (await db.execute(text("""
        SELECT super_agents.id, 'super_agent' AS kind, super_agents.name,
               super_agents.slug, super_agents.description, super_agents.system_prompt,
               super_agents.enabled,
               COALESCE(array_agg(super_agent_members.agent_id ORDER BY super_agent_members.position)
                   FILTER (WHERE super_agent_members.agent_id IS NOT NULL), '{}') AS agent_ids
        FROM super_agents
        LEFT JOIN super_agent_members ON super_agent_members.super_agent_id = super_agents.id
        GROUP BY super_agents.id ORDER BY super_agents.name
    """))).mappings()
    return AgentCatalogOutput.model_validate({
        "tools": [dict(row) for row in tools],
        "mcp_servers": [dict(row) for row in mcp_servers],
        "agents": [dict(row) for row in agents],
        "super_agents": [dict(row) for row in super_agents],
    })


async def _save_capability(
    db: AsyncSession,
    table: str,
    data: ToolInput | McpServerInput,
    resource_id: UUID | None,
) -> UUID:
    fields = {
        "name": data.name,
        "slug": data.slug,
        "description": data.description,
        "enabled": data.enabled,
    }
    if isinstance(data, ToolInput):
        fields["handler"] = data.handler
    else:
        fields["transport"] = data.transport
        fields["url"] = data.url
    if resource_id:
        assignments = ", ".join(f"{field} = :{field}" for field in fields)
        result = await db.execute(text(f"""
            UPDATE {table} SET {assignments}, updated_at = now()
            WHERE id = :id RETURNING id
        """), {**fields, "id": resource_id})
        saved_id = result.scalar_one_or_none()
        if not saved_id:
            raise HTTPException(status_code=404, detail="资源不存在")
        return saved_id
    columns = ", ".join(fields)
    values = ", ".join(f":{field}" for field in fields)
    return (await db.execute(text(f"""
        INSERT INTO {table} ({columns})
        VALUES ({values}) RETURNING id
    """), fields)).scalar_one()


@router.post("/tools", response_model=ToolOutput, response_model_by_alias=True, status_code=201)
@router.put("/tools/{resource_id}", response_model=ToolOutput, response_model_by_alias=True)
async def save_tool(
    data: ToolInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_id: UUID | None = None,
) -> ToolOutput:
    try:
        saved_id = await _save_capability(db, "tools", data, resource_id)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tool slug 已存在") from error
    return ToolOutput(id=saved_id, **data.model_dump())


@router.post("/mcp-servers", response_model=McpServerOutput, response_model_by_alias=True, status_code=201)
@router.put("/mcp-servers/{resource_id}", response_model=McpServerOutput, response_model_by_alias=True)
async def save_mcp_server(
    data: McpServerInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_id: UUID | None = None,
) -> McpServerOutput:
    try:
        saved_id = await _save_capability(db, "mcp_servers", data, resource_id)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="MCP slug 已存在") from error
    return McpServerOutput(id=saved_id, **data.model_dump())


@router.get("/available", response_model=list[AgentChoiceOutput], response_model_by_alias=True)
async def list_available_agents(
    _user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentChoiceOutput]:
    rows = (await db.execute(text("""
        SELECT id, 'agent' AS kind, name, description, system_prompt
                FROM agents
                WHERE agents.enabled
        UNION ALL
        SELECT id, 'super_agent' AS kind, name, description, system_prompt
                FROM super_agents
                WHERE super_agents.enabled
        ORDER BY kind DESC, name
    """))).mappings()
    return [AgentChoiceOutput.model_validate(dict(row)) for row in rows]


async def _require_capabilities(
    db: AsyncSession,
    table: str,
    capability_ids: list[UUID],
) -> list[UUID]:
    unique_ids = list(dict.fromkeys(capability_ids))
    for capability_id in unique_ids:
        found = await db.scalar(text(f"""
            SELECT 1 FROM {table}
            WHERE id = :id AND enabled
        """), {"id": capability_id})
        if not found:
            raise HTTPException(status_code=400, detail="Tool 或 MCP Server 不存在或不可用")
    return unique_ids


@router.post("", response_model=AgentOutput, response_model_by_alias=True, status_code=201)
async def create_agent(
    data: AgentInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentOutput:
    tool_ids = await _require_capabilities(db, "tools", data.tool_ids)
    mcp_server_ids = await _require_capabilities(db, "mcp_servers", data.mcp_server_ids)
    try:
        agent_id = (await db.execute(text("""
            INSERT INTO agents (
                owner_user_id, name, slug, description, system_prompt, enabled
            ) VALUES (
                :owner_user_id, :name, :slug, :description, :system_prompt, :enabled
            )
            RETURNING id
        """), {
            "owner_user_id": admin_id,
            "name": data.name,
            "slug": data.slug,
            "description": data.description,
            "system_prompt": data.system_prompt,
            "enabled": data.enabled,
        })).scalar_one()
        for tool_id in tool_ids:
            await db.execute(text("""
                INSERT INTO agent_tools (agent_id, tool_id)
                VALUES (:agent_id, :tool_id)
            """), {"agent_id": agent_id, "tool_id": tool_id})
        for mcp_server_id in mcp_server_ids:
            await db.execute(text("""
                INSERT INTO agent_mcp_servers (agent_id, mcp_server_id)
                VALUES (:agent_id, :mcp_server_id)
            """), {"agent_id": agent_id, "mcp_server_id": mcp_server_id})
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Agent slug 已存在") from error
    return AgentOutput.model_validate({
        "id": agent_id,
        "kind": "agent",
        "name": data.name,
        "slug": data.slug,
        "description": data.description,
        "system_prompt": data.system_prompt,
        "enabled": data.enabled,
        "tool_ids": tool_ids,
        "mcp_server_ids": mcp_server_ids,
        "graph_status": "not_generated",
    })


async def _replace_agent_links(
    db: AsyncSession,
    agent_id: UUID,
    tool_ids: list[UUID],
    mcp_server_ids: list[UUID],
) -> None:
    await db.execute(text("DELETE FROM agent_tools WHERE agent_id = :id"), {"id": agent_id})
    await db.execute(text("DELETE FROM agent_mcp_servers WHERE agent_id = :id"), {"id": agent_id})
    for tool_id in tool_ids:
        await db.execute(text("""
            INSERT INTO agent_tools (agent_id, tool_id)
            VALUES (:agent_id, :resource_id)
        """), {"agent_id": agent_id, "resource_id": tool_id})
    for mcp_server_id in mcp_server_ids:
        await db.execute(text("""
            INSERT INTO agent_mcp_servers (agent_id, mcp_server_id)
            VALUES (:agent_id, :resource_id)
        """), {"agent_id": agent_id, "resource_id": mcp_server_id})


@router.put("/{agent_id}", response_model=AgentOutput, response_model_by_alias=True)
async def update_agent(
    agent_id: UUID,
    data: AgentInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentOutput:
    tool_ids = await _require_capabilities(db, "tools", data.tool_ids)
    mcp_server_ids = await _require_capabilities(db, "mcp_servers", data.mcp_server_ids)
    try:
        result = await db.execute(text("""
            UPDATE agents SET name = :name, slug = :slug, description = :description,
                system_prompt = :system_prompt, enabled = :enabled, updated_at = now()
            WHERE id = :id
            RETURNING id
        """), {**data.model_dump(), "id": agent_id})
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Agent 不存在")
        await _replace_agent_links(db, agent_id, tool_ids, mcp_server_ids)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Agent slug 已存在") from error
    return AgentOutput.model_validate({
        **data.model_dump(), "id": agent_id, "kind": "agent",
        "tool_ids": tool_ids, "mcp_server_ids": mcp_server_ids,
        "graph_status": "not_generated",
    })


async def _save_super_agent(
    db: AsyncSession,
    admin_id: UUID,
    data: SuperAgentInput,
    super_agent_id: UUID | None,
) -> UUID:
    agent_ids = await _require_capabilities(db, "agents", data.agent_ids)
    values = data.model_dump(exclude={"agent_ids"})
    if super_agent_id:
        result = await db.execute(text("""
            UPDATE super_agents SET name = :name, slug = :slug, description = :description,
                system_prompt = :system_prompt, enabled = :enabled, updated_at = now()
            WHERE id = :id
            RETURNING id
        """), {**values, "id": super_agent_id})
        saved_id = result.scalar_one_or_none()
        if not saved_id:
            raise HTTPException(status_code=404, detail="Super Agent 不存在")
        await db.execute(text("DELETE FROM super_agent_members WHERE super_agent_id = :id"), {"id": saved_id})
    else:
        saved_id = (await db.execute(text("""
            INSERT INTO super_agents (
                owner_user_id, name, slug, description, system_prompt, enabled
            ) VALUES (
                :admin_id, :name, :slug, :description, :system_prompt, :enabled
            ) RETURNING id
        """), {**values, "admin_id": admin_id})).scalar_one()
    for position, agent_id in enumerate(agent_ids):
        await db.execute(text("""
            INSERT INTO super_agent_members (super_agent_id, agent_id, position)
            VALUES (:super_agent_id, :agent_id, :position)
        """), {"super_agent_id": saved_id, "agent_id": agent_id, "position": position})
    return saved_id


@router.post("/super", response_model=SuperAgentOutput, response_model_by_alias=True, status_code=201)
@router.put("/super/{super_agent_id}", response_model=SuperAgentOutput, response_model_by_alias=True)
async def save_super_agent(
    data: SuperAgentInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    super_agent_id: UUID | None = None,
) -> SuperAgentOutput:
    try:
        saved_id = await _save_super_agent(db, admin_id, data, super_agent_id)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Super Agent slug 已存在或成员重复") from error
    return SuperAgentOutput.model_validate({
        **data.model_dump(), "id": saved_id, "kind": "super_agent",
    })


@router.post("/{agent_id}/graph", response_model=AgentGraphOutput, response_model_by_alias=True)
async def generate_agent_graph(
    agent_id: UUID,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentGraphOutput:
    available = await db.scalar(text("""
        SELECT 1 FROM agents
        WHERE id = :agent_id AND enabled
    """), {"agent_id": agent_id})
    if not available:
                raise HTTPException(status_code=404, detail="Agent 不存在")
    try:
                await get_catalog_agent(db, "agent", agent_id)
    except RuntimeError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
    return AgentGraphOutput(agent_id=agent_id, status="ready")