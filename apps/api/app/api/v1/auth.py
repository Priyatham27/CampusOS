from fastapi import APIRouter, Depends, HTTPException, status, Body, Response, Request
from datetime import datetime, timedelta
import motor.motor_asyncio
from typing import Dict, Any

from apps.api.app.core.database import get_db
from apps.api.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    set_auth_cookies,
    clear_auth_cookies
)
from apps.api.app.core.config import settings
from apps.api.app.core.logger import logger
from apps.api.app.models.models import generate_prefixed_id, User, Tenant, Role, AuditLog
from apps.api.app.middleware.auth import get_current_user
from apps.api.app.schemas.schemas import (
    APIResponse,
    LoginRequest,
    UserResponse,
    UserWithDetails,
    TenantResponse,
    RoleResponse
)

router = APIRouter()

async def seed_defaults(db: motor.motor_asyncio.AsyncIOMotorDatabase):
    """Seed default tenant configuration, roles, system parameters, and SuperAdmin user if database is empty."""
    try:
        users_count = await db["users"].count_documents({})
        if users_count > 0:
            # Already seeded
            return None

        logger.info("Database is empty. Seeding defaults for CampusOS Tenant Platform Foundation...")
        
        # 1. Create Default Tenant
        tenant_id = generate_prefixed_id("ten")
        default_tenant = {
            "_id": tenant_id,
            "name": "CampusOS Main Academy",
            "slug": settings.DEFAULT_TENANT_SLUG,
            "config": {
                "theme": {
                    "primary_color": "#4f46e5",
                    "secondary_color": "#0891b2",
                    "logo_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=128&h=128&fit=crop&q=80",
                    "favicon_url": "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=32&h=32&fit=crop&q=80",
                    "custom_css": ""
                },
                "custom_domain": "localhost",
                "active_modules": ["core"],
                "feature_flags": {
                    "enable_events": True,
                    "enable_attendance": False,
                    "enable_certificates": False,
                    "enable_clubs": False,
                    "enable_analytics": False,
                    "enable_audit_logs": True,
                    "enable_file_uploads": True
                }
            },
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await db["tenants"].insert_one(default_tenant)

        # 2. Create Default Roles
        roles_to_create = [
            {
                "_id": generate_prefixed_id("rol"),
                "name": "SuperAdmin",
                "description": "System-wide owner with bypass privileges.",
                "permissions": ["*"],
                "is_system": True,
                "tenant_id": tenant_id
            },
            {
                "_id": generate_prefixed_id("rol"),
                "name": "Admin",
                "description": "Tenant administrator.",
                "permissions": [
                    "users:read", "users:manage", 
                    "roles:read", "roles:manage", 
                    "settings:read", "settings:write", 
                    "audit:read", "upload:file"
                ],
                "is_system": True,
                "tenant_id": tenant_id
            },
            {
                "_id": generate_prefixed_id("rol"),
                "name": "Staff",
                "description": "Educational staff / faculty.",
                "permissions": [
                    "users:read", "settings:read", "upload:file"
                ],
                "is_system": True,
                "tenant_id": tenant_id
            },
            {
                "_id": generate_prefixed_id("rol"),
                "name": "Student",
                "description": "Standard college student.",
                "permissions": [
                    "settings:read"
                ],
                "is_system": True,
                "tenant_id": tenant_id
            }
        ]
        
        role_map = {}
        for r in roles_to_create:
            await db["roles"].insert_one(r)
            role_map[r["name"]] = r["_id"]

        # 3. Create default SuperAdmin user
        user_id = generate_prefixed_id("usr")
        admin_user = {
            "_id": user_id,
            "email": "admin@campusos.com",
            "hashed_password": hash_password("password123"),
            "full_name": "CampusOS Administrator",
            "tenant_id": tenant_id,
            "role_id": role_map["SuperAdmin"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        await db["users"].insert_one(admin_user)
        logger.info(f"Seeded Tenant: {tenant_id}, Admin User: {user_id} (admin@campusos.com / password123)")
        
        # 4. Create default System Settings document
        await db["system_settings"].insert_one({
            "_id": "sys_settings",
            "general": {},
            "branding": {
                "platform_name": "CampusOS",
                "logo_url": None,
                "support_email": "support@campusos.com"
            },
            "storage": {
                "provider": "local",
                "upload_limit_mb": 10
            },
            "email": {
                "smtp_host": "smtp.mailgun.org",
                "smtp_port": 587,
                "smtp_user": None,
                "sender_name": "CampusOS Notifications"
            },
            "security": {
                "mfa_enabled": False,
                "password_history_limit": 3,
                "cookie_secure": False
            },
            "updated_at": datetime.utcnow()
        })
        
        # Write Audit Log
        await db["audit_logs"].insert_one({
            "_id": generate_prefixed_id("aud"),
            "tenant_id": tenant_id,
            "user_id": user_id,
            "user_email": "admin@campusos.com",
            "action": "system_seeding",
            "category": "security",
            "details": {"message": "Auto seeded default multi-tenant platform configuration"},
            "created_at": datetime.utcnow()
        })
        
        return tenant_id
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        return None

@router.post("/login", response_model=APIResponse[Dict[str, Any]])
async def login(
    response: Response,
    login_data: LoginRequest,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """Authenticate user, sets HttpOnly cookies, and returns standard success response."""
    # Ensure default data is seeded if database is fresh
    await seed_defaults(db)
    
    user_doc = await db["users"].find_one({"email": login_data.email.lower()})
    if not user_doc or not verify_password(login_data.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )
        
    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
        
    user_id = str(user_doc["_id"])
    tenant_id = str(user_doc["tenant_id"])
    
    # Update last login
    await db["users"].update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_email": user_doc["email"],
        "action": "user_login",
        "category": "security",
        "details": {"message": f"Successful login for {user_doc['email']}"},
        "created_at": datetime.utcnow()
    })
    
    # Generate tokens
    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    
    # Set cookies
    set_auth_cookies(response, access_token, refresh_token)
    
    return {
        "success": True,
        "message": "Authenticated successfully. Secure session cookies assigned.",
        "data": {
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "token_type": "bearer"
        },
        "meta": {},
        "errors": []
    }

@router.post("/logout", response_model=APIResponse[None])
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """Deletes authentication cookies and signs user out."""
    clear_auth_cookies(response)
    
    # Audit log
    await db["audit_logs"].insert_one({
        "_id": generate_prefixed_id("aud"),
        "tenant_id": current_user.tenant_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "action": "user_logout",
        "category": "security",
        "details": {"message": "Session terminated successfully"},
        "created_at": datetime.utcnow()
    })
    
    return {
        "success": True,
        "message": "Logged out successfully. Authentication cookies cleared.",
        "data": None,
        "meta": {},
        "errors": []
    }

@router.get("/me", response_model=APIResponse[UserWithDetails])
async def get_me(
    current_user: User = Depends(get_current_user),
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
):
    """Retrieve details of the active user session including their role configurations and tenant branding configs."""
    # Resolve Tenant
    tenant_doc = await db["tenants"].find_one({"_id": current_user.tenant_id})
    tenant = None
    if tenant_doc:
        tenant_doc["_id"] = str(tenant_doc["_id"])
        tenant = TenantResponse(**tenant_doc)
        
    # Resolve Role
    role_doc = await db["roles"].find_one({"_id": current_user.role_id})
    role = None
    if role_doc:
        role_doc["_id"] = str(role_doc["_id"])
        role = RoleResponse(**role_doc)
        
    user_res = UserWithDetails(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        tenant_id=current_user.tenant_id,
        role_id=current_user.role_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        tenant=tenant,
        role=role
    )
    
    return {
        "success": True,
        "message": "Active user session resolved.",
        "data": user_res,
        "meta": {},
        "errors": []
    }

@router.post("/seed", response_model=APIResponse[Dict[str, Any]])
async def manual_seed(db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)):
    """Exposes a route to seed tenant configurations."""
    seeded = await seed_defaults(db)
    if seeded:
        return {
            "success": True,
            "message": "Database successfully seeded.",
            "data": {"tenant_id": seeded},
            "meta": {},
            "errors": []
        }
    return {
        "success": True,
        "message": "Database already contains data, seeding skipped.",
        "data": {},
        "meta": {},
        "errors": []
    }
