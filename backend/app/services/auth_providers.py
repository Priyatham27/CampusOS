from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.models.identity.user import User
from app.services.credential import CredentialService

class AuthenticationProvider(ABC):
    """Abstract base class representing an extensible Authentication Provider strategy."""
    @abstractmethod
    async def authenticate(
        self,
        user: User,
        payload: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> bool:
        """Authenticate user against this provider's logic."""
        pass

class PasswordAuthenticationProvider(AuthenticationProvider):
    """Password-based credential authentication provider."""
    def __init__(self, credential_service: CredentialService):
        self.credential_service = credential_service

    async def authenticate(
        self,
        user: User,
        payload: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> bool:
        password = payload.get("password")
        if not password:
            return False
        return await self.credential_service.verify_password(
            user_id_str=str(user.id),
            password=password,
            ip_address=ip_address
        )
