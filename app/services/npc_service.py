import math
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import NPCOfferStatus, QuestSource, QuestStatus
from app.core.database import utcnow
from app.core.exceptions import bad_request, not_found
from app.models.npc import NPC, NPCQuestOffer, UserNPCSpawnState
from app.models.quest import QuestTemplate, UserQuest
from app.models.user import User
from app.models.walking import WalkingSession


class NPCService:
    async def start_session(self, db: AsyncSession, user: User, lat: float | None, lng: float | None) -> WalkingSession:
        session = WalkingSession(user_id=user.id, last_lat=lat, last_lng=lng, last_movement_at=utcnow())
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def update_session(self, db: AsyncSession, user: User, session_id: str, lat: float, lng: float, speed_mps: float | None) -> dict:
        session = await db.get(WalkingSession, session_id)
        if not session or session.user_id != user.id:
            raise not_found("Walking session not found")
        if session.last_lat is not None and session.last_lng is not None:
            session.total_distance_m = float(session.total_distance_m) + self._distance_m(float(session.last_lat), float(session.last_lng), lat, lng)
        session.last_lat = lat
        session.last_lng = lng
        session.last_movement_at = utcnow()
        offer = await self.check_spawn(db, user, session, speed_mps)
        await db.commit()
        return {"session_id": session.id, "npc_spawned": bool(offer), "offer": offer}

    async def check_spawn(self, db: AsyncSession, user: User, session: WalkingSession | None = None, speed_mps: float | None = None) -> NPCQuestOffer | None:
        settings = get_settings()
        if session is None:
            session = await db.scalar(select(WalkingSession).where(WalkingSession.user_id == user.id, WalkingSession.is_active.is_(True)).order_by(WalkingSession.started_at.desc()))
        if not session or session.npc_spawned:
            return None
        now = utcnow()
        elapsed = now - self._aware(session.started_at)
        moved_enough = float(session.total_distance_m) >= settings.npc_min_distance_meters or (speed_mps or 0) >= 0.5
        if elapsed < timedelta(minutes=settings.npc_min_walking_minutes) or not moved_enough:
            return None
        if session.npc_checked_at and now - self._aware(session.npc_checked_at) < timedelta(minutes=3):
            return None
        state = await self._spawn_state(db, user)
        if state.cooldown_until and self._aware(state.cooldown_until) <= now:
            state.current_spawn_chance = settings.npc_default_spawn_chance
            state.cooldown_until = None
        session.npc_checked_at = now
        if random.random() > float(state.current_spawn_chance):
            return None
        npc = await db.scalar(select(NPC).where(NPC.is_active.is_(True)).order_by(NPC.spawn_weight.desc()))
        template = await db.scalar(select(QuestTemplate).where(QuestTemplate.is_npc_eligible.is_(True), QuestTemplate.is_active.is_(True)))
        if not npc or not template:
            return None
        offer = NPCQuestOffer(
            npc_id=npc.id,
            user_id=user.id,
            quest_template_id=template.id,
            generated_title=f"{npc.name}'s Side Quest",
            generated_description=template.description_template.format(place_name="a nearby spot"),
            xp_reward=template.base_xp + 15,
            coin_reward=template.base_coins + 10,
            reward_item_id=None,
            expires_at=now + timedelta(minutes=15),
        )
        db.add(offer)
        session.npc_spawned = True
        state.last_spawned_at = now
        await db.flush()
        return offer

    async def accept_offer(self, db: AsyncSession, user: User, offer_id: str) -> UserQuest:
        settings = get_settings()
        offer = await db.get(NPCQuestOffer, offer_id)
        if not offer or offer.user_id != user.id:
            raise not_found("NPC offer not found")
        if offer.status != NPCOfferStatus.offered:
            raise bad_request("NPC offer is not available")
        if self._aware(offer.expires_at) <= utcnow():
            offer.status = NPCOfferStatus.expired
            await db.commit()
            raise bad_request("NPC offer has expired")
        offer.status = NPCOfferStatus.accepted
        offer.accepted_at = utcnow()
        template = await db.get(QuestTemplate, offer.quest_template_id) if offer.quest_template_id else None
        quest = UserQuest(
            user_id=user.id,
            template_id=offer.quest_template_id,
            source=QuestSource.npc,
            generated_title=offer.generated_title,
            generated_description=offer.generated_description,
            quest_type=template.quest_type if template else "action",
            stat_category=template.stat_category if template else "fitness",
            difficulty=template.base_difficulty if template else 2,
            xp_reward=offer.xp_reward,
            coin_reward=offer.coin_reward,
            status=QuestStatus.accepted,
            accepted_at=utcnow(),
            reward_item_id=offer.reward_item_id,
        )
        db.add(quest)
        state = await self._spawn_state(db, user)
        state.current_spawn_chance = settings.npc_accepted_spawn_chance
        state.cooldown_until = utcnow() + timedelta(hours=settings.npc_cooldown_hours)
        state.last_offer_accepted_at = utcnow()
        await db.commit()
        await db.refresh(quest)
        return quest

    async def decline_offer(self, db: AsyncSession, user: User, offer_id: str) -> NPCQuestOffer:
        offer = await db.get(NPCQuestOffer, offer_id)
        if not offer or offer.user_id != user.id:
            raise not_found("NPC offer not found")
        if offer.status != NPCOfferStatus.offered:
            raise bad_request("NPC offer is not available")
        offer.status = NPCOfferStatus.declined
        await db.commit()
        await db.refresh(offer)
        return offer

    async def _spawn_state(self, db: AsyncSession, user: User) -> UserNPCSpawnState:
        state = await db.scalar(select(UserNPCSpawnState).where(UserNPCSpawnState.user_id == user.id))
        if not state:
            state = UserNPCSpawnState(user_id=user.id, current_spawn_chance=get_settings().npc_default_spawn_chance)
            db.add(state)
            await db.flush()
        return state

    def _distance_m(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lng2 - lng1)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
