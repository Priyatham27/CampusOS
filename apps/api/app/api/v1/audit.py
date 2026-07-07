from fastapi import APIRouter, Depends, HTTPException, status, Query
import motor.motor_asyncio
from typing import List, Optional

from apps.api.app.core.database import get_db
from apps.api.app.middleware.auth import requires_permission
from apps.api.app.models.models import User
from apps.api.app.schemas.schemas import APIResponse, AuditLogResponse

router = APIRouter()

@router.get("", response_model=APIResponse[List[AuditLogResponse]])
async def list_audit_logs(
    limit: int = 100,
    category: Optional[str] = Query(None, description="Filter logs by category: activity, security, error, audit, api, performance"),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("audit:read"))
):
    """Retrieve compliance audit trail logs for the active tenant. Supports category filtering."""
    query = {"tenant_id": current_user.tenant_id}
    if category:
        query["category"] = category
        
    cursor = db["audit_logs"].find(query).sort("created_at", -1).limit(limit)
    logs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        logs.append(AuditLogResponse(**doc))
        
    return {
        "success": True,
        "message": f"Retrieved {len(logs)} compliance audit logs.",
        "data": logs,
        "meta": {"count": len(logs), "limit": limit, "category": category},
        "errors": []
    }
