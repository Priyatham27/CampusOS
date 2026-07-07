from typing import List, Optional, Dict
from datetime import datetime
import re
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession

from apps.api.app.models.org_engine.organization import Organization

class OrganizationRepository:
    """
    Repository handling all database operations for the Organization document collection.
    Enforces soft-delete checking (isDeleted = False) across all fetches.
    """

    async def create(self, org: Organization, session: Optional[ClientSession] = None) -> Organization:
        """Insert a new Organization document."""
        return await org.insert(session=session)

    async def update(
        self,
        org: Organization,
        update_fields: dict,
        session: Optional[ClientSession] = None
    ) -> Organization:
        """Apply partial modifications to an existing Organization."""
        # Clean update fields to avoid modifying read-only parameters
        for key in ["_id", "id", "organization_id", "slug", "created_at"]:
            update_fields.pop(key, None)

        update_query = {"$set": update_fields}
        await Organization.find_one(Organization.id == org.id).update(update_query, session=session)
        
        # Synchronize in-memory model attributes with update fields
        for k, v in update_fields.items():
            prop_name = k
            if k == "organizationId":
                prop_name = "organization_id"
            elif k == "universityId":
                prop_name = "university_id"
            elif k == "shortName":
                prop_name = "short_name"
            elif k == "darkLogo":
                prop_name = "dark_logo"
            elif k == "emailDomain":
                prop_name = "email_domain"
            elif k == "contactEmail":
                prop_name = "contact_email"
            elif k == "postalCode":
                prop_name = "postal_code"
            elif k == "searchKeywords":
                prop_name = "search_keywords"
            elif k == "normalizedName":
                prop_name = "normalized_name"
            setattr(org, prop_name, v)
            
        return org

    async def delete(self, org: Organization, session: Optional[ClientSession] = None) -> bool:
        """Soft delete the organization document using the unique organizationId key."""
        now = datetime.utcnow()
        update_data = {
            "isDeleted": True,
            "deletedAt": now,
            "revisionNumber": (org.revision_number or 0) + 1,
            "updatedAt": now,
            "changeReason": "API CRUD Delete action request"
        }
        # Use organizationId (unique business key) for a guaranteed match — avoids
        # relying on self.id which Beanie 2.x may not populate after find_one.
        collection = Organization.get_pymongo_collection()
        await collection.update_one(
            {"organizationId": org.organization_id},
            {"$set": update_data},
            session=session
        )
        org.is_deleted = True
        org.deleted_at = now
        return True

    async def find_by_id(self, org_id: str, session: Optional[ClientSession] = None) -> Optional[Organization]:
        """Find an active organization by its custom string organization_id."""
        return await Organization.find_one(
            Organization.organization_id == org_id,
            Organization.is_deleted == False,
            session=session
        )

    async def find_by_slug(self, slug: str, session: Optional[ClientSession] = None) -> Optional[Organization]:
        """Find an active organization by its unique slug."""
        return await Organization.find_one(
            Organization.slug == slug,
            Organization.is_deleted == False,
            session=session
        )

    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session: Optional[ClientSession] = None
    ) -> List[Organization]:
        """List active organizations with pagination, sorting, and filtering."""
        sort_field_map = {
            "createdAt": "created_at",
            "updatedAt": "updated_at",
            "name": "name",
            "slug": "slug",
            "organizationId": "organization_id",
        }
        internal_sort_by = sort_field_map.get(sort_by, "created_at")
        sort_direction = -1 if sort_order.lower() == "desc" else 1

        # Build query expressions using Beanie DSL (not raw dicts) for reliable alias handling
        query_expressions = [Organization.is_deleted == False]
        if filters:
            if "status" in filters and filters["status"]:
                query_expressions.append(Organization.status == filters["status"])
            if "university_id" in filters and filters["university_id"]:
                query_expressions.append(
                    Organization.university_id == PydanticObjectId(filters["university_id"])
                )

        cursor = Organization.find(*query_expressions, session=session).sort(
            [(internal_sort_by, sort_direction)]
        ).skip(skip).limit(limit)

        return await cursor.to_list()

    async def search(
        self,
        query_str: str,
        skip: int = 0,
        limit: int = 10,
        session: Optional[ClientSession] = None
    ) -> List[Organization]:
        """Search active organizations using name and keyword regex mappings."""
        # Use raw dict for $or text search but combine with Beanie expression for isDeleted
        search_filter = {
            "$and": [
                {"isDeleted": False},
                {"$or": [
                    {"name": {"$regex": query_str, "$options": "i"}},
                    {"slug": {"$regex": query_str, "$options": "i"}},
                    {"searchKeywords": {"$regex": query_str, "$options": "i"}},
                ]}
            ]
        }
        cursor = Organization.find(search_filter, session=session).skip(skip).limit(limit)
        return await cursor.to_list()

    async def exists(
        self,
        org_id: Optional[str] = None,
        slug: Optional[str] = None,
        email_domain: Optional[str] = None,
        name: Optional[str] = None,
        session: Optional[ClientSession] = None
    ) -> Dict[str, str]:
        """Verify field duplicate conflicts across active organizations."""
        conflicts = {}
        if org_id:
            dup_id = await Organization.find_one(
                Organization.organization_id == org_id,
                Organization.is_deleted == False,
                session=session
            )
            if dup_id:
                conflicts["organizationId"] = f"Organization ID '{org_id}' is already registered."
        if slug:
            dup_slug = await Organization.find_one(
                Organization.slug == slug,
                Organization.is_deleted == False,
                session=session
            )
            if dup_slug:
                conflicts["slug"] = f"Slug '{slug}' is already in use."
        if email_domain:
            dup_domain = await Organization.find_one(
                Organization.email_domain == email_domain,
                Organization.is_deleted == False,
                session=session
            )
            if dup_domain:
                conflicts["emailDomain"] = f"Email domain '{email_domain}' is already registered."
        if name:
            dup_name = await Organization.find_one(
                Organization.name == name,
                Organization.is_deleted == False,
                session=session
            )
            if dup_name:
                conflicts["name"] = f"Organization name '{name}' is already in use."
        return conflicts

    async def count(self, filters: Optional[dict] = None, session: Optional[ClientSession] = None) -> int:
        """Count active organizations matching optional filter settings."""
        query_expressions = [Organization.is_deleted == False]
        if filters:
            if "status" in filters and filters["status"]:
                query_expressions.append(Organization.status == filters["status"])
            if "university_id" in filters and filters["university_id"]:
                query_expressions.append(
                    Organization.university_id == PydanticObjectId(filters["university_id"])
                )
        return await Organization.find(*query_expressions, session=session).count()
