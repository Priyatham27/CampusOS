import contextvars
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from fastapi import Request, Depends, HTTPException, status

from apps.api.app.models.identity.user import User, Profile
from apps.api.app.models.org_engine.organization import Organization
from apps.api.app.models.identity.session import Session, Device
from apps.api.app.core.auth_exceptions import InvalidToken

# Thread-safe ContextVar to hold the active request's IdentityContext
_current_identity_context: contextvars.ContextVar[Optional["IdentityContext"]] = contextvars.ContextVar(
    "current_identity_context", default=None
)

class IdentityContext(BaseModel):
    """
    Consolidated request-bound identity containing User, Organization, Profile,
    Active Session, mapped RBAC privileges, locale/timezone preferences, capabilities, and flags.
    """
    user: User
    organization: Organization
    profile: Optional[Profile] = None
    active_roles: List[str] = Field(default_factory=list, alias="activeRoles")
    active_session: Session = Field(..., alias="activeSession")
    device: Optional[Device] = None
    permissions: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    locale: str = "en"
    timezone: str = "UTC"
    feature_flags: Dict[str, bool] = Field(default_factory=dict, alias="featureFlags")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

def get_identity_context() -> Optional[IdentityContext]:
    """Retrieve IdentityContext from current thread environment."""
    return _current_identity_context.get()

def set_identity_context(context: IdentityContext) -> contextvars.Token:
    """Set IdentityContext in current thread environment."""
    return _current_identity_context.set(context)

def reset_identity_context(token: contextvars.Token) -> None:
    """Reset thread IdentityContext environment to its previous state."""
    _current_identity_context.reset(token)

async def get_current_identity(request: Request) -> IdentityContext:
    """FastAPI Router dependency injecting active IdentityContext context."""
    # Check request state populated by middleware
    context = getattr(request.state, "identity_context", None)
    if not context:
        # Check fallback to ContextVar
        context = get_identity_context()
    if not context:
        raise InvalidToken("Identity context is not initialized or invalid.")
    return context

def get_current_user(context: IdentityContext = Depends(get_current_identity)) -> User:
    """Dependency injection resolver returning the active User model."""
    return context.user

def get_current_organization(context: IdentityContext = Depends(get_current_identity)) -> Organization:
    """Dependency injection resolver returning the active Organization model."""
    return context.organization

def check_permission(required_permission: str):
    """Dependency resolver factory to enforce required RBAC permissions."""
    async def dependency(context: IdentityContext = Depends(get_current_identity)) -> User:
        if "SuperAdmin" in context.active_roles or "super-admin" in context.active_roles or "admin" in context.active_roles:
            return context.user
        if required_permission not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required privilege: {required_permission}"
            )
        return context.user
    return dependency

def check_role(required_role: str):
    """Dependency resolver factory to enforce required roles."""
    async def dependency(context: IdentityContext = Depends(get_current_identity)) -> User:
        if "SuperAdmin" in context.active_roles or "super-admin" in context.active_roles:
            return context.user
        if required_role not in context.active_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return context.user
    return dependency
