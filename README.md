# Quest Up Backend

FastAPI backend foundation for Quest Up: JWT auth, PostgreSQL, SQLAlchemy 2.0, Alembic, seed data, quest top-up, progression, avatar store, weekly community quests, NPC encounters, and ML fallback interfaces.

## Local setup with `.venv`

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

For local tests without Docker, the test suite uses SQLite automatically.

```powershell
pytest
```

## Docker setup

```powershell
cd backend
Copy-Item .env.example .env
docker compose up --build
```

Docker Compose automatically applies migrations and idempotent seed data before starting the API.

API docs will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Useful endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `GET /profile`
- `POST /quests/session/open`
- `GET /quests/active`
- `POST /quests/{quest_id}/complete`
- `GET /community/weekly/current`
- `POST /walking/session/start`
- `POST /walking/session/update`
- `POST /npc/spawn/check`
- `POST /ml/recommend`
- `GET /external/weather`
- `GET /external/places`

Registration and login return both an access token and a refresh token. Use the access token in the `Authorization: Bearer ...` header. Refresh the session with:

```json
{
  "refresh_token": "your-refresh-token"
}
```

`GET /health` is the liveness check. `GET /health/ready` verifies PostgreSQL and Redis connectivity.

## External API smoke tests

The project includes `tests/test_external_apis.py`. It skips real external API checks unless you opt in:

```powershell
$env:RUN_EXTERNAL_API_TESTS="1"
$env:WEATHER_API_KEY=""
$env:GOOGLE_PLACES_API_KEY="your-key-if-you-have-one"
pytest tests/test_external_apis.py
```

Weather uses Open-Meteo, which does not require an API key for non-commercial MVP use, and falls back to mock data if the request fails. Places uses Google Places when `GOOGLE_PLACES_API_KEY` is set, otherwise it uses mock nearby places so the MVP remains runnable offline.

## PostgreSQL integration test

The normal test suite uses SQLite. To verify PostgreSQL-specific constraints against the isolated `questup_test` database:

```powershell
docker compose --profile test up -d test-db
$env:RUN_POSTGRES_TESTS="1"
$env:TEST_POSTGRES_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/questup_test"
pytest tests/test_postgres_integration.py
docker compose --profile test stop test-db
```
