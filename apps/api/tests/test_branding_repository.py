import pytest
from bson import ObjectId
from beanie import PydanticObjectId

from apps.api.app.models.org_engine.organization import Organization, Branding, BrandingRevision
from apps.api.app.repositories.branding import BrandingRepository

pytestmark = pytest.mark.asyncio

@pytest.fixture
def branding_repo():
    return BrandingRepository()

async def test_repo_branding_lifecycle(branding_repo):
    org_id = PydanticObjectId()
    
    # 1. Create default Branding
    branding = Branding(
        organizationId=org_id,
        primaryColor="#4F46E5",
        secondaryColor="#0891B2"
    )
    await branding.insert()
    assert branding.id is not None
    assert branding.primary_color == "#4F46E5"
    
    # 2. Get Branding
    found = await branding_repo.get(org_id)
    assert found is not None
    assert found.id == branding.id
    
    # 3. Update Branding
    update_data = {
        "primaryColor": "#FF0000",
        "fontFamily": "Roboto",
        "theme": "dark"
    }
    updated = await branding_repo.update(found, update_data)
    assert updated.primary_color == "#FF0000"
    assert updated.font_family == "Roboto"
    assert updated.theme == "dark"
    
    # 4. Reset Branding
    reset_brand = await branding_repo.reset(updated)
    assert reset_brand.primary_color == "#4F46E5"
    assert reset_brand.theme == "light"
    assert reset_brand.font_family == "Inter"

async def test_repo_history_and_revisions(branding_repo):
    org_id = PydanticObjectId()
    
    # Create branding
    branding = Branding(
        organizationId=org_id,
        primaryColor="#111111",
        secondaryColor="#222222"
    )
    await branding.insert()

    # Save Revision 1
    rev1 = BrandingRevision(
        brandingId=branding.id,
        organizationId=org_id,
        version=1,
        brandingData={"primary_color": "#111111", "version": 1}
    )
    await branding_repo.save_revision(rev1)

    # Save Revision 2
    rev2 = BrandingRevision(
        brandingId=branding.id,
        organizationId=org_id,
        version=2,
        brandingData={"primary_color": "#333333", "version": 2}
    )
    await branding_repo.save_revision(rev2)

    # Fetch History
    hist = await branding_repo.history(org_id)
    assert len(hist) == 2
    assert hist[0].version == 2
    assert hist[1].version == 1

    # Fetch specific revision
    target_rev = await branding_repo.get_revision(org_id, 1)
    assert target_rev is not None
    assert target_rev.branding_data["primary_color"] == "#111111"
