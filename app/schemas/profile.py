from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import QuestType


class ProfileOut(BaseModel):
    preferred_radius_km: float
    preferred_difficulty: int | None
    preferred_quest_types: list[str]
    timezone: str | None
    home_lat: float | None
    home_lng: float | None
    location_sharing_enabled: bool
    community_sharing_enabled: bool

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    preferred_radius_km: float | None = Field(default=None, gt=0, le=50)
    preferred_difficulty: int | None = Field(default=None, ge=1, le=5)
    preferred_quest_types: list[QuestType] | None = Field(default=None, min_length=1)
    timezone: str | None = Field(default=None, max_length=80)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lng: float | None = Field(default=None, ge=-180, le=180)
    location_sharing_enabled: bool | None = None
    community_sharing_enabled: bool | None = None

    @field_validator("preferred_quest_types")
    @classmethod
    def quest_types_are_unique(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("preferred_quest_types cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def home_coordinates_are_paired(self):
        if (self.home_lat is None) != (self.home_lng is None):
            raise ValueError("home_lat and home_lng must be provided together")
        return self


class StatsOut(BaseModel):
    social_xp: int
    creativity_xp: int
    exploration_xp: int
    knowledge_xp: int
    fitness_xp: int

    model_config = {"from_attributes": True}
