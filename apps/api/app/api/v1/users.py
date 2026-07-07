from fastapi import APIRouter, Depends, HTTPException, status
import motor.motor_asyncio
from datetime import datetime
from typing import List

from apps.api.app.core.database import get_db
from apps.api.app.core.security import hash_password
from apps.api.app.middleware.auth import requires_permission
from apps.api.app.models.models import generate_prefixed_id, User
from apps.api.app.schemas.schemas import APIResponse, UserResponse, UserCreate, UserUpdate

router = APIRouter()

@router.get("", response_model=APIResponse[List[UserResponse]])
async def list_users(
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("users:read"))
):
    """List users within the authenticated user's tenant boundary."""
    cursor = db["users"].find({"tenant_id": current_user.tenant_id})
    users = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        users.append(UserResponse(**doc))
        
    return {
        "success": True,
        "message": f"Successfully retrieved {len(users)} users.",
        "data": users,
        "meta": {"count": len(users)},
        "errors": []
    }

@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("users:manage"))
):
    """Create a user. Scopes the new account to the administrator's active tenant."""
    # Ensure they are only creating a user in their own tenant
    if user_data.tenant_id != current_user.tenant_id:
        role_doc = await db["roles"].find_one({"_id": current_user.role_id})
        if not role_doc or role_doc.get("name") != "SuperAdmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant ID mismatch."
            )

    # Check email duplicate
    existing = await db["users"].find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )

    # Verify role exists in tenant
    role_doc = await db["roles"].find_one({"_id": user_data.role_id})
    if not role_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    user_id = generate_prefixed_id("usr")
    new_user = {
        "_id": user_id,
        "email": user_data.email.lower(),
        "hashed_password": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "tenant_id": user_data.tenant_id,
        "role_id": user_data.role_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_login": None
    }

    await db["users"].insert_one(new_user)

    # Audit log using prefices
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "user_create",
        "category": "audit",
        "details": {"created_user_id": user_id, "email": new_user["email"]},
        "created_at": datetime.utcnow()
    })

    new_user["_id"] = str(new_user["_id"])
    return {
        "success": True,
        "message": "User account created successfully.",
        "data": UserResponse(**new_user),
        "meta": {},
        "errors": []
    }

@router.put("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("users:manage"))
):
    """Update profile parameters and security privileges of an active user."""
    target_user = await db["users"].find_one({"_id": user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Enforce organizational boundary
    if str(target_user["tenant_id"]) != current_user.tenant_id:
        role_doc = await db["roles"].find_one({"_id": current_user.role_id})
        if not role_doc or role_doc.get("name") != "SuperAdmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant ID scope mismatch."
            )

    update_fields = {}
    if user_data.email is not None:
        email_lower = user_data.email.lower()
        if email_lower != target_user["email"]:
            dup = await db["users"].find_one({"email": email_lower})
            if dup:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            update_fields["email"] = email_lower

    if user_data.full_name is not None:
        update_fields["full_name"] = user_data.full_name

    if user_data.role_id is not None:
        role_doc = await db["roles"].find_one({"_id": user_data.role_id})
        if not role_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role does not exist"
            )
        update_fields["role_id"] = user_data.role_id

    if user_data.is_active is not None:
        update_fields["is_active"] = user_data.is_active

    if not update_fields:
        target_user["_id"] = str(target_user["_id"])
        return {
            "success": True,
            "message": "No modification parameters provided.",
            "data": UserResponse(**target_user),
            "meta": {},
            "errors": []
        }

    result = await db["users"].find_one_and_update(
        {"_id": user_id},
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
        "action": "user_update",
        "category": "audit",
        "details": {"updated_user_id": user_id, "fields": list(update_fields.keys())},
        "created_at": datetime.utcnow()
    })

    return {
        "success": True,
        "message": "User account updated successfully.",
        "data": UserResponse(**result),
        "meta": {},
        "errors": []
    }

@router.delete("/{user_id}", response_model=APIResponse[None])
async def delete_user(
    user_id: str,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db),
    current_user: User = Depends(requires_permission("users:manage"))
):
    """Deactivate or remove user records from platform databases."""
    target_user = await db["users"].find_one({"_id": user_id})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if str(target_user["tenant_id"]) != current_user.tenant_id:
        role_doc = await db["roles"].find_one({"_id": current_user.role_id})
        if not role_doc or role_doc.get("name") != "SuperAdmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: tenant ID scope mismatch."
            )

    await db["users"].delete_one({"_id": user_id})

    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "user_delete",
        "category": "audit",
        "details": {"deleted_user_id": user_id, "email": target_user["email"]},
        "created_at": datetime.utcnow()
    })
    
    return {
        "success": True,
        "message": "User account deleted successfully.",
        "data": None,
        "meta": {},
        "errors": []
    }
