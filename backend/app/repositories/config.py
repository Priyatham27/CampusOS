from typing import List, Optional, Tuple, Any
from beanie import PydanticObjectId
from bson import ObjectId
import re

from app.models.org_engine.config import Configuration, FeatureFlag, ConfigScope, ConfigEnvironment

class ConfigurationRepository:
    """
    Handles MongoDB database persistence and query logic for Configurations.
    """
    async def create(self, config: Configuration, session=None) -> Configuration:
        return await config.insert(session=session)

    async def find_by_id(self, id_str: str, org_id: Optional[PydanticObjectId] = None, session=None) -> Optional[Configuration]:
        try:
            obj_id = PydanticObjectId(id_str)
            query = {"_id": obj_id, "isDeleted": False}
        except Exception:
            query = {"configId": id_str, "isDeleted": False}

        if org_id:
            query["$or"] = [{"organizationId": org_id}, {"organizationId": None}]

        return await Configuration.find_one(query, session=session)

    async def find_by_key_and_context(
        self,
        key: str,
        org_id: Optional[PydanticObjectId],
        environment: ConfigEnvironment,
        scope: ConfigScope,
        module: Optional[str] = None,
        session=None
    ) -> Optional[Configuration]:
        query = {
            "key": key,
            "environment": environment,
            "scope": scope,
            "isDeleted": False
        }
        if org_id is not None:
            query["organizationId"] = org_id
        else:
            query["organizationId"] = None

        if module is not None:
            query["module"] = module
        else:
            query["module"] = None

        return await Configuration.find_one(query, session=session)

    async def find_hierarchy_matches(
        self,
        key: str,
        org_id: Optional[PydanticObjectId],
        environment: ConfigEnvironment,
        module: Optional[str] = None,
        session=None
    ) -> List[Configuration]:
        """
        Retrieves all active configurations matching the key for hierarchy resolution:
        - GLOBAL/SYSTEM (no org id)
        - ORGANIZATION (matching org id)
        - MODULE (matching org id + matching module)
        - USER (matching org id + matching module, resolved dynamically)
        """
        # Build query matching any matching scopes
        clauses = [
            # Global/System scope
            {"organizationId": None, "scope": {"$in": ["GLOBAL", "SYSTEM"]}}
        ]
        if org_id:
            # Org scope
            clauses.append({"organizationId": org_id, "scope": "ORGANIZATION"})
            # Module scope
            if module:
                clauses.append({"organizationId": org_id, "scope": "MODULE", "module": module})
            # User scope (we retrieve all, filter in service if user context matches)
            clauses.append({"organizationId": org_id, "scope": "USER"})

        query = {
            "key": key,
            "environment": environment,
            "isDeleted": False,
            "$or": clauses
        }
        return await Configuration.find(query, session=session).to_list()

    async def list(
        self,
        org_id: Optional[PydanticObjectId],
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session=None
    ) -> List[Configuration]:
        query = {"isDeleted": False}
        if org_id is not None:
            query["$or"] = [
                {"organizationId": org_id},
                {"organizationId": None}
            ]
        else:
            query["organizationId"] = None

        if filters:
            for k, v in filters.items():
                if v is not None:
                    db_key = k
                    if k == "scope":
                        db_key = "scope"
                    elif k == "environment":
                        db_key = "environment"
                    elif k == "module":
                        db_key = "module"
                    elif k == "key":
                        db_key = "key"
                    query[db_key] = v

        direction = "-" if sort_order == "desc" else ""
        db_sort = sort_by
        if sort_by == "createdAt":
            db_sort = "createdAt"

        return await Configuration.find(query, session=session).sort(f"{direction}{db_sort}").skip(skip).limit(limit).to_list()

    async def count(self, org_id: Optional[PydanticObjectId], filters: Optional[dict] = None, session=None) -> int:
        query = {"isDeleted": False}
        if org_id is not None:
            query["$or"] = [
                {"organizationId": org_id},
                {"organizationId": None}
            ]
        else:
            query["organizationId"] = None

        if filters:
            for k, v in filters.items():
                if v is not None:
                    db_key = k
                    query[db_key] = v
        return await Configuration.find(query, session=session).count()

    async def update(self, config: Configuration, update_data: dict, session=None) -> Configuration:
        import re
        for k, v in update_data.items():
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            if hasattr(config, snake_k):
                setattr(config, snake_k, v)
            elif hasattr(config, k):
                setattr(config, k, v)
        return await config.save(session=session)

    async def delete(self, config: Configuration, session=None) -> None:
        await config.soft_delete(session=session)


