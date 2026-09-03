from collections.abc import AsyncIterator
import json
import logging
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .agent import get_agent, get_catalog_agent, stream_agent
from .database import get_db
from .schemas import ApprovalInput, ChatMessageOutput, ChatRunInput, ConversationInput, ConversationOutput
from .security import require_user_id

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)


async def _claim_conversation_run(
    db: AsyncSession,
    conversation_id: UUID,
    run_id: UUID,
) -> bool:
    claimed_run_id = await db.scalar(
        text("""
            INSERT INTO conversation_runs (conversation_id, run_id)
            VALUES (:conversation_id, :run_id)
            ON CONFLICT (conversation_id) DO UPDATE
            SET run_id = EXCLUDED.run_id, started_at = now()
            WHERE conversation_runs.started_at < now() - interval '1 hour'
            RETURNING run_id
        """),
        {"conversation_id": conversation_id, "run_id": run_id},
    )
    return claimed_run_id == run_id


async def _release_conversation_run(
    db: AsyncSession,
    conversation_id: UUID,
    run_id: UUID,
) -> None:
    await db.execute(
        text("""
            DELETE FROM conversation_runs
            WHERE conversation_id = :conversation_id AND run_id = :run_id
        """),
        {"conversation_id": conversation_id, "run_id": run_id},
    )
    await db.commit()

CONVERSATION_SELECT = """
SELECT c.id, c.title, c.created_at, c.updated_at,
       CASE WHEN c.agent_id IS NOT NULL THEN 'agent'
            WHEN c.super_agent_id IS NOT NULL THEN 'super_agent' END AS target_kind,
       COALESCE(c.agent_id, c.super_agent_id) AS target_id,
       COALESCE(a.name, s.name) AS target_name,
    COALESCE(a.slug, s.slug) AS target_slug,
       COALESCE(a.system_prompt, s.system_prompt) AS system_prompt
FROM conversations c
LEFT JOIN agents a ON a.id = c.agent_id
LEFT JOIN super_agents s ON s.id = c.super_agent_id
"""


async def require_conversation(db: AsyncSession, conversation_id: UUID, user_id: UUID) -> dict:
    found = (await db.execute(
        text(CONVERSATION_SELECT + " WHERE c.id = :id AND c.user_id = :user_id"),
        {"id": conversation_id, "user_id": user_id},
    )).mappings().first()
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return dict(found)


@router.get("", response_model=list[ConversationOutput], response_model_by_alias=True)
async def list_conversations(
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConversationOutput]:
    rows = (await db.execute(
        text(CONVERSATION_SELECT + " WHERE c.user_id = :user_id ORDER BY c.updated_at DESC"),
        {"user_id": user_id},
    )).mappings()
    return [ConversationOutput.model_validate(dict(row)) for row in rows]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(
        text("DELETE FROM conversations WHERE id = :id AND user_id = :user_id RETURNING id"),
        {"id": conversation_id, "user_id": user_id},
    )
    if result.scalar_one_or_none() is None:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    await db.commit()


