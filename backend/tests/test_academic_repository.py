import pytest
from datetime import datetime
from beanie import PydanticObjectId

from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.repositories.academic import (
    AcademicYearRepository, DepartmentRepository, ProgramRepository,
    BranchRepository, SemesterRepository, SectionRepository, CourseRepository
)

pytestmark = pytest.mark.asyncio

async def test_academic_year_repository_lifecycle():
    repo = AcademicYearRepository()
    org_id = PydanticObjectId()

    acy = AcademicYear(
        academicYearId="ACY_000001",
        organizationId=org_id,
        name="2026-2027",
        startDate=datetime(2026, 6, 1),
        endDate=datetime(2027, 5, 31),
        current=True
    )
    # Create
    await repo.create(acy)
    assert acy.id is not None

    # Find
    found = await repo.find_by_id("ACY_000001", org_id)
    assert found is not None
    assert found.name == "2026-2027"

    # Exists
    exists = await repo.exists(org_id, "2026-2027")
    assert exists is True

    # Count
    cnt = await repo.count(org_id)
    assert cnt == 1

    # Update
    await repo.update(acy, {"name": "2026-2027 Revised"})
    assert acy.name == "2026-2027 Revised"

    # Delete (soft)
    await repo.delete(acy)
    assert acy.is_deleted is True

    # Find after soft-delete should return None
    found_after = await repo.find_by_id("ACY_000001", org_id)
    assert found_after is None

async def test_department_repository_lifecycle():
    repo = DepartmentRepository()
    org_id = PydanticObjectId()

    dep = Department(
        departmentId="DEP_000001",
        organizationId=org_id,
        name="Computer Science & Engineering",
        code="CSE",
        status="ACTIVE"
    )
    await repo.create(dep)
    assert dep.id is not None

    found = await repo.find_by_id("DEP_000001", org_id)
    assert found is not None
    assert found.code == "CSE"

    exists = await repo.exists(org_id, "CSE")
    assert exists is True

    await repo.update(dep, {"hod": "Dr. Alan Turing"})
    assert dep.hod == "Dr. Alan Turing"

    await repo.delete(dep)
    assert dep.is_deleted is True

async def test_program_repository_lifecycle():
    repo = ProgramRepository()
    org_id = PydanticObjectId()
    dep_id = PydanticObjectId()

    prg = Program(
        programId="PRG_000001",
        organizationId=org_id,
        departmentId=dep_id,
        name="Bachelor of Technology",
        duration=4,
        level="UNDERGRADUATE"
    )
    await repo.create(prg)
    assert prg.id is not None

    found = await repo.find_by_id("PRG_000001", org_id)
    assert found is not None
    assert found.name == "Bachelor of Technology"

    exists = await repo.exists(org_id, dep_id, "Bachelor of Technology")
    assert exists is True

    await repo.delete(prg)
    assert prg.is_deleted is True
