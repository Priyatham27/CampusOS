import pytest
from beanie import PydanticObjectId

from app.models.org_engine.organization import Organization, SubscriptionInfo, SubscriptionPlan
from app.models.org_engine.capability import Capability, CapabilityStatus, LicenseTier
from app.services.capability import CapabilityService
from app.core.exceptions import (
    CircularDependency, LicenseViolation, CompatibilityViolation, CoreModuleProtected, DependencyMissing
)

pytestmark = pytest.mark.asyncio

async def test_capability_service_seeding_and_rules():
    service = CapabilityService()

    # 1. Create Organization (FREE Subscription Plan)
    org = Organization(
        organizationId="ORG_999000",
        name="Test Service College",
        shortName="TSC",
        slug="tsc-slug",
        emailDomain="tsc.edu",
        contactEmail="admin@tsc.edu",
        subscription=SubscriptionInfo(plan=SubscriptionPlan.FREE)
    )
    await org.insert()

    # 2. Seed Default Capabilities
    seeded = await service.seed_default_capabilities("ORG_999000")
    assert len(seeded) == 20

    # Verify that core platform capability is active
    platform_cap = await service.cap_repo.find_by_slug("platform", org.id)
    assert platform_cap is not None
    assert platform_cap.enabled is True

    # 3. Test Core Capability Protect (Disable Platform)
    with pytest.raises(CoreModuleProtected):
        await service.disable_capability("ORG_999000", platform_cap.capability_id)

    # 4. Test Core Capability Protect (Delete Platform)
    with pytest.raises(CoreModuleProtected):
        await service.delete_capability("ORG_999000", platform_cap.capability_id)

    # 5. Dependency Enable Check: Try to enable AI (depends on analytics)
    ai_cap = await service.cap_repo.find_by_slug("ai", org.id)
    assert ai_cap is not None
    assert ai_cap.enabled is False
    with pytest.raises(DependencyMissing):
        await service.enable_capability("ORG_999000", ai_cap.capability_id)

    # 6. Licensing Check: Enable Analytics (Pro tier) on FREE organization plan
    analytics_cap = await service.cap_repo.find_by_slug("analytics", org.id)
    assert analytics_cap is not None
    with pytest.raises(LicenseViolation):
        await service.enable_capability("ORG_999000", analytics_cap.capability_id)

    # Upgrade organization plan to PREMIUM (covers PRO tier analytics)
    org.subscription.plan = SubscriptionPlan.PREMIUM
    await org.save()

    # Enable Analytics should now succeed (since Platform core is enabled)
    enabled_analytics = await service.enable_capability("ORG_999000", analytics_cap.capability_id)
    assert enabled_analytics.enabled is True
    assert enabled_analytics.status == CapabilityStatus.ENABLED

    # 7. Dependent Disable Protection: Test using custom capabilities
    # Create cap-parent
    cap_parent = await service.create_capability("ORG_999000", {
        "name": "Parent Cap",
        "slug": "cap-parent",
        "displayName": "Parent Cap"
    })
    # Create cap-child (depends on cap-parent)
    cap_child = await service.create_capability("ORG_999000", {
        "name": "Child Cap",
        "slug": "cap-child",
        "displayName": "Child Cap",
        "dependencies": ["cap-parent"]
    })

    # Enable parent, then enable child
    await service.enable_capability("ORG_999000", cap_parent.capability_id)
    await service.enable_capability("ORG_999000", cap_child.capability_id)

    # Try to disable cap-parent while cap-child is active -> raises CompatibilityViolation
    with pytest.raises(CompatibilityViolation):
        await service.disable_capability("ORG_999000", cap_parent.capability_id)

    # 8. Circular Dependency Check
    # Register cap-a (no dependencies)
    cap_a = await service.create_capability("ORG_999000", {
        "name": "Cap A",
        "slug": "cap-a",
        "displayName": "Cap A",
        "dependencies": []
    })
    # Register cap-b (depends on cap-a)
    cap_b = await service.create_capability("ORG_999000", {
        "name": "Cap B",
        "slug": "cap-b",
        "displayName": "Cap B",
        "dependencies": ["cap-a"]
    })
    # Register cap-c (depends on cap-b)
    cap_c = await service.create_capability("ORG_999000", {
        "name": "Cap C",
        "slug": "cap-c",
        "displayName": "Cap C",
        "dependencies": ["cap-b"]
    })
    # Try to update cap-a to depend on cap-c, creating cycle: cap-a -> cap-c -> cap-b -> cap-a
    with pytest.raises(CircularDependency):
        await service.update_capability("ORG_999000", cap_a.capability_id, {
            "dependencies": ["cap-c"]
        })
