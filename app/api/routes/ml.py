from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_owned_quest
from app.core.database import get_db
from app.ml.difficulty_adapter import DifficultyAdapter
from app.ml.recommender import QuestRecommender
from app.models.ml import MLInteraction
from app.models.user import User
from app.schemas.ml import DifficultyRequest, MLEventRequest, RecommendRequest

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/recommend")
async def recommend(payload: RecommendRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await QuestRecommender().recommend(db, payload.lat, payload.lng, payload.limit)


@router.post("/adapt-difficulty")
async def adapt(payload: DifficultyRequest, current_user: User = Depends(get_current_user)):
    return {"quest_type": payload.quest_type, "difficulty": DifficultyAdapter().adapt(payload.base_difficulty)}


@router.post("/events")
async def event(payload: MLEventRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.user_quest_id:
        await get_owned_quest(db, current_user.id, payload.user_quest_id)
    event = MLInteraction(user_id=current_user.id, **payload.model_dump())
    db.add(event)
    await db.commit()
    return {"id": event.id}


@router.get("/health")
async def health():
    return {"status": "ok", "mode": "fallback-rule-based"}
