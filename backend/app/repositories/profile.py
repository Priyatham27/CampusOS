from typing import Optional
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession

from app.models.identity.user import Profile

class ProfileRepository:
    """
    Repository for all operations on the Profile collection.
    Enforces active check filtration where required.
    """

    async def create(self, profile: Profile, session: Optional[ClientSession] = None) -> Profile:
        """Insert a new Profile document."""
        return await profile.insert(session=session)

    async def update(
        self,
        profile: Profile,
        update_fields: dict,
        session: Optional[ClientSession] = None
    ) -> Profile:
        """Apply partial updates to a Profile document and sync in-memory fields."""
        # Clean update fields
        for key in ["_id", "id", "profileId", "profile_id", "userId", "user_id", "created_at"]:
            update_fields.pop(key, None)

        db_update = {}
        for k, v in update_fields.items():
            prop = k
            if k == "firstName":
                prop = "first_name"
            elif k == "middleName":
                prop = "middle_name"
            elif k == "lastName":
                prop = "last_name"
            elif k == "preferredName":
                prop = "preferred_name"
            elif k == "dateOfBirth":
                prop = "date_of_birth"
            elif k == "alternatePhone":
                prop = "alternate_phone"
            elif k == "postalCode":
                prop = "postal_code"

            db_update[k] = v
            setattr(profile, prop, v)

        if db_update:
            await Profile.find_one(Profile.id == profile.id).update({"$set": db_update}, session=session)

        return profile

    async def find_by_user_beanie_id(
        self,
        user_id: PydanticObjectId,
        session: Optional[ClientSession] = None
    ) -> Optional[Profile]:
        """Find the profile associated with a user's database ObjectId."""
        return await Profile.find_one(Profile.user_id == user_id, Profile.is_deleted == False, session=session)

    async def find_by_profile_id(
        self,
        profile_id: str,
        session: Optional[ClientSession] = None
    ) -> Optional[Profile]:
        """Find a profile by its custom PRF_xxxxxx ID string."""
        return await Profile.find_one(Profile.profile_id == profile_id, Profile.is_deleted == False, session=session)
