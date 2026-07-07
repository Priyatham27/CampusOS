from fastapi import APIRouter, Depends, HTTPException, status
import motor.motor_asyncio
from datetime import datetime
from typing import List

from apps.api.app.core.database import get_db
from apps.api.app.middleware.auth import requires_permission
from apps.api.app.models.models import generate_prefixed_id, User, Role
from apps.api.app.schemas.schemas import APIResponse, RoleResponse, RoleCreate, RoleUpdate, PermissionResponse

router = APIRouter()

# Static list of system permissions
SYSTEM_PERMISSIONS = [
    {"name": "users:read", "description": "View lists of users and user profiles", "module": "core"},
    {"name": "users:manage", "description": "Create, edit, and delete user profiles", "module": "core"},
    {"name": "roles:read", "description": "View roles and permission levels", "module": "core"},
    {"name": "roles:manage", "description": "Create, update, and remove roles", "module": "core"},
    {"name": "settings:read", "description": "Read organization metadata and theme settings", "module": "core"},
    {"name": "settings:write", "description": "Modify organization metadata, white-labeling rules, and configurations", "module": "core"},
    {"name": "audit:read", "description": "Access security logs and audit data", "module": "core"},
    {"name": "upload:file", "description": "Upload files using the system file service", "module": "core"},
    # Reserved permissions for future modules
    {"name": "events:read", "description": "View organized events", "module": "events"},
    {"name": "events:create", "description": "Create new events", "module": "events"},
    {"name": "events:manage", "description": "Manage registrations, edit, and delete events", "module": "events"},
    {"name": "attendance:manage", "description": "Take and record course/event attendance", "module": "attendance"},
    {"name": "clubs:manage", "description": "Administer campus clubs and student bodies", "module": "clubs"},
]

@router.get("/permissions/list", response_model=APIResponse[List[PermissionResponse]])
async def list_system_permissions(
    current_user: User = Depends(requires_permission("roles:read"))
):
    """Retrieve list of all system permissions registered across all modules."""
    return {
        "success": True,
        "message": "System permissions list loaded.",
        "data": SYSTEM_PERMISSIONS,
        "meta": {"count": len(SYSTEM_PERMISSIONS)},
        "errors": []
    }

@router.get("", response_model=APIResponse[List[RoleResponse]])
async def list_roles(
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("roles:read"))
):
    """List roles configured in the active tenant."""
    cursor = db["roles"].find({"tenant_id": current_user.tenant_id})
    roles = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        roles.append(RoleResponse(**doc))
        
    return {
        "success": True,
        "message": f"Successfully retrieved {len(roles)} roles.",
        "data": roles,
        "meta": {"count": len(roles)},
        "errors": []
    }

@router.post("", response_model=APIResponse[RoleResponse], status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("roles:manage"))
):
    """Create a security role for tenant access control."""
    # Ensure permission names are valid
    valid_perm_names = {p["name"] for p in SYSTEM_PERMISSIONS}
    valid_perm_names.add("*")
    
    for perm in role_data.permissions:
        if perm not in valid_perm_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid system permission: {perm}"
            )

    role_id = generate_prefixed_id("rol")
    new_role = {
        "_id": role_id,
        "name": role_data.name,
        "description": role_data.description,
        "permissions": role_data.permissions,
        "is_system": False,
        "tenant_id": current_user.tenant_id
    }

    await db["roles"].insert_one(new_role)

    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "role_create",
        "category": "audit",
        "details": {"created_role_id": role_id, "name": new_role["name"]},
        "created_at": datetime.utcnow()
    })

    new_role["_id"] = str(new_role["_id"])
    return {
        "success": True,
        "message": "Security role created successfully.",
        "data": RoleResponse(**new_role),
        "meta": {},
        "errors": []
    }

@router.put("/{role_id}", response_model=APIResponse[RoleResponse])
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("roles:manage"))
):
    """Update role details and permissions scope."""
    target_role = await db["roles"].find_one({"_id": role_id})
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if str(target_role["tenant_id"]) != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: role tenant scope mismatch."
        )

    if target_role.get("is_system", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system-defined roles"
        )

    update_fields = {}
    if role_data.name is not None:
        update_fields["name"] = role_data.name
    if role_data.description is not None:
        update_fields["description"] = role_data.description
    if role_data.permissions is not None:
        valid_perm_names = {p["name"] for p in SYSTEM_PERMISSIONS}
        valid_perm_names.add("*")
        for perm in role_data.permissions:
            if perm not in valid_perm_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid system permission: {perm}"
                )
        update_fields["permissions"] = role_data.permissions

    if not update_fields:
        target_role["_id"] = str(target_role["_id"])
        return {
            "success": True,
            "message": "No modification parameters provided.",
            "data": RoleResponse(**target_role),
            "meta": {},
            "errors": []
        }

    result = await db["roles"].find_one_and_update(
        {"_id": role_id},
        {"$set": update_fields},
        return_document=True
    )
    result["_id"] = str(result["_id"])

    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "role_update",
        "category": "audit",
        "details": {"updated_role_id": role_id, "fields": list(update_fields.keys())},
        "created_at": datetime.utcnow()
    })

    return {
        "success": True,
        "message": "Security role updated successfully.",
        "data": RoleResponse(**result),
        "meta": {},
        "errors": []
    }

@router.delete("/{role_id}", response_model=APIResponse[None])
async def delete_role(
    role_id: str,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("roles:manage"))
):
    """Delete a custom security role. Verifies that the role is not system-defined or currently active on user profiles."""
    target_role = await db["roles"].find_one({"_id": role_id})
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if str(target_role["tenant_id"]) != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: role tenant scope mismatch."
        )

    if target_role.get("is_system", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system-defined roles"
        )

    # Check if any user is currently assigned this role
    users_with_role = await db["users"].count_documents({"role_id": role_id})
    if users_with_role > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role because it is currently assigned to users"
        )

    await db["roles"].delete_one({"_id": role_id})

    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "role_delete",
        "category": "audit",
        "details": {"deleted_role_id": role_id, "name": target_role["name"]},
        "created_at": datetime.utcnow()
    })
    
    return {
        "success": True,
        "message": "Role profile removed successfully.",
        "data": None,
        "meta": {},
        "errors": []
    }
