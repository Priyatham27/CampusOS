from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId

schema_config = ConfigDict(
    populate_by_name=True,
    from_attributes=True,
    use_enum_values=True
)

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    slug: str = Field(..., min_length=2, max_length=50)
    priority: int = Field(default=10, ge=0, le=100)
    description: Optional[str] = Field(default=None, max_length=250)
    model_config = schema_config

class RoleResponse(BaseModel):
    role_id: str = Field(..., alias="roleId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str
    slug: str
    priority: int
    system_role: bool = Field(..., alias="systemRole")
    description: Optional[str] = None
    model_config = schema_config

class RoleUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    priority: int = Field(..., ge=0, le=100)
    description: Optional[str] = Field(default=None, max_length=250)
    model_config = schema_config

class PermissionCreate(BaseModel):
    module: str = Field(..., min_length=2, max_length=50)
    resource: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=20)
    slug: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, max_length=250)
    model_config = schema_config

class PermissionResponse(BaseModel):
    permission_id: str = Field(..., alias="permissionId")
    module: str
    resource: str
    action: str
    slug: str
    description: Optional[str] = None
    model_config = schema_config

class PermissionUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=250)
    model_config = schema_config

class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    effect: str = Field(..., min_length=5, max_length=5) # ALLOW or DENY
    priority: int = Field(default=10, ge=0, le=100)
    subjects: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    resources: List[str] = Field(default_factory=list)
    conditions: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(default=None, max_length=250)
    model_config = schema_config

class PolicyResponse(BaseModel):
    policy_id: str = Field(..., alias="policyId")
    organization_id: PydanticObjectId = Field(..., alias="organizationId")
    name: str
    description: Optional[str] = None
    effect: str
    priority: int
    subjects: List[str]
    actions: List[str]
    resources: List[str]
    conditions: Optional[Dict[str, Any]] = None
    is_active: bool = Field(..., alias="isActive")
    is_system: bool = Field(..., alias="isSystem")
    model_config = schema_config

class PolicyUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    effect: str = Field(..., min_length=5, max_length=5)
    priority: int = Field(..., ge=0, le=100)
    subjects: List[str]
    actions: List[str]
    resources: List[str]
    conditions: Optional[Dict[str, Any]] = None
    description: Optional[str] = Field(default=None, max_length=250)
    is_active: bool = Field(..., alias="isActive")
    model_config = schema_config

class RolePermissionAssign(BaseModel):
    permission_id: str = Field(..., alias="permissionId")
    model_config = schema_config
