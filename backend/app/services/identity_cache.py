import json
import logging
from typing import Optional, Dict, Any
from app.core.database import get_redis

logger = logging.getLogger("campusos.services.identity_cache")

class IdentityCacheService:
    """
    Manages caching and cache invalidation of resolved identity details
    (e.g. roles, permissions, capabilities) to avoid redundant DB queries.
    """
    def _get_key(self, org_id_str: str, user_id_str: str) -> str:
        return f"identity_cache:{org_id_str}:{user_id_str}"

    async def get_cached_identity(self, org_id_str: str, user_id_str: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached roles, permissions, and capabilities from Redis or local cache."""
        redis = get_redis()
        if not redis:
            return None
        
        key = self._get_key(org_id_str, user_id_str)
        try:
            val = redis.get(key)
            if val:
                logger.debug(f"Identity cache hit: {key}")
                # Support bytes or string decoding
                if isinstance(val, bytes):
                    val = val.decode("utf-8")
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Failed to read from identity cache: {e}")
        return None

    async def set_cached_identity(
        self,
        org_id_str: str,
        user_id_str: str,
        identity_data: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> None:
        """Write resolved roles, permissions, and capabilities to cache."""
        redis = get_redis()
        if not redis:
            return
        
        key = self._get_key(org_id_str, user_id_str)
        try:
            redis.set(key, json.dumps(identity_data), ex=ttl_seconds)
            logger.debug(f"Identity cache updated: {key} (TTL: {ttl_seconds}s)")
        except Exception as e:
            logger.warning(f"Failed to write to identity cache: {e}")

    async def invalidate_cached_identity(self, org_id_str: str, user_id_str: str) -> None:
        """Evict the cached identity context when user details or mapping updates."""
        redis = get_redis()
        if not redis:
            return
        
        key = self._get_key(org_id_str, user_id_str)
        try:
            redis.delete(key)
            logger.info(f"Identity cache evicted: {key}")
        except Exception as e:
            logger.warning(f"Failed to evict identity cache for key {key}: {e}")

def get_identity_cache_service() -> IdentityCacheService:
    return IdentityCacheService()
