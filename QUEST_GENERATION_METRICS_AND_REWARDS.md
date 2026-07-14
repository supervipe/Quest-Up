# Quest Generation Metrics, XP, Coins, And Rewards

This document explains the current backend rules used to choose quests, calculate XP/coins, award rewards, and evaluate achievements. It also describes how these rules should continue to apply when a trained model or OpenAI-based quest generation layer is integrated.

The important principle is:

```text
The model may recommend, rank, or write quests.
The backend remains the authority for game balance, validation, XP, coins, level progression, and rewards.
```

## Current Quest Sources

The backend currently supports three quest sources:

```text
normal
weekly
npc
```

Normal quests are generated from `QuestTemplate` records. Weekly quests are created from the active `WeeklyCommunityQuest`. NPC quests come from NPC offers.

## Normal Quest Generation Flow

Normal quest generation currently happens in `QuestGenerationService`.

Inputs used:

```text
user profile
user level
preferred quest types
preferred radius
preferred difficulty
recent quests
nearby places
weather
local time
active quest count
quest templates
```

High-level flow:

1. Lock the user row to avoid duplicate concurrent generation.
2. Expire stale normal quests.
3. Check the active normal quest limit.
4. Load user profile.
5. Find nearby places.
6. Get current weather.
7. Load recent normal quests.
8. Load active quest templates available at the user's level.
9. Avoid active duplicate templates and strongly recent templates.
10. Score each candidate template.
11. Pick one using weighted random selection.
12. Adapt difficulty.
13. Create the `UserQuest`.
14. Record an ML `shown` event.

## Active Quest Limit

The backend currently limits active normal quests:

```text
NORMAL_ACTIVE_QUEST_LIMIT = 2
```

Only quests with these statuses count toward the limit:

```text
active
accepted
```

Only normal quests count toward this limit. Weekly and NPC quests do not count against the normal quest limit.

## Template Eligibility

A normal quest template must be:

```text
is_active = true
min_user_level <= user.level
```

The generator then avoids repetition:

```text
1. Remove templates already active/accepted for the user, when possible.
2. Remove templates used in the latest 4 recent quests, when possible.
3. If filtering removes everything, fall back to the wider candidate set.
```

This keeps the feed from showing the exact same quest repeatedly unless there are too few templates available.

## Quest Recommendation Score

Each candidate quest template receives a score made from:

```text
context score
preference score
randomness
```

Final score:

```text
total = max(0.01, 0.60 * context_score + 0.20 * preference_score + 0.20 * randomness)
```

The chosen quest is selected with weighted random choice:

```text
random.choices(scored_templates, weights = total_score)
```

This means the highest-scoring quest is more likely, but not guaranteed. The feed keeps some variety.

## Context Score

Context score combines location, weather, and time:

```text
context_score = (location_score + weather_score + time_score) / 3
```

### Location Score

```text
if template does not require location:
    location_score = 0.75

if template requires location and matching place type exists nearby:
    location_score = 1.0

if template requires location and no matching place type exists:
    location_score = 0.15
```

Example:

```text
Template location_type = "park"
Nearby places include "park"
location_score = 1.0
```

### Weather Score

```text
if template has no weather rules:
    weather_score = 0.75

if current weather condition is allowed by template:
    weather_score = 1.0

if current weather condition is not allowed:
    weather_score = 0.1
```

### Time Score

```text
if template has no time window:
    time_score = 0.75

if local hour is inside the template time window:
    time_score = 1.0

if local hour is outside the template time window:
    time_score = 0.1
```

Time windows support normal ranges and overnight ranges.

## Preference Score

Preference score combines explicit preferences and observed behavior:

```text
preference_score = ((preferred_score + behavior_score) / 2) * repetition_score
```

### Preferred Score

```text
if template.quest_type is in profile.preferred_quest_types:
    preferred_score = 1.0
else:
    preferred_score = 0.35
```

If the user has no profile, the default preferred quest types are:

```text
location
social
action
```

### Behavior Score

The backend looks at recent quests with the same quest type.

```text
if no recent quests of the same type:
    behavior_score = 0.5
else:
    behavior_score = max(0.2, positive_same_type_count / same_type_count)
```

Positive statuses are:

```text
accepted
completed
```

This means if the user accepts or completes social quests often, future social templates get stronger behavior scores.

### Repetition Score

Repetition score reduces the chance of showing too many same-type quests in a row.

