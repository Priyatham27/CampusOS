import pytest
from datetime import datetime
from beanie import PydanticObjectId

from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.repositories.organization import OrganizationRepository
from apps.api.app.services.academic import AcademicService
from apps.api.app.core.exceptions import (
    DuplicateDepartment, DuplicateSemester, HierarchyViolation, DepartmentNotFound
)

pytestmark = pytest.mark.asyncio

async def test_service_academic_year_current_switch():
    org_repo = OrganizationRepository()
    service = AcademicService()

    # Create Organization
    org = Organization(
        organization_id="ORG_777888",
        name="Academic Service College",
        short_name="ASC",
        slug="academic-service-college",
        email_domain="asc.edu",
        contact_email="admin@asc.edu"
    )
    org = await org_repo.create(org)

    # 1. Create first current academic year
    acy1 = await service.create_academic_year("ORG_777888", {
        "name": "2026-2027",
        "startDate": datetime(2026, 6, 1),
        "endDate": datetime(2027, 5, 31),
        "current": True
    })
    assert acy1.current is True

    # 2. Create second current academic year -> should set first one to current=False
    acy2 = await service.create_academic_year("ORG_777888", {
        "name": "2027-2028",
        "startDate": datetime(2027, 6, 1),
        "endDate": datetime(2028, 5, 31),
        "current": True
    })
    assert acy2.current is True

    # Re-retrieve first academic year
    acy1_refreshed = await service.get_academic_year("ORG_777888", acy1.academic_year_id)
    assert acy1_refreshed.current is False


async def test_service_semester_sequential_integrity():
    org_repo = OrganizationRepository()
    service = AcademicService()

    # Create Organization
    org = Organization(
        organization_id="ORG_777111",
        name="Semester Seq College",
        short_name="SSC",
        slug="semester-seq-college",
        email_domain="ssc.edu",
        contact_email="admin@ssc.edu"
    )
    org = await org_repo.create(org)

    # Create Semester 1
    sem1 = await service.create_semester("ORG_777111", {
        "number": 1,
        "name": "Semester 1"
    })
    assert sem1.number == 1

    # Attempt to create Semester 3 (skip 2) -> Should fail
    with pytest.raises(HierarchyViolation):
        await service.create_semester("ORG_777111", {
            "number": 3,
            "name": "Semester 3"
        })

    # Create Semester 2 -> Succeeds
    sem2 = await service.create_semester("ORG_777111", {
        "number": 2,
        "name": "Semester 2"
    })
    assert sem2.number == 2


async def test_service_bulk_creations():
    org_repo = OrganizationRepository()
    service = AcademicService()

    # Create Organization
    org = Organization(
        organization_id="ORG_777222",
        name="Bulk Acad College",
        short_name="BAC",
        slug="bulk-acad-college",
        email_domain="bac.edu",
        contact_email="admin@bac.edu"
    )
    org = await org_repo.create(org)

    # Bulk create departments
    deps_data = [
        {"name": "Mechanical Engineering", "code": "ME"},
        {"name": "Electrical Engineering", "code": "EE"}
    ]
    deps = await service.bulk_create_departments("ORG_777222", deps_data)
    assert len(deps) == 2
    assert deps[0].code == "ME"
    assert deps[1].code == "EE"
