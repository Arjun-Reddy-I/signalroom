import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Set provider env vars BEFORE any app imports (before settings is read)
os.environ["STT_PROVIDER"] = "fallback"
os.environ["LLM_PROVIDER"] = "fallback"
os.environ["EMBEDDING_PROVIDER"] = "fallback"
os.environ["GEMINI_API_KEY"] = ""   # prevent SmartLLMProvider from calling Gemini in tests
os.environ["OPENAI_API_KEY"] = ""

# Add apps/api to Python path for pytest imports
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))


@pytest.fixture(autouse=True, scope="session")
def reset_provider_singletons():
    """Reset provider singletons and blank out API keys so tests use fallback providers."""
    import app.providers.stt as stt_mod
    import app.providers.llm as llm_mod
    import app.providers.embeddings as emb_mod
    from app.core.config import settings

    # Force fallback providers regardless of .env settings
    object.__setattr__(settings, "STT_PROVIDER", "fallback")
    object.__setattr__(settings, "LLM_PROVIDER", "fallback")
    object.__setattr__(settings, "EMBEDDING_PROVIDER", "fallback")
    object.__setattr__(settings, "GEMINI_API_KEY", "")
    object.__setattr__(settings, "OPENAI_API_KEY", "")

    stt_mod._provider_instance = None
    llm_mod._provider_instance = None
    emb_mod._provider_instance = None
    yield


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