```text
if latest 2 recent quests are the same quest type as the candidate:
    repetition_score = 0.25

else if latest recent quest is the same quest type as the candidate:
    repetition_score = 0.65

else:
    repetition_score = 1.0
```

So behavior can pull the system toward a user's interests, but repetition control prevents the feed from becoming one-note.

## Randomness Score

Randomness is:

```text
randomness = random.random()
```

This produces a value from `0.0` to `1.0`.

Randomness contributes 20% of the final score.

Purpose:

```text
avoid stale feeds
occasionally test different quest types
support discovery
```

## Difficulty Selection

Difficulty is currently selected from:

```text
profile.preferred_difficulty if present
otherwise template.base_difficulty
```

Then it is passed through `DifficultyService`.

Current difficulty rules:

```text
minimum difficulty = 1
maximum difficulty = 5
```

If completion rate is not available:

```text
difficulty = clamp(base_difficulty, 1, 5)
```

If completion rate is available:

```text
if completion_rate > 0.80:
    difficulty = min(5, base_difficulty + 1)

if completion_rate < 0.50:
    difficulty = max(1, base_difficulty - 1)

otherwise:
    difficulty = clamp(base_difficulty, 1, 5)
```

The current generation flow does not yet calculate per-user completion rate, but the service is ready for it.

## Base XP And Base Coins

Normal quests store XP and coins from the selected template:

```text
quest.xp_reward = template.base_xp
quest.coin_reward = template.base_coins
```

Examples from seeded templates:

| Template | Type | Base Difficulty | Base XP | Base Coins |
|---|---|---:|---:|---:|
| Visit a New Park | location | 2 | 45 | 12 |
| Cafe Vibe Check | location | 1 | 30 | 8 |
| Compliment Three People | social | 3 | 60 | 18 |
| Sketch the View | action | 2 | 50 | 14 |
| Outdoor Fitness Burst | action | 3 | 65 | 20 |

Weekly quests currently define their own fixed XP, coins, and reward item:

```text
Neighborhood Snapshot Challenge
XP = 120
Coins = 50
Reward item = Weekly Cape
Difficulty = 3 when converted to a user quest
```

## Quest Expiration

Normal quests expire after:

```text
1 day
```

Weekly user quests expire at:

```text
weekly_community_quest.ends_at
```

Expired active/accepted normal quests are marked:

```text
expired
```

Expired quests cannot be completed.

## XP Award Formula

XP is calculated when a quest is completed.

Formula:

```text
xp_awarded = floor(base_xp * difficulty_multiplier * streak_multiplier)
```

Where:

```text
base_xp = quest.xp_reward
```

Difficulty multipliers:

| Difficulty | Multiplier |
|---:|---:|
| 1 | 1.0 |
| 2 | 1.15 |
| 3 | 1.35 |
| 4 | 1.6 |
| 5 | 2.0 |

Streak multipliers:

| Current Streak | Multiplier |
|---:|---:|
| 0-2 | 1.0 |
| 3-6 | 1.1 |
| 7-13 | 1.25 |
| 14-29 | 1.5 |
| 30+ | 2.0 |

Example:

```text
base_xp = 60
difficulty = 3
difficulty_multiplier = 1.35
current_streak = 3
streak_multiplier = 1.1

xp_awarded = floor(60 * 1.35 * 1.1)
xp_awarded = floor(89.1)
xp_awarded = 89
```

The backend uses Decimal arithmetic and floors the result.

## Quest Coin Award

Quest coins currently come directly from the quest:

```text
coins_awarded = quest.coin_reward
```

Difficulty and streak do not currently multiply coins.

Total coins added on completion can include:

```text
quest coins
level-up coins
achievement coins
duplicate item compensation coins
```

## Streak Calculation

The backend uses the user's profile timezone when calculating streaks.

Rules:

```text
if user has never completed a quest:
    current_streak = 1

if completion is on the same local date as the previous completion:
    current_streak stays the same, with minimum 1

if completion is on the next local date:
    current_streak += 1

if one or more local dates were missed:
    current_streak = 1
```

The longest streak is updated with:

```text
longest_streak = max(longest_streak, current_streak)
```

## Level Formula

The XP required for each level is:

```text
xp_required_for_level(level) = floor(100 * 1.15 ^ (level - 1))
```

Examples:

```text
Level 2 requires 100 XP
Level 3 requires 115 additional XP
Level 4 requires 132 additional XP
```

Level is calculated by subtracting each level threshold from total XP until the remaining XP is below the next threshold.

Example:

