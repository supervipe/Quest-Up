from pydantic import BaseModel


class AvatarItemOut(BaseModel):
    id: str
    name: str
    item_type: str
    pixel_asset_key: str
    price_coins: int
    unlock_level: int
    rarity: str
    is_purchasable: bool
    is_reward_only: bool

    model_config = {"from_attributes": True}


class EquipRequest(BaseModel):
    equipped_items: dict[str, str]
    base_style: str | None = None
