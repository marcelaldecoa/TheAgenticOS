"""Agent Governance Runtime — FastAPI application.

Entry point for the AGR server. Provides:
- Agent Registry API (/registry/*)
- Audit Trail API (/audit/*)
- Health check (/health)
- Auto-generated OpenAPI docs (/docs)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agr_server import __version__
from agr_server.api import audit as audit_api
from agr_server.api import registry as registry_api
from agr_server.config import settings
from agr_server.store.sqlite import SQLiteStore

store = SQLiteStore(db_path=settings.db_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and tear down the store on server start/stop."""
    await store.initialize()
    registry_api.set_store(store)
    audit_api.set_store(store)
    yield
    await store.close()


app = FastAPI(
    title="Agent Governance Runtime",
    description=(
        "A DAPR-like governance runtime for AI agents across heterogeneous platforms. "
        "Provides agent registry, audit trail, capability management, and policy enforcement."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(registry_api.router)
app.include_router(audit_api.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "store": "sqlite",
    }


def run() -> None:
    """CLI entry point for ``agr-server``."""
    uvicorn.run(
        "agr_server.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
