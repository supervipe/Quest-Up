import argparse
import json
from pathlib import Path

from app.ml.model_registry import QUEST_RANKER_PATH
from app.ml.ranking_model import QuestRankingModel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        action="append",
        default=None,
        help="JSONL training file. Can be passed multiple times.",
    )
    parser.add_argument("--output", default=str(QUEST_RANKER_PATH))
    parser.add_argument("--min-examples", type=int, default=20)
    args = parser.parse_args()

    input_paths = [Path(path) for path in (args.input or ["ml_data/quest_ranking_examples.jsonl"])]
    result = QuestRankingModel.train_from_jsonl(
        input_paths=input_paths,
        output_path=Path(args.output),
        min_examples=args.min_examples,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
