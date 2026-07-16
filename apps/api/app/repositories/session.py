import logging
from datetime import datetime
from typing import Optional, List
from beanie import PydanticObjectId

from apps.api.app.models.identity.session import Session, Device, RefreshToken
from apps.api.app.services.cache_service import CacheService

logger = logging.getLogger("campusos.repository.session")

class SessionRepository:
    """
    Handles persistence and Redis caching for active user sessions.
    """
    def __init__(self):
        self.cache = CacheService()

    async def create_session(self, session: Session) -> Session:
        await session.insert()
        # Cache the session details
        ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
        if ttl > 0:
            self.cache.set_session(session.session_id, session.model_dump(by_alias=True), ttl)
        return session

    async def find_session_by_id(self, session_id: str) -> Optional[Session]:
        # 1. Try cache
        cached = self.cache.get_session(session_id)
        if cached:
            try:
                # Reconstruct Beanie document
                return Session.model_validate(cached)
            except Exception as e:
                logger.error(f"Failed to parse cached session: {e}")

        # 2. Try MongoDB
        session = await Session.find_one(Session.session_id == session_id)
        if session:
            # Write back to cache
            ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                self.cache.set_session(session.session_id, session.model_dump(by_alias=True), ttl)
        return session

    async def update_last_activity(self, session_id: str) -> None:
        session = await Session.find_one(Session.session_id == session_id)
        if session:
            session.last_activity = datetime.utcnow()
            await session.save()
            
            # Update cache
            ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
            if ttl > 0:
                self.cache.set_session(session.session_id, session.model_dump(by_alias=True), ttl)

    async def revoke_session(self, session_id: str) -> None:
        # Delete from MongoDB
        session = await Session.find_one(Session.session_id == session_id)
        if session:
            # Revoke associated refresh tokens in DB
            await RefreshToken.find(RefreshToken.session_id == session.id).update({"$set": {"revoked": True}})
            await session.delete()
            
        # Invalidate cache
        self.cache.delete_session(session_id)

    async def revoke_all_user_sessions(self, user_id: PydanticObjectId) -> None:
        sessions = await Session.find(Session.user_id == user_id).to_list()
        for session in sessions:
            # Revoke associated refresh tokens
            await RefreshToken.find(RefreshToken.session_id == session.id).update({"$set": {"revoked": True}})
            # Delete from cache
            self.cache.delete_session(session.session_id)
            await session.delete()

    async def list_active_sessions(self, user_id: PydanticObjectId) -> List[Session]:
        return await Session.find(Session.user_id == user_id, Session.expires_at > datetime.utcnow()).to_list()

    async def search_sessions(self, skip: int = 0, limit: int = 100) -> List[Session]:
        return await Session.find(limit=limit, skip=skip).to_list()

    async def cleanup_expired_sessions(self) -> int:
        now = datetime.utcnow()
        expired_sessions = await Session.find(Session.expires_at <= now).to_list()
        count = 0
        for ses in expired_sessions:
            await RefreshToken.find(RefreshToken.session_id == ses.id).update({"$set": {"revoked": True}})
            self.cache.delete_session(ses.session_id)
            await ses.delete()
            count += 1
        return count

class DeviceRepository:
    """
    Handles persistence and lookups for recognized user devices.
    """
    async def find_device(self, device_id: str) -> Optional[Device]:
        return await Device.find_one(Device.device_id == device_id)

    async def find_user_device_by_details(self, user_id: PydanticObjectId, name: str) -> Optional[Device]:
        return await Device.find_one(
            Device.user_id == user_id,
            Device.device_name == name
        )

    async def create_device(self, device: Device) -> Device:
        await device.insert()
        return device

    async def list_user_devices(self, user_id: PydanticObjectId) -> List[Device]:
        return await Device.find(Device.user_id == user_id).to_list()

    async def update_device_trust(self, device_id: str, trusted: bool) -> Optional[Device]:
        device = await Device.find_one(Device.device_id == device_id)
        if device:
            device.trusted = trusted
            await device.save()
        return device

    async def delete_device(self, device_id: str) -> bool:
        device = await Device.find_one(Device.device_id == device_id)
        if device:
            await device.delete()
            return True
        return False
