from typing import Optional
from fastapi import Depends
from app.models.identity.user import User
from app.core.identity_context import (
    get_current_identity,
    get_current_user,
    check_permission
)

# Backwards compatibility exports
requires_permission = check_permission
