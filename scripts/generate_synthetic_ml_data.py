import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


QUEST_TYPES = ["location", "social", "action"]
STAT_BY_TYPE = {
    "location": ["exploration", "knowledge"],
    "social": ["social"],
    "action": ["creativity", "fitness"],
}
WEATHER = ["clear", "cloudy", "rain", "snow", "wind"]
PLACE_TYPES = ["park", "cafe", "library", "restaurant", "gym", "mural"]
TIME_BUCKETS = ["morning", "afternoon", "evening", "night"]


@dataclass(frozen=True)
class SyntheticUser:
    synthetic_user_id: str
    archetype: str
    level: int
    preferred_quest_types: list[str]
    preferred_difficulty: int
    preferred_radius_km: float
    active_hours: list[str]
    weather_tolerance: list[str]
    place_affinities: list[str]
    completion_bias: dict[str, float]
    difficulty_tolerance: int
    social_comfort: float
    novelty_preference: float


@dataclass(frozen=True)
class CandidateQuest:
    quest_template_key: str
    quest_type: str
    stat_category: str
    base_difficulty: int
    base_xp: int
    base_coins: int
    duration_minutes: int
    requires_location: bool
    requires_photo: bool
    location_type: str | None
    model_prompt_theme: str


QUEST_CANDIDATES = [
    CandidateQuest(
        "park_micro_adventure",
        "location",
        "exploration",
        2,
        45,
        12,
        30,
        True,
        False,
        "park",
        "outdoor exploration near a park",
    ),
    CandidateQuest(
        "cafe_observation",
        "location",
        "knowledge",
        1,
        30,
        8,
        20,
        True,
        False,
        "cafe",
        "noticing details at a cafe or casual indoor place",
    ),
    CandidateQuest(
        "library_curiosity",
        "location",
        "knowledge",
        2,
        40,
        10,
        25,
        True,
        False,
        "library",
        "learning something small in a library or quiet public place",
    ),
    CandidateQuest(
        "three_compliments",
        "social",
        "social",
        3,
        60,
        18,
        45,
        False,
        False,
        None,
        "friendly social interaction with low pressure",
    ),
    CandidateQuest(
        "ask_local_tip",
        "social",
        "social",
        2,
        50,
        14,
        25,
        False,
        False,
        None,
        "asking someone for a local recommendation",
    ),
    CandidateQuest(
        "message_old_friend",
        "social",
        "social",
        1,
        35,
        8,
        15,
        False,
        False,
        None,
        "reconnecting with someone in a thoughtful way",
    ),
    CandidateQuest(
        "sketch_the_view",
        "action",
        "creativity",
        2,
        50,
        14,
        25,
        True,
        False,
        "mural",
        "creative observation and quick sketching",
    ),
    CandidateQuest(
        "fitness_burst",
        "action",
        "fitness",
        3,
        65,
        20,
        20,
        True,
        False,
        "park",
        "short outdoor movement challenge",
    ),
    CandidateQuest(
        "tiny_declutter",
        "action",
        "creativity",
        1,
        30,
        8,
        10,
        False,
        False,
        None,
        "small useful action that improves the user's space",
    ),
]


