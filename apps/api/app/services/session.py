import secrets
import hashlib
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from beanie import PydanticObjectId

from apps.api.app.core.config import settings
from apps.api.app.core.database import get_db
from apps.api.app.core.ua_parser import parse_user_agent
from apps.api.app.models.identity.user import User, UserStatus
from apps.api.app.models.identity.session import Session, Device, RefreshToken
from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.models.identity.rbac import UserRole, Role, RolePermission, Permission
from apps.api.app.models.identity.security import SecurityEvent, SecurityEventType, SecurityEventSeverity
from apps.api.app.repositories.session import SessionRepository, DeviceRepository
from apps.api.app.services.config import ConfigurationService
from apps.api.app.services.cache_service import CacheService
from apps.api.app.models.models import generate_prefixed_id
from apps.api.app.core.session_exceptions import (
    SessionNotFound,
    SessionExpired,
    RefreshTokenInvalid,
    RefreshTokenExpired,
    DeviceNotFound,
    SessionRevoked,
    TooManySessions
)

logger = logging.getLogger("campusos.service.session")

class SessionService:
    """
    Orchestrates authentication state retention, session timeouts,
    Refresh Token Rotation (RTR), concurrent limits, and device recognition.
    """
    def __init__(self):
        self.session_repo = SessionRepository()
        self.device_repo = DeviceRepository()
        self.config_service = ConfigurationService()
        self.cache = CacheService()

    async def create_session(
        self,
        user_id: PydanticObjectId,
        org_id: PydanticObjectId,
        ip: str,
        ua_string: str
    ) -> tuple[Session, str]:
        """
        Creates a new active session and associated rotated refresh token.
        Detects devices, applies concurrent session limits, and audits logs.
        """
        # 1. Parse user agent
        browser, os_name, platform = parse_user_agent(ua_string)
        device_name = f"{browser} on {os_name}"

        # 2. Device recognition
        device = await self.device_repo.find_user_device_by_details(user_id, device_name)
        new_device_registered = False
        if not device:
            dev_suffix = secrets.randbelow(900000) + 100000
            dev_id_str = f"DEV_{dev_suffix}"
            device = Device(
                deviceId=dev_id_str,
                userId=user_id,
                deviceName=device_name,
                browser=browser,
                os=os_name,
                platform=platform,
                trusted=False,
                lastLogin=datetime.utcnow()
            )
            await self.device_repo.create_device(device)
            new_device_registered = True
            logger.info(f"New device registered: '{device_name}' for user {user_id}")
        else:
            device.last_login = datetime.utcnow()
            await device.save()

        # 3. Concurrent Session Limits
        try:
            policy_doc = await self.config_service.resolve_configuration(
                org_id_str=str(org_id),
                key="security.sessions.concurrent_limit",
                environment="PRODUCTION"
            )
            concurrent_limit = int(policy_doc.get("value", 5))
        except Exception:
            concurrent_limit = 5

        active_sessions = await self.session_repo.list_active_sessions(user_id)
        if len(active_sessions) >= concurrent_limit:
            # Enforce by revoking the oldest active session
            active_sessions.sort(key=lambda s: s.last_activity)
            oldest = active_sessions[0]
            logger.info(f"Revoking oldest session '{oldest.session_id}' to satisfy concurrent limit of {concurrent_limit}.")
            await self.session_repo.revoke_session(oldest.session_id)

        # 4. Expiration details
        try:
            timeout_doc = await self.config_service.resolve_configuration(
                org_id_str=str(org_id),
                key="security.sessions.absolute_timeout_minutes",
                environment="PRODUCTION"
            )
            absolute_mins = int(timeout_doc.get("value", 60 * 24 * 7)) # default 7 days
        except Exception:
            absolute_mins = 60 * 24 * 7

        expires_at = datetime.utcnow() + timedelta(minutes=absolute_mins)

        # 5. Insert Session
        ses_suffix = secrets.randbelow(900000) + 100000
        session_id_str = f"SES_{ses_suffix}"
        
        session = Session(
            sessionId=session_id_str,
            userId=user_id,
            deviceId=device.device_id,
            ipAddress=ip or "127.0.0.1",
            browser=browser,
            platform=platform,
            userAgent=ua_string[:500],
            expiresAt=expires_at,
            lastActivity=datetime.utcnow()
        )
        await self.session_repo.create_session(session)

        # 6. Generate Rotated Refresh Token
        refresh_token_plain = secrets.token_hex(32)
        refresh_token_hash = hashlib.sha256(refresh_token_plain.encode("utf-8")).hexdigest()
        
        rtk_suffix = secrets.randbelow(900000) + 100000
        rtk_doc = RefreshToken(
            tokenId=f"RTK_{rtk_suffix}",
            sessionId=session.id,
            tokenHash=refresh_token_hash,
            expiresAt=expires_at,
            revoked=False
        )
        await rtk_doc.insert()

        # Cache refresh token
        rtk_ttl = int((expires_at - datetime.utcnow()).total_seconds())
        if rtk_ttl > 0:
            self.cache.set_refresh_token(refresh_token_hash, rtk_doc.model_dump(by_alias=True), rtk_ttl)

        # 7. Encode Access JWT
        user = await User.find_one(User.id == user_id)
        if not user:
            raise SessionExpired("User not found.")

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

        iat = int(datetime.utcnow().timestamp())
        exp = iat + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        jwt_payload = {
            "sub": str(user.id),
            "userId": str(user.id),
            "organizationId": str(org_id),
            "roles": role_slugs,
            "permissions": permissions,
            "sessionId": session_id_str,
            "type": "access",
            "iat": iat,
            "exp": exp,
            "iss": settings.APP_NAME,
            "aud": "campusos-api"
        }
        access_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # 8. Audit Logging
        await self._log_session_security_event(
            org_id=org_id,
            user_id=user_id,
            event_type=SecurityEventType.PASSWORD_CHANGED, # placeholder
            severity=SecurityEventSeverity.INFO,
            metadata={"message": f"Session created. Device: {device_name}.", "sessionId": session_id_str},
            ip_address=ip
        )
        if new_device_registered:
            logger.info(f"Audit log: New device '{device.device_id}' registered for user.")

        return session, access_token, refresh_token_plain

    async def refresh_session(
        self,
        refresh_token_plain: str,
        ip: str,
        ua_string: str
    ) -> tuple[str, str]:
        """
        Validates refresh token, rotates keys (RTR), and returns new Access/Refresh tokens.
        If a reused/revoked refresh token is sent, detects replay attack and invalidates user session.
        """
        token_hash = hashlib.sha256(refresh_token_plain.encode("utf-8")).hexdigest()

        # 1. Resolve refresh token (Cache first, then MongoDB)
        cached_rtk = self.cache.get_refresh_token(token_hash)
        rtk = None
        if cached_rtk:
            try:
                rtk = RefreshToken.model_validate(cached_rtk)
            except Exception:
                pass

        if not rtk:
            rtk = await RefreshToken.find_one(RefreshToken.token_hash == token_hash)

        if not rtk:
            raise RefreshTokenInvalid("Invalid refresh token reference.")

        # 2. Replay Attack Detection
        if rtk.revoked:
            session_doc = await Session.find_one(Session.id == rtk.session_id)
            if session_doc:
                logger.warning(f"Replay attack detected for token '{rtk.token_id}'. Revoking all sessions for user {session_doc.user_id}.")
                await self.logout_all_sessions(session_doc.user_id)
            raise RefreshTokenInvalid("Replay attack identified. Session has been revoked.")

        if rtk.expires_at < datetime.utcnow():
            raise RefreshTokenExpired("Refresh token has expired.")

        # 3. Resolve Session
        session = await Session.find_one(Session.id == rtk.session_id)
        if not session:
            raise SessionNotFound("Session associated with refresh token was not found.")

        # 4. Check absolute & idle timeouts on Session
        try:
            session = await self.validate_session_activity(session.session_id)
        except SessionExpired as e:
            # Propagate expired details
            raise e

        # 5. Rotate Refresh Token: revoke old token
        rtk.revoked = True
        await rtk.save()
        self.cache.delete_refresh_token(token_hash)

        # 6. Issue new Refresh Token
        new_refresh_plain = secrets.token_hex(32)
        new_refresh_hash = hashlib.sha256(new_refresh_plain.encode("utf-8")).hexdigest()
        
        rtk_suffix = secrets.randbelow(900000) + 100000
        new_rtk_doc = RefreshToken(
            tokenId=f"RTK_{rtk_suffix}",
            sessionId=session.id,
            tokenHash=new_refresh_hash,
            expiresAt=rtk.expires_at, # keep same absolute window
            revoked=False
        )
        await new_rtk_doc.insert()

        # Cache new refresh token
        rtk_ttl = int((rtk.expires_at - datetime.utcnow()).total_seconds())
        if rtk_ttl > 0:
            self.cache.set_refresh_token(new_refresh_hash, new_rtk_doc.model_dump(by_alias=True), rtk_ttl)

        # 7. Resolve Roles and Permissions for new Access Token
        user = await User.find_one(User.id == session.user_id)
        if not user or user.status in (UserStatus.SUSPENDED, UserStatus.INACTIVE):
            raise SessionExpired("User account is disabled or deleted.")

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

        # 8. Encode new Access JWT
        iat = int(datetime.utcnow().timestamp())
        exp = iat + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        jwt_payload = {
            "sub": str(user.id),
            "userId": str(user.id),
            "organizationId": str(user.organization_id),
            "roles": role_slugs,
            "permissions": permissions,
            "sessionId": session.session_id,
            "type": "access",
            "iat": iat,
            "exp": exp,
            "iss": settings.APP_NAME,
            "aud": "campusos-api"
        }
        access_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        return access_token, new_refresh_plain

    async def validate_session_activity(self, session_id: str) -> Session:
        """
        Validates absolute and idle timeouts on a session.
        If active, updates last activity and returns it.
        """
        session = await self.session_repo.find_session_by_id(session_id)
        if not session:
            raise SessionNotFound("Session was not found.")

        now = datetime.utcnow()

        # 1. Absolute Expiration
        if session.expires_at <= now:
            await self.session_repo.revoke_session(session_id)
            raise SessionExpired("Session has expired.")

        # 2. Idle Expiration
        try:
            timeout_doc = await self.config_service.resolve_configuration(
                org_id_str=None, # resolve via tenant context defaults or global defaults
                key="security.sessions.idle_timeout_minutes",
                environment="PRODUCTION"
            )
            idle_mins = int(timeout_doc.get("value", 30))
        except Exception:
            idle_mins = 30

        if now - session.last_activity > timedelta(minutes=idle_mins):
            await self.session_repo.revoke_session(session_id)
            raise SessionExpired("Session has expired due to inactivity.")

        # 3. Update activity
        await self.session_repo.update_last_activity(session_id)
        return session

    async def logout_session(self, session_id: str) -> None:
        """Revokes a specific session."""
        await self.session_repo.revoke_session(session_id)

    async def logout_all_sessions(self, user_id: PydanticObjectId) -> None:
        """Revokes all sessions associated with a user."""
        await self.session_repo.revoke_all_user_sessions(user_id)

    async def _log_session_security_event(
        self,
        org_id: PydanticObjectId,
        user_id: PydanticObjectId,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> None:
        try:
            count = await SecurityEvent.find({}).count()
            event = SecurityEvent(
                securityEventId=f"SEC_{count + 1:06d}",
                organizationId=org_id,
                userId=user_id,
                type=event_type,
                severity=severity,
                metadata=metadata or {},
                ipAddress=ip_address
            )
            await event.insert()
        except Exception as e:
            logger.error(f"Failed to record session security event: {e}")
