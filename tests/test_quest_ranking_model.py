from pathlib import Path

from app.ml.ranking_model import QuestRankingModel


def test_logistic_ranking_model_trains_and_scores(tmp_path: Path):
    output = tmp_path / "quest_ranker.joblib"
    result = QuestRankingModel.train_from_jsonl(
        [Path("ml_data/quest_ranking_examples.jsonl")],
        output,
        min_examples=20,
    )
    assert output.exists()
    assert result.model_type == "logistic_regression"
    assert result.examples >= 20
    assert result.positive > 0
    assert result.negative > 0

    model = QuestRankingModel.load(output)
    scores = model.score_examples(
        [
            {
                "schema_version": "quest_ranking_v1",
                "task": "quest_ranking",
                "user_features": {
                    "level": 3,
                    "preferred_quest_types": ["social"],
                    "preferred_difficulty": 3,
                    "current_streak": 2,
                },
                "context_features": {
                    "local_hour": 18,
                    "time_bucket": "evening",
                    "weather": "clear",
                    "nearby_place_types": ["cafe", "park"],
                },
                "quest_features": {
                    "quest_template_key": "three_compliments",
                    "quest_type": "social",
                    "stat_category": "social",
                    "base_difficulty": 3,
                    "base_xp": 60,
                    "base_coins": 18,
                    "requires_location": False,
                    "requires_photo": False,
                },
                "recent_behavior_features": {
                    "recent_counts": {"location": 1, "social": 3, "action": 0},
                    "recent_positive": {"location": 1, "social": 3, "action": 0},
                },
            }
        ]
    )
    assert len(scores) == 1
    assert 0 <= scores[0] <= 1