@router.post("", response_model=ConversationOutput, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationInput,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationOutput:
    if (data.target_kind is None) != (data.target_id is None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent 类型和 ID 必须同时提供")
    agent_id = None
    super_agent_id = None
    if data.target_kind and data.target_id:
        table = "agents" if data.target_kind == "agent" else "super_agents"
        visible = await db.scalar(text(f"""
            SELECT 1 FROM {table}
                        WHERE id = :target_id AND enabled
                """), {"target_id": data.target_id})
        if not visible:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent 不存在或不可用")
        if data.target_kind == "agent":
            agent_id = data.target_id
        else:
            super_agent_id = data.target_id
    row = (await db.execute(
        text("""
            INSERT INTO conversations (user_id, title, agent_id, super_agent_id)
            VALUES (:user_id, :title, :agent_id, :super_agent_id)
            RETURNING id
        """),
        {"user_id": user_id, "title": data.title, "agent_id": agent_id, "super_agent_id": super_agent_id},
    )).scalar_one()
    await db.commit()
    created = await require_conversation(db, row, user_id)
    return ConversationOutput.model_validate(created)


@router.get("/{conversation_id}/messages", response_model=list[ChatMessageOutput], response_model_by_alias=True)
async def list_messages(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChatMessageOutput]:
    await require_conversation(db, conversation_id, user_id)
    rows = (await db.execute(
        text("SELECT id, role, content, created_at FROM chat_messages WHERE conversation_id = :id ORDER BY created_at"),
        {"id": conversation_id},
    )).mappings()
    return [ChatMessageOutput.model_validate(dict(row)) for row in rows]


async def _conversation_agent(db: AsyncSession, conversation: dict) -> object:
    target_id = conversation.get("target_id")
    if target_id:
        return await get_catalog_agent(db, conversation["target_kind"], target_id)
    return await get_agent()


async def _pending_approvals(agent: object, conversation_id: UUID) -> list[dict]:
    return []


@router.get("/{conversation_id}/approval")
async def get_conversation_approval(
    conversation_id: UUID,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, list[dict]]:
    conversation = await require_conversation(db, conversation_id, user_id)
    try:
        agent = await _conversation_agent(db, conversation)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return {"requests": await _pending_approvals(agent, conversation_id)}


def _stream_response(
    db: AsyncSession,
    agent: object,
    conversation: dict,
    messages: list[dict[str, str]],
    user_id: UUID,
    conversation_id: UUID,
    run_id: UUID,
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        final_content = ""
        try:
            async for event_type, payload in stream_agent(
                agent,
                messages,
                user_id,
                conversation_id,
                root_agent_name=conversation.get("target_slug") or "coordinator",
            ):
                if event_type == "done":
                    final_content = json.loads(payload.split("data: ", 1)[1])["content"]
                yield payload
            if final_content:
                await db.execute(
                    text("INSERT INTO chat_messages (conversation_id, role, content) VALUES (:id, 'assistant', :content)"),
                    {"id": conversation_id, "content": final_content},
                )
                await db.commit()
        except Exception:
            logger.exception("Agent run failed", extra={"conversation_id": str(conversation_id)})
            await db.rollback()
            yield "event: error\ndata: {\"message\": \"Agent 执行失败\"}\n\n"
        finally:
            try:
                await _release_conversation_run(db, conversation_id, run_id)
            except Exception:
                logger.exception(
                    "Failed to release conversation run",
                    extra={"conversation_id": str(conversation_id), "run_id": str(run_id)},
                )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/{conversation_id}/runs")
async def run_conversation(
    conversation_id: UUID,
    data: ChatRunInput,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    conversation = await require_conversation(db, conversation_id, user_id)
    try:
        agent = await _conversation_agent(db, conversation)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    run_id = uuid4()
    if not await _claim_conversation_run(db, conversation_id, run_id):
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该对话正在回复，请稍候")
    try:
        await db.execute(
            text("INSERT INTO chat_messages (conversation_id, role, content) VALUES (:id, 'user', :content)"),
            {"id": conversation_id, "content": data.content},
        )
        await db.execute(
            text("UPDATE conversations SET updated_at = now(), title = CASE WHEN title = '新对话' THEN left(:content, 160) ELSE title END WHERE id = :id"),
            {"id": conversation_id, "content": data.content},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        await _release_conversation_run(db, conversation_id, run_id)
        raise
    rows = (await db.execute(
        text("SELECT role, content FROM chat_messages WHERE conversation_id = :id ORDER BY created_at"),
        {"id": conversation_id},
    )).mappings()
    messages = [{"role": row["role"], "content": row["content"]} for row in rows]

    return _stream_response(
        db, agent, conversation, messages, user_id, conversation_id, run_id
    )


@router.post("/{conversation_id}/runs/resume")
async def resume_conversation(
    conversation_id: UUID,
    data: ApprovalInput,
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Checkpoint 已禁用，无法恢复待确认操作",
    )