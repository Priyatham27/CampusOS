import csv
import io
import re
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from beanie import PydanticObjectId

from apps.api.app.core.database import get_db
from apps.api.app.core.logger import logger
from apps.api.app.core.user_exceptions import BulkImportFailed, InvalidOrganization
from apps.api.app.repositories.user import UserRepository
from apps.api.app.repositories.profile import ProfileRepository
from apps.api.app.repositories.organization import OrganizationRepository
from apps.api.app.models.identity.user import User, Profile, UserStatus, AccountType, StudentProfile, FacultyProfile, AdminProfile, StudentStatus, FacultyStatus
from apps.api.app.models.identity.rbac import Role, UserRole
from apps.api.app.models.org_engine.academic import Department, Branch, Semester, Section
from apps.api.app.models.org_engine.curriculum import Program
from apps.api.app.validators.user import USERNAME_REGEX, PHONE_REGEX
from apps.api.app.services.user import UserService

class BulkImportService:
    """
    BulkImportService manages CSV batch parsing, validation preview reports,
    partial ingestion, and transaction rollback on fatal errors.
    """
    def __init__(self):
        self.user_service = UserService()
        self.org_repo = OrganizationRepository()

    async def import_users_csv(
        self,
        org_id_str: str,
        csv_content: str,
        preview: bool,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Validate and ingest users from CSV.
        Supports preview modes and partial validation reports.
        """
        org = await self.user_service._resolve_org(org_id_str)

        f = io.StringIO(csv_content.strip())
        reader = csv.DictReader(f)
        
        row_number = 1
        reports = []
        valid_rows_data = []

        # Track duplicates inside the CSV batch itself
        batch_emails = set()
        batch_usernames = set()

        for row in reader:
            row_number += 1
            row_errors = []
            
            username = (row.get("username") or "").strip().lower()
            email = (row.get("email") or "").strip().lower()
            first_name = (row.get("firstName") or row.get("first_name") or "").strip()
            last_name = (row.get("lastName") or row.get("last_name") or "").strip()
            account_type_str = (row.get("accountType") or row.get("account_type") or "STUDENT").strip().upper()
            role_slug = (row.get("roleSlug") or row.get("role_slug") or "").strip().lower()
            phone = (row.get("phone") or "").strip()

            # 1. Required fields validation
            if not username:
                row_errors.append("Username is required.")
            if not email:
                row_errors.append("Email is required.")
            if not first_name:
                row_errors.append("FirstName is required.")
            if not last_name:
                row_errors.append("LastName is required.")

            # 2. Format validation
            if username:
                if not USERNAME_REGEX.match(username):
                    row_errors.append("Username format is invalid.")
            if email:
                if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    row_errors.append("Email format is invalid.")
                elif org.email_domain and not (email.endswith(f"@{org.email_domain}") or email.endswith(f".{org.email_domain}")):
                    row_errors.append(f"Email domain suffix must match organization domain '{org.email_domain}'.")

            if phone:
                if not PHONE_REGEX.match(phone):
                    row_errors.append("Phone format is invalid.")

            # 3. Account Type validation
            account_type = None
            if account_type_str:
                try:
                    account_type = AccountType[account_type_str]
                except KeyError:
                    row_errors.append(f"Invalid accountType: '{account_type_str}'.")

            # 4. Duplicate checks (Batch & DB)
            if username:
                if username in batch_usernames:
                    row_errors.append(f"Duplicate username '{username}' in CSV batch.")
                else:
                    batch_usernames.add(username)
                    existing = await User.find_one(User.username == username, User.organization_id == org.id, User.is_deleted == False)
                    if existing:
                        row_errors.append(f"Username '{username}' already exists in DB.")

            if email:
                if email in batch_emails:
                    row_errors.append(f"Duplicate email '{email}' in CSV batch.")
                else:
                    batch_emails.add(email)
                    existing = await User.find_one(User.email == email, User.is_deleted == False)
                    if existing:
                        row_errors.append(f"Email '{email}' already registered in DB.")

            # 5. Role validation
            role_id = None
            if role_slug:
                role = await Role.find_one(Role.slug == role_slug, Role.organization_id == org.id, Role.is_deleted == False)
                if not role:
                    row_errors.append(f"Role slug '{role_slug}' does not exist inside organization.")
                else:
                    role_id = str(role.id)

            # 6. Academic Affiliation mapping (if student)
            academic_affiliation = {}
            if account_type == AccountType.STUDENT and not row_errors:
                roll_number = row.get("rollNumber") or row.get("roll_number")
                dept_code = row.get("departmentCode") or row.get("department_code")
                prog_name = row.get("programName") or row.get("program_name")
                branch_code = row.get("branchCode") or row.get("branch_code")
                sem_num_str = row.get("semesterNumber") or row.get("semester_number")
                sec_name = row.get("sectionName") or row.get("section_name")
                batch = row.get("batch")
                adm_year_str = row.get("admissionYear") or row.get("admission_year")
                grad_year_str = row.get("graduationYear") or row.get("graduation_year")

                # Map codes to MongoDB ObjectIds
                if dept_code:
                    dept = await Department.find_one(Department.code == dept_code.upper(), Department.organization_id == org.id, Department.is_deleted == False)
                    if dept:
                        academic_affiliation["departmentId"] = str(dept.id)
                    else:
                        row_errors.append(f"Department code '{dept_code}' not found.")
                else:
                    row_errors.append("Department code is required for students.")

                if prog_name and "departmentId" in academic_affiliation:
                    prog = await Program.find_one(Program.name == prog_name, Program.department_id == PydanticObjectId(academic_affiliation["departmentId"]), Program.is_deleted == False)
                    if prog:
                        academic_affiliation["programId"] = str(prog.id)
                    else:
                        row_errors.append(f"Program '{prog_name}' not found under department.")

                if branch_code and "departmentId" in academic_affiliation:
                    branch = await Branch.find_one(Branch.code == branch_code.upper(), Branch.department_id == PydanticObjectId(academic_affiliation["departmentId"]), Branch.is_deleted == False)
                    if branch:
                        academic_affiliation["branchId"] = str(branch.id)
                    else:
                        row_errors.append(f"Branch code '{branch_code}' not found.")

                if sem_num_str:
                    try:
                        sem_num = int(sem_num_str)
                        sem = await Semester.find_one(Semester.number == sem_num, Semester.organization_id == org.id, Semester.is_deleted == False)
                        if sem:
                            academic_affiliation["semesterId"] = str(sem.id)
                        else:
                            row_errors.append(f"Semester number {sem_num} not found.")
                    except ValueError:
                        row_errors.append(f"Invalid semester number '{sem_num_str}'.")

                if sec_name and "branchId" in academic_affiliation and "semesterId" in academic_affiliation:
                    sec = await Section.find_one(
                        Section.name == sec_name,
                        Section.branch_id == PydanticObjectId(academic_affiliation["branchId"]),
                        Section.semester_id == PydanticObjectId(academic_affiliation["semesterId"]),
                        Section.is_deleted == False
                    )
                    if sec:
                        academic_affiliation["sectionId"] = str(sec.id)
                    else:
                        row_errors.append(f"Section '{sec_name}' not found under branch and semester.")

                if roll_number:
                    academic_affiliation["rollNumber"] = roll_number
                if batch:
                    academic_affiliation["batch"] = batch
                if adm_year_str:
                    try:
                        academic_affiliation["admissionYear"] = int(adm_year_str)
                    except ValueError:
                        row_errors.append("admissionYear must be an integer.")
                if grad_year_str:
                    try:
                        academic_affiliation["graduationYear"] = int(grad_year_str)
                    except ValueError:
                        row_errors.append("graduationYear must be an integer.")

            # Record row status
            if row_errors:
                reports.append({
                    "rowNumber": row_number,
                    "username": username,
                    "email": email,
                    "status": "FAILED",
                    "errors": row_errors
                })
            else:
                reports.append({
                    "rowNumber": row_number,
                    "username": username,
                    "email": email,
                    "status": "VALID",
                    "errors": []
                })
                valid_rows_data.append({
                    "username": username,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "account_type": account_type,
                    "phone": phone or None,
                    "role_ids": [role_id] if role_id else [],
                    "academic_affiliation": academic_affiliation if academic_affiliation else None,
                    "password": "Password123!"  # Default initial password
                })

        success_count = 0
        failure_count = len(reports) - len(valid_rows_data)

        if not preview and valid_rows_data:
            # Perform ingestion inside transaction scope
            db = get_db()
            client = db.client
            
            async def _bulk_insert(session):
                nonlocal success_count
                for user_data in valid_rows_data:
                    await self.user_service.create_user(
                        org_id_str=org_id_str,
                        data=user_data,
                        current_user=current_user,
                        session=session
                    )
                    success_count += 1
                
                # Log audit trail
                await db["audit_logs"].insert_one({
                    "_id": f"aud_{PydanticObjectId()}",
                    "tenant_id": str(org.id),
                    "user_id": str(current_user.id),
                    "user_email": current_user.email,
                    "action": "users_bulk_import",
                    "category": "audit",
                    "details": {
                        "imported_count": success_count,
                        "failed_count": failure_count
                    },
                    "created_at": datetime.utcnow()
                }, session=session)

            try:
                await self.user_service._run_transactional(_bulk_insert)
            except Exception as e:
                logger.error(f"Bulk import ingestion transaction crashed: {e}")
                raise BulkImportFailed(f"Bulk import insertion crashed. Ingestion rolled back: {str(e)}")
        else:
            # Preview mode doesn't execute ingestion
            success_count = len(valid_rows_data)

        return {
            "totalProcessed": len(reports),
            "successCount": success_count,
            "failureCount": failure_count,
            "rows": reports
        }
