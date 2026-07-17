from enum import StrEnum


class QuestType(StrEnum):
    location = "location"
    social = "social"
    action = "action"


class StatCategory(StrEnum):
    social = "social"
    creativity = "creativity"
    exploration = "exploration"
    knowledge = "knowledge"
    fitness = "fitness"


class QuestSource(StrEnum):
    normal = "normal"
    npc = "npc"
    weekly = "weekly"


class QuestStatus(StrEnum):
    active = "active"
    accepted = "accepted"
    completed = "completed"
    skipped = "skipped"
    expired = "expired"
    failed = "failed"


class VerificationStatus(StrEnum):
    not_required = "not_required"
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class Rarity(StrEnum):
    common = "common"
    uncommon = "uncommon"
    rare = "rare"
    epic = "epic"
    legendary = "legendary"


class AchievementCategory(StrEnum):
    milestone = "milestone"
    streak = "streak"
    quest_type = "quest_type"
    special = "special"
    weekly = "weekly"
    shop = "shop"
    npc = "npc"


class AvatarItemType(StrEnum):
    hair = "hair"
    head = "head"
    body = "body"
    outfit = "outfit"
    accessory = "accessory"
    weapon = "weapon"
    background = "background"
    badge = "badge"


class ItemAcquiredFrom(StrEnum):
    starter = "starter"
    purchase = "purchase"
    quest_reward = "quest_reward"
    weekly_reward = "weekly_reward"
    npc_reward = "npc_reward"
    level_up = "level_up"
    achievement = "achievement"


class RewardSource(StrEnum):
    quest_completion = "quest_completion"
    weekly_completion = "weekly_completion"
    npc_completion = "npc_completion"
    level_up = "level_up"
    achievement = "achievement"


class WeeklyQuestStatus(StrEnum):
    scheduled = "scheduled"
    active = "active"
    completed = "completed"


class NPCOfferStatus(StrEnum):
    offered = "offered"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"
    completed = "completed"


class MLEventType(StrEnum):
    shown = "shown"
    accepted = "accepted"
    skipped = "skipped"
    completed = "completed"
    failed = "failed"
    rated = "rated"
    npc_spawned = "npc_spawned"
    npc_accepted = "npc_accepted"
    npc_declined = "npc_declined"
    purchased_item = "purchased_item"
