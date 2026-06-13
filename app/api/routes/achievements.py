from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.achievement import Achievement, UserAchievement
from app.models.user import User

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
async def achievements(db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(Achievement).where(Achievement.is_active.is_(True))))


@router.get("/progress")
async def progress(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(UserAchievement).where(UserAchievement.user_id == current_user.id)))
