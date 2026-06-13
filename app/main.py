import asyncio

from fastapi import FastAPI, Response, status

from app.api.routes import achievements, auth, avatar, community, external, ml, npc, photos, profile, quests
from app.core.config import get_settings
from app.services.health_service import check_database, check_redis

settings = get_settings()
app = FastAPI(title=settings.app_name)

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
