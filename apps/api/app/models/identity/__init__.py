from apps.api.app.models.identity.user import (
    User,
    Profile,
    StudentProfile,
    FacultyProfile,
    AdminProfile,
    UserStatus,
    AccountType,
    StudentStatus,
    FacultyStatus
)
from apps.api.app.models.identity.rbac import (
    Permission,
    Role,
    UserRole,
    RolePermission
)
from apps.api.app.models.identity.session import (
    Device,
    Session,
    RefreshToken,
    OAuthAccount
)
from apps.api.app.models.identity.security import (
    PasswordResetToken,
    EmailVerificationToken,
    LoginHistory,
    SecurityEvent,
    SecurityEventSeverity,
    SecurityEventType,
    LoginStatus
)
from apps.api.app.models.identity.api_key import (
    APIKey
)

IDENTITY_MODELS = [
    User,
    Profile,
    StudentProfile,
    FacultyProfile,
    AdminProfile,
    Permission,
    Role,
    UserRole,
    RolePermission,
    Device,
    Session,
    RefreshToken,
    OAuthAccount,
    PasswordResetToken,
    EmailVerificationToken,
    LoginHistory,
    SecurityEvent,
    APIKey
]

__all__ = [
    "User",
    "Profile",
    "StudentProfile",
    "FacultyProfile",
    "AdminProfile",
    "UserStatus",
    "AccountType",
    "StudentStatus",
    "FacultyStatus",
    "Permission",
    "Role",
    "UserRole",
    "RolePermission",
    "Device",
    "Session",
    "RefreshToken",
    "OAuthAccount",
    "PasswordResetToken",
    "EmailVerificationToken",
    "LoginHistory",
    "SecurityEvent",
    "SecurityEventSeverity",
    "SecurityEventType",
    "LoginStatus",
    "APIKey",
    "IDENTITY_MODELS"
]
