import sys
from pathlib import Path

import pytest_asyncio

# Add apps/api to Python path for pytest imports
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    """Ensure the test database schema is created before any test runs."""
    from app.db.session import engine
    from app.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optionally drop all after tests (keep for inspection)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
