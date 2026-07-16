from typing import Optional, List
from pymongo import IndexModel
from pydantic import Field, field_validator
from beanie import PydanticObjectId

from app.models.base import BaseDocument
from app.models.org_engine.organization import validate_professional_id

class Policy(BaseDocument):
    policy_id: str = Field(..., alias="policyId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=250)
    effect: str = Field(..., min_length=4, max_length=5) # "ALLOW" or "DENY"
    priority: int = Field(default=10, ge=0, le=100)
    subjects: List[str] = Field(default_factory=list) # User IDs or Role slugs, or ["*"]
    actions: List[str] = Field(default_factory=list)  # Permission slugs, e.g. ["events.create"] or ["*"]
    resources: List[str] = Field(default_factory=list) # Target scopes, e.g. ["*"]
    conditions: Optional[dict] = Field(default=None) # Dynamic conditions (e.g. time range, department list)
    is_active: bool = Field(default=True, alias="isActive")
    is_system: bool = Field(default=False, alias="isSystem")

    @field_validator("policy_id")
    @classmethod
    def validate_pol_id(cls, v: str) -> str:
        return validate_professional_id(v, "POL")

    @field_validator("effect")
    @classmethod
    def validate_pol_effect(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ("ALLOW", "DENY"):
            raise ValueError("Policy effect must be 'ALLOW' or 'DENY'.")
        return v_upper

    class Settings:
        name = "policies"
        indexes = [
            IndexModel("policyId", unique=True),
            IndexModel("organizationId"),
            IndexModel("isActive"),
        ]
