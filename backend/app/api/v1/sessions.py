from fastapi import APIRouter, Depends, status, Request, Response, Path
from typing import List, Optional
from beanie import PydanticObjectId

from app.core.config import settings
from app.core.security import set_auth_cookies, clear_auth_cookies, extract_access_token
from app.core.identity_context import IdentityContext, get_current_identity
from app.schemas.schemas import APIResponse
from app.schemas.auth_schemas import AuthResponseDataSchema, AuthUserResponse
from app.schemas.session_schemas import (
    SessionCreateRequest,
    SessionResponse,
    DeviceResponse,
    DeviceTrustUpdate
)
from app.services.session import SessionService
from app.repositories.session import SessionRepository, DeviceRepository
from app.api.v1.auth import get_client_ip

router = APIRouter()

def get_session_service() -> SessionService:
    return SessionService()

@router.post(
    "/create",
    response_model=APIResponse[AuthResponseDataSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create active user session"
)
async def create_session(
    request: Request,
    response: Response,
    payload: SessionCreateRequest,
    service: SessionService = Depends(get_session_service)
):
    ua = request.headers.get("User-Agent", "Unknown")
    ip = get_client_ip(request)

    session, access_token, refresh_token = await service.create_session(
        user_id=PydanticObjectId(payload.user_id),
        org_id=PydanticObjectId(payload.organization_id),
        ip=ip,
        ua_string=ua
    )

    # Resolve User model to respond with AuthUserResponse
    from app.models.identity.user import User
    user = await User.find_one(User.id == PydanticObjectId(payload.user_id))

    set_auth_cookies(response, access_token, refresh_token)

    return APIResponse(
        success=True,
        message="Session created successfully.",
        data=AuthResponseDataSchema(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=AuthUserResponse.model_validate(user)
        )
    )

@router.post(
    "/refresh",
    response_model=APIResponse[AuthResponseDataSchema],
    summary="Rotate refresh token and issue new session access token"
)
async def refresh_session(
    request: Request,
    response: Response,
    service: SessionService = Depends(get_session_service)
):
    # Try cookies first, then header/body extraction
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_KEY)
    if not refresh_token:
        # Fallback to JSON payload or headers
        try:
            body = await request.json()
            refresh_token = body.get("refreshToken")
        except Exception:
            pass

    if not refresh_token:
        # Check header
        refresh_token = request.headers.get("x-refresh-token")

    if not refresh_token:
        from app.core.session_exceptions import RefreshTokenInvalid
        raise RefreshTokenInvalid("Session refresh token missing.")

    ip = get_client_ip(request)
    ua = request.headers.get("User-Agent", "Unknown")

    access_token, new_refresh_token = await service.refresh_session(refresh_token, ip, ua)

    # Reconstruct user from new access token
    import jwt
    decoded = jwt.decode(access_token, settings.SECRET_KEY, options={"verify_aud": False}, algorithms=[settings.ALGORITHM])
    from app.models.identity.user import User
    user = await User.find_one(User.id == PydanticObjectId(decoded["sub"]))

    set_auth_cookies(response, access_token, new_refresh_token)

    return APIResponse(
        success=True,
        message="Session tokens rotated successfully.",
        data=AuthResponseDataSchema(
            accessToken=access_token,
            refreshToken=new_refresh_token,
            expiresIn=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=AuthUserResponse.model_validate(user)
        )
    )

@router.post(
    "/logout",
    response_model=APIResponse[None],
    summary="Terminate current user session"
)
async def logout(
    response: Response,
    context: IdentityContext = Depends(get_current_identity),
    service: SessionService = Depends(get_session_service)
):
    await service.logout_session(context.active_session.session_id)
    clear_auth_cookies(response)
    return APIResponse(
        success=True,
        message="Session revoked successfully.",
        data=None
    )

@router.post(
    "/logout-all",
    response_model=APIResponse[None],
    summary="Terminate all active user sessions"
)
async def logout_all(
    response: Response,
    context: IdentityContext = Depends(get_current_identity),
    service: SessionService = Depends(get_session_service)
):
    await service.logout_all_sessions(context.user.id)
    clear_auth_cookies(response)
    return APIResponse(
        success=True,
        message="All active user sessions revoked successfully.",
        data=None
    )

@router.get(
    "/me",
    response_model=APIResponse[SessionResponse],
    summary="Retrieve current active session profile"
)
async def get_session_me(
    context: IdentityContext = Depends(get_current_identity)
):
    session = context.active_session
    res = SessionResponse.model_validate(session)
    res.is_current = True
    return APIResponse(
        success=True,
        message="Current session resolved.",
        data=res
    )

@router.get(
    "",
    response_model=APIResponse[List[SessionResponse]],
    summary="List all active user sessions"
)
async def list_active_sessions(
    context: IdentityContext = Depends(get_current_identity),
    repo: SessionRepository = Depends(SessionRepository)
):
    sessions = await repo.list_active_sessions(context.user.id)
    responses = []
    for s in sessions:
        res = SessionResponse.model_validate(s)
        res.is_current = (s.session_id == context.active_session.session_id)
        responses.append(res)
    return APIResponse(
        success=True,
        message="Active sessions resolved.",
        data=responses
    )

@router.get(
    "/devices",
    response_model=APIResponse[List[DeviceResponse]],
    summary="List all recognized user devices"
)
async def list_user_devices(
    context: IdentityContext = Depends(get_current_identity),
    repo: DeviceRepository = Depends(DeviceRepository)
):
    devices = await repo.list_user_devices(context.user.id)
    responses = [DeviceResponse.model_validate(d) for d in devices]
    return APIResponse(
        success=True,
        message="User devices resolved.",
        data=responses
    )

@router.patch(
    "/devices/{deviceId}/trust",
    response_model=APIResponse[DeviceResponse],
    summary="Update device trust state"
)
async def update_device_trust(
    payload: DeviceTrustUpdate,
    device_id: str = Path(..., alias="deviceId"),
    context: IdentityContext = Depends(get_current_identity),
    repo: DeviceRepository = Depends(DeviceRepository)
):
    device = await repo.find_device(device_id)
    if not device or device.user_id != context.user.id:
        from app.core.session_exceptions import DeviceNotFound
        raise DeviceNotFound("Device not found or does not belong to this user.")

    updated = await repo.update_device_trust(device_id, payload.trusted)
    return APIResponse(
        success=True,
        message="Device trust updated successfully.",
        data=DeviceResponse.model_validate(updated)
    )

@router.delete(
    "/devices/{deviceId}",
    response_model=APIResponse[None],
    summary="Revoke device registration"
)
async def revoke_device(
    device_id: str = Path(..., alias="deviceId"),
    context: IdentityContext = Depends(get_current_identity),
    repo: DeviceRepository = Depends(DeviceRepository)
):
    device = await repo.find_device(device_id)
    if not device or device.user_id != context.user.id:
        from app.core.session_exceptions import DeviceNotFound
        raise DeviceNotFound("Device not found or does not belong to this user.")

    await repo.delete_device(device_id)
    return APIResponse(
        success=True,
        message="Device registration revoked successfully.",
        data=None
    )
