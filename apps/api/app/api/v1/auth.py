import jwt
from fastapi import APIRouter, Depends, Query, Path, status, Request, Response
from typing import Optional, List

from apps.api.app.core.config import settings
from apps.api.app.core.security import set_auth_cookies, clear_auth_cookies, extract_access_token, decode_access_token
from apps.api.app.core.identity_context import IdentityContext, get_current_identity
from apps.api.app.core.auth_exceptions import InvalidToken, AccountDisabled
from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.schemas.auth_schemas import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthVerifyEmailRequest,
    AuthResponseDataSchema,
    AuthUserResponse
)
from apps.api.app.services.authentication import AuthenticationService, get_authentication_service
from apps.api.app.models.identity.user import User, UserStatus
from beanie import PydanticObjectId

router = APIRouter()

def get_client_ip(request: Request) -> Optional[str]:
    """Helper to extract IP address from request headers or client details."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None

async def get_current_active_user(request: Request) -> User:
    """Retrieve active user context using Beanie ODM and access token."""
    from datetime import datetime
    from apps.api.app.models.identity.session import Session

    token = extract_access_token(request)
    if not token:
        raise InvalidToken("Session token missing. Authentication required.")
        
    user_id = decode_access_token(token)
    if user_id is None:
        raise InvalidToken("Session invalid or expired. Please sign in again.")
        
    # Check if session exists in DB (revocation check)
    try:
        decoded_payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        session_id = decoded_payload.get("sessionId")
        if not session_id:
            raise InvalidToken("Session invalid.")
            
        session_exists = await Session.find_one(Session.session_id == session_id, Session.expires_at > datetime.utcnow())
        if not session_exists:
            raise InvalidToken("Session has been terminated or expired.")
    except Exception:
        raise InvalidToken("Session invalid or expired. Please sign in again.")
        
    try:
        obj_id = PydanticObjectId(user_id)
        user = await User.find_one(User.id == obj_id, User.is_deleted == False)
    except Exception:
        user = await User.find_one(User.user_id == user_id, User.is_deleted == False)
        
    if not user:
        raise InvalidToken("Session invalid or expired. Please sign in again.")
        
    if user.status in (UserStatus.SUSPENDED, UserStatus.INACTIVE):
        raise AccountDisabled("User account is suspended or inactive.")
        
    return user


@router.post(
    "/login",
    response_model=APIResponse[AuthResponseDataSchema],
    summary="Authenticate user and issue session tokens"
)
async def login(
    request: Request,
    response: Response,
    payload: AuthLoginRequest,
    service: AuthenticationService = Depends(get_authentication_service)
):
    # Resolve organization from Tenant context
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id or tenant_id == "ten_unseeded":
        tenant_id = request.headers.get("x-tenant-slug") or settings.DEFAULT_TENANT_SLUG

    user_agent = request.headers.get("User-Agent", "Unknown")
    ip = get_client_ip(request)

    res = await service.login(
        org_id_str=tenant_id,
        payload=payload.model_dump(by_alias=False, exclude_unset=True),
        user_agent=user_agent,
        ip_address=ip
    )
    
    set_auth_cookies(response, res["accessToken"], res["refreshToken"])
    
    return APIResponse(
        success=True,
        message="Logged in successfully.",
        data=AuthResponseDataSchema.model_validate(res)
    )

@router.post(
    "/logout",
    response_model=APIResponse[None],
    summary="Invalidate user session"
)
async def logout(
    request: Request,
    response: Response,
    service: AuthenticationService = Depends(get_authentication_service)
):
    token = extract_access_token(request)
    ip = get_client_ip(request)
    if token:
        try:
            # Decode ignoring expiry to allow logouts of expired sessions
            decoded = jwt.decode(token, settings.SECRET_KEY, options={"verify_exp": False, "verify_aud": False}, algorithms=[settings.ALGORITHM])
            session_id = decoded.get("sessionId")
            if session_id:
                await service.logout(session_id, ip_address=ip)
        except Exception:
            pass
            
    clear_auth_cookies(response)
    return APIResponse(
        success=True,
        message="Logged out successfully.",
        data=None
    )

@router.post(
    "/refresh",
    response_model=APIResponse[AuthResponseDataSchema],
    summary="Validate refresh token and issue a new access token"
)
async def refresh(
    response: Response,
    payload: AuthRefreshRequest,
    service: AuthenticationService = Depends(get_authentication_service)
):
    res = await service.refresh_access_token(payload.refresh_token)
    set_auth_cookies(response, res["accessToken"], res["refreshToken"])
    return APIResponse(
        success=True,
        message="Access token refreshed successfully.",
        data=AuthResponseDataSchema.model_validate(res)
    )

@router.get(
    "/me",
    response_model=APIResponse[AuthUserResponse],
    summary="Retrieve active user profile"
)
async def me(
    current_user: User = Depends(get_current_active_user)
):
    return APIResponse(
        success=True,
        message="User profile resolved.",
        data=AuthUserResponse.model_validate(current_user)
    )

@router.get(
    "/permissions/me",
    response_model=APIResponse[List[str]],
    summary="Retrieve effective permissions for current user"
)
async def get_my_permissions(
    context: IdentityContext = Depends(get_current_identity)
):
    from apps.api.app.services.authorization import AuthorizationService
    from typing import List
    service = AuthorizationService()
    perms = await service.get_effective_permissions_for_user(
        user_id=context.user.id,
        org_id=context.organization.id,
        active_roles=context.active_roles
    )
    return APIResponse(
        success=True,
        message="Effective user permissions resolved successfully.",
        data=perms
    )

@router.post(
    "/verify-email",
    response_model=APIResponse[None],
    summary="Verify user email address using token"
)
async def verify_email(
    payload: AuthVerifyEmailRequest,
    service: AuthenticationService = Depends(get_authentication_service)
):
    await service.verify_email(payload.user_id, payload.token)
    return APIResponse(
        success=True,
        message="Email verified successfully. Account is now active.",
        data=None
    )
