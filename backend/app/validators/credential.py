from typing import Optional, Dict, Any, List
from app.services.config import ConfigurationService
from app.core.credential_exceptions import PasswordPolicyViolation, PasswordReuseProhibited
from app.core.security import verify_password_argon2

# Secure baseline defaults conforming to OWASP / industry standards
DEFAULT_POLICY = {
    "min_length": 8,
    "max_length": 128,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_number": True,
    "require_special": True,
    "prevent_common": True,
}

COMMON_PASSWORDS = {
    "password", "password123", "123456", "12345678", "123456789", "12345",
    "1234567", "qwerty", "letmein1", "letmein", "welcome", "welcome1",
    "admin123", "admin", "campusos", "campusos123", "sunshine", "football",
    "shadow", "dragon", "master", "cheesecake", "princess", "iloveyou"
}

async def get_password_policy(org_id_str: Optional[str], config_service: ConfigurationService) -> Dict[str, Any]:
    """
    Fetches the password policy settings from the Runtime Configuration Engine.
    Falls back to secure defaults if keys are missing.
    """
    policy = DEFAULT_POLICY.copy()
    if not org_id_str:
        return policy

    keys = {
        "security.password.min_length": ("min_length", int),
        "security.password.max_length": ("max_length", int),
        "security.password.require_uppercase": ("require_uppercase", bool),
        "security.password.require_lowercase": ("require_lowercase", bool),
        "security.password.require_number": ("require_number", bool),
        "security.password.require_special": ("require_special", bool),
        "security.password.prevent_common": ("prevent_common", bool),
    }

    for config_key, (policy_key, cast_func) in keys.items():
        try:
            resolved = await config_service.resolve_configuration(
                org_id_str=org_id_str,
                key=config_key,
                environment="PRODUCTION"
            )
            val = resolved.get("value")
            if val is not None:
                policy[policy_key] = cast_func(val)
        except Exception:
            # Continue on failure, keeping defaults
            pass
            
    return policy

def validate_password_strength(password: str, policy: Dict[str, Any]) -> None:
    """
    Validates a password against a complexity policy.
    Raises PasswordPolicyViolation if validation fails.
    """
    min_len = policy.get("min_length", 8)
    max_len = policy.get("max_length", 128)
    if len(password) < min_len:
        raise PasswordPolicyViolation(f"Password must be at least {min_len} characters long.")
    if len(password) > max_len:
        raise PasswordPolicyViolation(f"Password must be at most {max_len} characters long.")

    # Uppercase check
    if policy.get("require_uppercase", True) and not any(c.isupper() for c in password):
        raise PasswordPolicyViolation("Password must contain at least one uppercase letter.")

    # Lowercase check
    if policy.get("require_lowercase", True) and not any(c.islower() for c in password):
        raise PasswordPolicyViolation("Password must contain at least one lowercase letter.")

    # Number check
    if policy.get("require_number", True) and not any(c.isdigit() for c in password):
        raise PasswordPolicyViolation("Password must contain at least one number.")

    # Special characters check
    special_chars = "!@#$%^&*()-_=+[]{}|;:',.<>?/`~"
    if policy.get("require_special", True) and not any(c in special_chars for c in password):
        raise PasswordPolicyViolation("Password must contain at least one special character.")

    # Common passwords check
    if policy.get("prevent_common", True):
        if password.lower() in COMMON_PASSWORDS:
            raise PasswordPolicyViolation("Password is too common or easily guessable.")

def validate_password_reuse(plain_password: str, password_history: List[str]) -> None:
    """
    Checks if a password has been used recently by matching against the hash history.
    Raises PasswordReuseProhibited if a match is found.
    """
    for historical_hash in password_history:
        if verify_password_argon2(plain_password, historical_hash):
            raise PasswordReuseProhibited("New password cannot be the same as any of the last 5 passwords used.")
