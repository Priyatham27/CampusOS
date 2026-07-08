from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from pymongo.client_session import ClientSession

from apps.api.app.models.org_engine.organization import Branding, BrandingRevision

class BrandingRepository:
    """
    Repository handling all database operations for the Branding and BrandingRevision documents.
    """

    async def get(
        self, 
        organization_id: PydanticObjectId, 
        session: Optional[ClientSession] = None
    ) -> Optional[Branding]:
        """Retrieve the active Branding document for an organization."""
        return await Branding.find_one(
            Branding.organization_id == organization_id, 
            session=session
        )

    async def update(
        self,
        branding: Branding,
        update_fields: dict,
        session: Optional[ClientSession] = None
    ) -> Branding:
        """Apply partial updates to the active Branding config."""
        # Exclude read-only database identity fields
        for key in ["_id", "id", "organization_id", "organizationId", "created_at", "version"]:
            update_fields.pop(key, None)

        # Build mapping from internal field name or alias to DB alias
        db_fields = {}
        field_mapping = {}
        for name, field in branding.model_fields.items():
            alias = field.alias or name
            db_fields[name] = alias
            field_mapping[name] = name
            if field.alias:
                db_fields[field.alias] = alias
                field_mapping[field.alias] = name

        # Translate update keys to DB aliases for update query
        db_update_fields = {}
        for k, v in update_fields.items():
            db_alias = db_fields.get(k, k)
            db_update_fields[db_alias] = v

        update_query = {"$set": db_update_fields}
        await Branding.find_one(Branding.id == branding.id).update(update_query, session=session)

        # Sync in-memory model using mapped property names
        for k, v in update_fields.items():
            attr_name = field_mapping.get(k, k)
            if hasattr(branding, attr_name):
                setattr(branding, attr_name, v)
        return branding



    async def reset(
        self,
        branding: Branding,
        session: Optional[ClientSession] = None
    ) -> Branding:
        """Reset branding colors and typography styles to CampusOS defaults."""
        defaults = {
            "organization_logo": None,
            "dark_logo": None,
            "favicon": None,
            "banner": None,
            "primary_color": "#4F46E5",
            "secondary_color": "#0891B2",
            "accent_color": "#F59E0B",
            "surface_color": "#FFFFFF",
            "background_color": "#F9FAFB",
            "text_primary_color": "#1F2937",
            "text_secondary_color": "#4B5563",
            "text_muted_color": "#9CA3AF",
            "text_on_primary": "#FFFFFF",
            "text_on_secondary": "#FFFFFF",
            "success_color": "#10B981",
            "warning_color": "#F59E0B",
            "danger_color": "#EF4444",
            "info_color": "#3B82F6",
            "border_radius": "0.5rem",
            "font_family": "Inter",
            "theme": "light",
            "default_landing_image": None,
            "certificate_watermark": None,
            "email_header_logo": None,
            "email_footer": None,
            "footer_text": None,
            "support_email": None,
            "website": None,
            "social_twitter": None,
            "social_linkedin": None,
            "social_facebook": None,
            "social_instagram": None,
            "social_youtube": None,
            "preview_config": None
        }
        return await self.update(branding, defaults, session=session)

    async def uploadLogo(
        self,
        branding: Branding,
        logo_url: str,
        is_dark: bool = False,
        session: Optional[ClientSession] = None
    ) -> Branding:
        """Set logo URL (regular logo or dark logo)."""
        field_key = "dark_logo" if is_dark else "organization_logo"
        return await self.update(branding, {field_key: logo_url}, session=session)

    async def uploadBanner(
        self,
        branding: Branding,
        banner_url: str,
        session: Optional[ClientSession] = None
    ) -> Branding:
        """Set banner URL."""
        return await self.update(branding, {"banner": banner_url}, session=session)

    async def deleteLogo(
        self,
        branding: Branding,
        is_dark: bool = False,
        session: Optional[ClientSession] = None
    ) -> Branding:
        """Soft remove logo (reset value to None)."""
        field_key = "dark_logo" if is_dark else "organization_logo"
        return await self.update(branding, {field_key: None}, session=session)


    async def history(
        self,
        organization_id: PydanticObjectId,
        session: Optional[ClientSession] = None
    ) -> List[BrandingRevision]:
        """Fetch branding changes revision history sorted by version descending."""
        return await BrandingRevision.find(
            BrandingRevision.organization_id == organization_id,
            session=session
        ).sort("-version").to_list()

    async def save_revision(
        self,
        revision: BrandingRevision,
        session: Optional[ClientSession] = None
    ) -> BrandingRevision:
        """Insert a branding history log snapshot."""
        return await revision.insert(session=session)

    async def get_revision(
        self,
        organization_id: PydanticObjectId,
        version: int,
        session: Optional[ClientSession] = None
    ) -> Optional[BrandingRevision]:
        """Retrieve a specific version snapshot from the revision history."""
        return await BrandingRevision.find_one(
            BrandingRevision.organization_id == organization_id,
            BrandingRevision.version == version,
            session=session
        )
