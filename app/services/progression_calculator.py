from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class ProgressionCalculation:
    xp_awarded: int
    difficulty_multiplier: float
    streak_multiplier: float
    current_streak: int
    previous_level: int
    new_level: int
    level_up_coins: int

    @property
    def leveled_up(self) -> bool:
        return self.new_level > self.previous_level


class ProgressionCalculator:
    DIFFICULTY_MULTIPLIERS = {1: 1.0, 2: 1.15, 3: 1.35, 4: 1.6, 5: 2.0}

    def calculate(
        self,
        base_xp: int,
        difficulty: int,
        total_xp: int,
        previous_level: int,
        claimed_reward_level: int,
        current_streak: int,
        last_completed_at: datetime | None,
        completed_at: datetime,
        timezone_name: str | None,
    ) -> ProgressionCalculation:
        next_streak = self.calculate_streak(
            current_streak,
            last_completed_at,
            completed_at,
            timezone_name,
        )
        difficulty_multiplier = self.difficulty_multiplier(difficulty)
        streak_multiplier = self.streak_multiplier(next_streak)
        xp_awarded = int(
            (
                Decimal(base_xp)
                * Decimal(str(difficulty_multiplier))
                * Decimal(str(streak_multiplier))
            ).to_integral_value(rounding=ROUND_FLOOR)
        )
        new_level = self.level_for_xp(total_xp + xp_awarded)
        level_up_coins = self.level_up_coin_reward(claimed_reward_level, new_level)
        return ProgressionCalculation(
            xp_awarded=xp_awarded,
            difficulty_multiplier=difficulty_multiplier,
            streak_multiplier=streak_multiplier,
            current_streak=next_streak,
            previous_level=previous_level,
            new_level=new_level,
            level_up_coins=level_up_coins,
        )

    def calculate_streak(
        self,
        current_streak: int,
        last_completed_at: datetime | None,
        completed_at: datetime,
        timezone_name: str | None,
    ) -> int:
        if last_completed_at is None:
            return 1
        zone = self._timezone(timezone_name)
        previous_date = self._aware(last_completed_at).astimezone(zone).date()
        completion_date = self._aware(completed_at).astimezone(zone).date()
        days = (completion_date - previous_date).days
        if days <= 0:
            return max(1, current_streak)
        if days == 1:
            return max(1, current_streak) + 1
        return 1

    def difficulty_multiplier(self, difficulty: int) -> float:
        return self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)

    def streak_multiplier(self, streak: int) -> float:
        if streak >= 30:
            return 2.0
        if streak >= 14:
            return 1.5
        if streak >= 7:
            return 1.25
        if streak >= 3:
            return 1.1
        return 1.0

    def xp_required_for_level(self, level: int) -> int:
        value = Decimal(100) * (Decimal("1.15") ** (level - 1))
        return int(value.to_integral_value(rounding=ROUND_FLOOR))

    def level_for_xp(self, xp: int) -> int:
        level = 1
        remaining = max(0, xp)
        while remaining >= self.xp_required_for_level(level):
            remaining -= self.xp_required_for_level(level)
            level += 1
        return level

    def level_up_coin_reward(self, claimed_level: int, new_level: int) -> int:
        if new_level <= claimed_level:
            return 0
        return sum(25 + level * 5 for level in range(claimed_level + 1, new_level + 1))

    def _timezone(self, timezone_name: str | None):
        if not timezone_name:
            return timezone.utc
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return timezone.utc

    def _aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
