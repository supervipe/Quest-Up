from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.models.quest import QuestTemplate
from app.services.location_service import LocationService
from app.services.recommendation_service import RecommendationService
from app.services.weather_service import WeatherService


class QuestRecommender:
    async def recommend(self, db: AsyncSession, lat: float | None, lng: float | None, limit: int = 5) -> list[dict]:
        templates = list(await db.scalars(select(QuestTemplate).where(QuestTemplate.is_active.is_(True))))
        places = await LocationService().find_nearby_places(lat, lng)
        weather = await WeatherService().get_current_weather(lat, lng)
        scored = RecommendationService().score_templates(
            templates,
            None,
            places,
            weather,
            utcnow(),
            [],
        )
        return [
            {
                "template_id": item.template.id,
                "title": item.template.title,
                "quest_type": item.template.quest_type.value,
                "score": round(item.total, 3),
            }
            for item in sorted(scored, key=lambda item: item.total, reverse=True)[:limit]
        ]
