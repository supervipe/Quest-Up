from pathlib import Path

import joblib

from app.ml.ranking_model import QuestRankingModel

MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "quest_recommender.pkl"
QUEST_RANKER_PATH = MODEL_DIR / "quest_ranker_logistic.joblib"


def load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def load_quest_ranker() -> QuestRankingModel | None:
    return QuestRankingModel.load(QUEST_RANKER_PATH)
