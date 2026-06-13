class DifficultyService:
    def adapt(self, base_difficulty: int, completion_rate: float | None = None) -> int:
        if completion_rate is None:
            return max(1, min(5, base_difficulty))
        if completion_rate > 0.80:
            return min(5, base_difficulty + 1)
        if completion_rate < 0.50:
            return max(1, base_difficulty - 1)
        return max(1, min(5, base_difficulty))
