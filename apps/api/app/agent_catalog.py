from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
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
    SkillInput,
    SkillOutput,
    SuperAgentInput,
    SuperAgentOutput,
)
from .runtime.skills import registry as skill_registry
from .security import require_admin_user_id, require_user_id

router = APIRouter(prefix="/agents", tags=["agents"])

SKILL_JSON_BINDINGS = (
    bindparam("input_schema", type_=JSONB),
    bindparam("output_schema", type_=JSONB),
    bindparam("execution_config", type_=JSONB),
)


@router.get("/catalog", response_model=AgentCatalogOutput, response_model_by_alias=True)
async def get_agent_catalog(
    _admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentCatalogOutput:
    skills = (await db.execute(text("""
        SELECT id, skill_code, skill_name, description, skill_type, handler,
               input_schema, output_schema, execution_config, enabled, version
        FROM skill_registry ORDER BY skill_name
    """))).mappings()
    agents = (await db.execute(text("""
        SELECT agents.id, 'agent' AS kind, agents.name, agents.slug,
               agents.description, agents.system_prompt,
               agents.enabled, 'not_generated' AS graph_status,
               COALESCE(array_agg(DISTINCT agent_skills.skill_id)
                   FILTER (WHERE agent_skills.skill_id IS NOT NULL), '{}') AS skill_ids
        FROM agents
        LEFT JOIN agent_skills ON agent_skills.agent_id = agents.id
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
        "skills": [dict(row) for row in skills],
        "skill_handlers": skill_registry.list_handlers(),
        "agents": [dict(row) for row in agents],
        "super_agents": [dict(row) for row in super_agents],
    })


@router.post("/skills", response_model=SkillOutput, response_model_by_alias=True, status_code=201)
@router.put("/skills/{resource_id}", response_model=SkillOutput, response_model_by_alias=True)
async def save_skill(
    data: SkillInput,
    _admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    resource_id: int | None = None,
) -> SkillOutput:
    if data.handler not in skill_registry.list_handlers():
        raise HTTPException(status_code=400, detail="Skill handler 不存在")
    if data.input_schema.get("type") != "object":
        raise HTTPException(status_code=400, detail="inputSchema 根类型必须是 object")
    values = data.model_dump()
    try:
        if resource_id is None:
            statement = text("""
                INSERT INTO skill_registry (
                    skill_code, skill_name, description, skill_type, handler,
                    input_schema, output_schema, execution_config, enabled, version
                ) VALUES (
                    :skill_code, :skill_name, :description, :skill_type, :handler,
                    :input_schema, :output_schema, :execution_config, :enabled, :version
                ) RETURNING id
            """).bindparams(*SKILL_JSON_BINDINGS)
            saved_id = (await db.execute(statement, values)).scalar_one()
        else:
            statement = text("""
                UPDATE skill_registry SET
                    skill_code = :skill_code, skill_name = :skill_name,
                    description = :description, skill_type = :skill_type,
                    handler = :handler, input_schema = :input_schema,
                    output_schema = :output_schema, execution_config = :execution_config,
                    enabled = :enabled, version = :version, updated_at = now()
                WHERE id = :id RETURNING id
            """).bindparams(*SKILL_JSON_BINDINGS)
            result = await db.execute(statement, {**values, "id": resource_id})
            saved_id = result.scalar_one_or_none()
            if saved_id is None:
                raise HTTPException(status_code=404, detail="Skill 不存在")
            await db.execute(text("""
                UPDATE agents SET updated_at = now()
                FROM agent_skills
                WHERE agent_skills.agent_id = agents.id
                  AND agent_skills.skill_id = :skill_id
            """), {"skill_id": saved_id})
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Skill code 已存在") from error
    return SkillOutput(id=saved_id, **values)


@router.delete("/skills/{resource_id}", status_code=204)
async def delete_skill(
    resource_id: int,
    _admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    skill_id = (await db.execute(text("""
        SELECT id FROM skill_registry
        WHERE id = :id
        FOR UPDATE
    """), {"id": resource_id})).scalar_one_or_none()
    if skill_id is None:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Skill 不存在")

    is_assigned = await db.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM agent_skills WHERE skill_id = :skill_id
        )
    """), {"skill_id": skill_id})
    if is_assigned:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Skill 已关联 Agent，无法删除")

    await db.execute(
        text("DELETE FROM skill_registry WHERE id = :id"),
        {"id": skill_id},
    )
    await db.commit()


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
    capability_ids: list[UUID] | list[int],
) -> list[UUID] | list[int]:
    unique_ids = list(dict.fromkeys(capability_ids))
    for capability_id in unique_ids:
        found = await db.scalar(text(f"""
            SELECT 1 FROM {table}
            WHERE id = :id AND enabled
        """), {"id": capability_id})
        if not found:
            raise HTTPException(status_code=400, detail="关联能力不存在或不可用")
    return unique_ids


@router.post("", response_model=AgentOutput, response_model_by_alias=True, status_code=201)
async def create_agent(
    data: AgentInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentOutput:
    skill_ids = await _require_capabilities(db, "skill_registry", data.skill_ids)
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
        for skill_id in skill_ids:
            await db.execute(text("""
                INSERT INTO agent_skills (agent_id, skill_id)
                VALUES (:agent_id, :skill_id)
            """), {"agent_id": agent_id, "skill_id": skill_id})
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
        "skill_ids": skill_ids,
        "graph_status": "not_generated",
    })


async def _replace_agent_links(
    db: AsyncSession,
    agent_id: UUID,
    skill_ids: list[int],
) -> None:
    await db.execute(text("DELETE FROM agent_skills WHERE agent_id = :id"), {"id": agent_id})
    for skill_id in skill_ids:
        await db.execute(text("""
            INSERT INTO agent_skills (agent_id, skill_id)
            VALUES (:agent_id, :resource_id)
        """), {"agent_id": agent_id, "resource_id": skill_id})


@router.put("/{agent_id}", response_model=AgentOutput, response_model_by_alias=True)
async def update_agent(
    agent_id: UUID,
    data: AgentInput,
    admin_id: Annotated[UUID, Depends(require_admin_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentOutput:
    skill_ids = await _require_capabilities(db, "skill_registry", data.skill_ids)
    try:
        result = await db.execute(text("""
            UPDATE agents SET name = :name, slug = :slug, description = :description,
                system_prompt = :system_prompt, enabled = :enabled, updated_at = now()
            WHERE id = :id
            RETURNING id
        """), {**data.model_dump(), "id": agent_id})
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Agent 不存在")
        await _replace_agent_links(db, agent_id, skill_ids)
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Agent slug 已存在") from error
    return AgentOutput.model_validate({
        **data.model_dump(), "id": agent_id, "kind": "agent",
        "skill_ids": skill_ids,
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