from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId
import re

from app.models.identity.user import User, Profile, StudentProfile, FacultyProfile, AdminProfile
from app.models.identity.rbac import UserRole, Role

class UserSearchService:
    """
    UserSearchService implements multi-field searches and filters across users,
    profiles, roles, and academic affiliations.
    """

    async def search_users(
        self,
        org_id: PydanticObjectId,
        query_str: Optional[str] = None,
        filters: Optional[dict] = None,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[User], int]:
        """
        Execute search and filter queries.
        Returns a tuple of (users, total_count).
        """
        query_exprs = [User.organization_id == org_id, User.is_deleted == False]
        filters = filters or {}

        # 1. Apply Status / Account Type Filters
        if "status" in filters and filters["status"]:
            query_exprs.append(User.status == filters["status"])
        if "accountType" in filters and filters["accountType"]:
            query_exprs.append(User.account_type == filters["accountType"])

        # 2. Filter by Role
        role_filter_ids = []
        if "roleId" in filters and filters["roleId"]:
            role_filter_ids.append(PydanticObjectId(filters["roleId"]))
        elif "roleSlug" in filters and filters["roleSlug"]:
            roles = await Role.find(Role.organization_id == org_id, Role.slug == filters["roleSlug"], Role.is_deleted == False).to_list()
            role_filter_ids.extend([r.id for r in roles])

        if role_filter_ids:
            user_roles = await UserRole.find({"roleId": {"$in": role_filter_ids}}).to_list()
            user_ids = list(set([ur.user_id for ur in user_roles]))
            query_exprs.append({"_id": {"$in": user_ids}})

        # 3. Filter by Academic Affiliations (department, program, branch, semester, section, academicYear)
        academic_user_ids = None
        has_academic_filter = False

        dept_id = filters.get("departmentId")
        prog_id = filters.get("programId")
        branch_id = filters.get("branchId")
        sem_id = filters.get("semesterId")
        sec_id = filters.get("sectionId")
        batch = filters.get("batch")

        # Academic filter sub-query
        if dept_id or prog_id or branch_id or sem_id or sec_id or batch:
            has_academic_filter = True
            std_query = {"organizationId": org_id, "isDeleted": False}
            if dept_id:
                std_query["departmentId"] = PydanticObjectId(dept_id)
            if prog_id:
                std_query["programId"] = PydanticObjectId(prog_id)
            if branch_id:
                std_query["branchId"] = PydanticObjectId(branch_id)
            if sem_id:
                std_query["semesterId"] = PydanticObjectId(sem_id)
            if sec_id:
                std_query["sectionId"] = PydanticObjectId(sec_id)
            if batch:
                std_query["batch"] = batch

            student_profiles = await StudentProfile.find(std_query).to_list()
            student_user_ids = [sp.user_id for sp in student_profiles]
            
            # Faculty affiliation search
            fac_query = {"organizationId": org_id, "isDeleted": False}
            if dept_id:
                fac_query["departmentId"] = PydanticObjectId(dept_id)
            faculty_profiles = await FacultyProfile.find(fac_query).to_list()
            faculty_user_ids = [fp.user_id for fp in faculty_profiles]

            academic_user_ids = list(set(student_user_ids + faculty_user_ids))

        if has_academic_filter:
            if academic_user_ids is not None:
                query_exprs.append({"_id": {"$in": academic_user_ids}})
            else:
                query_exprs.append({"_id": {"$in": []}})

        # 4. Global Text Query (query_str) matches username, email, first_name, last_name, preferred_name
        if query_str and query_str.strip():
            regex = re.compile(query_str, re.IGNORECASE)
            
            # Find matching Profiles
            profile_query = {
                "$and": [
                    {"isDeleted": False},
                    {"$or": [
                        {"firstName": {"$regex": regex}},
                        {"lastName": {"$regex": regex}},
                        {"middleName": {"$regex": regex}},
                        {"preferredName": {"$regex": regex}},
                        {"phone": {"$regex": regex}}
                    ]}
                ]
            }
            matching_profiles = await Profile.find(profile_query).to_list()
            profile_user_ids = [mp.user_id for mp in matching_profiles]

            text_or_conditions = [
                {"username": {"$regex": regex}},
                {"email": {"$regex": regex}}
            ]
            if profile_user_ids:
                text_or_conditions.append({"_id": {"$in": profile_user_ids}})
            
            query_exprs.append({"$or": text_or_conditions})

        # 5. Build Sorting
        sort_map = {
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            "username": "username",
            "email": "email",
            "userId": "user_id"
        }
        sort_field = sort_map.get(sort_by, "created_at")
        direction = -1 if sort_order.lower() == "desc" else 1

        # 6. Execute count & list queries
        total = await User.find(*query_exprs).count()
        users = await User.find(*query_exprs).sort([(sort_field, direction)]).skip(skip).limit(limit).to_list()

        return users, total
