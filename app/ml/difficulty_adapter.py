from app.services.difficulty_service import DifficultyService


class DifficultyAdapter:
    def adapt(self, base_difficulty: int, completion_rate: float | None = None) -> int:
        return DifficultyService().adapt(base_difficulty, completion_rate)
