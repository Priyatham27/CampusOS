import logging
from typing import List, Optional, Tuple, Dict, Any
from beanie import PydanticObjectId

from apps.api.app.core.exceptions import (
    CapabilityNotFound, CapabilityAlreadyExists, DependencyMissing,
    CircularDependency, LicenseViolation, CompatibilityViolation,
    CoreModuleProtected, OrganizationNotFound
)
from apps.api.app.models.org_engine.capability import (
    Capability, CapabilityCategory, CapabilityStatus, CapabilityVisibility, LicenseTier
)
from apps.api.app.models.org_engine.organization import Organization, SubscriptionPlan
from apps.api.app.repositories.capability import CapabilityRepository
from apps.api.app.core.database import get_db

logger = logging.getLogger("campusos.capability")

PROTECTED_SLUGS = {
    "platform", "organization", "branding", "academic",
    "settings", "audit", "storage", "notifications"
}

PLAN_VALUE_MAP = {
    SubscriptionPlan.FREE: 0,
    SubscriptionPlan.BASIC: 1,
    SubscriptionPlan.PREMIUM: 2,
    SubscriptionPlan.ENTERPRISE: 3
}

LICENSE_VALUE_MAP = {
    LicenseTier.FREE: 0,
    LicenseTier.STARTER: 1,
    LicenseTier.PRO: 2,
    LicenseTier.ENTERPRISE: 3
}