```text
total_xp = 215

Level 1 -> 2 costs 100
remaining = 115

Level 2 -> 3 costs 115
remaining = 0

level = 3
```

## Level-Up Coin Rewards

When a user reaches a new level, the backend awards level-up coins.

Formula for each newly reached level:

```text
level_coin_reward = 25 + level * 5
```

If the user jumps multiple levels at once, rewards are summed.

Example:

```text
user moves from level 1 to level 3

level 2 reward = 25 + 2 * 5 = 35
level 3 reward = 25 + 3 * 5 = 40

total level-up coins = 75
```

Duplicate level-up claims are prevented by:

```text
last_level_reward_claimed_for_level
```

## Stat XP

Each quest has a `stat_category`.

On completion, the backend adds the awarded XP to the matching stat:

```text
social_xp
creativity_xp
exploration_xp
knowledge_xp
fitness_xp
```

Example:

```text
quest.stat_category = social
xp_awarded = 81

user_stats.social_xp += 81
```

Achievement XP does not currently add to stat XP. Stat XP reflects quest completion XP.

## Item Rewards

Quest item rewards can come from:

```text
fixed quest reward item
template-based random item reward
weekly quest reward item
npc quest reward item
achievement reward item
```

### Fixed Quest Reward

If a `UserQuest` has:

```text
reward_item_id
```

then that item is awarded on completion if active.

### Template-Based Random Item Reward

If the quest has no fixed reward item, the backend checks its template:

```text
possible_item_reward_rarity
item_reward_chance
```

Rules:

```text
if no possible_item_reward_rarity:
    no random item reward

if item_reward_chance <= 0:
    no random item reward

if random.random() > item_reward_chance:
    no random item reward

otherwise:
    choose a random active item with matching rarity
```

Example seeded template:

```text
Outdoor Fitness Burst
possible_item_reward_rarity = common
item_reward_chance = 0.1
```

This means a 10% chance to award a random active common item.

## Duplicate Item Compensation

If the user already owns the item, the backend does not create a duplicate inventory row. Instead, it awards compensation coins.

Base compensation by rarity:

| Rarity | Compensation |
|---|---:|
| common | 10 |
| rare | 25 |
| epic | 60 |
| legendary | 120 |

If the item has a purchase price:

```text
compensation = max(rarity_compensation, item.price_coins // 2)
```

Example:

```text
rare item price = 120
rarity compensation = 25
half price = 60

duplicate compensation = 60
```

## Reward Event Sources

Reward events are stored with a source:

```text
quest_completion
weekly_completion
npc_completion
level_up
achievement
```

Inventory acquisition source is stored separately:

```text
starter
purchase
quest_reward
weekly_reward
npc_reward
level_up
achievement
```

## Achievement Metrics

Achievements are evaluated after quest completion.

The backend currently supports these condition types:

```text
completed_quests
streak
quest_type_completed
weekly_submission
npc_accept
purchase
```

Progress is calculated as:

```text
progress = min(current_count / target_count, 1)
```

If the target is reached, the achievement unlocks once.

### Seeded Achievements

| Achievement | Condition | Bonus |
|---|---|---|
| First Quest Complete | completed_quests count 1 | 25 XP, 10 coins |
| 3-Day Streak | streak 3 days | 15 coins |
| 7-Day Streak | streak 7 days | 40 coins |
| Social Starter | 5 social completions | none |
| Explorer | 5 location completions | none |
| Weekly Hero | 1 weekly submission | Trophy Badge item |
| NPC Friend | 1 NPC quest accepted | none |
| First Purchase | 1 purchase | none |

Achievement XP and coins are added to user totals.

If an achievement has an item reward and the user already owns it, duplicate compensation rules apply.

## ML Interaction Events

The backend stores interaction events that can later be used for model training.

Current event types include:

```text
shown
accepted
skipped
completed
failed
rated
npc_spawned
npc_accepted
npc_declined
purchased_item
```

For quest generation, the backend records:

```text
shown
```

When a quest is accepted:

```text
accepted
```

When a quest is skipped:

```text
skipped
```

When a quest is completed:

```text
completed
```

If the user rates a quest:

```text
rated
```

These events are important training data for future model integration.

## How Model Integration Should Work

When a model is integrated, it should not replace the backend progression and reward system.

Recommended split:

