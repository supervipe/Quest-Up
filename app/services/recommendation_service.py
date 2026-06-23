import random
from dataclasses import dataclass
from datetime import datetime

from app.models.quest import QuestTemplate, UserQuest
from app.models.user import UserProfile


@dataclass(frozen=True)
class TemplateScore:
    template: QuestTemplate
    total: float
    context: float
    preference: float
    randomness: float


class RecommendationService:
    def score_templates(
        self,
        templates: list[QuestTemplate],
        profile: UserProfile | None,
        places: list[dict],
        weather: dict,
        local_time: datetime,
        recent_quests: list[UserQuest],
    ) -> list[TemplateScore]:
        place_types = {place["place_type"] for place in places}
        preferred = set(profile.preferred_quest_types if profile else ["location", "social", "action"])
        scored: list[TemplateScore] = []
        for template in templates:
            location_score = self._location_score(template, place_types)
            weather_score = self._weather_score(template, weather.get("condition"))
            time_score = self._time_score(template, local_time.hour)
            context_score = (location_score + weather_score + time_score) / 3

            preferred_score = 1.0 if template.quest_type.value in preferred else 0.35
            behavior_score = self._behavior_score(template, recent_quests)
            repetition_score = self._repetition_score(template, recent_quests)
            preference_score = ((preferred_score + behavior_score) / 2) * repetition_score

            randomness = random.random()
            total = max(0.01, 0.60 * context_score + 0.20 * preference_score + 0.20 * randomness)
            scored.append(
                TemplateScore(
                    template=template,
                    total=total,
                    context=context_score,
                    preference=preference_score,
                    randomness=randomness,
                )
            )
        return scored

    def _location_score(self, template: QuestTemplate, place_types: set[str]) -> float:
        if not template.requires_location:
            return 0.75
        if template.location_type and template.location_type in place_types:
            return 1.0
        return 0.15

    def _weather_score(self, template: QuestTemplate, condition: str | None) -> float:
        rules = template.weather_conditions
        if not rules:
            return 0.75
        allowed = rules.get("conditions", []) if isinstance(rules, dict) else rules
        return 1.0 if condition in allowed else 0.1

    def _time_score(self, template: QuestTemplate, hour: int) -> float:
        rules = template.time_windows
        if not rules:
            return 0.75
        if isinstance(rules, dict) and "start_hour" in rules and "end_hour" in rules:
            start = int(rules["start_hour"])
            end = int(rules["end_hour"])
            matches = start <= hour < end if start <= end else hour >= start or hour < end
            return 1.0 if matches else 0.1
        return 0.75

    def _behavior_score(self, template: QuestTemplate, recent_quests: list[UserQuest]) -> float:
        same_type = [quest for quest in recent_quests if quest.quest_type == template.quest_type]
        if not same_type:
            return 0.5
        positive = sum(quest.status.value in {"accepted", "completed"} for quest in same_type)
        return max(0.2, positive / len(same_type))

    def _repetition_score(self, template: QuestTemplate, recent_quests: list[UserQuest]) -> float:
        if len(recent_quests) >= 2 and all(
            quest.quest_type == template.quest_type for quest in recent_quests[:2]
        ):
            return 0.25
        if recent_quests and recent_quests[0].quest_type == template.quest_type:
            return 0.65
        return 1.0
