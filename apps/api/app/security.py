from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db

SESSION_COOKIE = "maic_session"


def issue_session(user_id: UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=7)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )


def read_session(token: str | None) -> UUID | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None


async def require_user_id(
    maic_session: Annotated[str | None, Cookie()] = None,
) -> UUID:
    user_id = read_session(maic_session)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return user_id


async def require_admin_user_id(
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UUID:
    role = await db.scalar(text("SELECT role FROM users WHERE id = :id"), {"id": user_id})
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可以管理 Agent")
    return user_id