import secrets
import hashlib
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from beanie import PydanticObjectId

from apps.api.app.core.config import settings
from apps.api.app.core.database import get_db
from apps.api.app.models.identity.user import User, UserStatus
from apps.api.app.models.identity.security import SecurityEvent, SecurityEventType, SecurityEventSeverity
from apps.api.app.models.identity.session import Session, RefreshToken
from apps.api.app.models.models import generate_prefixed_id
from apps.api.app.repositories.authentication import AuthenticationRepository
from apps.api.app.services.credential import CredentialService, get_credential_service
from apps.api.app.services.auth_providers import PasswordAuthenticationProvider
from apps.api.app.core.security import verify_password_argon2
from apps.api.app.core.auth_exceptions import (
    AuthenticationException,
    AuthenticationFailed,
    AccountLocked,
    AccountDisabled,
    OrganizationNotFound,
    CredentialNotFound,
    EmailNotVerified,
    InvalidToken
)

logger = logging.getLogger("campusos.authentication")

class AuthenticationService:
    """
    Central user authentication logic for CampusOS.
    Implements multi-tenant checks, strategy providers, and secure token issuance.
    """
    def __init__(self):
        self.auth_repo = AuthenticationRepository()
        self.credential_service = get_credential_service()
        # Strategy Pattern: register authentication providers
        self.providers = {
            "password": PasswordAuthenticationProvider(self.credential_service)
        }

    async def login(
        self,
        org_id_str: str,
        payload: Dict[str, Any],
        user_agent: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticates a user, verifies status and email, and issues tokens and session records.
        Uses a timing-safe path for invalid user lookups to prevent enumeration attacks.
        """
        # 1. Resolve Organization
        try:
            org_id = PydanticObjectId(org_id_str)
            org = await self.auth_repo.find_org_by_id(org_id)
        except Exception:
            org = await self.auth_repo.find_org_by_slug(org_id_str)

        if not org:
            raise OrganizationNotFound("Requested organization is not registered.")

        # 2. Locate User (timing-safe fallback to prevent username/email enumeration)
        user = None
        email = payload.get("email")
        username = payload.get("username")
        
        if email:
            user = await self.auth_repo.find_user_by_email(email, org.id)
        elif username:
            user = await self.auth_repo.find_user_by_username(username, org.id)

        if not user:
            # Fake verifying process to mask response time
            verify_password_argon2("dummy", "$argon2id$v=19$m=16384,t=2,p=1$ZHVtbXlzYWx0$ZHVtbXloYXNo")
            raise AuthenticationFailed()

        # 3. Check Account Status
        if user.status in (UserStatus.SUSPENDED, UserStatus.INACTIVE):
            raise AccountDisabled("This user account is inactive or has been suspended.")

        # 4. Check Email Verification Status (resolves policy configuration)
        try:
            policy = await self.credential_service.config_service.resolve_configuration(
                org_id_str=str(org.id),
                key="security.auth.require_email_verification",
                environment="PRODUCTION"
            )
            require_verification = bool(policy.get("value", True))
        except Exception:
            require_verification = True

        if require_verification and not user.email_verified:
            # Publish failed login event
            await self._log_auth_audit(org.id, user, "email_verification_failure", ip_address)
            raise EmailNotVerified("Email verification is required before logging in.")

        # 5. Authenticate via selected Provider
        provider_name = payload.get("provider", "password")
        provider = self.providers.get(provider_name)
        if not provider:
            raise AuthenticationFailed("Unsupported authentication provider.")

        try:
            success = await provider.authenticate(user, payload, ip_address)
        except Exception as e:
            # Re-raise locked or other domain errors cleanly
            if "locked" in str(e).lower():
                await self._log_auth_audit(org.id, user, "locked_account_attempt", ip_address)
                raise AccountLocked("This account is temporarily locked.")
            raise e

        if not success:
            await self._log_auth_audit(org.id, user, "failed_login", ip_address)
            raise AuthenticationFailed()

        # 6. Resolve User RBAC Roles and Permissions
        roles = await self.auth_repo.find_user_roles(user.id)
        role_slugs = [r.slug for r in roles]
        permissions = await self.auth_repo.find_role_permissions([r.id for r in roles])
        permission_slugs = [p.slug for p in permissions]

        # 7. Issue Session & Refresh Token references in DB
        session_count = await Session.find({}).count()
        session_id_str = f"SES_{session_count + 1:06d}"
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        session_doc = Session(
            sessionId=session_id_str,
            userId=user.id,
            ipAddress=ip_address or "127.0.0.1",
            userAgent=user_agent,
            expiresAt=expires_at
        )
        await session_doc.insert()

        refresh_token_plain = secrets.token_hex(32)
        refresh_token_hash = hashlib.sha256(refresh_token_plain.encode("utf-8")).hexdigest()
        
        rtk_count = await RefreshToken.find({}).count()
        rtk_doc = RefreshToken(
            tokenId=f"RTK_{rtk_count + 1:06d}",
            sessionId=session_doc.id,
            tokenHash=refresh_token_hash,
            expiresAt=expires_at
        )
        await rtk_doc.insert()

        # 8. Encode Access JWT
        iat = int(datetime.utcnow().timestamp())
        exp = iat + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        jwt_payload = {
            "sub": str(user.id),
            "userId": str(user.id),
            "organizationId": str(org.id),
            "roles": role_slugs,
            "permissions": permission_slugs,
            "sessionId": session_id_str,
            "type": "access",
            "iat": iat,
            "exp": exp,
            "iss": settings.APP_NAME,
            "aud": "campusos-api"
        }
        access_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # 9. Audit Event Logging
        await self._log_auth_audit(org.id, user, "successful_login", ip_address)
        logger.info(f"Successful authentication for user '{user.email}'. Token issued.")

        return {
            "accessToken": access_token,
            "refreshToken": refresh_token_plain,
            "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user
        }

    async def refresh_access_token(self, refresh_token_plain: str) -> Dict[str, Any]:
        """
        Validates refresh token reference in DB and issues a new access token.
        """
        hashed_token = hashlib.sha256(refresh_token_plain.encode("utf-8")).hexdigest()
        
        # Locate refresh token record
        rtk = await RefreshToken.find_one(
            RefreshToken.token_hash == hashed_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        if not rtk:
            raise InvalidToken("Invalid or expired refresh token.")

        # Locate associated session
        session_doc = await Session.find_one(Session.id == rtk.session_id)
        if not session_doc or session_doc.expires_at < datetime.utcnow():
            raise InvalidToken("Session associated with refresh token is invalid or expired.")

        # Locate User
        user = await User.find_one(User.id == session_doc.user_id, User.is_deleted == False)
        if not user or user.status in (UserStatus.SUSPENDED, UserStatus.INACTIVE):
            raise AccountDisabled("User account is inactive or disabled.")

        # Resolve Roles and Permissions
        roles = await self.auth_repo.find_user_roles(user.id)
        role_slugs = [r.slug for r in roles]
        permissions = await self.auth_repo.find_role_permissions([r.id for r in roles])
        permission_slugs = [p.slug for p in permissions]

        # Issue new Access Token (preserving the active Session)
        iat = int(datetime.utcnow().timestamp())
        exp = iat + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        jwt_payload = {
            "sub": str(user.id),
            "userId": str(user.id),
            "organizationId": str(user.organization_id),
            "roles": role_slugs,
            "permissions": permission_slugs,
            "sessionId": session_doc.session_id,
            "type": "access",
            "iat": iat,
            "exp": exp,
            "iss": settings.APP_NAME,
            "aud": "campusos-api"
        }
        access_token = jwt.encode(jwt_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        return {
            "accessToken": access_token,
            "refreshToken": refresh_token_plain,
            "expiresIn": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user
        }


    async def logout(self, session_id_str: str, ip_address: Optional[str] = None) -> None:
        """
        Terminates authentication session and revokes the associated refresh tokens.
        """
        session_doc = await Session.find_one(Session.session_id == session_id_str)
        if not session_doc:
            return

        # Fetch user details for auditing
        user = await User.find_one(User.id == session_doc.user_id)
        
        # Revoke all tokens linked to this session
        await RefreshToken.find(RefreshToken.session_id == session_doc.id).update({"$set": {"revoked": True}})
        await session_doc.delete()

        if user:
            await self._log_auth_audit(user.organization_id, user, "user_logout", ip_address)
            logger.info(f"User '{user.email}' logged out successfully.")

    async def verify_email(self, user_id_str: str, token: str) -> None:
        """Verifies the email verification token via CredentialService."""
        await self.credential_service.verify_email_token(user_id_str, token)

    async def _log_auth_audit(
        self,
        org_id: PydanticObjectId,
        user: User,
        action: str,
        ip_address: Optional[str] = None
    ) -> None:
        """Writes audit logs and SecurityEvent documents for login outcomes."""
        try:
            db = get_db()
            await db["audit_logs"].insert_one({
                "_id": generate_prefixed_id("aud"),
                "tenant_id": str(org_id),
                "user_id": str(user.id),
                "user_email": user.email,
                "action": action,
                "category": "security",
                "details": {"message": f"Auth action: {action}"},
                "ip_address": ip_address,
                "created_at": datetime.utcnow()
            })
            
            # Map action type to SecurityEventType
            event_type = None
            severity = SecurityEventSeverity.INFO
            if action == "locked_account_attempt":
                event_type = SecurityEventType.ACCOUNT_LOCKED
                severity = SecurityEventSeverity.HIGH
            elif action == "failed_login":
                event_type = SecurityEventType.BRUTE_FORCE_ATTEMPT
                severity = SecurityEventSeverity.WARNING
            elif action == "successful_login":
                # INFO login event
                pass

            if event_type:
                count = await SecurityEvent.find({}).count()
                event = SecurityEvent(
                    securityEventId=f"SEC_{count + 1:06d}",
                    organizationId=org_id,
                    userId=user.id,
                    type=event_type,
                    severity=severity,
                    metadata={"message": f"Auth audit event trigger: {action}."},
                    ipAddress=ip_address
                )
                await event.insert()
        except Exception as e:
            logger.error(f"Error writing auth audit log: {e}")

def get_authentication_service() -> AuthenticationService:
    return AuthenticationService()
