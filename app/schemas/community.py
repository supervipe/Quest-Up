from pydantic import BaseModel, Field


class WeeklyQuestOut(BaseModel):
    id: str
    title: str
    description: str
    quest_type: str
    stat_category: str
    xp_reward: int
    coin_reward: int
    reward_item_id: str | None
    status: str

    model_config = {"from_attributes": True}


class CommunitySubmitRequest(BaseModel):
    user_quest_id: str | None = None
    photo_url: str = Field(min_length=1, max_length=2048)
    caption: str | None = Field(default=None, max_length=500)


class CommunityPostOut(BaseModel):
    id: str
    user_id: str
    weekly_quest_id: str | None
    user_quest_id: str | None
    photo_url: str
    caption: str | None
    likes_count: int

    model_config = {"from_attributes": True}
