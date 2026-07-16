from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.users import router as user_router
from app.api.v1.profile import router as profile_router
from app.api.v1.roles import router as roles_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.policies import router as policies_router
from app.api.v1.settings import router as settings_router
from app.api.v1.audit import router as audit_router
from app.api.v1.upload import router as upload_router
from app.api.v1.branding import router as branding_router
from app.academic.router import router as academic_router  # DDD Academic Bounded Context
from app.api.v1.capability import router as capability_router
from app.api.v1.config import router as config_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.identity_health import router as identity_health_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sessions_router, prefix="/sessions", tags=["Session & Device Management Engine"])
api_router.include_router(credentials_router, prefix="/credentials", tags=["Credentials Engine"])
# Mount organization CRUD router on "/organizations" prefix
api_router.include_router(organizations_router, prefix="/organizations", tags=["Organizations Engine"])
api_router.include_router(branding_router)
api_router.include_router(academic_router, tags=["Academic Platform"])
api_router.include_router(capability_router, prefix="/capabilities", tags=["Capabilities Engine"])
api_router.include_router(config_router, prefix="/runtime", tags=["Runtime Configuration Engine"])
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(profile_router, prefix="/profile", tags=["Profile"])
api_router.include_router(identity_health_router, prefix="/identity", tags=["Identity Health Engine"])

api_router.include_router(roles_router, prefix="/roles", tags=["Roles & Permissions"])
api_router.include_router(permissions_router, prefix="/permissions", tags=["Roles & Permissions"])
api_router.include_router(policies_router, prefix="/policies", tags=["Roles & Permissions"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings & Feature Flags"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit & Logs"])
api_router.include_router(upload_router, prefix="/upload", tags=["Upload Service"])
