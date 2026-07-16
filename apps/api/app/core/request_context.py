import contextvars
from typing import Optional
from fastapi import Request

_current_request: contextvars.ContextVar[Optional[Request]] = contextvars.ContextVar(
    "current_request", default=None
)

def get_request() -> Optional[Request]:
    """Retrieve the active Request object from the current execution context."""
    return _current_request.get()

def set_request(request: Request) -> contextvars.Token:
    """Set the active Request object in the current execution context."""
    return _current_request.set(request)

def reset_request(token: contextvars.Token) -> None:
    """Reset the request context to its previous state."""
    _current_request.reset(token)
