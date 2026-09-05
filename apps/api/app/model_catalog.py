from dataclasses import dataclass
import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .llm import LlmModelConfig, create_chat_model
from .llm.providers.azure_openai import AzureOpenAiSettings
from .schemas import LlmModelOutput
from .security import require_user_id

router = APIRouter(prefix="/models", tags=["models"])


@dataclass(frozen=True)
class CatalogModel:
    id: UUID
    name: str
    config: LlmModelConfig
    updated_at: str


MODEL_COLUMNS = "id, name, provider, model, api_key, connection_config, updated_at"


def _catalog_model(row: dict) -> CatalogModel:
    return CatalogModel(
        id=row["id"],
        name=row["name"],
        config=LlmModelConfig(
            provider=row["provider"],
            model=row["model"],
            api_key=row["api_key"],
            connection_config=row["connection_config"] or {},
        ),
        updated_at=row["updated_at"].isoformat(),
    )


async def bootstrap_legacy_model(db: AsyncSession) -> None:
    if not await db.scalar(text("SELECT 1 FROM llm_models LIMIT 1")):
        settings = AzureOpenAiSettings()
        if not settings.endpoint or not settings.api_key or not settings.deployment:
            return
        await db.execute(text("""
            INSERT INTO llm_models (name, provider, model, api_key, connection_config, enabled, is_default)
            VALUES (:name, 'azure_openai', :model, :api_key, CAST(:connection_config AS jsonb), true, true)
        """), {
            "name": settings.deployment,
            "model": settings.deployment,
            "api_key": settings.api_key,
            "connection_config": json.dumps({
                "endpoint": settings.endpoint,
                "apiVersion": settings.api_version,
                "deployment": settings.deployment,
            }),
        })
    await db.execute(text("""
        UPDATE conversations SET model_id = (
            SELECT id FROM llm_models WHERE enabled ORDER BY is_default DESC, created_at LIMIT 1
        )
        WHERE model_id IS NULL
    """))
    await db.commit()


async def get_model(db: AsyncSession, model_id: UUID | None) -> CatalogModel:
    if model_id is None:
        row = (await db.execute(text(f"""
            SELECT {MODEL_COLUMNS} FROM llm_models
            WHERE enabled ORDER BY is_default DESC, created_at LIMIT 1
        """))).mappings().first()
    else:
        row = (await db.execute(text(f"""
            SELECT {MODEL_COLUMNS} FROM llm_models WHERE id = :id AND enabled
        """), {"id": model_id})).mappings().first()
    if row is None:
        raise RuntimeError("没有可用的模型配置")
    return _catalog_model(dict(row))


async def warm_available_models(db: AsyncSession) -> tuple[int, int]:
    rows = (await db.execute(text(f"SELECT {MODEL_COLUMNS} FROM llm_models WHERE enabled"))).mappings()
    ready = 0
    failed = 0
    for row in rows:
        try:
            create_chat_model(_catalog_model(dict(row)).config)
            ready += 1
        except RuntimeError:
            failed += 1
    return ready, failed


@router.get("/available", response_model=list[LlmModelOutput], response_model_by_alias=True)
async def list_available_models(
    _: UUID = Depends(require_user_id),
    db: AsyncSession = Depends(get_db),
) -> list[LlmModelOutput]:
    rows = (await db.execute(text("""
        SELECT id, name, provider, model FROM llm_models
        WHERE enabled ORDER BY is_default DESC, name
    """))).mappings()
    return [LlmModelOutput.model_validate(dict(row)) for row in rows]