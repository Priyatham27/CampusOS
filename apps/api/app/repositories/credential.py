from typing import Optional
from beanie import PydanticObjectId
from apps.api.app.models.identity.credential import Credential, CredentialType

class CredentialRepository:
    """
    Handles MongoDB database persistence and query logic for Credentials.
    """
    async def create(self, credential: Credential, session=None) -> Credential:
        return await credential.insert(session=session)

    async def find_by_user_id(
        self, 
        user_id: PydanticObjectId, 
        cred_type: CredentialType = CredentialType.PASSWORD,
        session=None
    ) -> Optional[Credential]:
        return await Credential.find_one(
            Credential.user_id == user_id,
            Credential.type == cred_type,
            Credential.is_deleted == False,
            session=session
        )

    async def find_by_id(self, id_str: str, session=None) -> Optional[Credential]:
        try:
            obj_id = PydanticObjectId(id_str)
            query = {"_id": obj_id, "isDeleted": False}
        except Exception:
            query = {"credentialId": id_str, "isDeleted": False}
        return await Credential.find_one(query, session=session)

    async def update(self, credential: Credential, update_data: dict, session=None) -> Credential:
        import re
        for k, v in update_data.items():
            snake_k = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
            if hasattr(credential, snake_k):
                setattr(credential, snake_k, v)
            elif hasattr(credential, k):
                setattr(credential, k, v)
        return await credential.save(session=session)

    async def delete(self, credential: Credential, session=None) -> None:
        await credential.soft_delete(session=session)
