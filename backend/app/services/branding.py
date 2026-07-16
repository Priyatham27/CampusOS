from datetime import datetime
import io
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
from PIL import Image
from beanie import PydanticObjectId

from app.core.database import get_db
from app.core.logger import logger
from app.core.exceptions import (
    OrganizationNotFound,
    BrandingNotFound,
    InvalidColor,
    InvalidImage,
    InvalidTheme
)
from app.core.storage import get_storage_provider
from app.models.org_engine.organization import Organization, Branding, BrandingRevision
from app.models.models import generate_prefixed_id
from app.repositories.branding import BrandingRepository
from app.repositories.organization import OrganizationRepository

class BrandingService:
    """
    Service Layer managing institutional branding configurations, validation rules,
    revision history snapshots, image upload checks (Pillow-backed), and design system token compile functions.
    """

    def __init__(
        self, 
        repo: Optional[BrandingRepository] = None, 
        org_repo: Optional[OrganizationRepository] = None
    ):
        self.repo = repo or BrandingRepository()
        self.org_repo = org_repo or OrganizationRepository()
        self.storage = get_storage_provider()

    async def generate_default_branding(
        self, 
        org_id: PydanticObjectId, 
        session: Optional[Any] = None
    ) -> Branding:
        """Seed a default Branding document linked to a new organization."""
        branding = Branding(
            organizationId=org_id,
            primaryColor="#4F46E5",
            secondaryColor="#0891B2",
            accentColor="#F59E0B",
            surfaceColor="#FFFFFF",
            backgroundColor="#F9FAFB"
        )
        return await branding.insert(session=session)

    async def get_branding(
        self, 
        organization_id_str: str, 
        preview: bool = False
    ) -> Branding:
        """
        Retrieve active branding config for an organization.
        If preview is True, overlays the pending preview configuration modifications.
        """
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            # Heal/Generate default branding if missing
            branding = await self.generate_default_branding(org.id)

        if preview and branding.preview_config:
            # Map aliases/fieldnames to internal attribute name
            field_mapping = {}
            for name, field in branding.model_fields.items():
                field_mapping[name] = name
                if field.alias:
                    field_mapping[field.alias] = name

            # Deep overlay preview fields onto active branding schema representation
            for key, val in branding.preview_config.items():
                attr_name = field_mapping.get(key, key)
                if hasattr(branding, attr_name):
                    setattr(branding, attr_name, val)
        return branding


    async def update_branding(
        self,
        organization_id_str: str,
        update_data: dict,
        preview: bool = False,
        user_id: Optional[str] = None
    ) -> Branding:
        """
        Applies partial updates to branding configuration.
        Under preview=True, keeps changes in a temporary previewConfig document state.
        Under preview=False, increments version, saves history revision snapshot, and commits changes.
        """
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            branding = await self.generate_default_branding(org.id)

        # Validate theme selection if passed
        if "theme" in update_data and update_data["theme"] not in ("light", "dark", "auto"):
            raise InvalidTheme("Theme must be light, dark, or auto.")

        if preview:
            # Overwrite preview config buffer
            current_preview = branding.preview_config or {}
            current_preview.update(update_data)
            branding.preview_config = current_preview
            await self.repo.update(branding, {"preview_config": current_preview})
            
            # Write audit logs for preview save
            await self._log_audit(
                org_id=org.id,
                action="branding_preview_saved",
                details={"updated_preview_keys": list(update_data.keys())},
                user_id=user_id
            )
            
            # Overlay preview values for return
            for k, v in current_preview.items():
                if hasattr(branding, k):
                    setattr(branding, k, v)
            return branding

        # Proceeding to publish / commit changes
        # 1. Save pre-update revision history log
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # 2. Add incremental updates and clean preview buffer
        new_version = branding.version + 1
        update_data["preview_config"] = None
        update_data["version"] = new_version
        
        updated_branding = await self.repo.update(branding, update_data)
        updated_branding.version = new_version
        updated_branding.preview_config = None
        
        # Save structural Beanie version change
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": new_version}},
            # Exclude hook update so revision number increments appropriately
        )


        # 3. Log audit action
        await self._log_audit(
            org_id=org.id,
            action="branding_updated",
            details={
                "previous_version": revision.version,
                "new_version": updated_branding.version,
                "modified_fields": list(update_data.keys())
            },
            user_id=user_id
        )

        return updated_branding

    async def reset_branding(
        self, 
        organization_id_str: str, 
        user_id: Optional[str] = None
    ) -> Branding:
        """Reset all colors and custom assets back to default CampusOS base settings."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            branding = await self.generate_default_branding(org.id)

        # Create history record
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # Apply reset and increment version
        await self.repo.reset(branding)
        branding.version += 1
        branding.preview_config = None
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": branding.version, "preview_config": None}}
        )

        # Audit logs
        await self._log_audit(
            org_id=org.id,
            action="branding_reset",
            details={"previous_version": revision.version, "new_version": branding.version},
            user_id=user_id
        )

        return branding

    async def upload_logo(
        self,
        organization_id_str: str,
        file: UploadFile,
        is_dark: bool = False,
        user_id: Optional[str] = None
    ) -> Branding:
        """Validate and upload an organization logo image asset, updating configuration state."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            branding = await self.generate_default_branding(org.id)

        # Size Limit: Max 2MB for logos
        max_size = 2 * 1024 * 1024
        file_bytes = await file.read()
        if len(file_bytes) > max_size:
            raise InvalidImage(f"Logo file size exceeds limit of 2MB. Got {(len(file_bytes) / 1024 / 1024):.2f}MB.")

        # Allowed formats
        allowed_types = ["image/png", "image/svg+xml", "image/jpeg", "image/webp"]
        if file.content_type not in allowed_types:
            raise InvalidImage(f"Unsupported file format: '{file.content_type}'. Must be PNG, SVG, JPEG, or WEBP.")

        # Verify dimensions for non-SVG raster logos
        if file.content_type != "image/svg+xml":
            try:
                img = Image.open(io.BytesIO(file_bytes))
                width, height = img.size
                if width < 32 or height < 32:
                    raise InvalidImage(f"Logo dimensions too small ({width}x{height}px). Minimum is 32x32px.")
            except Exception as e:
                if isinstance(e, InvalidImage):
                    raise e
                raise InvalidImage("Failed to parse image headers. Corrupted image file.")

        # Upload
        folder = f"organizations/{organization_id_str}/branding"
        logo_url = await self.storage.upload(
            file_content=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            folder=folder
        )

        # Create history record
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # Apply update
        branding.version += 1
        await self.repo.uploadLogo(branding, logo_url, is_dark)
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": branding.version}}
        )

        # Log audit action
        await self._log_audit(
            org_id=org.id,
            action="logo_uploaded",
            details={
                "is_dark_logo": is_dark,
                "url": logo_url,
                "new_version": branding.version
            },
            user_id=user_id
        )

        return branding

    async def upload_banner(
        self,
        organization_id_str: str,
        file: UploadFile,
        user_id: Optional[str] = None
    ) -> Branding:
        """Validate and upload an organization banner asset. Enforces aspect ratio checking >= 2.0 (wider)."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            branding = await self.generate_default_branding(org.id)

        # Size Limit: Max 5MB for banners
        max_size = 5 * 1024 * 1024
        file_bytes = await file.read()
        if len(file_bytes) > max_size:
            raise InvalidImage(f"Banner file size exceeds limit of 5MB. Got {(len(file_bytes) / 1024 / 1024):.2f}MB.")

        # Allowed formats
        allowed_types = ["image/png", "image/svg+xml", "image/jpeg", "image/webp"]
        if file.content_type not in allowed_types:
            raise InvalidImage(f"Unsupported file format: '{file.content_type}'. Must be PNG, SVG, JPEG, or WEBP.")

        # Validate banner aspect ratio (must be a landscape banner width > height, ideally aspect ratio >= 2.0)
        if file.content_type != "image/svg+xml":
            try:
                img = Image.open(io.BytesIO(file_bytes))
                width, height = img.size
                aspect_ratio = width / height
                if aspect_ratio < 2.0:
                    raise InvalidImage(
                        f"Banner image aspect ratio too narrow ({aspect_ratio:.2f}). Must be a wide banner with aspect ratio >= 2.0 (e.g. 16:9 or 3:1)."
                    )
            except Exception as e:
                if isinstance(e, InvalidImage):
                    raise e
                raise InvalidImage("Failed to parse banner image dimensions.")

        # Upload
        folder = f"organizations/{organization_id_str}/branding"
        banner_url = await self.storage.upload(
            file_content=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            folder=folder
        )

        # Create history record
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # Apply update
        branding.version += 1
        await self.repo.uploadBanner(branding, banner_url)
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": branding.version}}
        )

        # Log audit action
        await self._log_audit(
            org_id=org.id,
            action="banner_uploaded",
            details={
                "url": banner_url,
                "new_version": branding.version
            },
            user_id=user_id
        )

        return branding

    async def delete_logo(
        self,
        organization_id_str: str,
        is_dark: bool = False,
        user_id: Optional[str] = None
    ) -> Branding:
        """Soft remove the logo setting it back to None."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            raise BrandingNotFound("Branding settings do not exist.")

        # Create history record
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # Apply deletion
        branding.version += 1
        await self.repo.deleteLogo(branding, is_dark)
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": branding.version}}
        )

        # Log audit action
        await self._log_audit(
            org_id=org.id,
            action="logo_deleted",
            details={
                "is_dark_logo": is_dark,
                "new_version": branding.version
            },
            user_id=user_id
        )

        return branding

    async def rollback_branding(
        self,
        organization_id_str: str,
        target_version: int,
        user_id: Optional[str] = None
    ) -> Branding:
        """Roll back institutional branding to a previously recorded snapshot version."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")

        branding = await self.repo.get(org.id)
        if not branding:
            raise BrandingNotFound("Branding settings do not exist.")

        # Find target snapshot in revision log
        target_revision = await self.repo.get_revision(org.id, target_version)
        if not target_revision:
            raise BrandingNotFound(f"Revision version {target_version} not found in branding history.")

        # Create current snapshot record
        old_state = branding.model_dump(by_alias=False, exclude={"id", "created_at", "updated_at", "organization_id"})
        revision = BrandingRevision(
            brandingId=branding.id,
            organizationId=org.id,
            version=branding.version,
            brandingData=old_state
        )
        await self.repo.save_revision(revision)

        # Apply target snapshot values and increment version
        rollback_data = target_revision.branding_data
        # Remove version from rollback data to allow local custom setting
        rollback_data.pop("version", None)
        rollback_data.pop("preview_config", None)
        
        await self.repo.update(branding, rollback_data)
        branding.version += 1
        branding.preview_config = None
        
        await Branding.find_one(Branding.id == branding.id).update(
            {"$set": {"version": branding.version, "preview_config": None}}
        )

        # Log audit action
        await self._log_audit(
            org_id=org.id,
            action="branding_rollback",
            details={
                "rolled_back_to_version": target_version,
                "new_version": branding.version
            },
            user_id=user_id
        )

        return branding

    async def get_branding_history(
        self, 
        organization_id_str: str
    ) -> List[BrandingRevision]:
        """Retrieve revision logs history for the organization."""
        org = await self.org_repo.find_by_id(organization_id_str)
        if not org:
            raise OrganizationNotFound(f"Organization '{organization_id_str}' not found.")
        return await self.repo.history(org.id)

    def generate_css_variables(self, branding: Branding, preview: bool = False) -> str:
        """Compiles branding theme variables into standard custom CSS properties string."""
        # Use overlay if preview flag is true
        b = branding
        if preview and branding.preview_config:
            # create temporary clone and overlay properties
            b = Branding(**branding.model_dump())
            for k, v in branding.preview_config.items():
                if hasattr(b, k):
                    setattr(b, k, v)

        css_vars = f"""/* CampusOS Institutional Auto-Generated Branding Stylesheet */