class FeatureFlagRepository:
    """
    Handles MongoDB database persistence and query logic for Feature Flags.
    """
    async def create(self, flag: FeatureFlag, session=None) -> FeatureFlag:
        return await flag.insert(session=session)

    async def find_by_id(self, id_str: str, org_id: Optional[PydanticObjectId] = None, session=None) -> Optional[FeatureFlag]:
        try:
            obj_id = PydanticObjectId(id_str)
            query = {"_id": obj_id, "isDeleted": False}
        except Exception:
            query = {"flagId": id_str, "isDeleted": False}

        if org_id:
            query["$or"] = [{"organizationId": org_id}, {"organizationId": None}]

        return await FeatureFlag.find_one(query, session=session)

    async def find_by_key(self, key: str, org_id: Optional[PydanticObjectId], environment: ConfigEnvironment, session=None) -> Optional[FeatureFlag]:
        query = {
            "key": key,
            "environment": environment,
            "isDeleted": False
        }
        if org_id is not None:
            query["$or"] = [
                {"organizationId": org_id},
                {"organizationId": None}
            ]
        else:
            query["organizationId"] = None

        # Sort so that Organization-specific flag takes priority over System flag
        flags = await FeatureFlag.find(query, session=session).to_list()
        if not flags:
            return None
        # Find if there is an organization specific flag, otherwise return the system flag
        org_flag = next((f for f in flags if f.organization_id == org_id), None)
        if org_flag:
            return org_flag
        return flags[0]

    async def list(
        self,
        org_id: Optional[PydanticObjectId],
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None,
        session=None
    ) -> List[FeatureFlag]:
        query = {"isDeleted": False}
        if org_id is not None:
            query["$or"] = [
                {"organizationId": org_id},
                {"organizationId": None}
            ]
        else:
            query["organizationId"] = None

        if filters:
            for k, v in filters.items():
                if v is not None:
                    db_key = k
                    if k == "category":
                        db_key = "category"
                    elif k == "environment":
                        db_key = "environment"
                    elif k == "enabled":
                        db_key = "enabled"
                    elif k == "key":
                        db_key = "key"
                    query[db_key] = v

        direction = "-" if sort_order == "desc" else ""
        db_sort = sort_by
        if sort_by == "createdAt":
            db_sort = "createdAt"

        return await FeatureFlag.find(query, session=session).sort(f"{direction}{db_sort}").skip(skip).limit(limit).to_list()

    async def count(self, org_id: Optional[PydanticObjectId], filters: Optional[dict] = None, session=None) -> int:
        query = {"isDeleted": False}
        if org_id is not None:
            query["$or"] = [
                {"organizationId": org_id},
                {"organizationId": None}
            ]
        else:
            query["organizationId"] = None

        if filters:
            for k, v in filters.items():
                if v is not None:
                    db_key = k
                    query[db_key] = v
        return await FeatureFlag.find(query, session=session).count()

    async def update(self, flag: FeatureFlag, update_data: dict, session=None) -> FeatureFlag:
        import re
        for k, v in update_data.items():
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            if hasattr(flag, snake_k):
                setattr(flag, snake_k, v)
            elif hasattr(flag, k):
                setattr(flag, k, v)
        return await flag.save(session=session)

    async def delete(self, flag: FeatureFlag, session=None) -> None:
        await flag.soft_delete(session=session)
