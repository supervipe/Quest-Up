"""add stability constraints

Revision ID: 20260613_0002
Revises: 20260602_0001
Create Date: 2026-06-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0002"
down_revision: Union[str, None] = "20260602_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINTS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("ck_users_total_xp_nonnegative", "total_xp >= 0"),
        ("ck_users_level_positive", "level >= 1"),
        ("ck_users_coins_nonnegative", "coins >= 0"),
        ("ck_users_current_streak_nonnegative", "current_streak >= 0"),
        ("ck_users_streak_order", "longest_streak >= current_streak"),
        ("ck_users_reward_level_positive", "last_level_reward_claimed_for_level >= 1"),
    ],
    "user_profiles": [
        ("ck_profiles_radius", "preferred_radius_km > 0 AND preferred_radius_km <= 50"),
        ("ck_profiles_difficulty", "preferred_difficulty IS NULL OR preferred_difficulty BETWEEN 1 AND 5"),
        ("ck_profiles_lat", "home_lat IS NULL OR home_lat BETWEEN -90 AND 90"),
        ("ck_profiles_lng", "home_lng IS NULL OR home_lng BETWEEN -180 AND 180"),
        ("ck_profiles_home_coordinates_pair", "(home_lat IS NULL) = (home_lng IS NULL)"),
    ],
    "user_stats": [
        ("ck_stats_social_xp", "social_xp >= 0"),
        ("ck_stats_creativity_xp", "creativity_xp >= 0"),
        ("ck_stats_exploration_xp", "exploration_xp >= 0"),
        ("ck_stats_knowledge_xp", "knowledge_xp >= 0"),
        ("ck_stats_fitness_xp", "fitness_xp >= 0"),
    ],
    "quest_templates": [
        ("ck_quest_templates_difficulty", "base_difficulty BETWEEN 1 AND 5"),
        ("ck_quest_templates_xp", "base_xp >= 0"),
        ("ck_quest_templates_coins", "base_coins >= 0"),
        ("ck_quest_templates_duration", "duration_minutes IS NULL OR duration_minutes > 0"),
        ("ck_quest_templates_min_level", "min_user_level >= 1"),
        ("ck_quest_templates_reward_chance", "item_reward_chance BETWEEN 0 AND 1"),
    ],
    "user_quests": [
        ("ck_user_quests_difficulty", "difficulty BETWEEN 1 AND 5"),
        ("ck_user_quests_xp_reward", "xp_reward >= 0"),
        ("ck_user_quests_coin_reward", "coin_reward >= 0"),
        ("ck_user_quests_rating", "user_rating IS NULL OR user_rating BETWEEN 1 AND 5"),
        ("ck_user_quests_verification_score", "verification_score IS NULL OR verification_score BETWEEN 0 AND 100"),
        ("ck_user_quests_target_lat", "target_lat IS NULL OR target_lat BETWEEN -90 AND 90"),
        ("ck_user_quests_target_lng", "target_lng IS NULL OR target_lng BETWEEN -180 AND 180"),
        ("ck_user_quests_target_coordinates_pair", "(target_lat IS NULL) = (target_lng IS NULL)"),
        ("ck_user_quests_expiration", "expires_at IS NULL OR expires_at > assigned_at"),
    ],
    "quest_completions": [
        ("ck_quest_completions_xp", "xp_awarded >= 0"),
        ("ck_quest_completions_coins", "coins_awarded >= 0"),
        ("ck_quest_completions_lat", "completion_lat IS NULL OR completion_lat BETWEEN -90 AND 90"),
        ("ck_quest_completions_lng", "completion_lng IS NULL OR completion_lng BETWEEN -180 AND 180"),
        ("ck_quest_completions_coordinates_pair", "(completion_lat IS NULL) = (completion_lng IS NULL)"),
    ],
    "weekly_community_quests": [
        ("ck_weekly_quests_xp", "xp_reward >= 0"),
        ("ck_weekly_quests_coins", "coin_reward >= 0"),
        ("ck_weekly_quests_dates", "ends_at > starts_at"),
    ],
    "community_posts": [("ck_community_posts_likes", "likes_count >= 0")],
    "avatar_items": [
        ("ck_avatar_items_price", "price_coins >= 0"),
        ("ck_avatar_items_unlock_level", "unlock_level >= 1"),
    ],
    "npcs": [("ck_npcs_spawn_weight", "spawn_weight > 0")],
    "npc_quest_offers": [
        ("ck_npc_offers_xp", "xp_reward >= 0"),
        ("ck_npc_offers_coins", "coin_reward >= 0"),
        ("ck_npc_offers_expiration", "expires_at > offered_at"),
    ],
    "user_npc_spawn_state": [
        ("ck_npc_spawn_state_chance", "current_spawn_chance BETWEEN 0 AND 1"),
    ],
    "walking_sessions": [
        ("ck_walking_sessions_distance", "total_distance_m >= 0"),
        ("ck_walking_sessions_lat", "last_lat IS NULL OR last_lat BETWEEN -90 AND 90"),
        ("ck_walking_sessions_lng", "last_lng IS NULL OR last_lng BETWEEN -180 AND 180"),
        ("ck_walking_sessions_coordinates_pair", "(last_lat IS NULL) = (last_lng IS NULL)"),
        ("ck_walking_sessions_dates", "ended_at IS NULL OR ended_at >= started_at"),
    ],
    "ml_interactions": [
        ("ck_ml_interactions_difficulty", "difficulty IS NULL OR difficulty BETWEEN 1 AND 5"),
        ("ck_ml_interactions_rating", "rating IS NULL OR rating BETWEEN 1 AND 5"),
    ],
}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    for table, constraints in CONSTRAINTS.items():
        existing = {constraint["name"] for constraint in inspector.get_check_constraints(table)}
        for name, expression in constraints:
            if name not in existing:
                op.create_check_constraint(name, table, expression)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    for table, constraints in reversed(list(CONSTRAINTS.items())):
        existing = {constraint["name"] for constraint in inspector.get_check_constraints(table)}
        for name, _ in reversed(constraints):
            if name in existing:
                op.drop_constraint(name, table, type_="check")
