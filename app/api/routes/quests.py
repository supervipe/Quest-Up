from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_owned_quest
from app.core.constants import QuestSource, QuestStatus
from app.core.database import get_db
from app.core.exceptions import bad_request
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User
from app.schemas.quest import CompleteQuestRequest, QuestCompletionOut, QuestOut, SessionOpenRequest
from app.services.progression_service import ProgressionService
from app.services.quest_generation_service import QuestGenerationService
from app.services.quest_topup_service import QuestTopUpService

router = APIRouter(prefix="/quests", tags=["quests"])


@router.post("/session/open")
async def open_session(payload: SessionOpenRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await QuestTopUpService().open_session(db, current_user, payload.lat, payload.lng, payload.timezone)
    return {
        "normal": [QuestOut.model_validate(q) for q in data["normal"]],
        "weekly": data["weekly"],
        "npc_offer": data["npc_offer"],
        "progression": {"level": current_user.level, "xp": current_user.total_xp, "coins": current_user.coins},
    }


@router.get("/active")
async def active(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quests = list(await db.scalars(select(UserQuest).where(UserQuest.user_id == current_user.id, UserQuest.status.in_([QuestStatus.active, QuestStatus.accepted]))))
    return {
        "normal": [QuestOut.model_validate(q) for q in quests if q.source == QuestSource.normal],
        "npc": [QuestOut.model_validate(q) for q in quests if q.source == QuestSource.npc],
        "weekly": [QuestOut.model_validate(q) for q in quests if q.source == QuestSource.weekly],
    }


@router.post("/generate", response_model=QuestOut)
async def generate(force: bool = Query(False), lat: float | None = None, lng: float | None = None, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quest = await QuestGenerationService().generate_normal_quest(db, current_user, lat, lng, None)
    await db.commit()
    await db.refresh(quest)
    return quest


@router.get("/templates")
async def templates(db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(QuestTemplate).where(QuestTemplate.is_active.is_(True))))


@router.get("/history")
async def history(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(UserQuest).where(UserQuest.user_id == current_user.id, UserQuest.status == QuestStatus.completed)))


@router.get("/{quest_id}", response_model=QuestOut)
async def quest_detail(quest_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_owned_quest(db, current_user.id, quest_id)


@router.post("/{quest_id}/accept", response_model=QuestOut)
async def accept(quest_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quest = await get_owned_quest(db, current_user.id, quest_id)
    if quest.status != QuestStatus.active:
        raise bad_request("Only active quests can be accepted")
    quest.status = QuestStatus.accepted
    from app.core.database import utcnow

    quest.accepted_at = utcnow()
    await db.commit()
    await db.refresh(quest)
    return quest


@router.post("/{quest_id}/skip", response_model=QuestOut)
async def skip(quest_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    quest = await get_owned_quest(db, current_user.id, quest_id)
    if quest.status not in [QuestStatus.active, QuestStatus.accepted]:
        raise bad_request("Only active or accepted quests can be skipped")
    quest.status = QuestStatus.skipped
    await db.commit()
    await db.refresh(quest)
    return quest


@router.post("/{quest_id}/complete", response_model=QuestCompletionOut)
async def complete(quest_id: str, payload: CompleteQuestRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await ProgressionService().complete_quest(db, current_user, quest_id, payload.photo_url, payload.caption, payload.completion_lat, payload.completion_lng, payload.notes, payload.rating, payload.shared_to_community)
