# Synthetic ML Data

This folder contains synthetic data for Quest Up ML development.

It is intentionally stored in files instead of the application database so fake users do not pollute production-style tables.

## Files

- `synthetic_users.jsonl`: synthetic user personas with similar and different behavior profiles.
- `quest_ranking_examples.jsonl`: examples for training/evaluating a quest ranking model.
- `quest_generation_examples.jsonl`: examples for an OpenAI/text-generation layer that creates quest text from scratch under backend constraints.

## Counts

- Users: `120`
- Ranking examples: `3600`
- Text generation examples: `3600`

## User Variety

- `balanced_casual`: `20`
- `creative_doer`: `20`
- `fitness_regular`: `20`
- `location_explorer`: `20`
- `shy_growth`: `20`
- `social_connector`: `20`

## Intended Model Uses

Ranking examples should train or test a model that predicts whether a user is likely to accept, complete, or enjoy a candidate quest.

Generation examples should guide an OpenAI prompt/fine-tuning/evaluation workflow where the model writes original quest titles and descriptions from scratch.

The backend should still control XP, coins, rewards, active quest limits, difficulty bounds, and validation.