class CapabilityService:
    """
    Service Layer managing business rules, licensing, cycle detection,
    and dependency graphs for the Modules & Capabilities Engine.
    """
    def __init__(self):
        self.cap_repo = CapabilityRepository()

    async def _resolve_org(self, org_id_str: str, session=None) -> Organization:
        # Resolve Organization by organizationId or ObjectId
        org = None
        try:
            obj_id = PydanticObjectId(org_id_str)
            org = await Organization.find_one(
                Organization.id == obj_id,
                Organization.is_deleted == False,
                session=session
            )
        except Exception:
            pass

        if not org:
            org = await Organization.find_one(
                Organization.organization_id == org_id_str,
                Organization.is_deleted == False,
                session=session
            )

        if not org:
            raise OrganizationNotFound(f"Organization '{org_id_str}' not found.")
        return org

    async def _run_transactional(self, func):
        db = get_db()
        client = db.client
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await func(session)
        except Exception as e:
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower() or "sessions are not supported" in str(e).lower():
                logger.warning("Transactions are not supported on this MongoDB configuration. Running in non-transactional fallback mode.")
                return await func(None)
            else:
                logger.error(f"Capability transaction failure: {e}")
                raise e

    async def check_circular_dependency(
        self,
        org_id: PydanticObjectId,
        target_slug: str,
        dependencies: List[str],
        exclude_id: Optional[PydanticObjectId] = None,
        session=None
    ) -> None:
        """
        Runs a DFS cycle detection algorithm to verify that introducing/updating
        dependencies does not result in a loop.
        """
        existing = await Capability.find(
            Capability.organization_id == org_id,
            Capability.is_deleted == False,
            session=session
        ).to_list()

        # Build graph mapping slug -> dependencies
        graph = {}
        for c in existing:
            if exclude_id and c.id == exclude_id:
                continue
            graph[c.slug] = c.dependencies

        # Overlay target slug
        graph[target_slug] = dependencies

        # DFS state trackers: 0 = unvisited, 1 = visiting, 2 = visited
        state = {}

        def dfs(node: str) -> bool:
            state[node] = 1  # visiting
            for neighbor in graph.get(node, []):
                if state.get(neighbor, 0) == 1:
                    return True  # Cycle detected
                if state.get(neighbor, 0) == 0:
                    if dfs(neighbor):
                        return True
            state[node] = 2  # visited
            return False

        for node in graph:
            if state.get(node, 0) == 0:
                if dfs(node):
                    logger.error(f"Circular dependency validation failure: Cycle contains slug '{node}'")
                    raise CircularDependency(f"Circular dependency detected containing slug '{node}'")

    async def seed_default_capabilities(self, org_id_str: str) -> List[Capability]:
        """Seeds the 20 standard capabilities for a brand new organization."""
        org = await self._resolve_org(org_id_str)

        async def _seed(session):
            count = await self.cap_repo.count(org.id, session=session)
            
            # Static definition of the 20 default capabilities
            defaults = [
                # Core (enabled by default)
                ("platform", "Platform Core", CapabilityCategory.Core, LicenseTier.FREE, True, True, []),
                ("organization", "Organization Manager", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                ("branding", "Institutional Branding", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                ("academic", "Academic Structure", CapabilityCategory.Academic, LicenseTier.FREE, True, True, ["platform"]),
                ("settings", "Settings Engine", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                ("audit", "Compliance Audit Logs", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                ("storage", "Storage Registry", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                ("notifications", "Notification Dispatcher", CapabilityCategory.Core, LicenseTier.FREE, True, True, ["platform"]),
                # Custom/Org modules (disabled by default)
                ("events", "Events Registry", CapabilityCategory.Events, LicenseTier.FREE, False, False, ["notifications"]),
                ("attendance", "Smart Attendance", CapabilityCategory.Attendance, LicenseTier.FREE, False, False, ["academic"]),
                ("certificates", "Certificate Generator", CapabilityCategory.Certificates, LicenseTier.FREE, False, False, ["platform"]),
                ("analytics", "Institutional Analytics", CapabilityCategory.Analytics, LicenseTier.PRO, False, False, ["platform"]),
                ("student-portfolio", "Student Portfolio Manager", CapabilityCategory.Student, LicenseTier.FREE, False, False, ["academic"]),
                ("volunteer", "Volunteer Platform", CapabilityCategory.Student, LicenseTier.FREE, False, False, ["platform"]),
                ("clubs", "Student Clubs Manager", CapabilityCategory.Student, LicenseTier.FREE, False, False, ["platform"]),
                ("placement", "Placements Portal", CapabilityCategory.Placement, LicenseTier.PRO, False, False, ["academic"]),
                ("library", "Library Catalogue", CapabilityCategory.Library, LicenseTier.FREE, False, False, ["platform"]),
                ("hostel", "Hostel Allocation", CapabilityCategory.Hostel, LicenseTier.FREE, False, False, ["platform"]),
                ("transport", "Transport Tracker", CapabilityCategory.Transport, LicenseTier.FREE, False, False, ["platform"]),
                ("ai", "AI Virtual Assistant", CapabilityCategory.AI, LicenseTier.ENTERPRISE, False, False, ["analytics"]),
            ]

            seeded = []
            for idx, item in enumerate(defaults):
                slug, name, cat, tier, is_core, enabled, deps = item
                
                # Check duplicate
                if await self.cap_repo.exists(org.id, slug, session=session):
                    continue

                cap_id = f"CAP_{count + idx + 1:06d}"
                status = CapabilityStatus.ENABLED if enabled else CapabilityStatus.AVAILABLE
                visibility = CapabilityVisibility.SYSTEM if is_core else CapabilityVisibility.ORGANIZATION
                
                cap = Capability(
                    capabilityId=cap_id,
                    organizationId=org.id,
                    name=name,
                    slug=slug,
                    displayName=name,
                    description=f"Standard system module for {name}.",
                    category=cat,
                    icon="cpu" if is_core else "layers",
                    capability_version="1.0.0",
                    status=status,
                    visibility=visibility,
                    dependencies=deps,
                    requiredCapabilities=deps,
                    defaultEnabled=is_core,
                    installed=is_core,
                    enabled=enabled,
                    licenseRequired=(tier != LicenseTier.FREE),
                    licenseTier=tier
                )
                res = await self.cap_repo.create(cap, session=session)
                seeded.append(res)

            logger.info(f"Seeded {len(seeded)} default capabilities for organization ID: {org.id}")
            return seeded

        return await self._run_transactional(_seed)

    async def create_capability(self, org_id_str: str, data: dict) -> Capability:
        """Registers a custom capability."""
        org = await self._resolve_org(org_id_str)
        slug = data["slug"].lower()

        async def _create(session):
            if await self.cap_repo.exists(org.id, slug, session=session):
                raise CapabilityAlreadyExists(f"Capability slug '{slug}' already exists in this organization.")

            # Validate dependencies exist
            deps = data.get("dependencies", [])
            for dep_slug in deps:
                dep_exists = await self.cap_repo.exists(org.id, dep_slug, session=session)
                if not dep_exists:
                    raise DependencyMissing(f"Required capability dependency '{dep_slug}' is not registered.")

            # Cycle Check
            await self.check_circular_dependency(org.id, slug, deps, session=session)

            count = await self.cap_repo.count(org.id, session=session)
            cap_id = f"CAP_{count + 1:06d}"

            cap = Capability(
                capabilityId=cap_id,
                organizationId=org.id,
                name=data["name"],
                slug=slug,
                displayName=data["displayName"],
                description=data.get("description"),
                category=data.get("category", CapabilityCategory.Custom),
                icon=data.get("icon"),
                capability_version=data.get("version", "1.0.0"),
                status=data.get("status", CapabilityStatus.AVAILABLE),
                visibility=data.get("visibility", CapabilityVisibility.ORGANIZATION),
                dependencies=deps,
                requiredCapabilities=deps,
                defaultEnabled=data.get("defaultEnabled", False),
                installed=data.get("installed", False),
                enabled=data.get("enabled", False),
                licenseRequired=data.get("licenseRequired", False),
                licenseTier=data.get("licenseTier", LicenseTier.FREE),
                configuration=data.get("configuration", {}),
                metadata=data.get("metadata", {})
            )
            res = await self.cap_repo.create(cap, session=session)
            logger.info(f"Capability '{res.name}' (ID: {res.capability_id}) registered.")
            return res

        return await self._run_transactional(_create)

    async def get_capability(self, org_id_str: str, cap_id: str) -> Capability:
        org = await self._resolve_org(org_id_str)
        cap = await self.cap_repo.find_by_id(cap_id, org.id)
        if not cap:
            raise CapabilityNotFound("Capability not found.")
        return cap

    async def list_capabilities(
        self,
        org_id_str: str,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "asc",
        filters: Optional[dict] = None
    ) -> Tuple[List[Capability], int]:
        org = await self._resolve_org(org_id_str)
        items = await self.cap_repo.list(org.id, skip, limit, sort_by, sort_order, filters)
        total = await self.cap_repo.count(org.id, filters)
        return items, total

    async def list_installed(self, org_id_str: str) -> List[Capability]:
        org = await self._resolve_org(org_id_str)
        filters = {"installed": True}
        return await self.cap_repo.list(org.id, limit=1000, filters=filters)

    async def list_enabled(self, org_id_str: str) -> List[Capability]:
        org = await self._resolve_org(org_id_str)
        filters = {"enabled": True}
        return await self.cap_repo.list(org.id, limit=1000, filters=filters)

    async def update_capability(self, org_id_str: str, cap_id: str, update_data: dict) -> Capability:
        org = await self._resolve_org(org_id_str)
        cap = await self.cap_repo.find_by_id(cap_id, org.id)
        if not cap:
            raise CapabilityNotFound("Capability not found.")

        # Slugs are immutable
        if "slug" in update_data and update_data["slug"].lower() != cap.slug:
            raise CompatibilityViolation("Capability slugs are immutable and cannot be modified.")

        # Map version from schema to capability_version in model
        if "version" in update_data:
            update_data["capability_version"] = update_data.pop("version")

        # Dependency check cycle validation if updated
        if "dependencies" in update_data:
            deps = update_data["dependencies"]
            # Validate dependencies exist
            for dep_slug in deps:
                dep_exists = await self.cap_repo.exists(org.id, dep_slug)
                if not dep_exists:
                    raise DependencyMissing(f"Required capability dependency '{dep_slug}' is not registered.")
            await self.check_circular_dependency(org.id, cap.slug, deps, exclude_id=cap.id)

        res = await self.cap_repo.update(cap, update_data)
        logger.info(f"Capability ID: {cap_id} updated.")
        return res

    async def delete_capability(self, org_id_str: str, cap_id: str) -> bool:
        org = await self._resolve_org(org_id_str)
        cap = await self.cap_repo.find_by_id(cap_id, org.id)
        if not cap:
            raise CapabilityNotFound("Capability not found.")

        if cap.slug in PROTECTED_SLUGS or cap.category == CapabilityCategory.Core or cap.visibility == CapabilityVisibility.SYSTEM:
            raise CoreModuleProtected(f"Core module capability '{cap.slug}' is system-protected and cannot be deleted.")

        await self.cap_repo.delete(cap)
        logger.info(f"Capability ID: {cap_id} soft deleted.")
        return True

    async def enable_capability(self, org_id_str: str, cap_id: str) -> Capability:
        org = await self._resolve_org(org_id_str)
        cap = await self.cap_repo.find_by_id(cap_id, org.id)
        if not cap:
            raise CapabilityNotFound("Capability not found.")

        if cap.enabled:
            return cap

        # Validate dependencies are enabled
        for dep_slug in cap.dependencies:
            dep_doc = await self.cap_repo.find_by_slug(dep_slug, org.id)
            if not dep_doc or not dep_doc.enabled:
                logger.warning(f"Dependency validation failure: Cannot enable {cap.slug} because {dep_slug} is disabled/missing.")
                raise DependencyMissing(
                    f"Cannot enable capability '{cap.slug}' because required dependency "
                    f"'{dep_slug}' is not active or installed."
                )

        # Validate license tier
        org_plan_val = PLAN_VALUE_MAP.get(org.subscription.plan, 0)
        cap_tier_val = LICENSE_VALUE_MAP.get(cap.license_tier, 0)
        if org_plan_val < cap_tier_val:
            logger.warning(f"License violation: Org plan {org.subscription.plan} tried to enable {cap.slug} requiring {cap.license_tier}")
            raise LicenseViolation(
                f"Organization subscription tier '{org.subscription.plan}' does not permit enabling capability "
                f"'{cap.slug}' which requires a '{cap.license_tier}' license."
            )

        update_fields = {
            "installed": True,
            "enabled": True,
            "status": CapabilityStatus.ENABLED
        }
        res = await self.cap_repo.update(cap, update_fields)
        logger.info(f"Capability '{res.slug}' successfully enabled.")
        return res

    async def disable_capability(self, org_id_str: str, cap_id: str) -> Capability:
        org = await self._resolve_org(org_id_str)
        cap = await self.cap_repo.find_by_id(cap_id, org.id)
        if not cap:
            raise CapabilityNotFound("Capability not found.")

        if not cap.enabled:
            return cap

        # Core protection check
        if cap.slug in PROTECTED_SLUGS or cap.category == CapabilityCategory.Core or cap.visibility == CapabilityVisibility.SYSTEM:
            raise CoreModuleProtected(f"Core module capability '{cap.slug}' is system-protected and cannot be disabled.")

        # Check if another currently enabled capability depends on it
        dependent_caps = await Capability.find(
            Capability.organization_id == org.id,
            Capability.enabled == True,
            Capability.is_deleted == False
        ).to_list()

        for dc in dependent_caps:
            if dc.slug != cap.slug and cap.slug in dc.dependencies:
                logger.warning(f"Conflict: Cannot disable {cap.slug} because active module {dc.slug} depends on it.")
                raise CompatibilityViolation(
                    f"Cannot disable capability '{cap.slug}' because it is a required dependency "
                    f"for currently active capability '{dc.slug}'."
                )

        update_fields = {
            "enabled": False,
            "status": CapabilityStatus.DISABLED
        }
        res = await self.cap_repo.update(cap, update_fields)
        logger.info(f"Capability '{res.slug}' disabled.")
        return res

def get_capability_service() -> CapabilityService:
    return CapabilityService()
