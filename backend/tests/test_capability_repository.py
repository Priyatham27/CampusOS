import pytest
from beanie import PydanticObjectId

from app.models.org_engine.capability import Capability, CapabilityCategory, CapabilityStatus, LicenseTier
from app.repositories.capability import CapabilityRepository

pytestmark = pytest.mark.asyncio

async def test_capability_repository_lifecycle():
    repo = CapabilityRepository()
    org_id = PydanticObjectId()

    cap = Capability(
        capabilityId="CAP_000001",
        organizationId=org_id,
        name="Test Analytics",
        slug="test-analytics",
        displayName="Test Analytics Capability",
        description="A capability for verification testing.",
        category=CapabilityCategory.Analytics,
        icon="bar-chart",
        capability_version="1.0.0",
        status=CapabilityStatus.AVAILABLE,
        dependencies=[],
        licenseRequired=True,
        licenseTier=LicenseTier.PRO
    )

    # 1. Create
    await repo.create(cap)
    assert cap.id is not None

    # 2. Find by Custom ID
    found = await repo.find_by_id("CAP_000001", org_id)
    assert found is not None
    assert found.slug == "test-analytics"

    # 3. Find by Slug
    found_slug = await repo.find_by_slug("test-analytics", org_id)
    assert found_slug is not None
    assert found_slug.name == "Test Analytics"

    # 4. Exists
    exists = await repo.exists(org_id, "test-analytics")
    assert exists is True

    # 5. List and Count
    items = await repo.list(org_id, limit=5)
    assert len(items) == 1
    cnt = await repo.count(org_id)
    assert cnt == 1

    # 6. Update
    await repo.update(cap, {"displayName": "Test Analytics Revised"})
    assert cap.display_name == "Test Analytics Revised"

    # 7. Delete (soft)
    await repo.delete(cap)
    assert cap.is_deleted is True

    # Find after soft-delete should return None
    found_after = await repo.find_by_id("CAP_000001", org_id)
    assert found_after is None
