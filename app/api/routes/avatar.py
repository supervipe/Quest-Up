from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.exceptions import not_found
from app.models.avatar import AvatarItem, UserAvatar, UserAvatarItem
from app.models.user import User
from app.schemas.avatar import AvatarItemOut, EquipRequest
from app.services.store_service import StoreService

router = APIRouter(tags=["avatar-store"])


@router.get("/avatar")
async def avatar(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_avatar = await db.scalar(select(UserAvatar).where(UserAvatar.user_id == current_user.id))
    if not user_avatar:
        raise not_found("Avatar not found")
    return user_avatar


@router.put("/avatar/equip")
async def equip(payload: EquipRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await StoreService().equip(db, current_user, payload.equipped_items, payload.base_style)


@router.get("/store/items", response_model=list[AvatarItemOut])
async def store_items(db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(AvatarItem).where(AvatarItem.is_active.is_(True))))


@router.post("/store/items/{item_id}/purchase")
async def purchase(item_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await StoreService().purchase(db, current_user, item_id)


@router.get("/inventory")
async def inventory(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return list(await db.scalars(select(UserAvatarItem).where(UserAvatarItem.user_id == current_user.id)))
