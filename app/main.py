from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.users import router as users_router
from app.db import engine
from app.models import Base  # noqa: F401  (registers model metadata)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Allerjeez",
    description="AI-powered food ingredient safety analyser.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "app": "Allerjeez",
        "message": "AI-powered food ingredient safety analyser",
    }
