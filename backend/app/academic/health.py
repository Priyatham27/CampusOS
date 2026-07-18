from typing import Any, Dict
from beanie import PydanticObjectId

from app.core.database import get_db, get_redis
from app.models.calendar import AcademicCalendar
from app.models.org_engine.academic import AcademicYear
from app.models.org_engine.curriculum import Program

class AcademicHealthService:
    """
    Monitors health across MongoDB collections, Beanie ODM model indices, 
    Redis state, active calendar context configurations, and runtime requirements.
    """
    async def check_health(self, org_id: PydanticObjectId) -> Dict[str, Any]:
        status = {
            "status": "healthy",
            "components": {
                "database": {"status": "healthy"},
                "redis_cache": {"status": "healthy"},
                "calendar_engine": {"status": "healthy"},
                "catalog_engine": {"status": "healthy"}
            }
        }

        # 1. MongoDB Check
        try:
            db = get_db()
            ping_res = await db.command("ping")
            if not ping_res:
                status["components"]["database"] = {"status": "unhealthy", "error": "Database ping returned empty"}
                status["status"] = "degraded"
        except Exception as e:
            status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
            status["status"] = "unhealthy"

        # 2. Redis Check
        try:
            r = get_redis()
            if r and r.ping():
                status["components"]["redis_cache"] = {
                    "status": "connected",
                    "backend": "in_memory" if hasattr(r, "_store") else "redis_server"
                }
            else:
                status["components"]["redis_cache"] = {"status": "disconnected", "error": "Ping failed"}
                status["status"] = "degraded"
        except Exception as e:
            status["components"]["redis_cache"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

        # 3. Calendar Check
        try:
            active_cal = await AcademicCalendar.find_one(
                AcademicCalendar.organization_id == org_id,
                AcademicCalendar.is_active == True,
                AcademicCalendar.is_deleted == False
            )
            if active_cal:
                status["components"]["calendar_engine"] = {
                    "status": "active",
                    "calendarId": active_cal.calendar_id,
                    "name": active_cal.name
                }
            else:
                status["components"]["calendar_engine"] = {
                    "status": "inactive",
                    "details": "No active calendar configured for this organization context."
                }
                status["status"] = "degraded"
        except Exception as e:
            status["components"]["calendar_engine"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

        # 4. Catalog Check (Academic structure check)
        try:
            years_count = await AcademicYear.find(
                AcademicYear.organization_id == org_id,
                AcademicYear.is_deleted == False
            ).count()
            programs_count = await Program.find(
                Program.organization_id == org_id,
                Program.is_deleted == False
            ).count()
            
            status["components"]["catalog_engine"] = {
                "status": "ready" if years_count > 0 else "unseeded",
                "registeredYears": years_count,
                "registeredPrograms": programs_count
            }
        except Exception as e:
            status["components"]["catalog_engine"] = {"status": "error", "error": str(e)}
            status["status"] = "degraded"

        return status
