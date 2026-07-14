import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class TrainingResult:
    model_path: str
    examples: int
    positive: int
    negative: int
    accuracy: float | None
    roc_auc: float | None
    schema_version: str
    model_type: str


class QuestRankingModel:
    model_type = "logistic_regression"
    schema_version = "quest_ranking_v1"

    def __init__(self, artifact: dict[str, Any]) -> None:
        self.artifact = artifact
        self.pipeline: Pipeline = artifact["pipeline"]
        self.metadata: dict = artifact.get("metadata", {})

    @classmethod
    def load(cls, path: Path) -> "QuestRankingModel | None":
        if not path.exists():
            return None
        return cls(joblib.load(path))

    @classmethod
    def train_from_jsonl(
        cls,
        input_paths: list[Path],
        output_path: Path,
        *,
        min_examples: int = 20,
        random_state: int = 42,
    ) -> TrainingResult:
        rows = load_labeled_examples(input_paths)
        if len(rows) < min_examples:
            raise ValueError(f"Need at least {min_examples} labeled examples, found {len(rows)}")

        x = [flatten_example(row) for row in rows]
        y = [int(row["label"]) for row in rows]
        positive = sum(y)
        negative = len(y) - positive
        if positive == 0 or negative == 0:
            raise ValueError("Training requires at least one positive and one negative example")

        pipeline = Pipeline(
            [
                ("vectorizer", DictVectorizer(sparse=True)),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=random_state,
                    ),
                ),
            ]
        )

        accuracy = None
        roc_auc = None
        stratify = y if min(positive, negative) >= 2 else None
        if len(rows) >= 30 and stratify is not None:
            train_x, test_x, train_y, test_y = train_test_split(
                x,
                y,
                test_size=0.2,
                random_state=random_state,
                stratify=stratify,
            )
            pipeline.fit(train_x, train_y)
            predictions = pipeline.predict(test_x)
            probabilities = pipeline.predict_proba(test_x)[:, 1]
            accuracy = round(float(accuracy_score(test_y, predictions)), 4)
            if len(set(test_y)) > 1:
                roc_auc = round(float(roc_auc_score(test_y, probabilities)), 4)

        pipeline.fit(x, y)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "pipeline": pipeline,
            "metadata": {
                "schema_version": cls.schema_version,
                "model_type": cls.model_type,
                "examples": len(rows),
                "positive": positive,
                "negative": negative,
                "accuracy": accuracy,
                "roc_auc": roc_auc,
                "input_files": [str(path) for path in input_paths],
            },
        }
        joblib.dump(artifact, output_path)
        return TrainingResult(
            model_path=str(output_path),
            examples=len(rows),
            positive=positive,
            negative=negative,
            accuracy=accuracy,
            roc_auc=roc_auc,
            schema_version=cls.schema_version,
            model_type=cls.model_type,
        )

    def score_examples(self, examples: list[dict]) -> list[float]:
        if not examples:
            return []
        x = [flatten_example(example) for example in examples]
        return [float(value) for value in self.pipeline.predict_proba(x)[:, 1]]


def load_labeled_examples(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("label") in {0, 1}:
                    rows.append(row)
    return rows


def flatten_example(example: dict) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    allowed_sections = [
        "user_features",
        "quest_features",
        "context_features",
        "recent_behavior_features",
    ]
    for section in allowed_sections:
        _flatten(section, example.get(section, {}), flattened)
    return flattened


def _flatten(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(_join(prefix, key), item, output)
        return
    if isinstance(value, list):
        for item in value:
            output[f"{prefix}={item}"] = 1
        output[f"{prefix}__count"] = len(value)
        return
    if value is None:
        output[f"{prefix}__missing"] = 1
        return
    if isinstance(value, bool):
        output[prefix] = int(value)
        return
    if isinstance(value, (int, float)):
        output[prefix] = value
        return
    output[f"{prefix}={value}"] = 1


def _join(prefix: str, key: str) -> str:
    return key if not prefix else f"{prefix}.{key}"
