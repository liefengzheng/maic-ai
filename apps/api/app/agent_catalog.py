from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .agent import get_catalog_agent
from .database import get_db
from .schemas import AgentChoiceOutput, AgentCreateInput, AgentGraphOutput, AgentOutput
from .security import require_admin_user_id, require_user_id

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/available", response_model=list[AgentChoiceOutput], response_model_by_alias=True)
async def list_available_agents(
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentChoiceOutput]:
    rows = (await db.execute(text("""
        WITH current_tenant AS (
            SELECT tenant_id FROM users WHERE id = :user_id
        )
        SELECT id, 'agent' AS kind, name, description, system_prompt
        FROM agents, current_tenant
        WHERE agents.tenant_id = current_tenant.tenant_id
          AND agents.enabled
          AND (agents.owner_user_id = :user_id OR agents.visibility = 'tenant')
        UNION ALL
        SELECT id, 'super_agent' AS kind, name, description, system_prompt
        FROM super_agents, current_tenant
        WHERE super_agents.tenant_id = current_tenant.tenant_id
          AND super_agents.enabled
          AND (super_agents.owner_user_id = :user_id OR super_agents.visibility = 'tenant')
        ORDER BY kind DESC, name
    """), {"user_id": user_id})).mappings()
    return [AgentChoiceOutput.model_validate(dict(row)) for row in rows]


async def _require_capabilities(
    db: AsyncSession,
    tenant_id: UUID,
    table: str,
    capability_ids: list[UUID],
) -> list[UUID]:
    unique_ids = list(dict.fromkeys(capability_ids))
    for capability_id in unique_ids:
        found = await db.scalar(text(f"""
            SELECT 1 FROM {table}
            WHERE id = :id AND tenant_id = :tenant_id AND enabled
        """), {"id": capability_id, "tenant_id": tenant_id})
        if not found:
            raise HTTPException(status_code=400, detail="Tool 或 MCP Server 不存在或不可用")
    return unique_ids


@router.post("", response_model=AgentOutput, response_model_by_alias=True, status_code=201)
async def create_agent(
    data: AgentCreateInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentOutput:
    tenant_id = await db.scalar(text("SELECT tenant_id FROM users WHERE id = :id"), {"id": admin_id})
    tool_ids = await _require_capabilities(db, tenant_id, "tools", data.tool_ids)
    mcp_server_ids = await _require_capabilities(db, tenant_id, "mcp_servers", data.mcp_server_ids)
    try:
        agent_id = (await db.execute(text("""
            INSERT INTO agents (
                tenant_id, owner_user_id, name, slug, description,
                system_prompt, visibility
            ) VALUES (
                :tenant_id, :owner_user_id, :name, :slug, :description,
                :system_prompt, :visibility
            )
            RETURNING id
        """), {
            "tenant_id": tenant_id,
            "owner_user_id": admin_id,
            "name": data.name,
            "slug": data.slug,
            "description": data.description,
            "system_prompt": data.system_prompt,
            "visibility": data.visibility,
        })).scalar_one()
        for tool_id in tool_ids:
            await db.execute(text("""
                INSERT INTO agent_tools (tenant_id, agent_id, tool_id)
                VALUES (:tenant_id, :agent_id, :tool_id)
            """), {"tenant_id": tenant_id, "agent_id": agent_id, "tool_id": tool_id})
        for mcp_server_id in mcp_server_ids:
            await db.execute(text("""
                INSERT INTO agent_mcp_servers (tenant_id, agent_id, mcp_server_id)
                VALUES (:tenant_id, :agent_id, :mcp_server_id)
            """), {"tenant_id": tenant_id, "agent_id": agent_id, "mcp_server_id": mcp_server_id})
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
        "visibility": data.visibility,
        "graph_status": "not_generated",
    })


@router.post("/{agent_id}/graph", response_model=AgentGraphOutput, response_model_by_alias=True)
async def generate_agent_graph(
    agent_id: UUID,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentGraphOutput:
    owned = await db.scalar(text("""
        SELECT 1 FROM agents
        WHERE id = :agent_id AND owner_user_id = :admin_id AND enabled
    """), {"agent_id": agent_id, "admin_id": admin_id})
    if not owned:
      raise HTTPException(status_code=404, detail="Agent 不存在")
    try:
      await get_catalog_agent(db, admin_id, "agent", agent_id)
    except RuntimeError as error:
      raise HTTPException(status_code=422, detail=str(error)) from error
    return AgentGraphOutput(agent_id=agent_id, status="ready")