from typing import List, Optional, Tuple, Any
from beanie import PydanticObjectId
from bson import ObjectId

from app.models.org_engine.capability import Capability

class CapabilityRepository:
    """
    Production-grade repository engine for Capabilities.
    Encapsulates all database reads and writes with multi-tenant scoping.
    """

    async def create(self, capability: Capability, session=None) -> Capability:
        return await capability.insert(session=session)

    async def find_by_id(self, id_str: str, org_id: PydanticObjectId, session=None) -> Optional[Capability]:
        # Support search by MongoDB ObjectId or custom capabilityId string
        try:
            obj_id = PydanticObjectId(id_str)
            return await Capability.find_one(
                Capability.id == obj_id,
                Capability.organization_id == org_id,
                Capability.is_deleted == False,
                session=session
            )
        except Exception:
            return await Capability.find_one(
                Capability.capability_id == id_str,
                Capability.organization_id == org_id,
                Capability.is_deleted == False,
                session=session
            )

    async def find_by_slug(self, slug: str, org_id: PydanticObjectId, session=None) -> Optional[Capability]:
        return await Capability.find_one(
            Capability.slug == slug,
            Capability.organization_id == org_id,
            Capability.is_deleted == False,
            session=session
        )

    async def exists(self, org_id: PydanticObjectId, slug: str, session=None) -> bool:
        doc = await Capability.find_one(
            Capability.slug == slug,
            Capability.organization_id == org_id,
            Capability.is_deleted == False,
            session=session
        )
        return doc is not None

    async def list(
        self,
        org_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session=None
    ) -> List[Capability]:
        query = {
            "organizationId": org_id,
            "isDeleted": False
        }
        if filters:
            for k, v in filters.items():
                if v is not None:
                    # Map filter keys to MongoDB schema names if needed
                    # Python fields to DB aliases translation
                    db_key = k
                    if k == "category":
                        db_key = "category"
                    elif k == "status":
                        db_key = "status"
                    elif k == "enabled":
                        db_key = "enabled"
                    elif k == "installed":
                        db_key = "installed"
                    elif k == "licenseTier":
                        db_key = "licenseTier"
                    query[db_key] = v

        # Determine sorting field and order
        direction = "-" if sort_order == "desc" else ""
        # Map sort_by Python attributes to DB aliases
        db_sort = sort_by
        if sort_by == "createdAt":
            db_sort = "createdAt"
        elif sort_by == "name":
            db_sort = "name"
        elif sort_by == "slug":
            db_sort = "slug"

        return await Capability.find(
            query,
            session=session
        ).sort(f"{direction}{db_sort}").skip(skip).limit(limit).to_list()

    async def count(self, org_id: PydanticObjectId, filters: Optional[dict] = None, session=None) -> int:
        query = {
            "organizationId": org_id,
            "isDeleted": False
        }
        if filters:
            for k, v in filters.items():
                if v is not None:
                    db_key = k
                    if k == "category":
                        db_key = "category"
                    elif k == "status":
                        db_key = "status"
                    elif k == "enabled":
                        db_key = "enabled"
                    elif k == "installed":
                        db_key = "installed"
                    elif k == "licenseTier":
                        db_key = "licenseTier"
                    query[db_key] = v
        return await Capability.find(query, session=session).count()

    async def update(self, capability: Capability, update_data: dict, session=None) -> Capability:
        import re
        for k, v in update_data.items():
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            if hasattr(capability, snake_k):
                setattr(capability, snake_k, v)
            elif hasattr(capability, k):
                setattr(capability, k, v)
        return await capability.save(session=session)

    async def delete(self, capability: Capability, session=None) -> None:
        await capability.soft_delete(session=session)
