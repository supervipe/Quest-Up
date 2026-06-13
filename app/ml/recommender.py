from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quest import QuestTemplate
from app.services.location_service import LocationService
from app.services.recommendation_service import RecommendationService


class QuestRecommender:
    async def recommend(self, db: AsyncSession, lat: float | None, lng: float | None, limit: int = 5) -> list[dict]:
        templates = list(await db.scalars(select(QuestTemplate).where(QuestTemplate.is_active.is_(True))))
        places = await LocationService().find_nearby_places(lat, lng)
        scored = RecommendationService().score_templates(templates, None, places)
        return [
            {"template_id": template.id, "title": template.title, "quest_type": template.quest_type.value, "score": round(score, 3)}
            for template, score in sorted(scored, key=lambda item: item[1], reverse=True)[:limit]
        ]
