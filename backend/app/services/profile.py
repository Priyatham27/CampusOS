from typing import Optional, Dict, Any
from beanie import PydanticObjectId
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.logger import logger
from app.core.user_exceptions import ProfileNotFound, UserNotFound
from app.repositories.profile import ProfileRepository
from app.repositories.user import UserRepository
from app.models.identity.user import Profile, User
from app.validators.profile import validate_profile_completeness
from app.validators.user import validate_phone_format

class ProfileService:
    """
    ProfileService handles personal details management, timezone/locale options,
    profile completeness verification, and auditing modifications.
    """
    def __init__(self):
        self.profile_repo = ProfileRepository()
        self.user_repo = UserRepository()

    async def get_profile_by_user_id(self, user_id: PydanticObjectId) -> Profile:
        """Resolve profile document associated with a user Beanie ObjectId."""
        profile = await self.profile_repo.find_by_user_beanie_id(user_id)
        if not profile:
            raise ProfileNotFound(f"Profile for user '{user_id}' not found.")
        return profile

    async def update_profile_by_user_id(
        self,
        user_id: PydanticObjectId,
        update_data: dict,
        current_user: User
    ) -> Profile:
        """Update profile details, validate phone format, and audit the changes."""
        profile = await self.get_profile_by_user_id(user_id)

        # Validate phone numbers if they are being updated
        if "phone" in update_data:
            validate_phone_format(update_data["phone"])
        if "alternatePhone" in update_data or "alternate_phone" in update_data:
            alt_phone = update_data.get("alternatePhone") or update_data.get("alternate_phone")
            validate_phone_format(alt_phone)

        # Apply updates
        updated_profile = await self.profile_repo.update(profile, update_data)

        # Standard Audit Log entry
        db = get_db()
        await db["audit_logs"].insert_one({
            "_id": f"aud_{PydanticObjectId()}",
            "tenant_id": str(current_user.organization_id),
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "action": "profile_update",
            "category": "audit",
            "details": {
                "target_profile_id": str(profile.id),
                "target_user_id": str(user_id),
                "fields_modified": list(update_data.keys())
            },
            "created_at": datetime.utcnow()
        })

        return updated_profile

    async def verify_and_complete_profile(self, user_id: PydanticObjectId) -> bool:
        """Verify profile meets baseline completeness rules."""
        profile = await self.get_profile_by_user_id(user_id)
        try:
            validate_profile_completeness(profile.model_dump())
            return True
        except ValueError:
            return False
