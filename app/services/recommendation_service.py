import random

from app.models.quest import QuestTemplate
from app.models.user import UserProfile


class RecommendationService:
    def score_templates(self, templates: list[QuestTemplate], profile: UserProfile | None, places: list[dict]) -> list[tuple[QuestTemplate, float]]:
        place_types = {place["place_type"] for place in places}
        preferred = set(profile.preferred_quest_types if profile else ["location", "social", "action"])
        scored = []
        for template in templates:
            score = 1.0
            if template.location_type and template.location_type in place_types:
                score += 3.0
            if template.quest_type.value in preferred:
                score += 1.5
            score += random.random()
            scored.append((template, score))
        return scored
