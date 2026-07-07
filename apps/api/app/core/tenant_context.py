import contextvars
from typing import Optional

# Thread-safe ContextVar to hold the active tenant ID
_current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)

def get_tenant_id() -> Optional[str]:
    """Retrieve the active tenant ID from the current async thread context."""
    return _current_tenant_id.get()

def set_tenant_id(tenant_id: Optional[str]) -> contextvars.Token:
    """Set the active tenant ID inside the current async thread context."""
    return _current_tenant_id.set(tenant_id)

def reset_tenant_id(token: contextvars.Token) -> None:
    """Reset the tenant ID context back to its previous state."""
    _current_tenant_id.reset(token)
