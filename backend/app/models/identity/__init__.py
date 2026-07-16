from app.models.identity.user import (
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
from app.models.identity.credential import (
    Credential,
    CredentialType
)
from app.models.identity.rbac import (
    Permission,
    Role,
    UserRole,
    RolePermission
)
from app.models.identity.session import (
    Device,
    Session,
    RefreshToken,
    OAuthAccount
)
from app.models.identity.security import (
    PasswordResetToken,
    EmailVerificationToken,
    LoginHistory,
    SecurityEvent,
    SecurityEventSeverity,
    SecurityEventType,
    LoginStatus
)
from app.models.identity.api_key import (
    APIKey
)
from app.models.identity.policy import (
    Policy
)

IDENTITY_MODELS = [
    User,
    Profile,
    StudentProfile,
    FacultyProfile,
    AdminProfile,
    Credential,
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
    APIKey,
    Policy
]

__all__ = [
    "User",
    "Profile",
    "StudentProfile",
    "FacultyProfile",
    "AdminProfile",
    "Credential",
    "CredentialType",
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
    "Policy",
    "IDENTITY_MODELS"
]

