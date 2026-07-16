import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from beanie import PydanticObjectId

from app.models.identity.user import User, UserStatus
from app.models.identity.credential import Credential, CredentialType
from app.models.identity.security import (
    SecurityEvent,
    SecurityEventType,
    SecurityEventSeverity,
    PasswordResetToken,
    EmailVerificationToken
)
from app.repositories.credential import CredentialRepository
from app.services.config import ConfigurationService
from app.core.security import hash_password_argon2, verify_password_argon2
from app.core.credential_exceptions import (
    CredentialException,
    CredentialNotFound,
    CredentialAlreadyExists,
    InvalidPassword,
    PasswordPolicyViolation,
    CredentialLocked,
    EmailNotVerified
)
from app.validators.credential import (
    get_password_policy,
    validate_password_strength,
    validate_password_reuse
)

logger = logging.getLogger("campusos.credential")

class CredentialService:
    """
    Credential Lifecycle Service for CampusOS.
    Implements Argon2id password management, history checks, and account lockouts.
    """
    def __init__(self):
        self.cred_repo = CredentialRepository()
        self.config_service = ConfigurationService()

    async def _resolve_user(self, user_id_str: str) -> User:
        """Helper to resolve active User document."""
        user = None
        try:
            obj_id = PydanticObjectId(user_id_str)
            user = await User.find_one(User.id == obj_id, User.is_deleted == False)
        except Exception:
            pass

        if not user:
            user = await User.find_one(User.user_id == user_id_str, User.is_deleted == False)

        if not user:
            raise CredentialException("User account not found.")
        return user

    async def _log_security_event(
        self,
        org_id: PydanticObjectId,
        user_id: PydanticObjectId,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> SecurityEvent:
        """Logs a critical identity security event in the database."""
        try:
            count = await SecurityEvent.find({}).count()
            event_id = f"SEC_{count + 1:06d}"
            
            event = SecurityEvent(
                securityEventId=event_id,
                organizationId=org_id,
                userId=user_id,
                type=event_type,
                severity=severity,
                metadata=metadata or {},
                ipAddress=ip_address
            )
            await event.insert()
            return event
        except Exception as e:
            logger.error(f"Failed to record security event: {e}")

    async def create_credential(
        self,
        user_id_str: str,
        password: str,
        cred_type: CredentialType = CredentialType.PASSWORD,
        ip_address: Optional[str] = None
    ) -> Credential:
        """
        Creates a new authentication credential for a user.
        Validates email verification state and password complexity.
        """
        user = await self._resolve_user(user_id_str)
        
        # Verify email is active/verified before enabling credential
        if not user.email_verified:
            raise EmailNotVerified("Email must be verified before credential activation.")

        # Check for existing credential of the same type
        existing = await self.cred_repo.find_by_user_id(user.id, cred_type)
        if existing:
            raise CredentialAlreadyExists(f"Credential of type {cred_type.value} already exists for this user.")

        # If password, validate policy and hash it
        pw_hash = None
        pw_history = []
        if cred_type == CredentialType.PASSWORD:
            policy = await get_password_policy(str(user.organization_id), self.config_service)
            validate_password_strength(password, policy)
            pw_hash = hash_password_argon2(password)
            pw_history.append(pw_hash)

        count = await Credential.find({}).count()
        cred_id = f"CRD_{count + 1:06d}"

        credential = Credential(
            credentialId=cred_id,
            userId=user.id,
            organizationId=user.organization_id,
            type=cred_type,
            passwordHash=pw_hash,
            passwordHistory=pw_history,
            passwordChangedAt=datetime.utcnow() if pw_hash else None,
            requiresPasswordChange=False
        )

        res = await self.cred_repo.create(credential)
        
        await self._log_security_event(
            org_id=user.organization_id,
            user_id=user.id,
            event_type=SecurityEventType.PASSWORD_CHANGED,
            severity=SecurityEventSeverity.INFO,
            metadata={"message": "Credential container initialized successfully."},
            ip_address=ip_address
        )
        logger.info(f"Credential '{cred_id}' initialized for user '{user.user_id}'.")
        return res

    async def get_credential_by_user(self, user_id_str: str) -> Credential:
        """Retrieves a user's credential. Raises error if not found."""
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("No credential found for this user.")
        return cred

    async def change_password(
        self,
        user_id_str: str,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> Credential:
        """
        Validates existing password and changes it to the new password.
        Increments failed login attempts and schedules lockouts on mismatch.
        """
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("Credential not found.")

        # Check lock status
        if cred.is_locked:
            if cred.locked_until and datetime.utcnow() < cred.locked_until:
                raise CredentialLocked(f"Account is locked until {cred.locked_until.isoformat()}.")
            else:
                # Lockout time has expired
                cred.is_locked = False
                cred.locked_until = None
                cred.failed_login_attempts = 0

        # Verify current password
        if not cred.password_hash or not verify_password_argon2(current_password, cred.password_hash):
            cred.failed_login_attempts += 1
            policy = await get_password_policy(str(user.organization_id), self.config_service)
            max_failed = policy.get("password_max_failed_attempts", 5)
            lock_duration = policy.get("password_lockout_duration_minutes", 15)

            if cred.failed_login_attempts >= max_failed:
                cred.is_locked = True
                cred.locked_until = datetime.utcnow() + timedelta(minutes=lock_duration)
                await cred.save()
                await self._log_security_event(
                    org_id=user.organization_id,
                    user_id=user.id,
                    event_type=SecurityEventType.ACCOUNT_LOCKED,
                    severity=SecurityEventSeverity.HIGH,
                    metadata={"reason": f"Brute force protection. Failed attempts: {cred.failed_login_attempts}."},
                    ip_address=ip_address
                )
                raise CredentialLocked(f"Account locked due to {cred.failed_login_attempts} failed attempts.")
            else:
                await cred.save()
                raise InvalidPassword("Incorrect current password.")

        # Successful verification: change password
        policy = await get_password_policy(str(user.organization_id), self.config_service)
        validate_password_strength(new_password, policy)
        validate_password_reuse(new_password, cred.password_history)

        new_hash = hash_password_argon2(new_password)
        cred.password_history.append(new_hash)
        
        # Keep last 5 hashes in history
        if len(cred.password_history) > 5:
            cred.password_history = cred.password_history[-5:]

        cred.password_hash = new_hash
        cred.password_changed_at = datetime.utcnow()
        cred.failed_login_attempts = 0
        cred.is_locked = False
        cred.locked_until = None
        cred.requires_password_change = False

        await cred.save()

        await self._log_security_event(
            org_id=user.organization_id,
            user_id=user.id,
            event_type=SecurityEventType.PASSWORD_CHANGED,
            severity=SecurityEventSeverity.HIGH,
            metadata={"message": "Password changed successfully via user profile request."},
            ip_address=ip_address
        )
        return cred

    async def verify_password(
        self,
        user_id_str: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Verifies a user's password using the Argon2id hashing algorithms.
        Manages failed login attempts and lockout thresholds internally.
        """
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("Credential not found.")

        # Check lock status
        if cred.is_locked:
            if cred.locked_until and datetime.utcnow() < cred.locked_until:
                raise CredentialLocked(f"Account is locked until {cred.locked_until.isoformat()}.")
            else:
                # Lockout time has expired
                cred.is_locked = False
                cred.locked_until = None
                cred.failed_login_attempts = 0

        if not cred.password_hash or not verify_password_argon2(password, cred.password_hash):
            cred.failed_login_attempts += 1
            policy = await get_password_policy(str(user.organization_id), self.config_service)
            max_failed = policy.get("password_max_failed_attempts", 5)
            lock_duration = policy.get("password_lockout_duration_minutes", 15)

            if cred.failed_login_attempts >= max_failed:
                cred.is_locked = True
                cred.locked_until = datetime.utcnow() + timedelta(minutes=lock_duration)
                await cred.save()
                await self._log_security_event(
                    org_id=user.organization_id,
                    user_id=user.id,
                    event_type=SecurityEventType.ACCOUNT_LOCKED,
                    severity=SecurityEventSeverity.HIGH,
                    metadata={"reason": f"Brute force protection. Failed attempts: {cred.failed_login_attempts}."},
                    ip_address=ip_address
                )
                raise CredentialLocked(f"Account locked due to {cred.failed_login_attempts} failed attempts.")
            else:
                await cred.save()
                return False

        # Reset failed attempts on success
        if cred.failed_login_attempts > 0 or cred.is_locked:
            cred.failed_login_attempts = 0
            cred.is_locked = False
            cred.locked_until = None
            await cred.save()

        return True

    async def verify_email_token(self, user_id_str: str, token: str) -> bool:
        """Verifies the email verification token and activates the user account."""
        user = await self._resolve_user(user_id_str)
        
        # Hash the input token
        hashed_input = hashlib.sha256(token.encode('utf-8')).hexdigest()
        
        # Find token
        evt = await EmailVerificationToken.find_one(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.verified == False,
            EmailVerificationToken.expires_at > datetime.utcnow()
        )
        
        if not evt or (evt.token_hash != token and evt.token_hash != hashed_input):
            raise CredentialException("Invalid or expired email verification token.")
            
        # Mark token verified
        evt.verified = True
        await evt.save()
        
        # Update user verified status
        user.email_verified = True
        await user.save()
        
        return True

    async def reset_password(

        self,
        user_id_str: str,
        token: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> Credential:
        """
        Resets a user's password using a valid, unused password reset token.
        """
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("Credential not found.")

        # Find active reset token
        hashed_input_token = hashlib.sha256(token.encode("utf-8")).hexdigest()
        reset_token = await PasswordResetToken.find_one(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        )

        # Check matches (direct or hashed match for compatibility)
        if not reset_token or (reset_token.token_hash != token and reset_token.token_hash != hashed_input_token):
            raise CredentialException("Invalid or expired password reset token.")

        # Process reset
        policy = await get_password_policy(str(user.organization_id), self.config_service)
        validate_password_strength(new_password, policy)
        validate_password_reuse(new_password, cred.password_history)

        # Mark token used
        reset_token.used = True
        await reset_token.save()

        new_hash = hash_password_argon2(new_password)
        cred.password_history.append(new_hash)
        if len(cred.password_history) > 5:
            cred.password_history = cred.password_history[-5:]

        cred.password_hash = new_hash
        cred.password_changed_at = datetime.utcnow()
        cred.failed_login_attempts = 0
        cred.is_locked = False
        cred.locked_until = None
        cred.requires_password_change = False

        await cred.save()

        await self._log_security_event(
            org_id=user.organization_id,
            user_id=user.id,
            event_type=SecurityEventType.PASSWORD_CHANGED,
            severity=SecurityEventSeverity.HIGH,
            metadata={"message": "Password reset completed successfully via token."},
            ip_address=ip_address
        )
        return cred

    async def force_password_reset(
        self,
        user_id_str: str,
        new_password: str,
        ip_address: Optional[str] = None
    ) -> Credential:
        """
        Administrative force-reset updates password and flags it for next change.
        """
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("Credential not found.")

        policy = await get_password_policy(str(user.organization_id), self.config_service)
        validate_password_strength(new_password, policy)
        validate_password_reuse(new_password, cred.password_history)

        new_hash = hash_password_argon2(new_password)
        cred.password_history.append(new_hash)
        if len(cred.password_history) > 5:
            cred.password_history = cred.password_history[-5:]

        cred.password_hash = new_hash
        cred.password_changed_at = datetime.utcnow()
        cred.failed_login_attempts = 0
        cred.is_locked = False
        cred.locked_until = None
        cred.requires_password_change = True  # Mandatory change flag

        await cred.save()

        await self._log_security_event(
            org_id=user.organization_id,
            user_id=user.id,
            event_type=SecurityEventType.PASSWORD_CHANGED,
            severity=SecurityEventSeverity.HIGH,
            metadata={"message": "Administrative password force-reset executed."},
            ip_address=ip_address
        )
        return cred

    async def update_credential_fields(self, user_id_str: str, update_data: dict) -> Credential:
        """Updates generic credential metadata and fields."""
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("Credential not found.")
        return await self.cred_repo.update(cred, update_data)

    async def trigger_email_verification(self, user_id_str: str) -> EmailVerificationToken:
        """
        Generates and stores an email verification token for the user.
        """
        user = await self._resolve_user(user_id_str)
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        
        count = await EmailVerificationToken.find({}).count()
        token_id = f"EVT_{count + 1:06d}"
        
        evt = EmailVerificationToken(
            verificationTokenId=token_id,
            userId=user.id,
            tokenHash=token_hash,
            expiresAt=datetime.utcnow() + timedelta(hours=24),
            verified=False
        )
        await evt.insert()
        
        await self._log_security_event(
            org_id=user.organization_id,
            user_id=user.id,
            event_type=SecurityEventType.EMAIL_VERIFIED,
            severity=SecurityEventSeverity.INFO,
            metadata={"message": f"Email verification trigger initiated: {token_id}"}
        )
        logger.info(f"Verification token generated for user '{user_id_str}': {token_id}")
        return evt

    async def validate_credential_status(self, user_id_str: str) -> Dict[str, Any]:
        """
        Checks current status of a credential: locks, expiration, pending changes.
        """
        user = await self._resolve_user(user_id_str)
        cred = await self.cred_repo.find_by_user_id(user.id)
        if not cred:
            raise CredentialNotFound("No credential found for this user.")

        # Check account status
        if user.status == UserStatus.SUSPENDED:
            raise CredentialException("User account is suspended.")
        elif user.status == UserStatus.INACTIVE:
            raise CredentialException("User account is inactive.")

        # Check lock status
        if cred.is_locked:
            if cred.locked_until and datetime.utcnow() < cred.locked_until:
                raise CredentialLocked(f"Account is locked until {cred.locked_until.isoformat()}.")
            else:
                cred.is_locked = False
                cred.locked_until = None
                cred.failed_login_attempts = 0
                await cred.save()

        # Check password expiration policy
        policy = await get_password_policy(str(user.organization_id), self.config_service)
        expiration_days = policy.get("password_expiration_days", 90)
        
        password_expired = False
        if cred.password_changed_at:
            age = datetime.utcnow() - cred.password_changed_at
            if age.days >= expiration_days:
                password_expired = True

        return {
            "valid": True,
            "requiresPasswordChange": cred.requires_password_change or password_expired,
            "passwordExpired": password_expired,
            "failedLoginAttempts": cred.failed_login_attempts
        }

def get_credential_service() -> CredentialService:
    return CredentialService()
