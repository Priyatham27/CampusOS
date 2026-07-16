from typing import Optional
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, EmailStr, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class Device(BaseDocument):
    device_id: str = Field(..., alias="deviceId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    device_name: str = Field(..., alias="deviceName", min_length=2, max_length=100)
    browser: Optional[str] = Field(default=None, max_length=50)
    os: Optional[str] = Field(default=None, max_length=50)
    platform: Optional[str] = Field(default=None, max_length=50)
    trusted: bool = Field(default=False)
    last_login: datetime = Field(default_factory=datetime.utcnow, alias="lastLogin")

    @field_validator("device_id")
    @classmethod
    def validate_dev_id(cls, v: str) -> str:
        return validate_professional_id(v, "DEV")

    class Settings:
        name = "devices"
        indexes = [
            IndexModel("deviceId", unique=True),
            IndexModel("userId"),
            IndexModel([("userId", 1), ("deviceName", 1)], unique=True),
        ]

class Session(BaseDocument):
    session_id: str = Field(..., alias="sessionId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    device_id: Optional[str] = Field(default=None, alias="deviceId") # references Device.device_id
    ip_address: str = Field(..., alias="ipAddress", max_length=45) # supports IPv4 & IPv6
    browser: Optional[str] = Field(default=None, max_length=50)
    platform: Optional[str] = Field(default=None, max_length=50)
    user_agent: str = Field(..., alias="userAgent", max_length=500)
    expires_at: datetime = Field(..., alias="expiresAt")
    last_activity: datetime = Field(default_factory=datetime.utcnow, alias="lastActivity")

    @field_validator("session_id")
    @classmethod
    def validate_ses_id(cls, v: str) -> str:
        return validate_professional_id(v, "SES")

    class Settings:
        name = "sessions"
        indexes = [
            IndexModel("sessionId", unique=True),
            IndexModel("userId"),
            IndexModel("expiresAt"), # TTL Index candidate (expiresAt can be managed by app or MongoDB TTL)
        ]

class RefreshToken(BaseDocument):
    token_id: str = Field(..., alias="tokenId")
    session_id: PydanticObjectId = Field(..., alias="sessionId")
    token_hash: str = Field(..., alias="tokenHash")
    expires_at: datetime = Field(..., alias="expiresAt")
    revoked: bool = Field(default=False)

    @field_validator("token_id")
    @classmethod
    def validate_rtk_id(cls, v: str) -> str:
        return validate_professional_id(v, "RTK")

    class Settings:
        name = "refresh_tokens"
        indexes = [
            IndexModel("tokenId", unique=True),
            IndexModel("sessionId"),
            IndexModel("tokenHash", unique=True),
        ]

class OAuthAccount(BaseDocument):
    oauth_account_id: str = Field(default_factory=lambda: "OAUTH_000000", alias="oauthAccountId")
    user_id: PydanticObjectId = Field(..., alias="userId")
    provider: str = Field(..., min_length=2, max_length=30)     # e.g., "google", "microsoft", "github"
    provider_user_id: str = Field(..., alias="providerUserId", min_length=2, max_length=100)
    provider_email: Optional[EmailStr] = Field(default=None, alias="providerEmail")

    @field_validator("oauth_account_id")
    @classmethod
    def validate_oauth_id(cls, v: str) -> str:
        if v == "OAUTH_000000":
            return v
        return validate_professional_id(v, "OAUTH")

    class Settings:
        name = "oauth_accounts"
        indexes = [
            IndexModel("oauthAccountId", unique=True),
            IndexModel([("provider", 1), ("providerUserId", 1)], unique=True),
            IndexModel("userId"),
        ]
