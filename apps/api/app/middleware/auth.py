from fastapi import Depends, HTTPException, status, Request
from apps.api.app.core.security import decode_access_token, extract_access_token
from apps.api.app.core.database import get_db
from apps.api.app.core.logger import logger
from apps.api.app.models.models import User, Role
import motor.motor_asyncio
from bson import ObjectId

async def get_current_user(
    request: Request,
    db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
) -> User:
    """Retrieve user context by extracting token from HttpOnly secure cookies or Auth headers."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalid or expired. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing. Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
        
    try:
        user_doc = await db["users"].find_one({"_id": user_id})
        if user_doc is None:
            raise credentials_exception
        
        # Convert _id to string for model compliance
        user_doc["_id"] = str(user_doc["_id"])
        user = User(**user_doc)
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
            
        return user
    except Exception as e:
        logger.error(f"Error resolving current user session: {e}")
        raise credentials_exception

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
        db: motor.motor_asyncio.AsyncIOMotorDatabase = Depends(get_db)
    ) -> User:
        """Verify that the user contains the required RBAC privilege or matches SuperAdmin name."""
        try:
            # Fetch user's role
            role_doc = await db["roles"].find_one({"_id": current_user.role_id})
            if not role_doc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User role profiles not resolved"
                )
                
            role = Role(**role_doc)
            
            # SuperAdmin bypass
            if role.name == "SuperAdmin":
                return current_user
                
            # Check permissions
            if self.required_permission not in role.permissions:
                logger.warning(
                    f"User {current_user.email} denied access. Required: {self.required_permission}. Role: {role.name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required privilege: {self.required_permission}"
                )
                
            return current_user
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying user permissions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error validating security level access"
            )
            
def requires_permission(permission: str):
    return PermissionChecker(permission)
