import re
from typing import Optional, Dict, Any
from beanie import PydanticObjectId

from app.core.user_exceptions import InvalidOrganization
from app.models.org_engine.academic import Department, Branch, Semester, Section
from app.models.org_engine.curriculum import Program

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{3,30}$")
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-()]{7,25}$")

def validate_email_domain(email: str, org_email_domain: str) -> None:
    """Ensure that the email address aligns with the organization's registered domain."""
    email_lower = email.lower()
    domain_lower = org_email_domain.lower()
    if not (email_lower.endswith(f"@{domain_lower}") or email_lower.endswith(f".{domain_lower}")):
        raise ValueError(f"Email address '{email}' must belong to the organization's domain '{org_email_domain}'.")

def validate_username_rules(username: str) -> None:
    """Ensure username fits character format and length requirements."""
    if not USERNAME_REGEX.match(username):
        raise ValueError("Username must be 3-30 characters and can only contain alphanumeric characters, underscores, hyphens, and periods.")

def validate_phone_format(phone: Optional[str]) -> None:
    """Validate telephone format if present."""
    if phone and not PHONE_REGEX.match(phone):
        raise ValueError("Phone number must be a valid telephone format (7-25 characters).")

async def validate_academic_references(org_id: PydanticObjectId, affiliation: Dict[str, Any]) -> None:
    """Verify that any provided academic references actually exist and are scoped to the organization."""
    # 1. Department
    dept_id_str = affiliation.get("department_id") or affiliation.get("departmentId")
    if dept_id_str:
        dept = await Department.find_one(
            Department.id == PydanticObjectId(dept_id_str),
            Department.organization_id == org_id,
            Department.is_deleted == False
        )
        if not dept:
            raise InvalidOrganization(f"Department with ID '{dept_id_str}' does not exist inside this organization.")

    # 2. Program
    prog_id_str = affiliation.get("program_id") or affiliation.get("programId")
    if prog_id_str:
        prog = await Program.find_one(
            Program.id == PydanticObjectId(prog_id_str),
            Program.organization_id == org_id,
            Program.is_deleted == False
        )
        if not prog:
            raise InvalidOrganization(f"Program with ID '{prog_id_str}' does not exist inside this organization.")

    # 3. Branch
    branch_id_str = affiliation.get("branch_id") or affiliation.get("branchId")
    if branch_id_str:
        branch = await Branch.find_one(
            Branch.id == PydanticObjectId(branch_id_str),
            Branch.organization_id == org_id,
            Branch.is_deleted == False
        )
        if not branch:
            raise InvalidOrganization(f"Branch with ID '{branch_id_str}' does not exist inside this organization.")

    # 4. Semester
    sem_id_str = affiliation.get("semester_id") or affiliation.get("semesterId")
    if sem_id_str:
        sem = await Semester.find_one(
            Semester.id == PydanticObjectId(sem_id_str),
            Semester.organization_id == org_id,
            Semester.is_deleted == False
        )
        if not sem:
            raise InvalidOrganization(f"Semester with ID '{sem_id_str}' does not exist inside this organization.")

    # 5. Section
    sec_id_str = affiliation.get("section_id") or affiliation.get("sectionId")
    if sec_id_str:
        sec = await Section.find_one(
            Section.id == PydanticObjectId(sec_id_str),
            Section.organization_id == org_id,
            Section.is_deleted == False
        )
        if not sec:
            raise InvalidOrganization(f"Section with ID '{sec_id_str}' does not exist inside this organization.")
