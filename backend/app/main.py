"""Application entrypoint.

Composition root: builds the FastAPI app, mounts the API routers under /api,
and (in production) serves the built React SPA as static files from the same
origin — so the whole portal ships as a single container with no CORS in prod.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routers import auth, dashboards, folders, me, reports
from .config import settings
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed reference data (folders + demo content) unless explicitly disabled.
    if os.getenv("SEED_ON_STARTUP", "true").lower() == "true":
        from .seed import seed

        seed()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Governed, AI-native BI portal with Okta OAuth + RBAC.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(folders.router)
app.include_router(reports.router)
app.include_router(dashboards.router)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "auth_mode": settings.auth_mode,
        "data_backend": "snowflake" if settings.snowflake_configured else "synthetic",
        "insight_backend": "claude" if settings.claude_configured else "mock",
    }


# --------------------------------------------------------------------------- #
# Static SPA hosting (production single-container mode).
# In dev the React app runs on Vite (:5173) and proxies /api to this server.
# --------------------------------------------------------------------------- #
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "static"

if _FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_catch_all(full_path: str):
        # Anything that isn't an API route falls through to index.html so the
        # client-side router can handle it (SPA deep-links).
        index = _FRONTEND_DIST / "index.html"
        return FileResponse(index)
