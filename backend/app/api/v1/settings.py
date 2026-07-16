from fastapi import APIRouter, Depends, HTTPException, status, Body
import motor.motor_asyncio
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_db
from app.core.feature_flags import feature_flags
from app.core.logger import logger
from app.models.models import generate_prefixed_id, User, Tenant, SystemSettings
from app.middleware.auth import requires_permission
from app.schemas.schemas import APIResponse, SystemSettingsResponse

router = APIRouter()

@router.get("/feature-flags", response_model=APIResponse[Dict[str, bool]])
async def get_tenant_feature_flags(
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("settings:read"))
):
    """Retrieve all feature flags with tenant overrides applied."""
    tenant_doc = await db["tenants"].find_one({"_id": current_user.tenant_id})
    if not tenant_doc:
        raise HTTPException(status_code=404, detail="Tenant registry not found")
        
    tenant_flags = tenant_doc.get("config", {}).get("feature_flags", {})
    resolved_flags = feature_flags.get_all_flags(tenant_flags)
    
    return {
        "success": True,
        "message": "Tenant feature flags resolved.",
        "data": resolved_flags,
        "meta": {},
        "errors": []
    }

@router.post("/feature-flags", response_model=APIResponse[Dict[str, bool]])
async def update_tenant_feature_flags(
    flags_data: Dict[str, bool] = Body(...),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("settings:write"))
):
    """Update tenant overrides for feature flags."""
    tenant_doc = await db["tenants"].find_one({"_id": current_user.tenant_id})
    if not tenant_doc:
        raise HTTPException(status_code=404, detail="Tenant registry not found")

    # Validate feature flags being toggled exist in settings
    for key in flags_data.keys():
        if key not in feature_flags.default_flags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown feature flag module: {key}"
            )

    # Get existing overrides
    config = tenant_doc.get("config", {})
    existing_flags = config.get("feature_flags", {})
    existing_flags.update(flags_data)

    await db["tenants"].update_one(
        {"_id": current_user.tenant_id},
        {
            "$set": {
                "config.feature_flags": existing_flags,
                "updated_at": datetime.utcnow()
            }
        }
    )

    # Log action
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "feature_flags_update",
        "category": "audit",
        "details": {"updated_flags": flags_data},
        "created_at": datetime.utcnow()
    })

    resolved_flags = feature_flags.get_all_flags(existing_flags)
    return {
        "success": True,
        "message": "Tenant feature flags updated successfully.",
        "data": resolved_flags,
        "meta": {},
        "errors": []
    }

@router.get("/system", response_model=APIResponse[SystemSettingsResponse])
async def get_system_settings(
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("settings:read"))
):
    """Retrieve platform-wide system settings. Restricted to SuperAdmin bypass roles."""
    role_doc = await db["roles"].find_one({"_id": current_user.role_id})
    if not role_doc or role_doc.get("name") != "SuperAdmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: requires platform system access level."
        )

    sys_settings = await db["system_settings"].find_one({"_id": "sys_settings"})
    if not sys_settings:
        raise HTTPException(status_code=404, detail="System settings document not resolved.")
        
    return {
        "success": True,
        "message": "System configurations resolved.",
        "data": SystemSettingsResponse(**sys_settings),
        "meta": {},
        "errors": []
    }

@router.put("/system", response_model=APIResponse[SystemSettingsResponse])
async def update_system_settings(
    settings_data: Dict[str, Any] = Body(...),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("settings:write"))
):
    """Modify system branding, email servers, security configurations, or storage engines."""
    role_doc = await db["roles"].find_one({"_id": current_user.role_id})
    if not role_doc or role_doc.get("name") != "SuperAdmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: requires system-level updates."
        )

    update_fields = {}
    for scope in ["general", "branding", "storage", "email", "security"]:
        if scope in settings_data:
            for k, v in settings_data[scope].items():
                update_fields[f"{scope}.{k}"] = v

    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        result = await db["system_settings"].find_one_and_update(
            {"_id": "sys_settings"},
            {"$set": update_fields},
            return_document=True
        )
    else:
        result = await db["system_settings"].find_one({"_id": "sys_settings"})

    # Log action
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "system_settings_update",
        "category": "security",
        "details": {"updated_scopes": list(settings_data.keys())},
        "created_at": datetime.utcnow()
    })

    return {
        "success": True,
        "message": "System configuration parameters updated.",
        "data": SystemSettingsResponse(**result),
        "meta": {},
        "errors": []
    }
