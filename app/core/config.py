from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Quest Up API"
    environment: str = "local"
    database_url: str = "sqlite+aiosqlite:///./questup.db"
    sync_database_url: str = "sqlite:///./questup.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    weather_api_key: str = ""
    google_places_api_key: str = ""
    openai_api_key: str = ""
    photo_storage_mode: str = "local"
    normal_active_quest_limit: int = 2
    npc_default_spawn_chance: float = 0.70
    npc_accepted_spawn_chance: float = 0.20
    npc_cooldown_hours: int = 3
    npc_min_walking_minutes: int = 3
    npc_min_distance_meters: float = 100
    weekly_rollover_interval_seconds: int = 86400
    cors_allow_origins: list[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    cors_allow_origin_regex: str | None = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
