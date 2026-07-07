from datetime import datetime
from typing import Optional
from beanie import Document, before_event, Insert, Replace, Save, Update
from pydantic import Field, ConfigDict
from pydantic.alias_generators import to_camel
from bson import ObjectId

class BaseDocument(Document):
    """
    Production-grade base document class for Beanie ODM models.
    Supports auto-timestamps, version control, change-revisions, camelCase API serialization, and soft deletes.
    """
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    deleted_at: Optional[datetime] = Field(default=None, alias="deletedAt")
    created_by: Optional[str] = Field(default=None, alias="createdBy")
    updated_by: Optional[str] = Field(default=None, alias="updatedBy")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    
    # Document Revision Versioning
    version: int = Field(default=1)
    revision_number: int = Field(default=0, alias="revisionNumber")
    change_reason: Optional[str] = Field(default=None, alias="changeReason")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    @before_event(Insert)
    def before_insert_hook(self):
        """Lifecycle event to set audit timestamps on initial document insertion."""
        now = datetime.utcnow()
        self.created_at = now
        self.updated_at = now
        self.version = 1
        self.revision_number = 0

    @before_event(Replace, Save, Update)
    def before_update_hook(self):
        """Lifecycle event to update modification timestamps and increment revisions before saves/updates."""
        self.updated_at = datetime.utcnow()
        self.revision_number += 1

    async def soft_delete(self, user_id: Optional[str] = None, reason: Optional[str] = None, session=None) -> None:
        """Mark document as logically deleted (soft delete) using atomic collection-level update."""
        now = datetime.utcnow()
        update_data = {
            "isDeleted": True,
            "deletedAt": now,
            "revisionNumber": self.revision_number + 1,
            "updatedAt": now
        }
        if reason:
            update_data["changeReason"] = reason
        if user_id:
            update_data["updatedBy"] = user_id

        # Use raw motor collection to guarantee _id lookup regardless of Beanie id state
        collection = self.__class__.get_pymongo_collection()
        doc_id = self.id if self.id is not None else ObjectId()
        await collection.update_one({"_id": doc_id}, {"$set": update_data}, session=session)

        self.is_deleted = True
        self.deleted_at = now
        self.revision_number += 1
        if reason:
            self.change_reason = reason
        if user_id:
            self.updated_by = user_id

    async def restore(self, user_id: Optional[str] = None, reason: Optional[str] = None, session=None) -> None:
        """Restore a soft-deleted document back to active state using atomic collection-level update."""
        now = datetime.utcnow()
        update_data = {
            "isDeleted": False,
            "deletedAt": None,
            "revisionNumber": self.revision_number + 1,
            "updatedAt": now
        }
        if reason:
            update_data["changeReason"] = reason
        if user_id:
            update_data["updatedBy"] = user_id

        # Use raw motor collection to guarantee _id lookup regardless of Beanie id state
        collection = self.__class__.get_pymongo_collection()
        doc_id = self.id if self.id is not None else ObjectId()
        await collection.update_one({"_id": doc_id}, {"$set": update_data}, session=session)

        self.is_deleted = False
        self.deleted_at = None
        self.revision_number += 1
        if reason:
            self.change_reason = reason
        if user_id:
            self.updated_by = user_id
