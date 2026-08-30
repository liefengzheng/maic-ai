from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import sys

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .auth import router as auth_router
from .agent_catalog import router as agent_catalog_router
from .config import get_settings
from .conversations import router as conversations_router
from .workshops import router as workshops_router

if sys.version_info[:2] != (3, 12):
    raise RuntimeError("MAIC AI API requires Python 3.12")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


settings = get_settings()
app = FastAPI(title="MAIC AI API", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax", https_only=settings.cookie_secure)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(agent_catalog_router)
app.include_router(conversations_router)
app.include_router(workshops_router)


@app.exception_handler(HTTPException)
async def http_error(_: Request, error: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"message": error.detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"message": "请求数据无效", "issues": error.errors()},
    )


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}