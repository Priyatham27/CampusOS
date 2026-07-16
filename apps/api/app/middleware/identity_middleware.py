import jwt
import logging
from typing import Optional, List, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from fastapi import Request, Response
from beanie import PydanticObjectId

from apps.api.app.core.config import settings
from apps.api.app.core.security import extract_access_token, decode_access_token
from apps.api.app.core.identity_context import IdentityContext, set_identity_context, reset_identity_context
from apps.api.app.models.identity.user import User, UserStatus, Profile
from apps.api.app.models.org_engine.organization import Organization, OrganizationStatus
from apps.api.app.models.identity.session import Session, Device
from apps.api.app.models.identity.rbac import UserRole, Role, RolePermission, Permission
from apps.api.app.services.session import SessionService
from apps.api.app.services.config import ConfigurationService

logger = logging.getLogger("campusos.middleware.identity")

def safe_object_id(val: str) -> Optional[PydanticObjectId]:
    try:
        return PydanticObjectId(val)
    except Exception:
        return None

class IdentityMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware that resolves active JWT headers and cookies on incoming requests,
    verifies session health, constructs the unified request-bound IdentityContext, and
    sets the async-safe thread ContextVar.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Skip resolving for open endpoints
        if request.url.path in ["/", "/openapi.json", "/docs", "/redoc", "/favicon.ico"]:
            return await call_next(request)

        # 2. Extract access token
        token = extract_access_token(request)
        if not token:
            return await call_next(request)

        try:
            # 3. Decode access token
            try:
                decoded = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    options={"verify_aud": False},
                    algorithms=[settings.ALGORITHM]
                )
            except jwt.PyJWTError as e:
                logger.warning(f"Access token validation failed: {e}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "Session invalid or expired. Please sign in again.",
                        "data": None,
                        "meta": {},
                        "errors": ["InvalidToken"]
                    }
                )

            user_id_str = decoded.get("sub") or decoded.get("userId")
            if not user_id_str:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "Access token is missing user subject claim.",
                        "data": None,
                        "meta": {},
                        "errors": ["InvalidTokenClaims"]
                    }
                )

            # 4. Resolve User
            user_obj_id = safe_object_id(user_id_str)
            if user_obj_id:
                user = await User.find_one(User.id == user_obj_id, User.is_deleted == False)
            else:
                user = await User.find_one(User.user_id == user_id_str, User.is_deleted == False)

            if not user:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "User account was not found.",
                        "data": None,
                        "meta": {},
                        "errors": ["UserNotFound"]
                    }
                )

            if user.status in (UserStatus.SUSPENDED, UserStatus.INACTIVE):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "User account is suspended or inactive.",
                        "data": None,
                        "meta": {},
                        "errors": ["AccountDisabled"]
                    }
                )

            # 5. Resolve Organization
            org_id_str = decoded.get("organizationId") or str(user.organization_id)
            org_obj_id = safe_object_id(org_id_str)
            if org_obj_id:
                org = await Organization.find_one(Organization.id == org_obj_id, Organization.is_deleted == False)
            else:
                org = await Organization.find_one(Organization.organization_id == org_id_str, Organization.is_deleted == False)

            if not org:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "User organization profile was not found.",
                        "data": None,
                        "meta": {},
                        "errors": ["OrganizationNotFound"]
                    }
                )

            if org.status != OrganizationStatus.ACTIVE:
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "Organization has been suspended or deactivated.",
                        "data": None,
                        "meta": {},
                        "errors": ["OrganizationInactive"]
                    }
                )

            # 6. Resolve Session (Stateful if sessionId is present, Stateless bypass if not)
            session_id = decoded.get("sessionId")
            if not session_id:
                from datetime import datetime, timedelta
                session = Session(
                    sessionId="SES_000000",
                    userId=user.id,
                    ipAddress="127.0.0.1",
                    userAgent="Stateless Bypass",
                    expiresAt=datetime.utcnow() + timedelta(days=1),
                    lastActivity=datetime.utcnow()
                )
            else:
                session_service = SessionService()
                try:
                    session = await session_service.validate_session_activity(session_id)
                except Exception as e:
                    logger.warning(f"Session validation failed for '{session_id}': {e}")
                    return JSONResponse(
                        status_code=401,
                        content={
                            "success": False,
                            "message": str(e),
                            "data": None,
                            "meta": {},
                            "errors": [e.__class__.__name__]
                        }
                    )

            # 7. Resolve user Profile
            profile = None
            if user.profile_id:
                profile = await Profile.find_one(Profile.id == user.profile_id, Profile.is_deleted == False)
            if not profile:
                profile = await Profile.find_one(Profile.user_id == user.id, Profile.is_deleted == False)

            # 8. Resolve Roles, Permissions, and Capabilities using IdentityCacheService
            from apps.api.app.services.identity_cache import IdentityCacheService
            from apps.api.app.models.org_engine.capability import Capability

            cache_service = IdentityCacheService()
            cached_data = await cache_service.get_cached_identity(str(org.id), str(user.id))

            if cached_data:
                role_slugs = cached_data.get("roles", [])
                permissions = cached_data.get("permissions", [])
                capabilities = cached_data.get("capabilities", [])
            else:
                user_roles = await UserRole.find(UserRole.user_id == user.id).to_list()
                role_ids = [ur.role_id for ur in user_roles]
                roles = await Role.find({"_id": {"$in": role_ids}, "isDeleted": False}).to_list()
                role_slugs = [r.slug for r in roles]

                permissions = []
                if role_ids:
                    role_perms = await RolePermission.find({"roleId": {"$in": role_ids}}).to_list()
                    perm_ids = [rp.permission_id for rp in role_perms]
                    perms = await Permission.find({"_id": {"$in": perm_ids}, "isDeleted": False}).to_list()
                    permissions = [p.slug for p in perms]

                # Resolve active Capabilities for this organization
                enabled_caps = await Capability.find(
                    Capability.organization_id == org.id,
                    Capability.enabled == True,
                    Capability.is_deleted == False
                ).to_list()
                capabilities = [c.slug for c in enabled_caps]

                # Cache the resolved roles/permissions/capabilities
                await cache_service.set_cached_identity(
                    str(org.id),
                    str(user.id),
                    {
                        "roles": role_slugs,
                        "permissions": permissions,
                        "capabilities": capabilities
                    }
                )

            # 9. Resolve Device
            device = None
            if session.device_id:
                device = await Device.find_one(Device.device_id == session.device_id)

            # 10. Resolve Locale, Timezone, and Feature Flags
            locale_header = request.headers.get("Accept-Language", "en")
            locale = locale_header.split(",")[0].strip() if "," in locale_header else locale_header

            config_service = ConfigurationService()
            try:
                flags_doc = await config_service.resolve_configuration(
                    org_id_str=str(org.id),
                    key="feature_flags",
                    environment="PRODUCTION"
                )
                flags = flags_doc.get("value", settings.FEATURE_FLAGS)
            except Exception:
                flags = settings.FEATURE_FLAGS

            # 11. Construct Context & Set Bindings
            context = IdentityContext(
                user=user,
                organization=org,
                profile=profile,
                activeRoles=role_slugs,
                activeSession=session,
                device=device,
                permissions=permissions,
                capabilities=capabilities,
                locale=locale,
                timezone=org.timezone or "UTC",
                featureFlags=flags
            )

            request.state.identity_context = context
            token_var = set_identity_context(context)
            try:
                response = await call_next(request)
                return response
            finally:
                reset_identity_context(token_var)

        except Exception as e:
            logger.exception("Unexpected error in IdentityMiddleware processing")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal error occurred resolving request identity context.",
                    "data": None,
                    "meta": {},
                    "errors": [str(e)]
                }
            )
