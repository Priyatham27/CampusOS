import pytest
import io
from fastapi import UploadFile
from beanie import PydanticObjectId

from app.core.exceptions import (
    OrganizationNotFound,
    BrandingNotFound,
    InvalidColor,
    InvalidImage,
    InvalidTheme
)
from app.models.org_engine.organization import Organization, Branding, BrandingRevision
from app.services.branding import BrandingService
from app.repositories.branding import BrandingRepository
from app.repositories.organization import OrganizationRepository

pytestmark = pytest.mark.asyncio

@pytest.fixture
def branding_service():
    return BrandingService()

@pytest.fixture
def org_repo():
    return OrganizationRepository()

async def test_service_default_seeding(branding_service, org_repo):
    # 1. Test create organization triggers branding seeding
    from app.services.organization import OrganizationService
    org_service = OrganizationService()
    
    payload = {
        "organizationId": "ORG_987654",
        "name": "Branding Seed College",
        "shortName": "SeedCol",
        "emailDomain": "seed.edu",
        "contactEmail": "admin@seed.edu",
    }
    org = await org_service.create_organization(payload)
    
    # 2. Get branding through branding service
    branding = await branding_service.get_branding("ORG_987654")
    assert branding is not None
    assert branding.primary_color == "#4F46E5"
    assert branding.secondary_color == "#0891B2"
    assert branding.version == 1

async def test_service_update_and_preview(branding_service, org_repo):
    org = Organization(
        organization_id="ORG_444111",
        name="Update Service College",
        short_name="UpServ",
        slug="update-service-college",
        email_domain="upserv.edu",
        contact_email="admin@upserv.edu"
    )
    org = await org_repo.create(org)
    
    # Test preview update (buffered in preview_config)
    preview_data = {"primaryColor": "#FF5733", "theme": "dark"}
    branding = await branding_service.update_branding("ORG_444111", preview_data, preview=True)
    assert branding.preview_config is not None
    assert branding.preview_config["primaryColor"] == "#FF5733"
    
    # Active color should still be default in DB
    raw_branding = await Branding.find_one(Branding.organization_id == org.id)
    assert raw_branding.primary_color == "#4F46E5"
    
    # Getting branding with preview=True should return updated values
    resolved = await branding_service.get_branding("ORG_444111", preview=True)
    assert resolved.primary_color == "#FF5733"
    assert resolved.theme == "dark"

    # Commit update (preview=False)
    commit_data = {"primaryColor": "#00FF00", "theme": "light"}
    published = await branding_service.update_branding("ORG_444111", commit_data, preview=False)
    assert published.primary_color == "#00FF00"
    assert published.version == 2
    assert published.preview_config is None

    # Check history contains version 1 snapshot
    history = await branding_service.get_branding_history("ORG_444111")
    assert len(history) == 1
    assert history[0].version == 1
    assert history[0].branding_data["primary_color"] == "#4F46E5"

async def test_service_css_and_tailwind_generation(branding_service):
    branding = Branding(
        organization_id=PydanticObjectId(),
        primary_color="#FFAA00",
        secondary_color="#00AAFF"
    )
    css = branding_service.generate_css_variables(branding)
    assert "--primary-color: #FFAA00" in css
    assert "--secondary-color: #00AAFF" in css
    
    tokens = branding_service.generate_theme_tokens(branding)
    assert tokens["theme"]["extend"]["colors"]["primary"] == "#FFAA00"
    assert tokens["theme"]["extend"]["colors"]["secondary"] == "#00AAFF"

async def test_service_rollback(branding_service, org_repo):
    org = Organization(
        organization_id="ORG_333222",
        name="Rollback College",
        short_name="RollCol",
        slug="rollback-college",
        email_domain="roll.edu",
        contact_email="admin@roll.edu"
    )
    org = await org_repo.create(org)

    # Make version 1 -> version 2
    await branding_service.update_branding("ORG_333222", {"primaryColor": "#FF0000"}, preview=False)
    # Make version 2 -> version 3
    await branding_service.update_branding("ORG_333222", {"primaryColor": "#00FF00"}, preview=False)

    # Rollback to version 2 (which had primary_color = #FF0000)
    rolled = await branding_service.rollback_branding("ORG_333222", 2)
    assert rolled.primary_color == "#FF0000"
    assert rolled.version == 4  # Version increments cleanly on rollback

    # Rollback again to version 1 (which had primary_color = #4F46E5)
    rolled2 = await branding_service.rollback_branding("ORG_333222", 1)
    assert rolled2.primary_color == "#4F46E5"
    assert rolled2.version == 5

async def test_service_image_size_and_format_validation(branding_service, org_repo):
    org = Organization(
        organization_id="ORG_777888",
        name="Image College",
        short_name="ImgCol",
        slug="image-college",
        email_domain="img.edu",
        contact_email="admin@img.edu"
    )
    org = await org_repo.create(org)

    # 1. Size failure
    large_bytes = b"0" * (6 * 1024 * 1024) # 6MB
    upload_file = UploadFile(filename="logo.png", file=io.BytesIO(large_bytes), headers={"content-type": "image/png"})
    with pytest.raises(InvalidImage) as exc:
        await branding_service.upload_logo("ORG_777888", upload_file)
    assert "logo file size exceeds limit" in str(exc.value).lower()

    # 2. Format failure
    invalid_format = UploadFile(filename="doc.txt", file=io.BytesIO(b"hello"), headers={"content-type": "text/plain"})
    with pytest.raises(InvalidImage) as exc:
        await branding_service.upload_logo("ORG_777888", invalid_format)
    assert "unsupported file format" in str(exc.value).lower()
