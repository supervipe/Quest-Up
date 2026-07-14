import argparse
import asyncio
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.ml.training import TrainingDatasetService


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="ml_data/real_quest_ranking_examples.jsonl")
    parser.add_argument("--include-unlabeled", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    service = TrainingDatasetService()
    async with AsyncSessionLocal() as db:
        examples = await service.build_examples(
            db,
            include_unlabeled=args.include_unlabeled,
            limit=args.limit,
        )
    output = Path(args.output)
    service.write_jsonl(output, examples)
    positive = sum(1 for example in examples if example["label"] == 1)
    negative = sum(1 for example in examples if example["label"] == 0)
    unlabeled = sum(1 for example in examples if example["label"] is None)
    print(f"Wrote {len(examples)} examples to {output}")
    print(f"positive={positive} negative={negative} unlabeled={unlabeled}")


if __name__ == "__main__":
    asyncio.run(main())
