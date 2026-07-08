import pytest
from beanie import PydanticObjectId

from apps.api.app.models.org_engine.config import (
    Configuration, FeatureFlag, ConfigScope, ConfigEnvironment
)
from apps.api.app.repositories.config import ConfigurationRepository, FeatureFlagRepository

pytestmark = pytest.mark.asyncio

async def test_configuration_repository_lifecycle():
    repo = ConfigurationRepository()
    org_id = PydanticObjectId()

    config = Configuration(
        configId="CFG_000001",
        organizationId=org_id,
        key="app.theme",
        value="dark",
        type="string",
        scope=ConfigScope.ORGANIZATION,
        environment=ConfigEnvironment.PRODUCTION
    )

    # 1. Create
    await repo.create(config)
    assert config.id is not None

    # 2. Find by Custom ID
    found = await repo.find_by_id("CFG_000001", org_id)
    assert found is not None
    assert found.key == "app.theme"

    # 3. Find by key and context
    found_ctx = await repo.find_by_key_and_context("app.theme", org_id, ConfigEnvironment.PRODUCTION, ConfigScope.ORGANIZATION)
    assert found_ctx is not None
    assert found_ctx.value == "dark"

    # 4. List and count
    items = await repo.list(org_id, limit=5)
    assert len(items) == 1
    cnt = await repo.count(org_id)
    assert cnt == 1

    # 5. Update
    await repo.update(config, {"value": "light"})
    assert config.value == "light"

    # 6. Delete
    await repo.delete(config)
    assert config.is_deleted is True

    # Find after soft-delete should return None
    found_after = await repo.find_by_id("CFG_000001", org_id)
    assert found_after is None

async def test_feature_flag_repository_lifecycle():
    repo = FeatureFlagRepository()
    org_id = PydanticObjectId()

    flag = FeatureFlag(
        flagId="FLG_000001",
        organizationId=org_id,
        key="events.qr_enabled",
        name="QR Registration Flag",
        category="Events",
        enabled=True,
        defaultValue=False,
        environment=ConfigEnvironment.PRODUCTION
    )

    # 1. Create
    await repo.create(flag)
    assert flag.id is not None

    # 2. Find by ID
    found = await repo.find_by_id("FLG_000001", org_id)
    assert found is not None
    assert found.key == "events.qr_enabled"

    # 3. Find by Key
    found_key = await repo.find_by_key("events.qr_enabled", org_id, ConfigEnvironment.PRODUCTION)
    assert found_key is not None
    assert found_key.enabled is True

    # 4. List and count
    items = await repo.list(org_id, limit=5)
    assert len(items) == 1
    cnt = await repo.count(org_id)
    assert cnt == 1

    # 5. Update
    await repo.update(flag, {"name": "QR Registration Flag Revised"})
    assert flag.name == "QR Registration Flag Revised"

    # 6. Delete
    await repo.delete(flag)
    assert flag.is_deleted is True

    # Find after soft-delete should return None
    found_after = await repo.find_by_id("FLG_000001", org_id)
    assert found_after is None
