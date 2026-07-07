from fastapi import APIRouter
from apps.api.app.api.v1.auth import router as auth_router
from apps.api.app.api.v1.organizations import router as organizations_router
from apps.api.app.api.v1.users import router as user_router
from apps.api.app.api.v1.roles import router as roles_router
from apps.api.app.api.v1.settings import router as settings_router
from apps.api.app.api.v1.audit import router as audit_router
from apps.api.app.api.v1.upload import router as upload_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# Mount organization CRUD router on "/organizations" prefix
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations Engine"])
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(roles_router, prefix="/roles", tags=["Roles & Permissions"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings & Feature Flags"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit & Logs"])
api_router.include_router(upload_router, prefix="/upload", tags=["Upload Service"])