ARCHETYPES = [
    {
        "name": "location_explorer",
        "preferred": ["location"],
        "completion_bias": {"location": 0.82, "social": 0.38, "action": 0.54},
        "places": ["park", "cafe", "library"],
        "hours": ["morning", "afternoon"],
        "weather": ["clear", "cloudy"],
        "social_comfort": 0.35,
        "novelty": 0.72,
    },
    {
        "name": "social_connector",
        "preferred": ["social"],
        "completion_bias": {"location": 0.48, "social": 0.86, "action": 0.44},
        "places": ["cafe", "restaurant", "park"],
        "hours": ["afternoon", "evening"],
        "weather": ["clear", "cloudy", "rain"],
        "social_comfort": 0.88,
        "novelty": 0.55,
    },
    {
        "name": "balanced_casual",
        "preferred": ["location", "social", "action"],
        "completion_bias": {"location": 0.62, "social": 0.58, "action": 0.56},
        "places": ["park", "cafe", "library", "mural"],
        "hours": ["afternoon", "evening"],
        "weather": ["clear", "cloudy", "rain"],
        "social_comfort": 0.58,
        "novelty": 0.62,
    },
    {
        "name": "creative_doer",
        "preferred": ["action", "location"],
        "completion_bias": {"location": 0.58, "social": 0.42, "action": 0.82},
        "places": ["mural", "park", "gym"],
        "hours": ["morning", "evening"],
        "weather": ["clear", "cloudy"],
        "social_comfort": 0.42,
        "novelty": 0.78,
    },
    {
        "name": "shy_growth",
        "preferred": ["location", "action"],
        "completion_bias": {"location": 0.68, "social": 0.36, "action": 0.63},
        "places": ["library", "park", "cafe"],
        "hours": ["morning", "afternoon"],
        "weather": ["clear", "cloudy"],
        "social_comfort": 0.25,
        "novelty": 0.48,
    },
    {
        "name": "fitness_regular",
        "preferred": ["action"],
        "completion_bias": {"location": 0.45, "social": 0.34, "action": 0.88},
        "places": ["gym", "park"],
        "hours": ["morning", "evening"],
        "weather": ["clear", "cloudy", "wind"],
        "social_comfort": 0.45,
        "novelty": 0.38,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=120)
    parser.add_argument("--examples-per-user", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="ml_data")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    users = [make_user(i) for i in range(args.users)]
    ranking_examples = []
    generation_examples = []

    for user in users:
        history = []
        for example_index in range(args.examples_per_user):
            context = make_context(user)
            quest = random.choice(QUEST_CANDIDATES)
            outcome = simulate_outcome(user, quest, context, history)
            ranking_examples.append(
                make_ranking_example(user, quest, context, outcome, history, example_index)
            )
            generation_examples.append(
                make_generation_example(user, quest, context, outcome, history)
            )
            history.append(
                {
                    "quest_type": quest.quest_type,
                    "accepted": outcome["accepted"],
                    "completed": outcome["completed"],
                    "skipped": outcome["skipped"],
                    "failed": outcome["failed"],
                    "rating": outcome["rating"],
                }
            )

    write_jsonl(output_dir / "synthetic_users.jsonl", [asdict(user) for user in users])
    write_jsonl(output_dir / "quest_ranking_examples.jsonl", ranking_examples)
    write_jsonl(output_dir / "quest_generation_examples.jsonl", generation_examples)
    write_readme(output_dir, users, ranking_examples, generation_examples)

    print(f"Wrote {len(users)} synthetic users")
    print(f"Wrote {len(ranking_examples)} ranking examples")
    print(f"Wrote {len(generation_examples)} quest generation examples")
    print(f"Output directory: {output_dir.resolve()}")


def make_user(index: int) -> SyntheticUser:
    archetype = ARCHETYPES[index % len(ARCHETYPES)]
    level = random.choices([1, 2, 3, 4, 5, 6, 7, 8], weights=[24, 20, 17, 13, 10, 7, 5, 4], k=1)[0]
    preferred_difficulty = min(5, max(1, round(random.gauss(2.4 + level / 8, 0.8))))
    return SyntheticUser(
        synthetic_user_id=f"syn_user_{index + 1:04d}",
        archetype=archetype["name"],
        level=level,
        preferred_quest_types=archetype["preferred"],
        preferred_difficulty=preferred_difficulty,
        preferred_radius_km=random.choice([2.5, 5.0, 8.0, 12.0]),
        active_hours=archetype["hours"],
        weather_tolerance=archetype["weather"],
        place_affinities=archetype["places"],
        completion_bias=archetype["completion_bias"],
        difficulty_tolerance=min(5, max(1, preferred_difficulty + random.choice([-1, 0, 0, 1]))),
        social_comfort=round(clamp(archetype["social_comfort"] + random.uniform(-0.12, 0.12)), 2),
        novelty_preference=round(clamp(archetype["novelty"] + random.uniform(-0.12, 0.12)), 2),
    )


def make_context(user: SyntheticUser) -> dict:
    hour_bucket = random.choices(
        TIME_BUCKETS,
        weights=[4 if bucket in user.active_hours else 1 for bucket in TIME_BUCKETS],
        k=1,
    )[0]
    weather = random.choices(
        WEATHER,
        weights=[4 if item in user.weather_tolerance else 1 for item in WEATHER],
        k=1,
    )[0]
    nearby = random.sample(PLACE_TYPES, k=random.randint(2, 4))
    if random.random() < 0.75:
        nearby[0] = random.choice(user.place_affinities)
    return {
        "time_bucket": hour_bucket,
        "local_hour": {"morning": 9, "afternoon": 14, "evening": 19, "night": 22}[hour_bucket],
        "weather": weather,
        "nearby_place_types": sorted(set(nearby)),
        "day_type": random.choice(["weekday", "weekend"]),
    }


def simulate_outcome(
    user: SyntheticUser,
    quest: CandidateQuest,
    context: dict,
    history: list[dict],
) -> dict:
    score = user.completion_bias[quest.quest_type]
    if quest.quest_type in user.preferred_quest_types:
        score += 0.08
    if quest.base_difficulty > user.difficulty_tolerance:
        score -= 0.16 * (quest.base_difficulty - user.difficulty_tolerance)
    if context["time_bucket"] not in user.active_hours:
        score -= 0.07
    if context["weather"] not in user.weather_tolerance and quest.requires_location:
        score -= 0.12
    if quest.location_type and quest.location_type in user.place_affinities:
        score += 0.08
    if quest.quest_type == "social":
        score += (user.social_comfort - 0.5) * 0.25

    recent_same_type = sum(1 for item in history[-4:] if item["quest_type"] == quest.quest_type)
    if recent_same_type >= 2:
        score -= (1 - user.novelty_preference) * 0.18

    completion_probability = clamp(score)
    accepted_probability = clamp(completion_probability + 0.12)
    accepted = random.random() < accepted_probability
    completed = accepted and random.random() < completion_probability
    skipped = not accepted
    failed = accepted and not completed and random.random() < 0.25

    if completed:
        rating = random.choices([3, 4, 5], weights=[1, 3, 5], k=1)[0]
    elif skipped or failed:
        rating = random.choices([None, 1, 2, 3], weights=[5, 2, 3, 1], k=1)[0]
    else:
        rating = None

    label = 1 if completed or rating in {4, 5} else 0
    return {
        "accepted": accepted,
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "rating": rating,
        "label_positive": label,
        "simulated_completion_probability": round(completion_probability, 4),
    }


def make_ranking_example(
    user: SyntheticUser,
    quest: CandidateQuest,
    context: dict,
    outcome: dict,
    history: list[dict],
    example_index: int,
) -> dict:
    recent_counts = {quest_type: 0 for quest_type in QUEST_TYPES}
    recent_positive = {quest_type: 0 for quest_type in QUEST_TYPES}
    for item in history[-8:]:
        recent_counts[item["quest_type"]] += 1
        if item["completed"] or item["rating"] in {4, 5}:
            recent_positive[item["quest_type"]] += 1

    return {
        "example_id": f"{user.synthetic_user_id}_rank_{example_index:03d}",
        "task": "quest_ranking",
        "synthetic_user_id": user.synthetic_user_id,
        "user_features": {
            "archetype": user.archetype,
            "level": user.level,
            "preferred_quest_types": user.preferred_quest_types,
            "preferred_difficulty": user.preferred_difficulty,
            "difficulty_tolerance": user.difficulty_tolerance,
            "social_comfort": user.social_comfort,
            "novelty_preference": user.novelty_preference,
        },
        "context_features": context,
        "quest_features": asdict(quest),
        "recent_behavior_features": {
            "recent_counts": recent_counts,
            "recent_positive": recent_positive,
        },
        "outcome": outcome,
        "label": outcome["label_positive"],
    }


def make_generation_example(
    user: SyntheticUser,
    quest: CandidateQuest,
    context: dict,
    outcome: dict,
    history: list[dict],
) -> dict:
    tone = tone_for_user(user)
    title, description = generate_reference_quest_text(user, quest, context, tone)
    return {
        "task": "quest_text_generation",
        "synthetic_user_id": user.synthetic_user_id,
        "input": {
            "user_archetype": user.archetype,
            "level": user.level,
            "preferred_quest_types": user.preferred_quest_types,
            "recent_behavior_summary": summarize_history(history),
            "context": context,
            "desired_quest_type": quest.quest_type,
            "stat_category": quest.stat_category,
            "difficulty": quest.base_difficulty,
            "duration_minutes": quest.duration_minutes,
            "requires_location": quest.requires_location,
            "requires_photo": quest.requires_photo,
            "location_type": quest.location_type,
            "theme": quest.model_prompt_theme,
            "tone": tone,
            "constraints": {
                "backend_controls_xp": True,
                "backend_controls_coins": True,
                "backend_controls_rewards": True,
                "do_not_include_xp_or_coin_amounts": True,
                "keep_safe_and_real_world_doable": True,
            },
        },
        "output": {
            "title": title,
            "description": description,
            "quest_type": quest.quest_type,
            "stat_category": quest.stat_category,
            "difficulty_hint": quest.base_difficulty,
            "safety_notes": [],
        },
        "ranking_label_from_simulation": outcome["label_positive"],
    }


def tone_for_user(user: SyntheticUser) -> str:
    if user.archetype == "shy_growth":
        return "gentle and low-pressure"
    if user.archetype == "fitness_regular":
        return "direct and energetic"
    if user.archetype == "creative_doer":
        return "playful and observant"
    if user.archetype == "social_connector":
        return "warm and social"
    return "curious and encouraging"


def generate_reference_quest_text(
    user: SyntheticUser,
    quest: CandidateQuest,
    context: dict,
    tone: str,
) -> tuple[str, str]:
    place = quest.location_type or "nearby"
    weather_phrase = {
        "clear": "while the weather is friendly",
        "cloudy": "under the softer light today",
        "rain": "without needing to stay outside long",
        "snow": "in a way that stays safe and warm",
        "wind": "somewhere sheltered from the wind",
    }[context["weather"]]

    if quest.quest_type == "social":
        if user.social_comfort < 0.4:
            return (
                "Start One Small Connection",
                "Have one brief, kind interaction today, then write down what made it easier than expected.",
            )
        return (
            "Collect A Local Recommendation",
            "Ask someone for a favorite nearby spot or small tip, then save the recommendation for a future side quest.",
        )

    if quest.quest_type == "location":
        return (
            f"Notice Something New At A {place.title()}",
            f"Visit a {place} {weather_phrase}, find one detail you would usually miss, and write a short note about it.",
        )

    if quest.stat_category == "fitness":
        return (
            "Do A Quick Movement Burst",
            f"Find a comfortable spot {weather_phrase} and complete a short movement routine that feels challenging but doable.",
        )

    return (
        "Make A Tiny Creative Field Note",
        f"Pause near something visually interesting {weather_phrase}, then sketch or describe one detail in your own style.",
    )


def summarize_history(history: list[dict]) -> dict:
    if not history:
        return {"completed_by_type": {}, "skipped_by_type": {}, "average_rating": None}
    completed_by_type = {quest_type: 0 for quest_type in QUEST_TYPES}
    skipped_by_type = {quest_type: 0 for quest_type in QUEST_TYPES}
    ratings = []
    for item in history[-10:]:
        if item["completed"]:
            completed_by_type[item["quest_type"]] += 1
        if item["skipped"]:
            skipped_by_type[item["quest_type"]] += 1
        if item["rating"] is not None:
            ratings.append(item["rating"])
    return {
        "completed_by_type": completed_by_type,
        "skipped_by_type": skipped_by_type,
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + "\n")


def write_readme(
    output_dir: Path,
    users: list[SyntheticUser],
    ranking_examples: list[dict],
    generation_examples: list[dict],
) -> None:
    archetype_counts = {}
    for user in users:
        archetype_counts[user.archetype] = archetype_counts.get(user.archetype, 0) + 1

    lines = [
        "# Synthetic ML Data",
        "",
        "This folder contains synthetic data for Quest Up ML development.",
        "",
        "It is intentionally stored in files instead of the application database so fake users do not pollute production-style tables.",
        "",
        "## Files",
        "",
        "- `synthetic_users.jsonl`: synthetic user personas with similar and different behavior profiles.",
        "- `quest_ranking_examples.jsonl`: examples for training/evaluating a quest ranking model.",
        "- `quest_generation_examples.jsonl`: examples for an OpenAI/text-generation layer that creates quest text from scratch under backend constraints.",
        "",
        "## Counts",
        "",
        f"- Users: `{len(users)}`",
        f"- Ranking examples: `{len(ranking_examples)}`",
        f"- Text generation examples: `{len(generation_examples)}`",
        "",
        "## User Variety",
        "",
    ]
    for archetype, count in sorted(archetype_counts.items()):
        lines.append(f"- `{archetype}`: `{count}`")

    lines.extend(
        [
            "",
            "## Intended Model Uses",
            "",
            "Ranking examples should train or test a model that predicts whether a user is likely to accept, complete, or enjoy a candidate quest.",
            "",
            "Generation examples should guide an OpenAI prompt/fine-tuning/evaluation workflow where the model writes original quest titles and descriptions from scratch.",
            "",
            "The backend should still control XP, coins, rewards, active quest limits, difficulty bounds, and validation.",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def clamp(value: float, minimum: float = 0.05, maximum: float = 0.95) -> float:
    return max(minimum, min(maximum, value))


if __name__ == "__main__":
    main()
