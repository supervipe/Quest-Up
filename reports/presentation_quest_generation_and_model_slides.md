# Presentation Slide Plan: Quest Generation + ML Model

## Slide 1: How Quest Up Generates A Quest

### Slide Goal

Explain that quest generation is not random only. It combines real-world context, user preferences, behavior, and controlled randomness.

### Suggested Slide Title

```text
How Quest Up Generates A Quest
```

### Suggested Layout

Use a simple left-to-right flow diagram:

```text
User + Context
      ↓
Candidate Quest Templates
      ↓
Scoring Formula
      ↓
Weighted Quest Selection
      ↓
Backend Finalizes Quest
```

### Main Slide Content

```text
1. Collect context
   - User profile and preferences
   - Nearby places
   - Weather
   - Time of day
   - Recent quest history

2. Score candidate quests
   Final Score =
   60% Context Match
   + 20% Preference / Behavior
   + 20% Random Discovery

3. Select and finalize
   - Pick a quest using weighted selection
   - Apply difficulty rules
   - Set XP, coins, expiration, and rewards
   - Save quest to the database
```

### Formula To Show On Slide

```text
Quest Score =
0.60(Context)
+ 0.20(Preference + Behavior)
+ 0.20(Randomness)
```

### Visual Suggestion

Use three colored blocks feeding into one score:

```text
[Context 60%] + [User Fit 20%] + [Discovery 20%] → Quest Score
```

Then show:

```text
Highest score is not always guaranteed.
Weighted selection keeps the feed varied.
```

### Speaker Notes

```text
The backend first finds valid quest templates, then scores them based on how well they match the user's current context and behavior. Context has the biggest weight because Quest Up is location-aware. Preferences and behavior help personalize the feed, while randomness prevents the same type of quest from appearing every time. After a quest is selected, the backend still controls game balance: difficulty, XP, coins, expiration, and rewards.
```

---

## Slide 2: Quest Ranking Model

### Slide Goal

Explain the trained model in simple terms: it predicts which quest a user is likely to accept, complete, or enjoy.

### Suggested Slide Title

```text
ML Model: Ranking Quests For Each User
```

### Suggested Layout

Use a two-column layout.

Left side:

```text
What the model uses
```

Right side:

```text
What the model outputs
```

Bottom:

```text
How it combines with backend rules
```

### Main Slide Content

```text
Model Type:
Logistic Regression ranking model

Purpose:
Predict how likely a user is to accept, complete, or enjoy a quest.

Training Data:
Synthetic quest interaction examples + real backend ML interaction export.
```

### Features Used

```text
User Features
- Level
- XP and coins
- Current streak
- Preferred quest types
- Preferred difficulty

Quest Features
- Quest type
- Difficulty
- XP reward
- Coin reward
- Requires location
- Requires photo

Context Features
- Local hour
- Weather
- Nearby place types

Recent Behavior
- Recent accepted/completed quests
- Recent skipped quests
- Positive/negative behavior by quest type
```

### Model Output Example

```text
Candidate quests:

Visit a Park        → Model Score: 0.42
Compliment Someone  → Model Score: 0.78
Sketch the View     → Model Score: 0.36

The model suggests the social quest is the strongest fit.
```

### Hybrid Ranking Formula

```text
Hybrid Score =
65% Backend Rule Score
+ 35% ML Model Score
```

### Important Clarification

```text
The model helps choose the best quest.
The backend still controls XP, coins, rewards, levels, and validation.
```

### Visual Suggestion

Use a simple diagram:

```text
Backend Rule Score ─┐
                    ├─ Hybrid Score → Quest Selection
ML Model Score ─────┘
```

Or:

```text
[Rule Score 65%] + [Model Score 35%] → Final Ranking
```

### Speaker Notes

```text
The model is trained to rank quests, not to control the game economy. It looks at user features, quest features, context, and recent behavior to predict which quest is most likely to be accepted or completed. The backend then combines the model score with the existing rule score. This keeps the system personalized but still balanced and predictable.
```

---

## Short Talk Track For Both Slides

```text
Quest Up generates quests through a hybrid process. First, the backend evaluates valid quest templates using context, preferences, behavior, and randomness. Then the ML ranking model adds a personalization score based on patterns learned from training data. The final quest is selected using a combined score, but the backend remains responsible for all progression rules like XP, coins, rewards, difficulty, and levels.
```

## Optional One-Sentence Summary

```text
Quest generation is context-aware and personalized, while backend rules keep the RPG progression balanced.
```
