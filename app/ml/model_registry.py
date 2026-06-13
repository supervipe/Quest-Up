from pathlib import Path

import joblib


MODEL_PATH = Path("models/quest_recommender.pkl")


def load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)
