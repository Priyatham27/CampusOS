import logging
from typing import Dict, Any
from apps.api.app.core.database import get_db, get_redis, db_manager
from apps.api.app.models.identity.session import Session
from apps.api.app.models.identity.rbac import Role
from apps.api.app.services.config import ConfigurationService

logger = logging.getLogger("campusos.services.health")

class IdentityHealthService:
    """
    Validates components of the Identity Platform, running diagnostics
    on database connectivity, cache stores, session integrity, configuration, and auth models.
    """
    async def get_health_status(self) -> Dict[str, Any]:
        status = {
            "status": "healthy",
            "components": {}
        }

        # 1. MongoDB Check
        try:
            db = get_db()
            await db.command("ping")
            status["components"]["mongodb"] = {"status": "connected", "details": "Ping successful"}
        except Exception as e:
            logger.error(f"Health Check: MongoDB connection failed: {e}")
            status["components"]["mongodb"] = {"status": "disconnected", "details": str(e)}
            status["status"] = "degraded"

        # 2. Redis Check
        try:
            redis = get_redis()
            if redis and redis.ping():
                # Check if it is a mock fallback or true Redis
                backend_type = "in_memory" if hasattr(redis, "_store") else "redis_server"
                status["components"]["cache"] = {"status": "connected", "backend": backend_type, "details": "Ping successful"}
            else:
                status["components"]["cache"] = {"status": "disconnected", "details": "Redis client instantiated but ping failed"}
                status["status"] = "degraded"
        except Exception as e:
            logger.warning(f"Health Check: Redis check failed: {e}")
            status["components"]["cache"] = {"status": "disconnected", "details": str(e)}
            status["status"] = "degraded"

        # 3. Session Store Check
        try:
            # Query session limit to check collection access
            await Session.find({}).limit(1).to_list()
            status["components"]["session_store"] = {"status": "healthy", "details": "Session collections queryable"}
        except Exception as e:
            logger.error(f"Health Check: Session store query failed: {e}")
            status["components"]["session_store"] = {"status": "unhealthy", "details": str(e)}
            status["status"] = "degraded"

        # 4. Authorization / RBAC Configurations Check
        try:
            role_count = await Role.find({}).count()
            status["components"]["authorization"] = {
                "status": "healthy" if role_count > 0 else "uninitialized",
                "details": f"Total registered roles: {role_count}"
            }
        except Exception as e:
            logger.error(f"Health Check: RBAC models query failed: {e}")
            status["components"]["authorization"] = {"status": "unhealthy", "details": str(e)}
            status["status"] = "degraded"

        # 5. Configuration Service Check
        try:
            config_svc = ConfigurationService()
            status["components"]["runtime_configuration"] = {
                "status": "healthy" if config_svc is not None else "unhealthy",
                "details": "Configuration engine active"
            }
        except Exception as e:
            status["components"]["runtime_configuration"] = {"status": "unhealthy", "details": str(e)}
            status["status"] = "degraded"

        return status

def get_identity_health_service() -> IdentityHealthService:
    return IdentityHealthService()
