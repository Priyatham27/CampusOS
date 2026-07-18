import functools
import logging
from datetime import datetime
from typing import Any, Callable

from app.core.database import get_db

logger = logging.getLogger("campusos.academic.audit")

def audit_academic_action(action_name: str):
    """
    Decorator to audit academic write operations automatically in the request thread context.
    """
    def decorator(func: Callable[..., Any]):
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            res = await func(*args, **kwargs)
            try:
                db = get_db()
                org_id = None
                user_id = "system"

                # Try resolving current identity context
                try:
                    from app.core.identity_context import get_current_identity
                    from fastapi import Request
                    identity = await get_current_identity()
                    if identity:
                        if identity.organization:
                            org_id = identity.organization.id
                        if identity.user:
                            user_id = identity.user.user_id
                except Exception:
                    pass

                # Fallback to output properties
                if not org_id and res and hasattr(res, "organization_id"):
                    org_id = res.organization_id

                details = {
                    "method": func.__name__,
                    "details": {}
                }
                
                # Capture primary entity ID
                for field in ["id", "academic_year_id", "semester_id", "department_id", "program_id", "branch_id", "section_id", "course_id", "calendar_id", "timeline_id", "window_id", "event_id"]:
                    if res and hasattr(res, field):
                        details["details"][field] = str(getattr(res, field))

                await db["audit_logs"].insert_one({
                    "organizationId": org_id,
                    "action": action_name,
                    "timestamp": datetime.utcnow(),
                    "performedBy": user_id,
                    "module": "academic",
                    "details": details
                })
            except Exception as e:
                logger.error(f"Audit log insertion failed: {e}")
            return res
        return wrapper
    return decorator
