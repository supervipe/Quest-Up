import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import QuestSource, QuestStatus
from app.core.database import utcnow
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User, UserProfile
from app.services.difficulty_service import DifficultyService
from app.services.location_service import LocationService
from app.services.recommendation_service import RecommendationService
from app.services.weather_service import WeatherService


class QuestGenerationService:
    def __init__(self) -> None:
        self.locations = LocationService()
        self.weather = WeatherService()
        self.recommendations = RecommendationService()
        self.difficulty = DifficultyService()

    async def generate_normal_quest(self, db: AsyncSession, user: User, lat: float | None, lng: float | None, timezone: str | None) -> UserQuest:
        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
        radius = float(profile.preferred_radius_km) if profile else 5
        places = await self.locations.find_nearby_places(lat, lng, radius)
        weather = await self.weather.get_current_weather(lat, lng)
        templates = list(await db.scalars(select(QuestTemplate).where(QuestTemplate.is_active.is_(True), QuestTemplate.min_user_level <= user.level)))
        if not templates:
            raise RuntimeError("No quest templates are seeded")
        scored = self.recommendations.score_templates(templates, profile, places)
        chosen = random.choices([item[0] for item in scored], weights=[item[1] for item in scored], k=1)[0]
        place = self._best_place(chosen.location_type, places)
        difficulty = self.difficulty.adapt(chosen.base_difficulty)
        title = chosen.title if not place else f"{chosen.title}: {place['name']}"
        description = chosen.description_template.format(place_name=place["name"] if place else "somewhere nearby")
        quest = UserQuest(
            user_id=user.id,
            template_id=chosen.id,
            source=QuestSource.normal,
            generated_title=title,
            generated_description=description,
            quest_type=chosen.quest_type,
            stat_category=chosen.stat_category,
            difficulty=difficulty,
            xp_reward=chosen.base_xp,
            coin_reward=chosen.base_coins,
            status=QuestStatus.active,
            expires_at=utcnow() + timedelta(days=1),
            target_lat=place["lat"] if place else None,
            target_lng=place["lng"] if place else None,
            target_place_name=place["name"] if place else None,
            target_place_type=place["place_type"] if place else None,
            weather_snapshot=weather,
            context_snapshot={"timezone": timezone, "places": places},
        )
        db.add(quest)
        await db.flush()
        return quest

    def _best_place(self, location_type: str | None, places: list[dict]) -> dict | None:
        if not location_type:
            return None
        return next((place for place in places if place["place_type"] == location_type), None)
