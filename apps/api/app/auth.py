from typing import Annotated, Any
from uuid import UUID, uuid4

import bcrypt
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import get_db
from .schemas import AuthOutput, LoginInput, RegisterInput, UserOutput
from .security import SESSION_COOKIE, issue_session, require_user_id

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
oauth = OAuth()
if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


USER_QUERY = text("""
SELECT u.id, u.tenant_id, t.name AS tenant_name, u.role,
       u.email, u.display_name, u.avatar_url, u.created_at,
       (CASE WHEN u.password_hash IS NULL THEN ARRAY[]::text[]
             ELSE ARRAY['credentials']::text[] END) ||
       COALESCE(array_agg(DISTINCT oa.provider) FILTER (WHERE oa.provider IS NOT NULL), ARRAY[]::text[]) providers
FROM users u
JOIN tenants t ON t.id = u.tenant_id
LEFT JOIN oauth_accounts oa ON oa.user_id = u.id
WHERE u.id = :user_id
GROUP BY u.id, t.name
""")


async def load_user(db: AsyncSession, user_id: UUID) -> UserOutput | None:
    row = (await db.execute(USER_QUERY, {"user_id": user_id})).mappings().first()
    return UserOutput.model_validate(dict(row)) if row else None


def set_session(response: Response, user_id: UUID) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


async def create_tenant(db: AsyncSession, name: str) -> UUID:
    tenant_id = uuid4()
    return (await db.execute(
        text("INSERT INTO tenants (id, name, slug) VALUES (:id, :name, :slug) RETURNING id"),
        {"id": tenant_id, "name": f"{name} Workspace", "slug": f"tenant-{tenant_id}"},
    )).scalar_one()


@router.post("/register", response_model=AuthOutput, response_model_by_alias=True)
async def register(
    data: RegisterInput,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthOutput:
    email = data.email.lower()
    existing = await db.scalar(text("SELECT 1 FROM users WHERE email = :email"), {"email": email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册")
    password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt(rounds=12)).decode()
    tenant_id = await create_tenant(db, data.display_name)
    user_id = (await db.execute(
        text("INSERT INTO users (tenant_id, email, display_name, password_hash, role) VALUES (:tenant_id, :email, :name, :password, 'admin') RETURNING id"),
        {"tenant_id": tenant_id, "email": email, "name": data.display_name, "password": password_hash},
    )).scalar_one()
    await db.commit()
    user = await load_user(db, user_id)
    if user is None:
        raise RuntimeError("Newly created user could not be loaded")
    set_session(response, user.id)
    return AuthOutput(user=user)


@router.post("/login", response_model=AuthOutput, response_model_by_alias=True)
async def login(
    data: LoginInput,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthOutput:
    row = (await db.execute(
        text("SELECT id, password_hash FROM users WHERE email = :email"),
        {"email": data.email.lower()},
    )).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该账号尚未注册，请先注册")
    password_hash = row["password_hash"]
    if not password_hash or not bcrypt.checkpw(data.password.encode(), password_hash.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码不正确")
    user = await load_user(db, row["id"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    set_session(response, user.id)
    return AuthOutput(user=user)


@router.get("/me", response_model=AuthOutput, response_model_by_alias=True)
async def me(
    user_id: Annotated[UUID, Depends(require_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthOutput:
    user = await load_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    return AuthOutput(user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/google")
async def google_login(request: Request) -> Response:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google 登录尚未配置")
    callback = settings.google_callback_url or str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, callback)


@router.get("/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 登录失败") from error
    profile: dict[str, Any] = token.get("userinfo") or {}
    if not profile.get("sub") or not profile.get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google 身份信息不完整")
    account_id = await db.scalar(
        text("SELECT user_id FROM oauth_accounts WHERE provider = 'google' AND provider_account_id = :sub"),
        {"sub": profile["sub"]},
    )
    user_id = account_id
    if user_id is None:
        user_id = await db.scalar(text("SELECT id FROM users WHERE email = :email"), {"email": profile["email"].lower()})
        if user_id is None:
            display_name = profile.get("name") or profile["email"].split("@")[0]
            tenant_id = await create_tenant(db, display_name)
            user_id = (await db.execute(
                text("INSERT INTO users (tenant_id, email, display_name, avatar_url, role) VALUES (:tenant_id, :email, :name, :avatar, 'admin') RETURNING id"),
                {"tenant_id": tenant_id, "email": profile["email"].lower(), "name": display_name, "avatar": profile.get("picture")},
            )).scalar_one()
        await db.execute(
            text("INSERT INTO oauth_accounts (user_id, provider, provider_account_id) VALUES (:user_id, 'google', :sub)"),
            {"user_id": user_id, "sub": profile["sub"]},
        )
    await db.execute(
        text("UPDATE users SET display_name = COALESCE(:name, display_name), avatar_url = COALESCE(:avatar, avatar_url), updated_at = now() WHERE id = :user_id"),
        {"user_id": user_id, "name": profile.get("name"), "avatar": profile.get("picture")},
    )
    await db.commit()
    response = RedirectResponse(f"{settings.web_origins[0]}/chat")
    set_session(response, user_id)
    return response