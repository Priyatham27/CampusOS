import json
import logging
from typing import Optional, Any
from bson import ObjectId
from beanie import PydanticObjectId
from datetime import datetime

from app.core.database import get_redis

logger = logging.getLogger("campusos.cache")

class CustomEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle BSON ObjectIds, PydanticObjectIds, and datetime serialization."""
    def default(self, o: Any) -> Any:
        if isinstance(o, (PydanticObjectId, ObjectId)):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

class CacheService:
    """
    Handles caching for active sessions and refresh tokens using Redis.
    Provides fallback to MongoDB Atlas by capturing errors and returning None.
    """
    def __init__(self):
        self.redis = get_redis()

    def _get(self, key: str) -> Optional[str]:
        try:
            return self.redis.get(key)
        except Exception as e:
            logger.warning(f"Cache GET failed for '{key}': {e}. Falling back.")
            return None

    def _set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> None:
        try:
            self.redis.set(key, value, ex=ttl_seconds)
        except Exception as e:
            logger.warning(f"Cache SET failed for '{key}': {e}.")

    def _delete(self, key: str) -> None:
        try:
            self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Cache DELETE failed for '{key}': {e}.")

    def get_session(self, session_id: str) -> Optional[dict]:
        raw = self._get(f"session:{session_id}")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_session(self, session_id: str, data: dict, ttl_seconds: int) -> None:
        self._set(f"session:{session_id}", json.dumps(data, cls=CustomEncoder), ttl_seconds)

    def delete_session(self, session_id: str) -> None:
        self._delete(f"session:{session_id}")

    def get_refresh_token(self, token_hash: str) -> Optional[dict]:
        raw = self._get(f"refresh:{token_hash}")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_refresh_token(self, token_hash: str, data: dict, ttl_seconds: int) -> None:
        self._set(f"refresh:{token_hash}", json.dumps(data, cls=CustomEncoder), ttl_seconds)

    def delete_refresh_token(self, token_hash: str) -> None:
        self._delete(f"refresh:{token_hash}")

    def get_user_roles(self, user_id: str) -> Optional[List[str]]:
        raw = self._get(f"user:{user_id}:roles")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_user_roles(self, user_id: str, roles: List[str], ttl_seconds: int = 3600) -> None:
        self._set(f"user:{user_id}:roles", json.dumps(roles, cls=CustomEncoder), ttl_seconds)

    def delete_user_roles(self, user_id: str) -> None:
        self._delete(f"user:{user_id}:roles")

    def get_user_permissions(self, user_id: str) -> Optional[List[str]]:
        raw = self._get(f"user:{user_id}:permissions")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_user_permissions(self, user_id: str, permissions: List[str], ttl_seconds: int = 3600) -> None:
        self._set(f"user:{user_id}:permissions", json.dumps(permissions, cls=CustomEncoder), ttl_seconds)

    def delete_user_permissions(self, user_id: str) -> None:
        self._delete(f"user:{user_id}:permissions")

    def get_org_policies(self, org_id: str) -> Optional[List[dict]]:
        raw = self._get(f"org:{org_id}:policies")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return None

    def set_org_policies(self, org_id: str, policies: List[dict], ttl_seconds: int = 3600) -> None:
        self._set(f"org:{org_id}:policies", json.dumps(policies, cls=CustomEncoder), ttl_seconds)

    def delete_org_policies(self, org_id: str) -> None:
        self._delete(f"org:{org_id}:policies")


