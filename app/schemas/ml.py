from pydantic import BaseModel, Field

from app.core.constants import MLEventType, QuestType


class RecommendRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)
    limit: int = Field(default=5, ge=1, le=20)


class DifficultyRequest(BaseModel):
    quest_type: QuestType
    base_difficulty: int = Field(ge=1, le=5)


class MLEventRequest(BaseModel):
    user_quest_id: str | None = None
    event_type: MLEventType
    quest_type: QuestType | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    rating: int | None = Field(default=None, ge=1, le=5)
    context: dict | None = None


class TrainingDatasetPreviewRequest(BaseModel):
    include_unlabeled: bool = False
    limit: int = Field(default=20, ge=1, le=200)
