from datetime import datetime
from typing import Any, Dict
from beanie import PydanticObjectId
import logging

from app.core.database import get_db

logger = logging.getLogger("campusos.academic.event_publisher")

class AcademicEventPublisher:
    """
    Decoupled event publisher dispatching academic platform state adjustments 
    to database collections or downstream event streams.
    """
    @staticmethod
    async def publish_event(
        org_id: PydanticObjectId,
        event_type: str,
        payload: Dict[str, Any],
        performed_by: str = "system"
    ) -> None:
        try:
            db = get_db()
            event_doc = {
                "organizationId": org_id,
                "eventType": event_type,
                "timestamp": datetime.utcnow(),
                "performedBy": performed_by,
                "payload": payload
            }
            await db["academic_events"].insert_one(event_doc)
            logger.info(f"Academic Event Published: {event_type} for Org: {org_id}")
        except Exception as e:
            logger.error(f"Failed to publish academic event: {e}")
