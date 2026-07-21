import asyncio
import contextlib

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import achievements, auth, avatar, community, external, ml, npc, photos, profile, quests
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.services.health_service import check_database, check_redis
from app.services.weekly_quest_service import WeeklyQuestService

settings = get_settings()
weekly_rollover_task: asyncio.Task | None = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global weekly_rollover_task
    weekly_rollover_task = asyncio.create_task(_weekly_rollover_loop())
    try:
        yield
    finally:
        if weekly_rollover_task:
            weekly_rollover_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await weekly_rollover_task


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(quests.router)
app.include_router(photos.router)
app.include_router(achievements.router)
app.include_router(avatar.router)
app.include_router(community.router)
app.include_router(npc.router)
app.include_router(ml.router)
app.include_router(external.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/health/ready")
async def readiness(response: Response):
    database_ok, redis_ok = await asyncio.gather(check_database(), check_redis())
    ready = database_ok and redis_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": {"database": database_ok, "redis": redis_ok},
    }


async def _weekly_rollover_loop():
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await WeeklyQuestService().ensure_current_weekly(db)
                await db.commit()
        except Exception:
            # Keep the API alive if the scheduler races database startup; the
            # next iteration and request-time rollover will try again.
            pass
        await asyncio.sleep(settings.weekly_rollover_interval_seconds)
