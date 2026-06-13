import os

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.quest import QuestTemplate

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1" or not os.getenv("TEST_POSTGRES_DATABASE_URL"),
    reason="Set RUN_POSTGRES_TESTS=1 and TEST_POSTGRES_DATABASE_URL to a dedicated questup_test database",
)
async def test_postgres_schema_and_check_constraints():
    database_url = os.environ["TEST_POSTGRES_DATABASE_URL"]
    if not database_url.rstrip("/").endswith("/questup_test"):
        pytest.fail("TEST_POSTGRES_DATABASE_URL must point to the dedicated questup_test database")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            session.add(
                QuestTemplate(
                    title="Invalid difficulty",
                    description_template="This row should be rejected.",
                    quest_type="action",
                    stat_category="fitness",
                    base_difficulty=6,
                    base_xp=10,
                    base_coins=5,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
