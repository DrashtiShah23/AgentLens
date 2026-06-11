"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import evaluations, health, investigations, metrics, runs
from observatory.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Failure Observatory API",
    description="Agent reliability observability — read-only metrics and validated run ingestion.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(runs.router)
app.include_router(evaluations.router)
app.include_router(metrics.router)
app.include_router(investigations.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "AI Failure Observatory", "docs": "/docs"}
