import pytest
from app.models.org_engine.organization import Organization

pytestmark = pytest.mark.asyncio

async def test_repo_create_organization(repo):
    org = Organization(
        organization_id="ORG_123456",
        name="Test Academy",
        short_name="TestAcad",
        slug="test-academy",
        email_domain="testacad.edu",
        contact_email="admin@testacad.edu"
    )
    saved_org = await repo.create(org)
    assert saved_org.id is not None
    assert saved_org.name == "Test Academy"
    assert saved_org.is_deleted is False

async def test_repo_find_by_id_and_slug(repo):
    org = Organization(
        organization_id="ORG_654321",
        name="Search Academy",
        short_name="Search",
        slug="search-academy",
        email_domain="search.edu",
        contact_email="admin@search.edu"
    )
    await repo.create(org)

    found_by_id = await repo.find_by_id("ORG_654321")
    assert found_by_id is not None
    assert found_by_id.name == "Search Academy"

    found_by_slug = await repo.find_by_slug("search-academy")
    assert found_by_slug is not None
    assert found_by_slug.organization_id == "ORG_654321"

async def test_repo_soft_delete(repo):
    org = Organization(
        organization_id="ORG_999999",
        name="Delete Academy",
        short_name="Delete",
        slug="delete-academy",
        email_domain="delete.edu",
        contact_email="admin@delete.edu"
    )
    saved_org = await repo.create(org)

    await repo.delete(saved_org)
    
    # Check that find_by_id filters it out!
    found = await repo.find_by_id("ORG_999999")
    assert found is None

    # But it still exists in the raw collection with is_deleted=True
    raw_found = await Organization.find_one(Organization.organization_id == "ORG_999999")
    assert raw_found is not None
    assert raw_found.is_deleted is True
    assert raw_found.deleted_at is not None

async def test_repo_exists_conflicts(repo):
    org = Organization(
        organization_id="ORG_888888",
        name="Conflict College",
        short_name="Conflict",
        slug="conflict-college",
        email_domain="conflict.edu",
        contact_email="admin@conflict.edu"
    )
    await repo.create(org)

    conflicts = await repo.exists(
        org_id="ORG_888888",
        slug="conflict-college",
        email_domain="conflict.edu",
        name="Conflict College"
    )
    assert "organizationId" in conflicts
    assert "slug" in conflicts
    assert "emailDomain" in conflicts
    assert "name" in conflicts

    clean = await repo.exists(
        org_id="ORG_777777",
        slug="clean-college",
        email_domain="clean.edu",
        name="Clean College"
    )
    assert len(clean) == 0

async def test_repo_list_and_search(repo):
    org1 = Organization(
        organization_id="ORG_111111",
        name="Engineering College",
        short_name="Engg",
        slug="engg-college",
        email_domain="engg.edu",
        contact_email="admin@engg.edu",
        search_keywords=["engineering", "engg"]
    )
    org2 = Organization(
        organization_id="ORG_222222",
        name="Medical College",
        short_name="Med",
        slug="med-college",
        email_domain="med.edu",
        contact_email="admin@med.edu",
        search_keywords=["medical", "med"]
    )
    await repo.create(org1)
    await repo.create(org2)

    # Test count
    cnt = await repo.count()
    assert cnt == 2

    # Test list pagination & sort
    lst = await repo.list(skip=0, limit=1, sort_by="name", sort_order="asc")
    assert len(lst) == 1
    assert lst[0].name == "Engineering College"

    # Test search fuzzy
    search_res = await repo.search("medical")
    assert len(search_res) == 1
    assert search_res[0].organization_id == "ORG_222222"
