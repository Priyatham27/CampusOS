from typing import Optional, List
from datetime import datetime
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class APIKey(BaseDocument):
    key_id: str = Field(..., alias="keyId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=100)
    key_hash: str = Field(..., alias="keyHash")
    scopes: List[str] = Field(default_factory=list)              # M2M integration permission scopes
    expires_at: Optional[datetime] = Field(default=None, alias="expiresAt")
    revoked: bool = Field(default=False)
    last_used: Optional[datetime] = Field(default=None, alias="lastUsed")

    @field_validator("key_id")
    @classmethod
    def validate_aky_id(cls, v: str) -> str:
        return validate_professional_id(v, "AKY")

    class Settings:
        name = "api_keys"
        indexes = [
            IndexModel("keyId", unique=True),
            IndexModel("keyHash", unique=True),
            IndexModel("organizationId"),
        ]
