from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import not_found
from app.models.user import User, UserProfile, UserStats
from app.schemas.profile import ProfileOut, ProfileUpdate, StatsOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
async def get_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if not profile:
        raise not_found("Profile not found")
    return profile


@router.put("", response_model=ProfileOut)
async def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == current_user.id))
    if not profile:
        raise not_found("Profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "preferred_quest_types" and value is not None:
            value = [quest_type.value for quest_type in value]
        setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/stats", response_model=StatsOut)
async def get_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stats = await db.scalar(select(UserStats).where(UserStats.user_id == current_user.id))
    if not stats:
        raise not_found("Stats not found")
    return stats


@router.get("/progression")
async def progression(current_user: User = Depends(get_current_user)):
    return {"total_xp": current_user.total_xp, "level": current_user.level, "coins": current_user.coins, "current_streak": current_user.current_streak}
