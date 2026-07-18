import sys
import os

# Inject workspace directory and set test database environment variable BEFORE imports
sys.path.append("e:/CampusOS/backend")
os.environ["MONGODB_URL"] = "mongodb://localhost:27017/campusos_test_db"

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.database import db_manager
from app.models.org_engine import ORG_ENGINE_MODELS
from app.models.identity import IDENTITY_MODELS
from app.models.catalog import CATALOG_MODELS
from app.models.calendar import CALENDAR_MODELS
from app.repositories.organization import OrganizationRepository
from app.services.organization import OrganizationService

@pytest.fixture(scope="session")
async def test_db_client():
    """Initialize Beanie ODM with test database scope client once per session."""
    client = AsyncIOMotorClient("mongodb://localhost:27017/campusos_test_db")
    db = client.get_database("campusos_test_db")
    
    # Initialize Beanie Document Models for both modules
    await init_beanie(
        database=db,
        document_models=ORG_ENGINE_MODELS + IDENTITY_MODELS + CATALOG_MODELS + CALENDAR_MODELS
    )
    
    # Patch the global db_manager to use this test connection and disable standard connect calls
    db_manager.client = client
    db_manager.db = db
    db_manager.connect = lambda: None
    
    yield client
    
    # Clean up test database
    await client.drop_database("campusos_test_db")
    client.close()

@pytest.fixture(autouse=True)
async def clean_database(test_db_client):
    """Automatically clear all collection documents and flush the cache before running each test case."""
    db = test_db_client.get_database("campusos_test_db")
    collections = await db.list_collection_names()
    for col in collections:
        if not col.startswith("system."):
            await db[col].delete_many({})

    # Flush the caching layer to prevent cross-test leakage
    from app.core.database import get_redis
    redis = get_redis()
    if redis:
        if hasattr(redis, "flushall"):
            redis.flushall()
        elif hasattr(redis, "flushdb"):
            redis.flushdb()

@pytest.fixture
def repo():
    """Fixture returning the OrganizationRepository."""
    return OrganizationRepository()

@pytest.fixture
def service(repo):
    """Fixture returning the OrganizationService."""
    return OrganizationService(repo=repo)

@pytest.fixture(scope="session")
async def async_client(test_db_client):
    """Async Client for calling route endpoints during integration checks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
