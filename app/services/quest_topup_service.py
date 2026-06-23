from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import NPCOfferStatus, QuestSource, QuestStatus
from app.models.npc import NPCQuestOffer
from app.models.quest import UserQuest
from app.models.user import User
from app.services.quest_generation_service import QuestGenerationService
from app.services.weekly_quest_service import WeeklyQuestService


class QuestTopUpService:
    def __init__(self) -> None:
        self.generator = QuestGenerationService()
        self.weekly = WeeklyQuestService()

    async def open_session(self, db: AsyncSession, user: User, lat: float | None, lng: float | None, timezone: str | None) -> dict:
        settings = get_settings()
        await self.generator.lock_user(db, user.id)
        await self.generator.expire_stale_normal_quests(db, user.id)
        normal = list(await db.scalars(select(UserQuest).where(
            UserQuest.user_id == user.id,
            UserQuest.source == QuestSource.normal,
            UserQuest.status.in_([QuestStatus.active, QuestStatus.accepted]),
        )))
        for _ in range(max(0, settings.normal_active_quest_limit - len(normal))):
            normal.append(await self.generator.generate_normal_quest(db, user, lat, lng, timezone))
        current_weekly = await self.weekly.current_weekly(db)
        weekly = await self.weekly.get_or_create_user_weekly(db, user, current_weekly)
        npc_offer = await db.scalar(select(NPCQuestOffer).where(NPCQuestOffer.user_id == user.id, NPCQuestOffer.status == NPCOfferStatus.offered).order_by(NPCQuestOffer.offered_at.desc()))
        await db.commit()
        return {"normal": normal, "weekly": weekly, "weekly_community": current_weekly, "npc_offer": npc_offer}
