from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MLEventType, QuestStatus
from app.core.database import utcnow
from app.core.exceptions import bad_request
from app.models.ml import MLInteraction
from app.models.quest import UserQuest
from app.models.user import User


class QuestLifecycleService:
    async def accept(self, db: AsyncSession, user: User, quest: UserQuest) -> UserQuest:
        if quest.status != QuestStatus.active:
            raise bad_request("Only active quests can be accepted")
        quest.status = QuestStatus.accepted
        quest.accepted_at = utcnow()
        db.add(self._event(user, quest, MLEventType.accepted))
        await db.commit()
        await db.refresh(quest)
        return quest

    async def skip(self, db: AsyncSession, user: User, quest: UserQuest) -> UserQuest:
        if quest.status not in [QuestStatus.active, QuestStatus.accepted]:
            raise bad_request("Only active or accepted quests can be skipped")
        quest.status = QuestStatus.skipped
        db.add(self._event(user, quest, MLEventType.skipped))
        await db.commit()
        await db.refresh(quest)
        return quest

    def _event(
        self,
        user: User,
        quest: UserQuest,
        event_type: MLEventType,
    ) -> MLInteraction:
        return MLInteraction(
            user_id=user.id,
            user_quest_id=quest.id,
            event_type=event_type,
            quest_type=quest.quest_type,
            difficulty=quest.difficulty,
            context={"source": quest.source.value, "template_id": quest.template_id},
        )
