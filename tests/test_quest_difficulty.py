from app.services.quest_generation_service import QuestGenerationService


def test_default_preference_preserves_template_difficulty():
    service = QuestGenerationService()

    assert service._difficulty_for_preference(1, 3) == 1
    assert service._difficulty_for_preference(2, 3) == 2
    assert service._difficulty_for_preference(3, 3) == 3


def test_missing_preference_preserves_template_difficulty():
    service = QuestGenerationService()

    assert service._difficulty_for_preference(1, None) == 1
    assert service._difficulty_for_preference(3, None) == 3


def test_preference_nudges_template_difficulty_with_bounds():
    service = QuestGenerationService()

    assert service._difficulty_for_preference(1, 1) == 1
    assert service._difficulty_for_preference(2, 1) == 1
    assert service._difficulty_for_preference(3, 2) == 2
    assert service._difficulty_for_preference(1, 4) == 2
    assert service._difficulty_for_preference(3, 5) == 4
    assert service._difficulty_for_preference(5, 5) == 5
