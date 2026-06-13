def build_features(context: dict) -> dict:
    return {
        "user_level": context.get("user_level", 1),
        "difficulty": context.get("difficulty", 1),
        "hour_of_day": context.get("hour_of_day", 12),
        "current_streak": context.get("current_streak", 0),
    }
