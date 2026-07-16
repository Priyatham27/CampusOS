from typing import Optional
from fastapi import Depends
from apps.api.app.models.identity.user import User
from apps.api.app.core.identity_context import (
    get_current_identity,
    get_current_user,
    check_permission
)

# Backwards compatibility exports
requires_permission = check_permission