:root {{
  --primary-color: {b.primary_color};
  --secondary-color: {b.secondary_color};
  --accent-color: {b.accent_color};
  --surface-color: {b.surface_color};
  --background-color: {b.background_color};
  --text-primary: {b.text_primary_color};
  --text-secondary: {b.text_secondary_color};
  --text-muted: {b.text_muted_color};
  --text-on-primary: {b.text_on_primary};
  --text-on-secondary: {b.text_on_secondary};
  --success-color: {b.success_color};
  --warning-color: {b.warning_color};
  --danger-color: {b.danger_color};
  --info-color: {b.info_color};
  --border-radius: {b.border_radius};
  --font-family: "{b.font_family}", sans-serif;
}}
"""
        return css_vars

    def generate_theme_tokens(self, branding: Branding, preview: bool = False) -> dict:
        """Returns JSON theme configurations structured to extend default Tailwind utility configurations."""
        b = branding
        if preview and branding.preview_config:
            b = Branding(**branding.model_dump())
            for k, v in branding.preview_config.items():
                if hasattr(b, k):
                    setattr(b, k, v)

        return {
            "theme": {
                "extend": {
                    "colors": {
                        "primary": b.primary_color,
                        "secondary": b.secondary_color,
                        "accent": b.accent_color,
                        "surface": b.surface_color,
                        "background": b.background_color,
                        "text": {
                            "primary": b.text_primary_color,
                            "secondary": b.text_secondary_color,
                            "muted": b.text_muted_color,
                            "on-primary": b.text_on_primary,
                            "on-secondary": b.text_on_secondary
                        },
                        "success": b.success_color,
                        "warning": b.warning_color,
                        "danger": b.danger_color,
                        "info": b.info_color
                    },
                    "borderRadius": {
                        "institutional": b.border_radius
                    },
                    "fontFamily": {
                        "institutional": [b.font_family, "sans-serif"]
                    }
                }
            }
        }

    async def _log_audit(
        self, 
        org_id: PydanticObjectId, 
        action: str, 
        details: dict, 
        user_id: Optional[str] = None
    ) -> None:
        """Audit logging interface saving changes into motor db['audit_logs'] collection."""
        try:
            db = get_db()
            user_email = "system@campusos.com"
            if user_id:
                user_doc = await db["users"].find_one({"_id": user_id})
                if user_doc:
                    user_email = user_doc.get("email", user_email)

            await db["audit_logs"].insert_one({
                "_id": generate_prefixed_id("aud"),
                "tenant_id": str(org_id),
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "category": "audit",
                "details": details,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Audit log write failed in BrandingService: {e}")

def get_branding_service() -> BrandingService:
    return BrandingService()
