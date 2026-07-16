from functools import wraps
from typing import List, Callable, Any, Optional
from datetime import datetime

from apps.api.app.core.identity_context import get_identity_context
from apps.api.app.core.permission_evaluator import PermissionEvaluator
from apps.api.app.core.authorization_exceptions import AuthorizationDenied

def require_permission(permission: str) -> Callable[..., Any]:
    """
    Python decorator that checks if the active IdentityContext user has
    the requested permission.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = get_identity_context()
            if not context:
                raise AuthorizationDenied("Access denied. No active identity context resolved.")

            evaluator = PermissionEvaluator()
            allowed = await evaluator.evaluate(
                user=context.user,
                org=context.organization,
                active_roles=context.active_roles,
                permission=permission,
                context_data={
                    "time": datetime.utcnow().time().strftime("%H:%M"),
                    "department": getattr(context.user, "department", None)
                }
            )
            if not allowed:
                raise AuthorizationDenied(f"Access denied: permission '{permission}' required.")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_permissions(*permissions: str) -> Callable[..., Any]:
    """
    Checks if the active IdentityContext user possesses all of the specified permissions.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = get_identity_context()
            if not context:
                raise AuthorizationDenied("Access denied. No active identity context resolved.")

            evaluator = PermissionEvaluator()
            context_data = {
                "time": datetime.utcnow().time().strftime("%H:%M"),
                "department": getattr(context.user, "department", None)
            }
            for perm in permissions:
                allowed = await evaluator.evaluate(
                    user=context.user,
                    org=context.organization,
                    active_roles=context.active_roles,
                    permission=perm,
                    context_data=context_data
                )
                if not allowed:
                    raise AuthorizationDenied(f"Access denied: permission '{perm}' required.")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_role(role: str) -> Callable[..., Any]:
    """
    Checks if the active user possesses the requested role (or inherits it).
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = get_identity_context()
            if not context:
                raise AuthorizationDenied("Access denied. No active identity context resolved.")

            from apps.api.app.core.role_resolver import expand_roles
            expanded = expand_roles(context.active_roles)
            if role not in expanded:
                raise AuthorizationDenied(f"Access denied: role '{role}' required.")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_roles(*roles: str) -> Callable[..., Any]:
    """
    Checks if the active user possesses at least one of the specified roles (or inherits it).
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            context = get_identity_context()
            if not context:
                raise AuthorizationDenied("Access denied. No active identity context resolved.")

            from apps.api.app.core.role_resolver import expand_roles
            expanded = expand_roles(context.active_roles)
            if not any(r in expanded for r in roles):
                raise AuthorizationDenied(f"Access denied: one of roles {roles} is required.")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
