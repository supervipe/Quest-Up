import random
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import QuestSource, QuestStatus
from app.core.database import utcnow
from app.core.exceptions import conflict
from app.ml.live_ranker import LiveQuestRanker
from app.models.ml import MLInteraction
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
        self.live_ranker = LiveQuestRanker()

    async def generate_normal_quest(
        self,
        db: AsyncSession,
        user: User,
        lat: float | None,
        lng: float | None,
        timezone: str | None,
        force: bool = False,
    ) -> UserQuest:
        await self.lock_user(db, user.id)
        await self.expire_stale_normal_quests(db, user.id)
        active_count = await self.count_active_normal_quests(db, user.id)
        settings = get_settings()
        if active_count >= settings.normal_active_quest_limit and not force:
            raise conflict(
                f"Normal quest limit reached ({settings.normal_active_quest_limit} active quests)"
            )

        profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
        radius = float(profile.preferred_radius_km) if profile else 5
        places = await self.locations.find_nearby_places(lat, lng, radius)
        weather = await self.weather.get_current_weather(lat, lng)
        recent_quests = list(
            await db.scalars(
                select(UserQuest)
                .where(UserQuest.user_id == user.id, UserQuest.source == QuestSource.normal)
                .order_by(UserQuest.assigned_at.desc())
                .limit(8)
            )
        )
        templates = list(
            await db.scalars(
                select(QuestTemplate).where(
                    QuestTemplate.is_active.is_(True),
                    QuestTemplate.min_user_level <= user.level,
                )
            )
        )
        if not templates:
            raise RuntimeError("No quest templates are seeded")

        candidates = self._avoid_recent_templates(templates, recent_quests)
        local_time = self._local_time(timezone or (profile.timezone if profile else None))
        scored = self.recommendations.score_templates(
            candidates,
            profile,
            places,
            weather,
            local_time,
            recent_quests,
        )
        model_scores = self.live_ranker.score_templates(
            user=user,
            profile=profile,
            templates=[item.template for item in scored],
            places=places,
            weather=weather,
            local_time=local_time,
            recent_quests=recent_quests,
        )
        hybrid_weights = [
            self._hybrid_score(item.total, model_scores.get(item.template.id))
            for item in scored
        ]
        selected = random.choices(scored, weights=hybrid_weights, k=1)[0]
        selected_model_score = model_scores.get(selected.template.id)
        selected_hybrid_score = self._hybrid_score(selected.total, selected_model_score)
        chosen = selected.template
        place = self._best_place(chosen.location_type, places)
        preferred_difficulty = profile.preferred_difficulty if profile else None
        base_difficulty = preferred_difficulty or chosen.base_difficulty
        difficulty = self.difficulty.adapt(base_difficulty)
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
            context_snapshot={
                "timezone": timezone,
                "local_hour": local_time.hour,
                "place_types": sorted({place["place_type"] for place in places}),
                "selection_score": round(selected.total, 4),
                "model_interest_score": round(selected_model_score, 4) if selected_model_score is not None else None,
                "hybrid_selection_score": round(selected_hybrid_score, 4),
                "ranking_model": self.live_ranker.metadata if self.live_ranker.available else None,
                "score_components": {
                    "context": round(selected.context, 4),
                    "preference": round(selected.preference, 4),
                    "randomness": round(selected.randomness, 4),
                    "model": round(selected_model_score, 4) if selected_model_score is not None else None,
                    "hybrid": round(selected_hybrid_score, 4),
                },
            },
        )
        db.add(quest)
        await db.flush()
        db.add(
            MLInteraction(
                user_id=user.id,
                user_quest_id=quest.id,
                event_type="shown",
                quest_type=quest.quest_type,
                difficulty=quest.difficulty,
                context={
                    "source": "normal",
                    "template_id": chosen.id,
                    "user_level": user.level,
                    "preferred_quest_types": profile.preferred_quest_types if profile else None,
                    "preferred_difficulty": profile.preferred_difficulty if profile else None,
                    "local_hour": local_time.hour,
                    "place_types": sorted({place["place_type"] for place in places}),
                    "weather_condition": weather.get("condition"),
                    "rule_selection_score": round(selected.total, 4),
                    "model_interest_score": round(selected_model_score, 4) if selected_model_score is not None else None,
                    "hybrid_selection_score": round(selected_hybrid_score, 4),
                    "ranking_model": self.live_ranker.metadata if self.live_ranker.available else None,
                    "rule_context_score": round(selected.context, 4),
                    "rule_preference_score": round(selected.preference, 4),
                    "rule_randomness_score": round(selected.randomness, 4),
                },
            )
        )
        return quest

    async def lock_user(self, db: AsyncSession, user_id: str) -> None:
        await db.execute(select(User.id).where(User.id == user_id).with_for_update())

    async def count_active_normal_quests(self, db: AsyncSession, user_id: str) -> int:
        quests = await db.scalars(
            select(UserQuest.id).where(
                UserQuest.user_id == user_id,
                UserQuest.source == QuestSource.normal,
                UserQuest.status.in_([QuestStatus.active, QuestStatus.accepted]),
            )
        )
        return len(list(quests))

    async def expire_stale_normal_quests(self, db: AsyncSession, user_id: str) -> None:
        await db.execute(
            update(UserQuest)
            .where(
                UserQuest.user_id == user_id,
                UserQuest.source == QuestSource.normal,
                UserQuest.status.in_([QuestStatus.active, QuestStatus.accepted]),
                UserQuest.expires_at.is_not(None),
                UserQuest.expires_at <= utcnow(),
            )
            .values(status=QuestStatus.expired)
            .execution_options(synchronize_session=False)
        )

    def _avoid_recent_templates(
        self,
        templates: list[QuestTemplate],
        recent_quests: list[UserQuest],
    ) -> list[QuestTemplate]:
        active_template_ids = {
            quest.template_id
            for quest in recent_quests
            if quest.status in [QuestStatus.active, QuestStatus.accepted] and quest.template_id
        }
        without_active_duplicates = [
            template for template in templates if template.id not in active_template_ids
        ]
        candidates = without_active_duplicates or templates

        recent_template_ids = {
            quest.template_id for quest in recent_quests[:4] if quest.template_id
        }
        without_recent = [
            template for template in candidates if template.id not in recent_template_ids
        ]
        return without_recent or candidates

    def _local_time(self, timezone_name: str | None):
        if not timezone_name:
            return utcnow()
        try:
            return utcnow().astimezone(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            return utcnow()

    def _best_place(self, location_type: str | None, places: list[dict]) -> dict | None:
        if not location_type:
            return None
        matches = [place for place in places if place["place_type"] == location_type]
        return min(matches, key=lambda place: place.get("distance_m", float("inf")), default=None)

    def _hybrid_score(self, rule_score: float, model_score: float | None) -> float:
        if model_score is None:
            return rule_score
        return max(0.01, 0.65 * rule_score + 0.35 * model_score)
