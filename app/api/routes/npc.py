from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.constants import NPCOfferStatus
from app.core.database import get_db
from app.core.database import utcnow
from app.core.exceptions import bad_request, not_found
from app.models.npc import NPCQuestOffer
from app.models.user import User
from app.schemas.npc import WalkingStartRequest, WalkingUpdateRequest
from app.services.npc_service import NPCService

router = APIRouter(tags=["walking-npc"])


@router.post("/walking/session/start")
async def start(payload: WalkingStartRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NPCService().start_session(db, current_user, payload.lat, payload.lng)


@router.post("/walking/session/update")
async def update(payload: WalkingUpdateRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NPCService().update_session(db, current_user, payload.session_id, payload.lat, payload.lng, payload.speed_mps)


@router.post("/walking/session/end")
async def end(session_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.walking import WalkingSession

    session = await db.get(WalkingSession, session_id)
    if not session or session.user_id != current_user.id:
        raise not_found("Walking session not found")
    if not session.is_active:
        raise bad_request("Walking session has already ended")
    session.is_active = False
    session.ended_at = utcnow()
    await db.commit()
    return {"ended": True}


@router.get("/npc/offers/current")
async def current_offer(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await db.scalar(select(NPCQuestOffer).where(NPCQuestOffer.user_id == current_user.id, NPCQuestOffer.status == NPCOfferStatus.offered).order_by(NPCQuestOffer.offered_at.desc()))


@router.post("/npc/spawn/check")
async def spawn_check(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    offer = await NPCService().check_spawn(db, current_user)
    await db.commit()
    return {"npc_spawned": bool(offer), "offer": offer}


@router.post("/npc/offers/{offer_id}/accept")
async def accept_offer(offer_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NPCService().accept_offer(db, current_user, offer_id)


@router.post("/npc/offers/{offer_id}/decline")
async def decline_offer(offer_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await NPCService().decline_offer(db, current_user, offer_id)