| Responsibility | Model | Backend |
|---|---:|---:|
| Suggest quest themes | yes | validate |
| Rank candidate templates | yes | yes |
| Generate quest title/description | yes | validate/store |
| Estimate user interest | yes | yes |
| Enforce active quest limit | no | yes |
| Enforce difficulty range | no | yes |
| Calculate XP | no | yes |
| Calculate coins | no | yes |
| Award items | no | yes |
| Award achievements | no | yes |
| Set expiration | no | yes |
| Validate quest type/stat category | no | yes |
| Save database records | no | yes |

## Model Input Context

The model can receive structured context like:

```json
{
  "user": {
    "level": 3,
    "preferred_quest_types": ["location", "social"],
    "preferred_difficulty": 2,
    "recent_completion_counts": {
      "location": 1,
      "social": 3,
      "action": 0
    }
  },
  "context": {
    "local_hour": 15,
    "weather": "clear",
    "nearby_place_types": ["park", "cafe", "library"]
  },
  "constraints": {
    "allowed_quest_types": ["location", "social", "action"],
    "difficulty_min": 1,
    "difficulty_max": 5,
    "normal_active_quest_limit": 2
  }
}
```

## Model Output Contract

The model should return structured output, not free-form text only.

Example:

```json
{
  "quest_type": "social",
  "stat_category": "social",
  "difficulty_hint": 3,
  "title": "Start A Small Conversation",
  "description": "Ask someone nearby about a local favorite spot and write down one recommendation.",
  "requires_location": false,
  "requires_photo": false,
  "safety_notes": []
}
```

The backend should then validate and finalize:

```text
quest_type must be allowed
stat_category must be allowed
difficulty_hint must be clamped to 1-5
XP must be calculated by backend/template rules
coins must be calculated by backend/template rules
item rewards must be assigned by backend rules
expiration must be assigned by backend rules
```

## Model Integration Options

### Option 1: Model Ranks Existing Templates

The safest first integration:

```text
Backend loads valid templates.
Backend computes existing rule-based scores.
Model ranks or adjusts the candidate list.
Backend chooses from valid candidates.
Backend applies existing XP/coin/reward rules.
```

Benefits:

```text
low risk
keeps economy balanced
easy to test
uses existing quest templates
```

### Option 2: Model Rewrites Template Text

The model does not invent rewards. It only rewrites title/description.

```text
Template: Compliment Three People
Model output: "Give three genuine compliments during your next errand."
```

Backend still uses:

```text
template.quest_type
template.stat_category
template.base_xp
template.base_coins
template.base_difficulty
```

This gives variety without breaking game balance.

### Option 3: Model Proposes New Quest Candidates

More advanced:

```text
Model proposes a quest from scratch.
Backend validates it.
Backend maps it to allowed categories and reward bands.
Backend rejects unsafe/unbalanced quests.
```

This should happen only after enough interaction data exists.

## Recommended First Model Integration

The recommended first step is:

```text
Use the model to rewrite selected template title/description,
and optionally provide a personalization explanation.
```

Keep these backend values unchanged:

```text
quest_type
stat_category
difficulty
xp_reward
coin_reward
reward_item_id
expires_at
source
```

This improves quest variety while preserving the current tested mechanics.

## Example End-To-End With Model

1. Backend selects template:

```text
Compliment Three People
quest_type = social
base_difficulty = 3
base_xp = 60
base_coins = 18
```

2. Model rewrites content:

```text
Title: Make Three Small Moments Better
Description: Give three specific compliments today and note which one felt most natural.
```

3. Backend finalizes:

```text
difficulty = 3
xp_reward = 60
coin_reward = 18
expires_at = now + 1 day
```

4. User completes at streak 3:

```text
xp_awarded = floor(60 * 1.35 * 1.1)
xp_awarded = 89
coins_awarded = 18
```

5. Backend checks:

```text
level-up coins
item reward chance
duplicate item compensation
achievements
ML interaction events
```

The model improved the writing. The backend preserved the game balance.

## Current Design Summary

Quest selection is currently rule-based:

```text
60% context
20% preference/behavior
20% randomness
```

Quest completion rewards are currently formula-based:

```text
xp_awarded = floor(base_xp * difficulty_multiplier * streak_multiplier)
coins_awarded = quest.coin_reward
```

Leveling is currently cumulative:

```text
xp_required_for_level(level) = floor(100 * 1.15 ^ (level - 1))
```

Item rewards are currently backend-controlled:

```text
fixed quest reward
or template rarity chance
or achievement reward
or duplicate compensation
```

When the model is integrated, these formulas should remain backend-owned. The model should improve personalization, ranking, and text generation, while the backend enforces constraints and calculates all progression outcomes.
