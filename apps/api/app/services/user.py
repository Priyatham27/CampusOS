from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
from pymongo.errors import PyMongoError
from datetime import datetime
import logging

from apps.api.app.core.database import get_db
from apps.api.app.core.logger import logger
from apps.api.app.core.user_exceptions import (
    UserNotFound,
    DuplicateEmail,
    DuplicateUsername,
    InvalidOrganization,
    BulkImportFailed
)
from apps.api.app.repositories.user import UserRepository
from apps.api.app.repositories.profile import ProfileRepository
from apps.api.app.repositories.organization import OrganizationRepository
from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.models.identity.user import User, Profile, UserStatus, AccountType, StudentProfile, FacultyProfile, AdminProfile, StudentStatus, FacultyStatus
from apps.api.app.models.identity.rbac import Role, UserRole
from apps.api.app.validators.user import (
    validate_email_domain,
    validate_username_rules,
    validate_phone_format,
    validate_academic_references
)
from apps.api.app.validators.profile import validate_profile_completeness
from apps.api.app.services.credential import CredentialService

def generate_usr_id(prefix: str, count: int) -> str:
    return f"{prefix}_{count:06d}"

class UserService:
    """
    Service layer coordinates user management business logic, transactions,
    organization isolation enforcement, role mappings, and audit trail hooks.
    """
    def __init__(self):
        self.user_repo = UserRepository()
        self.profile_repo = ProfileRepository()
        self.org_repo = OrganizationRepository()
        self.credential_service = CredentialService()

    async def _resolve_org(self, org_id_str: str) -> Organization:
        """Resolve organization by MongoDB ObjectId, string organization_id, or slug."""
        org = None
        try:
            obj_id = PydanticObjectId(org_id_str)
            org = await Organization.find_one(Organization.id == obj_id)
        except Exception:
            pass
        if not org:
            org = await Organization.find_one(Organization.organization_id == org_id_str)
        if not org:
            org = await Organization.find_one(Organization.slug == org_id_str)
        if not org or getattr(org, "is_deleted", False):
            raise InvalidOrganization(f"Organization '{org_id_str}' not found.")
        return org

    async def _run_transactional(self, func, *args, **kwargs):
        db = get_db()
        client = db.client
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await func(session, *args, **kwargs)
        except (PyMongoError, Exception) as e:
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower():
                logger.warning("Transactions not supported. Falling back to non-transactional execution.")
                return await func(None, *args, **kwargs)
            else:
                logger.error(f"User Platform transaction failure: {e}")
                raise e

    async def create_user(
        self,
        org_id_str: str,
        data: dict,
        current_user: Optional[User] = None,
        session: Optional[Any] = None
    ) -> User:
        """Create a user with automatic profile generation, role assignments, and credentials in a transaction."""
        org = await self._resolve_org(org_id_str)
        if not org:
            raise InvalidOrganization(f"Organization '{org_id_str}' not found.")

        # Enforce email domain match if configured
        if org.email_domain:
            validate_email_domain(data["email"], org.email_domain)

        # Validate username rules
        validate_username_rules(data["username"])

        # Check unique constraint violations
        if await self.user_repo.find_by_username(data["username"], org.id):
            raise DuplicateUsername(f"Username '{data['username']}' is already in use in this organization.")

        if await self.user_repo.find_by_email(data["email"]):
            raise DuplicateEmail(f"Email '{data['email']}' is already registered.")

        # Verify role availability
        role_ids = data.get("role_ids") or []
        roles = []
        if role_ids:
            for rid in role_ids:
                role = await Role.find_one(Role.role_id == rid, Role.organization_id == org.id, Role.is_deleted == False)
                if not role:
                    role = await Role.find_one(Role.id == PydanticObjectId(rid), Role.organization_id == org.id, Role.is_deleted == False)
                if not role:
                    raise InvalidOrganization(f"Role '{rid}' does not exist inside this organization.")
                roles.append(role)
        else:
            # Fallback to default role
            default_role = await Role.find_one(Role.organization_id == org.id, Role.default_role == True, Role.is_deleted == False)
            if default_role:
                roles.append(default_role)

        # Validate academic references if sub-profile details exist
        academic = data.get("academic_affiliation")
        if academic:
            await validate_academic_references(org.id, academic)

        async def _save_transaction(session):
            count = await self.user_repo.count(org.id, session=session)
            user_id = generate_usr_id("USR", count + 1)
            profile_id_str = generate_usr_id("PRF", count + 1)

            # 1. Initialize User Document
            user = User(
                userId=user_id,
                organizationId=org.id,
                username=data["username"].lower(),
                email=data["email"].lower(),
                status=UserStatus.ACTIVE,
                accountType=data.get("account_type", AccountType.STUDENT),
                emailVerified=False,
                phoneVerified=False,
                mfaEnabled=False
            )
            created_user = await self.user_repo.create(user, session=session)

            # 2. Initialize Base Profile Document
            profile = Profile(
                profileId=profile_id_str,
                userId=created_user.id,
                firstName=data["first_name"],
                lastName=data["last_name"],
                phone=data.get("phone"),
                timezone=org.timezone or "UTC",
                language=org.language or "en"
            )
            created_profile = await self.profile_repo.create(profile, session=session)

            # 3. Associate Profile in User Document
            created_user.profile_id = created_profile.id
            await self.user_repo.update(created_user, {"profileId": created_profile.id}, session=session)

            # 4. Map Assigned Roles
            for role in roles:
                ur = UserRole(userId=created_user.id, roleId=role.id)
                await ur.insert(session=session)

            # 5. Populate Sub-Profiles (Academic Affiliation)
            if academic:
                if created_user.account_type == AccountType.STUDENT:
                    student_id_str = generate_usr_id("STD", count + 1)
                    std_prof = StudentProfile(
                        studentProfileId=student_id_str,
                        userId=created_user.id,
                        organizationId=org.id,
                        rollNumber=academic.get("roll_number") or academic.get("rollNumber"),
                        departmentId=PydanticObjectId(academic.get("department_id") or academic.get("departmentId")),
                        programId=PydanticObjectId(academic.get("program_id") or academic.get("programId")),
                        branchId=PydanticObjectId(academic.get("branch_id") or academic.get("branchId")),
                        semesterId=PydanticObjectId(academic.get("semester_id") or academic.get("semesterId")),
                        sectionId=PydanticObjectId(academic.get("section_id") or academic.get("sectionId")),
                        batch=academic.get("batch"),
                        admissionYear=academic.get("admission_year") or academic.get("admissionYear"),
                        graduationYear=academic.get("graduation_year") or academic.get("graduationYear"),
                        studentStatus=StudentStatus.ACTIVE
                    )
                    await std_prof.insert(session=session)
                elif created_user.account_type == AccountType.FACULTY:
                    faculty_id_str = generate_usr_id("FAC", count + 1)
                    fac_prof = FacultyProfile(
                        facultyProfileId=faculty_id_str,
                        userId=created_user.id,
                        organizationId=org.id,
                        employeeId=academic.get("employee_id") or academic.get("employeeId"),
                        designation=academic.get("designation"),
                        departmentId=PydanticObjectId(academic.get("department_id") or academic.get("departmentId")),
                        joiningDate=datetime.utcnow(),
                        qualification=academic.get("qualification", "N/A"),
                        status=FacultyStatus.ACTIVE
                    )
                    await fac_prof.insert(session=session)
                elif created_user.account_type in (AccountType.ADMIN, AccountType.SUPERADMIN):
                    admin_id_str = generate_usr_id("ADM", count + 1)
                    adm_prof = AdminProfile(
                        adminProfileId=admin_id_str,
                        userId=created_user.id,
                        organizationId=org.id,
                        designation=academic.get("designation", "Administrator"),
                        notes=academic.get("notes")
                    )
                    await adm_prof.insert(session=session)

            # 6. Save Credentials if password is provided
            if data.get("password"):
                from apps.api.app.models.identity.credential import Credential, CredentialType
                from apps.api.app.core.security import hash_password_argon2
                pw_hash = hash_password_argon2(data["password"])
                cred_count = await Credential.find({}).count()
                cred_id = f"CRD_{cred_count + 1:06d}"
                credential = Credential(
                    credentialId=cred_id,
                    userId=created_user.id,
                    organizationId=org.id,
                    type=CredentialType.PASSWORD,
                    passwordHash=pw_hash,
                    passwordHistory=[pw_hash],
                    passwordChangedAt=datetime.utcnow(),
                    requiresPasswordChange=False
                )
                await credential.insert(session=session)

            # 7. Audit Log Entry
            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": f"aud_{PydanticObjectId()}",
                "tenant_id": str(org.id),
                "user_id": str(current_user.id) if current_user else "SYSTEM",
                "user_email": current_user.email if current_user else "system@campusos.com",
                "action": "user_create",
                "category": "audit",
                "details": {
                    "created_user_id": str(created_user.id),
                    "user_id_str": created_user.user_id,
                    "email": created_user.email
                },
                "created_at": datetime.utcnow()
            }, session=session)

            return created_user

        if session:
            res = await _save_transaction(session)
        else:
            res = await self._run_transactional(_save_transaction)
        logger.info(f"User '{res.email}' successfully created with ID '{res.user_id}'.")
        return res

    async def get_user_details(self, org_id_str: str, user_id_str: str) -> User:
        """Fetch active user details, including profile mapping, scoped by organization."""
        org = await self._resolve_org(org_id_str)

        # Find user by string identifier (USR_xxxxxx) or MongoDB PydanticObjectId
        user = await self.user_repo.find_by_id(user_id_str, org.id)
        if not user:
            try:
                user = await self.user_repo.find_by_beanie_id(PydanticObjectId(user_id_str), org.id)
            except Exception:
                pass
        if not user:
            raise UserNotFound(f"User '{user_id_str}' not found.")
        return user

    async def update_user(self, org_id_str: str, user_id_str: str, update_data: dict, current_user: User) -> User:
        """Update core user account details and roles in a transactional context."""
        org = await self._resolve_org(org_id_str)

        user = await self.get_user_details(org_id_str, user_id_str)

        # Handle username update uniqueness
        if "username" in update_data and update_data["username"].lower() != user.username:
            validate_username_rules(update_data["username"])
            dup = await self.user_repo.find_by_username(update_data["username"], org.id)
            if dup:
                raise DuplicateUsername(f"Username '{update_data['username']}' is already in use.")
            update_data["username"] = update_data["username"].lower()

        # Handle email update uniqueness
        if "email" in update_data and update_data["email"].lower() != user.email:
            if org.email_domain:
                validate_email_domain(update_data["email"], org.email_domain)
            dup = await self.user_repo.find_by_email(update_data["email"])
            if dup:
                raise DuplicateEmail(f"Email '{update_data['email']}' is already registered.")
            update_data["email"] = update_data["email"].lower()

        # Handle roles mapping update
        role_ids = update_data.pop("role_ids", None)
        roles = []
        if role_ids is not None:
            for rid in role_ids:
                role = await Role.find_one(Role.role_id == rid, Role.organization_id == org.id, Role.is_deleted == False)
                if not role:
                    role = await Role.find_one(Role.id == PydanticObjectId(rid), Role.organization_id == org.id, Role.is_deleted == False)
                if not role:
                    raise InvalidOrganization(f"Role '{rid}' not found in this organization.")
                roles.append(role)

        async def _update_transaction(session):
            if update_data:
                await self.user_repo.update(user, update_data, session=session)

            if role_ids is not None:
                # Remove old user role assignments
                await UserRole.find(UserRole.user_id == user.id, session=session).delete(session=session)
                # Map new roles
                for r in roles:
                    ur = UserRole(userId=user.id, roleId=r.id)
                    await ur.insert(session=session)

            # Audit Log Entry
            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": f"aud_{PydanticObjectId()}",
                "tenant_id": str(org.id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "action": "user_update",
                "category": "audit",
                "details": {
                    "updated_user_id": str(user.id),
                    "user_id_str": user.user_id,
                    "fields_modified": list(update_data.keys()) + (["roles"] if role_ids is not None else [])
                },
                "created_at": datetime.utcnow()
            }, session=session)

            return user

        res = await self._run_transactional(_update_transaction)
        logger.info(f"User account '{res.email}' updated.")
        return res

    async def change_user_status(self, org_id_str: str, user_id_str: str, status: UserStatus, current_user: User, reason: Optional[str] = None) -> User:
        """Modify a user's lifecycle state (Active, Suspended, Inactive, Archived)."""
        org = await self._resolve_org(org_id_str)

        user = await self.get_user_details(org_id_str, user_id_str)
        user.status = status

        async def _save_status(session):
            await self.user_repo.update(user, {"status": status}, session=session)

            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": f"aud_{PydanticObjectId()}",
                "tenant_id": str(org.id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "action": f"user_{status.lower()}",
                "category": "audit",
                "details": {
                    "target_user_id": str(user.id),
                    "user_id_str": user.user_id,
                    "new_status": status,
                    "reason": reason
                },
                "created_at": datetime.utcnow()
            }, session=session)

            return user

        return await self._run_transactional(_save_status)

    async def soft_delete_user(self, org_id_str: str, user_id_str: str, current_user: User) -> bool:
        """Flag the user document as logically soft deleted."""
        org = await self._resolve_org(org_id_str)

        user = await self.get_user_details(org_id_str, user_id_str)

        async def _delete_transaction(session):
            await self.user_repo.delete(user, reason="API Soft Delete request", session=session)

            # Soft delete corresponding profile
            profile = await self.profile_repo.find_by_user_beanie_id(user.id, session=session)
            if profile:
                await profile.soft_delete(reason="Cascade soft delete from user log", session=session)

            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": f"aud_{PydanticObjectId()}",
                "tenant_id": str(org.id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "action": "user_delete",
                "category": "audit",
                "details": {
                    "deleted_user_id": str(user.id),
                    "user_id_str": user.user_id,
                    "email": user.email
                },
                "created_at": datetime.utcnow()
            }, session=session)
            return True

        await self._run_transactional(_delete_transaction)
        logger.info(f"User ID '{user_id_str}' has been soft-deleted.")
        return True

    async def restore_user(self, org_id_str: str, user_id_str: str, current_user: User) -> User:
        """Restore a soft-deleted user and their associated profile."""
        org = await self._resolve_org(org_id_str)

        # We query with is_deleted=True bypass directly from pymongo or using find_one(is_deleted=True)
        user = await User.find_one(
            User.user_id == user_id_str,
            User.organization_id == org.id,
            User.is_deleted == True
        )
        if not user:
            raise UserNotFound(f"Soft-deleted user '{user_id_str}' not found.")

        async def _restore_transaction(session):
            await self.user_repo.restore(user, reason="API Restore request", session=session)

            # Restore profile
            profile = await Profile.find_one(Profile.user_id == user.id, Profile.is_deleted == True, session=session)
            if profile:
                await profile.restore(reason="Cascade restore from user log", session=session)

            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": f"aud_{PydanticObjectId()}",
                "tenant_id": str(org.id),
                "user_id": str(current_user.id),
                "user_email": current_user.email,
                "action": "user_restore",
                "category": "audit",
                "details": {
                    "restored_user_id": str(user.id),
                    "user_id_str": user.user_id
                },
                "created_at": datetime.utcnow()
            }, session=session)
            return user

        return await self._run_transactional(_restore_transaction)

    async def bulk_status_change(
        self,
        org_id_str: str,
        user_ids: List[str],
        status: UserStatus,
        current_user: User,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Bulk status modification across selected users inside organization isolation boundary."""
        org = await self._resolve_org(org_id_str)

        async def _bulk_status(session):
            success_ids = []
            failed_ids = []
            
            for uid in user_ids:
                user = await self.user_repo.find_by_id(uid, org.id, session=session)
                if not user:
                    # Try Beanie ID fallback
                    try:
                        user = await self.user_repo.find_by_beanie_id(PydanticObjectId(uid), org.id, session=session)
                    except Exception:
                        pass
                
                if user:
                    user.status = status
                    await self.user_repo.update(user, {"status": status}, session=session)
                    success_ids.append(uid)
                    
                    db = get_db()
                    await db["audit_logs"].insert_one({
                        "_id": f"aud_{PydanticObjectId()}",
                        "tenant_id": str(org.id),
                        "user_id": str(current_user.id),
                        "user_email": current_user.email,
                        "action": f"user_{status.lower()}",
                        "category": "audit",
                        "details": {
                            "target_user_id": str(user.id),
                            "user_id_str": user.user_id,
                            "bulk": True,
                            "reason": reason
                        },
                        "created_at": datetime.utcnow()
                    }, session=session)
                else:
                    failed_ids.append(uid)
                    
            return {"success": success_ids, "failed": failed_ids}

        return await self._run_transactional(_bulk_status)

    async def bulk_role_assignment(
        self,
        org_id_str: str,
        user_ids: List[str],
        role_ids: List[str],
        action: str,
        current_user: User
    ) -> Dict[str, Any]:
        """Bulk role mappings (add, remove, replace) across organization user boundaries."""
        org = await self._resolve_org(org_id_str)

        # Resolve Roles
        roles = []
        for rid in role_ids:
            role = await Role.find_one(Role.role_id == rid, Role.organization_id == org.id, Role.is_deleted == False)
            if not role:
                role = await Role.find_one(Role.id == PydanticObjectId(rid), Role.organization_id == org.id, Role.is_deleted == False)
            if not role:
                raise InvalidOrganization(f"Role '{rid}' not found in this organization.")
            roles.append(role)

        async def _bulk_roles(session):
            success_ids = []
            failed_ids = []

            for uid in user_ids:
                user = await self.user_repo.find_by_id(uid, org.id, session=session)
                if not user:
                    try:
                        user = await self.user_repo.find_by_beanie_id(PydanticObjectId(uid), org.id, session=session)
                    except Exception:
                        pass

                if user:
                    if action == "add":
                        for role in roles:
                            exists = await UserRole.find_one(UserRole.user_id == user.id, UserRole.role_id == role.id, session=session)
                            if not exists:
                                ur = UserRole(userId=user.id, roleId=role.id, assignedBy=current_user.user_id)
                                await ur.insert(session=session)
                    elif action == "remove":
                        role_db_ids = [r.id for r in roles]
                        await UserRole.find(UserRole.user_id == user.id, {"roleId": {"$in": role_db_ids}}, session=session).delete(session=session)
                    elif action == "replace":
                        await UserRole.find(UserRole.user_id == user.id, session=session).delete(session=session)
                        for role in roles:
                            ur = UserRole(userId=user.id, roleId=role.id, assignedBy=current_user.user_id)
                            await ur.insert(session=session)

                    success_ids.append(uid)
                    
                    db = get_db()
                    await db["audit_logs"].insert_one({
                        "_id": f"aud_{PydanticObjectId()}",
                        "tenant_id": str(org.id),
                        "user_id": str(current_user.id),
                        "user_email": current_user.email,
                        "action": "user_role_update",
                        "category": "audit",
                        "details": {
                            "target_user_id": str(user.id),
                            "action": action,
                            "roles_list": role_ids
                        },
                        "created_at": datetime.utcnow()
                    }, session=session)
                else:
                    failed_ids.append(uid)

            return {"success": success_ids, "failed": failed_ids}

        return await self._run_transactional(_bulk_roles)
