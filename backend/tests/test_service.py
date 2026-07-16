import pytest
from app.core.exceptions import (
    OrganizationAlreadyExists,
    SlugAlreadyExists,
    EmailDomainAlreadyExists
)
from app.models.org_engine.organization import Branding, OrganizationSettings
from app.models.org_engine.extension import Module, FeatureFlag

pytestmark = pytest.mark.asyncio

async def test_service_create_success(service):
    payload = {
        "organizationId": "ORG_111222",
        "name": "Service College",
        "shortName": "ServCol",
        "emailDomain": "service.edu",
        "contactEmail": "admin@service.edu",
    }
    
    # 1. Test creation and default slug generation
    org = await service.create_organization(payload)
    assert org.slug == "service-college"
    assert org.name == "Service College"
    
    # 2. Test dynamic seeds: Branding, settings, modules, flags
    branding = await Branding.find_one(Branding.organization_id == org.id)
    assert branding is not None
    assert branding.primary_color == "#4F46E5"

    settings = await OrganizationSettings.find_one(OrganizationSettings.organization_id == org.id)
    assert settings is not None
    assert settings.attendance_enabled is False

    modules_count = await Module.find(Module.organization_id == org.id).count()
    assert modules_count == 4

    flags_count = await FeatureFlag.find(FeatureFlag.organization_id == org.id).count()
    assert flags_count == 3

async def test_service_create_conflicts(service):
    payload1 = {
        "organizationId": "ORG_555555",
        "name": "Unique College",
        "shortName": "Unique",
        "slug": "unique-college",
        "emailDomain": "unique.edu",
        "contactEmail": "admin@unique.edu",
    }
    await service.create_organization(payload1)

    # Dup organizationId
    payload_dup_id = payload1.copy()
    payload_dup_id["name"] = "Other Name"
    payload_dup_id["slug"] = "other-slug"
    payload_dup_id["emailDomain"] = "other.edu"
    with pytest.raises(OrganizationAlreadyExists):
        await service.create_organization(payload_dup_id)

    # Dup name
    payload_dup_name = payload1.copy()
    payload_dup_name["organizationId"] = "ORG_666666"
    payload_dup_name["slug"] = "other-slug"
    payload_dup_name["emailDomain"] = "other.edu"
    with pytest.raises(OrganizationAlreadyExists):
        await service.create_organization(payload_dup_name)

    # Dup slug
    payload_dup_slug = payload1.copy()
    payload_dup_slug["organizationId"] = "ORG_666666"
    payload_dup_slug["name"] = "Other Name"
    payload_dup_slug["emailDomain"] = "other.edu"
    with pytest.raises(SlugAlreadyExists):
        await service.create_organization(payload_dup_slug)

    # Dup email domain
    payload_dup_domain = payload1.copy()
    payload_dup_domain["organizationId"] = "ORG_666666"
    payload_dup_domain["name"] = "Other Name"
    payload_dup_domain["slug"] = "other-slug"
    with pytest.raises(EmailDomainAlreadyExists):
        await service.create_organization(payload_dup_domain)
