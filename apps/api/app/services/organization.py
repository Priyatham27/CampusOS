from typing import List, Optional, Tuple, Dict
from datetime import datetime
from beanie import PydanticObjectId
from pymongo.errors import PyMongoError
import slugify
import re

from apps.api.app.core.database import get_db
from apps.api.app.core.logger import logger
from apps.api.app.core.exceptions import (
    OrganizationNotFound,
    SlugAlreadyExists,
    EmailDomainAlreadyExists,
    OrganizationAlreadyExists
)
from apps.api.app.repositories.organization import OrganizationRepository
from apps.api.app.models.org_engine.organization import Organization, Branding, OrganizationSettings
from apps.api.app.models.org_engine.extension import Module, FeatureFlag

class OrganizationService:
    """
    Service Layer orchestrating business validations, duplicate conflict checking,
    dynamic slug configurations, default module/feature-flag seeds, and transactional database writes.
    """

    def __init__(self, repo: Optional[OrganizationRepository] = None):
        self.repo = repo or OrganizationRepository()

    async def create_organization(self, data: dict, user_id: Optional[str] = None) -> Organization:
        """Create an organization and seed its default settings inside a transaction block."""
        name = data.get("name")
        slug = data.get("slug")
        email_domain = (data.get("email_domain") or data.get("emailDomain") or "").lower()
        org_id = data.get("organization_id") or data.get("organizationId")
        contact_email = data.get("contact_email") or data.get("contactEmail")
        short_name = data.get("short_name") or data.get("shortName") or name[:20]
        university_id = data.get("university_id") or data.get("universityId")

        # 1. Generate slug automatically if omitted
        if not slug:
            slug = slugify.slugify(name)
        else:
            slug = slugify.slugify(slug)

        # 2. Check for duplicate conflicts (unique constraints validation)
        conflicts = await self.repo.exists(org_id=org_id, slug=slug, email_domain=email_domain, name=name)
        if conflicts:
            logger.warning(f"Conflict detected during Organization creation: {conflicts}")
            if "organizationId" in conflicts:
                raise OrganizationAlreadyExists(conflicts["organizationId"])
            if "name" in conflicts:
                raise OrganizationAlreadyExists(conflicts["name"])
            if "slug" in conflicts:
                raise SlugAlreadyExists(conflicts["slug"])
            if "emailDomain" in conflicts:
                raise EmailDomainAlreadyExists(conflicts["emailDomain"])

        # Construct organization document instance in snake_case
        search_keywords = list(set([name.lower(), slug.lower()] + [w.lower() for w in name.split()]))
        org = Organization(
            organization_id=org_id,
            university_id=PydanticObjectId(university_id) if university_id else None,
            name=name,
            short_name=short_name,
            slug=slug,
            description=data.get("description"),
            logo=data.get("logo"),
            dark_logo=data.get("dark_logo") or data.get("darkLogo"),
            favicon=data.get("favicon"),
            banner=data.get("banner"),
            website=data.get("website"),
            email_domain=email_domain,
            contact_email=contact_email,
            phone=data.get("phone"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country"),
            postal_code=data.get("postal_code") or data.get("postalCode"),
            timezone=data.get("timezone", "UTC"),
            currency=data.get("currency", "USD"),
            language=data.get("language", "en"),
            search_keywords=search_keywords,
            normalized_name=name.lower()
        )
        if user_id:
            org.created_by = user_id

        # 3. Save organization and default settings inside a transaction session
        db = get_db()
        client = db.client

        async def _run_creation_flow(session_arg=None):
            # Create organization
            inserted_org = await self.repo.create(org, session=session_arg)
            org_object_id = inserted_org.id

            # Create default Branding config
            from apps.api.app.services.branding import BrandingService
            branding_service = BrandingService()
            await branding_service.generate_default_branding(org_object_id, session=session_arg)


            # Create default settings
            settings = OrganizationSettings(
                organizationId=org_object_id,
                attendanceEnabled=False,
                certificateEnabled=False,
                analyticsEnabled=False
            )
            await settings.insert(session=session_arg)

            # Create default modules seed
            default_modules = [
                {"idx": "01", "name": "Core Platform Engine", "slug": "core", "version": "1.0.0", "dependencies": []},
                {"idx": "02", "name": "Events Management", "slug": "events", "version": "1.0.0", "dependencies": ["core"]},
                {"idx": "03", "name": "Attendance Tracker", "slug": "attendance", "version": "1.0.0", "dependencies": ["core"]},
                {"idx": "04", "name": "Digital Credentials", "slug": "certificates", "version": "1.0.0", "dependencies": ["core"]},
            ]
            org_digits = re.sub(r"\D", "", org_id)
            for m in default_modules:
                mod = Module(
                    moduleId=f"MOD_{m['idx']}{org_digits}",
                    organizationId=org_object_id,
                    name=m["name"],
                    slug=m["slug"],
                    version=m["version"],
                    enabled=True if m["slug"] == "core" else False,
                    dependencies=m["dependencies"]
                )
                await mod.insert(session=session_arg)

            # Create default feature flags seed
            default_flags = [
                {"idx": "01", "name": "Enable Events Module", "key": "enable_events"},
                {"idx": "02", "name": "Enable Attendance Checks", "key": "enable_attendance"},
                {"idx": "03", "name": "Enable Certificates Generation", "key": "enable_certificates"},
            ]
            for f in default_flags:
                flag = FeatureFlag(
                    flagId=f"FLG_{f['idx']}{org_digits}",
                    organizationId=org_object_id,
                    name=f["name"],
                    key=f["key"],
                    enabled=False
                )
                await flag.insert(session=session_arg)

            return inserted_org

        try:
            # Attempt to execute inside a MongoDB transaction session
            async with await client.start_session() as session:
                async with session.start_transaction():
                    result = await _run_creation_flow(session)
                    logger.info(f"Organization '{name}' (ID: {org_id}) created successfully inside transaction.")
                    return result
        except (PyMongoError, Exception) as e:
            # Fallback for standalone/local DB instance that does not support transactions
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower():
                logger.warning("Transactions are not supported on this MongoDB configuration. Running in non-transactional fallback mode.")
                result = await _run_creation_flow(None)
                logger.info(f"Organization '{name}' (ID: {org_id}) created successfully (Non-transactional fallback).")
                return result
            else:
                logger.error(f"Transaction failed during Organization creation: {e}")
                raise e

    async def get_organization(self, org_id: str) -> Organization:
        """Retrieve organization details by unique custom ID."""
        org = await self.repo.find_by_id(org_id)
        if not org:
            logger.warning(f"Organization lookup failed: ID '{org_id}' not found.")
            raise OrganizationNotFound(f"Organization with ID '{org_id}' not found.")
        return org

    async def update_organization(self, org_id: str, update_data: dict, user_id: Optional[str] = None) -> Organization:
        """Modify fields on an existing organization document after conflicts checks."""
        org = await self.get_organization(org_id)

        # Check unique name conflicts if name changes
        new_name = update_data.get("name")
        if new_name and new_name != org.name:
            conflicts = await self.repo.exists(name=new_name)
            if conflicts:
                raise OrganizationAlreadyExists(conflicts["name"])
            
            # Update search parameters as well
            update_data["normalizedName"] = new_name.lower()
            update_data["searchKeywords"] = list(set([new_name.lower(), org.slug.lower()] + [w.lower() for w in new_name.split()]))

        if user_id:
            update_data["updatedBy"] = user_id

        updated_org = await self.repo.update(org, update_data)
        logger.info(f"Organization ID '{org_id}' successfully updated fields: {list(update_data.keys())}")
        return updated_org

    async def delete_organization(self, org_id: str, user_id: Optional[str] = None) -> bool:
        """Perform soft delete on the organization document."""
        org = await self.get_organization(org_id)
        await self.repo.delete(org)
        logger.info(f"Organization ID '{org_id}' soft deleted successfully.")
        return True

    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None
    ) -> Tuple[List[Organization], int]:
        """List active organizations with paginated metadata count."""
        orgs = await self.repo.list(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, filters=filters)
        total = await self.repo.count(filters=filters)
        return orgs, total

    async def search_organizations(self, query_str: str, skip: int = 0, limit: int = 10) -> List[Organization]:
        """Search active organizations using query parameter triggers."""
        return await self.repo.search(query_str, skip=skip, limit=limit)

def get_organization_service() -> OrganizationService:
    return OrganizationService()
