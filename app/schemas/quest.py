from pydantic import BaseModel, Field, model_validator


class SessionOpenRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)
    weather: dict | None = None

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be provided together")
        return self


class CompleteQuestRequest(BaseModel):
    photo_url: str | None = Field(default=None, max_length=2048)
    caption: str | None = Field(default=None, max_length=500)
    completion_lat: float | None = Field(default=None, ge=-90, le=90)
    completion_lng: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    shared_to_community: bool = False

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.completion_lat is None) != (self.completion_lng is None):
            raise ValueError("completion_lat and completion_lng must be provided together")
        return self


class QuestOut(BaseModel):
    id: str
    source: str
    generated_title: str
    generated_description: str
    quest_type: str
    stat_category: str
    difficulty: int
    xp_reward: int
    coin_reward: int
    status: str
    target_lat: float | None = None
    target_lng: float | None = None
    target_place_name: str | None = None
    target_place_type: str | None = None

    model_config = {"from_attributes": True}


class QuestCompletionOut(BaseModel):
    id: str
    xp_awarded: int
    coins_awarded: int
    level_up_coins: int
    item_awarded_id: str | None
    duplicate_item_id: str | None
    duplicate_compensation_coins: int
    achievement_xp_bonus: int
    achievement_coin_bonus: int
    unlocked_achievements: list[dict]
    shared_to_community: bool
    previous_level: int
    level: int
    leveled_up: bool
    total_xp: int
    total_coins: int
    current_streak: int
    longest_streak: int

    model_config = {"from_attributes": True}
