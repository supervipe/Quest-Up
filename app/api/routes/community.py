from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_owned_quest
from app.core.constants import QuestSource, QuestStatus, WeeklyQuestStatus
from app.core.database import get_db
from app.core.exceptions import bad_request, not_found
from app.models.community import CommunityPost, WeeklyCommunityQuest
from app.models.user import User
from app.schemas.community import CommunityPostOut, CommunitySubmitRequest, WeeklyQuestOut

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/weekly/current", response_model=WeeklyQuestOut | None)
async def current_weekly(db: AsyncSession = Depends(get_db)):
    return await db.scalar(select(WeeklyCommunityQuest).where(WeeklyCommunityQuest.status == WeeklyQuestStatus.active).order_by(WeeklyCommunityQuest.starts_at.desc()))


@router.post("/weekly/{weekly_quest_id}/submit", response_model=CommunityPostOut)
async def submit(weekly_quest_id: str, payload: CommunitySubmitRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    weekly_quest = await db.get(WeeklyCommunityQuest, weekly_quest_id)
    if not weekly_quest:
        raise not_found("Weekly quest not found")
    if weekly_quest.status != WeeklyQuestStatus.active:
        raise bad_request("Weekly quest is not active")
    if payload.user_quest_id:
        user_quest = await get_owned_quest(db, current_user.id, payload.user_quest_id)
        if user_quest.source != QuestSource.weekly or user_quest.status != QuestStatus.completed:
            raise bad_request("Community submissions require a completed weekly quest")
    post = CommunityPost(user_id=current_user.id, weekly_quest_id=weekly_quest_id, user_quest_id=payload.user_quest_id, photo_url=payload.photo_url, caption=payload.caption)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/weekly/{weekly_quest_id}/posts", response_model=list[CommunityPostOut])
async def posts(weekly_quest_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(WeeklyCommunityQuest, weekly_quest_id):
        raise not_found("Weekly quest not found")
    return list(await db.scalars(select(CommunityPost).where(CommunityPost.weekly_quest_id == weekly_quest_id).order_by(CommunityPost.created_at.desc())))


@router.get("/weekly/{weekly_quest_id}/leaderboard")
async def leaderboard(weekly_quest_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(WeeklyCommunityQuest, weekly_quest_id):
        raise not_found("Weekly quest not found")
    posts = list(await db.scalars(select(CommunityPost).where(CommunityPost.weekly_quest_id == weekly_quest_id).order_by(CommunityPost.likes_count.desc(), CommunityPost.created_at.asc())))
    return [{"rank": idx + 1, "user_id": post.user_id, "likes_count": post.likes_count, "post_id": post.id} for idx, post in enumerate(posts)]
