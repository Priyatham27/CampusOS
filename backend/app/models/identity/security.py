from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class SecurityEventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecurityEventType(str, Enum):
    BRUTE_FORCE_ATTEMPT = "BRUTE_FORCE_ATTEMPT"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    MFA_FAILED = "MFA_FAILED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    SUSPICIOUS_IP = "SUSPICIOUS_IP"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"

class LoginStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    LOCKED = "LOCKED"

class PasswordResetToken(BaseDocument):
    reset_token_id: str = Field(..., alias="resetTokenId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    token_hash: str = Field(..., alias="tokenHash")
    expires_at: datetime = Field(..., alias="expiresAt")
    used: bool = Field(default=False)

    @field_validator("reset_token_id")
    @classmethod
    def validate_prt_id(cls, v: str) -> str:
        return validate_professional_id(v, "PRT")

    class Settings:
        name = "password_reset_tokens"
        indexes = [
            IndexModel("resetTokenId", unique=True),
            IndexModel("tokenHash", unique=True),
            IndexModel("userId"),
        ]

class EmailVerificationToken(BaseDocument):
    verification_token_id: str = Field(..., alias="verificationTokenId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    token_hash: str = Field(..., alias="tokenHash")
    expires_at: datetime = Field(..., alias="expiresAt")
    verified: bool = Field(default=False)

    @field_validator("verification_token_id")
    @classmethod
    def validate_evt_id(cls, v: str) -> str:
        return validate_professional_id(v, "EVT")

    class Settings:
        name = "email_verification_tokens"
        indexes = [
            IndexModel("verificationTokenId", unique=True),
            IndexModel("tokenHash", unique=True),
            IndexModel("userId"),
        ]

class LoginHistory(BaseDocument):
    login_history_id: str = Field(..., alias="loginHistoryId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    login_time: datetime = Field(default_factory=datetime.utcnow, alias="loginTime")
    logout_time: Optional[datetime] = Field(default=None, alias="logoutTime")
    ip_address: str = Field(..., alias="ipAddress", max_length=45)
    browser: Optional[str] = Field(default=None, max_length=50)
    platform: Optional[str] = Field(default=None, max_length=50)
    status: LoginStatus = Field(default=LoginStatus.SUCCESS)

    @field_validator("login_history_id")
    @classmethod
    def validate_lgh_id(cls, v: str) -> str:
        return validate_professional_id(v, "LGH")

    class Settings:
        name = "login_histories"
        indexes = [
            IndexModel("loginHistoryId", unique=True),
            IndexModel("userId"),
            IndexModel("loginTime"),
        ]

class SecurityEvent(BaseDocument):
    security_event_id: str = Field(..., alias="securityEventId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    user_id: Optional[PydanticObjectId] = Field(default=None, alias="userId")
    type: SecurityEventType = Field(...)
    severity: SecurityEventSeverity = Field(default=SecurityEventSeverity.INFO)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = Field(default=None, alias="ipAddress", max_length=45)

    @field_validator("security_event_id")
    @classmethod
    def validate_sec_id(cls, v: str) -> str:
        return validate_professional_id(v, "SEC")

    class Settings:
        name = "security_events"
        indexes = [
            IndexModel("securityEventId", unique=True),
            IndexModel("organizationId"),
            IndexModel("userId"),
            IndexModel("type"),
            IndexModel("severity"),
        ]
