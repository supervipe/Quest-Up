from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.ml.live_ranker import LiveQuestRanker
from app.models.quest import QuestTemplate
from app.models.user import User, UserProfile
from app.services.location_service import LocationService
from app.services.recommendation_service import RecommendationService
from app.services.weather_service import WeatherService


class QuestRecommender:
    def __init__(self) -> None:
        self.live_ranker = LiveQuestRanker()

    async def recommend(self, db: AsyncSession, user: User | None, lat: float | None, lng: float | None, limit: int = 5) -> list[dict]:
        templates = list(await db.scalars(select(QuestTemplate).where(QuestTemplate.is_active.is_(True))))
        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id)) if user else None
        places = await LocationService().find_nearby_places(lat, lng)
        weather = await WeatherService().get_current_weather(lat, lng)
        local_time = utcnow()
        scored = RecommendationService().score_templates(
            templates,
            profile,
            places,
            weather,
            local_time,
            [],
        )
        model_scores = self.live_ranker.score_templates(
            user=user,
            profile=profile,
            templates=[item.template for item in scored],
            places=places,
            weather=weather,
            local_time=local_time,
            recent_quests=[],
        ) if user else {}
        ranked = [
            {
                "item": item,
                "model_score": model_scores.get(item.template.id),
                "hybrid_score": self._hybrid_score(item.total, model_scores.get(item.template.id)),
            }
            for item in scored
        ]
        return [
            {
                "template_id": row["item"].template.id,
                "title": row["item"].template.title,
                "quest_type": row["item"].template.quest_type.value,
                "score": round(row["hybrid_score"], 3),
                "rule_score": round(row["item"].total, 3),
                "model_score": round(row["model_score"], 3) if row["model_score"] is not None else None,
                "ranking_model": self.live_ranker.metadata if self.live_ranker.available else None,
            }
            for row in sorted(ranked, key=lambda row: row["hybrid_score"], reverse=True)[:limit]
        ]

    def _hybrid_score(self, rule_score: float, model_score: float | None) -> float:
        if model_score is None:
            return rule_score
        return max(0.01, 0.65 * rule_score + 0.35 * model_score)
