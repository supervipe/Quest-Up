from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class WalkingStartRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_are_paired(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be provided together")
        return self


class WalkingUpdateRequest(BaseModel):
    session_id: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    timestamp: datetime | None = None
    speed_mps: float | None = Field(default=None, ge=0, le=20)


class NPCOfferOut(BaseModel):
    id: str
    npc_id: str
    generated_title: str
    generated_description: str
    xp_reward: int
    coin_reward: int
    status: str

    model_config = {"from_attributes": True}
