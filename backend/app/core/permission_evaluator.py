import logging
from typing import Optional, List, Dict, Any
from beanie import PydanticObjectId

from app.models.identity.user import User
from app.models.org_engine.organization import Organization
from app.models.identity.rbac import Role, Permission, RolePermission
from app.core.role_resolver import expand_roles
from app.core.policy_engine import PolicyEngine, match_wildcard
from app.repositories.authorization import AuthorizationRepository
from app.core.authorization_exceptions import AuthorizationDenied, PolicyViolation
from app.models.identity.security import SecurityEvent, SecurityEventType, SecurityEventSeverity

logger = logging.getLogger("campusos.core.permission_evaluator")

class PermissionEvaluator:
    """
    Evaluates permissions in a precise order:
    1. Super Admin Override
    2. Explicit Deny (Policies)
    3. Explicit Allow (Policies)
    4. Role Inheritance (RBAC)
    5. Default Deny
    """
    def __init__(self):
        self.repo = AuthorizationRepository()
        self.policy_engine = PolicyEngine()

    async def evaluate(
        self,
        user: User,
        org: Organization,
        active_roles: List[str],
        permission: str,
        resource: str = "*",
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        context_data = context_data or {}
        user_id_str = str(user.id)

        # 1. Super Admin Override
        if "super-admin" in active_roles or "super_admin" in active_roles:
            logger.info(f"Access granted: Super Admin override for user '{user_id_str}'.")
            return True

        # Resolve active policies for this organization
        policies = await self.repo.list_active_policies_for_org(org.id)

        # Filter policies that match subject, action, resource, and pass conditions
        matching_policies = []
        for policy in policies:
            if self.policy_engine.matches_policy(policy, user_id_str, active_roles, permission, resource):
                if self.policy_engine.evaluate_conditions(policy, context_data):
                    matching_policies.append(policy)

        # Sort policies by Priority (lower integer = higher priority)
        matching_policies.sort(key=lambda p: p.priority)

        # 2. Explicit Deny
        for policy in matching_policies:
            if policy.effect == "DENY":
                logger.warning(f"Access blocked: Explicit DENY policy '{policy.name}' for user '{user_id_str}'.")
                await self._audit_authorization_failure(
                    org.id, user.id, permission, f"Explicit DENY policy matching: {policy.name}"
                )
                raise PolicyViolation(f"Policy violation: Access denied by policy '{policy.name}'.")

        # 3. Explicit Allow
        for policy in matching_policies:
            if policy.effect == "ALLOW":
                logger.info(f"Access granted: Explicit ALLOW policy '{policy.name}' for user '{user_id_str}'.")
                return True

        # 4. Role Inheritance (RBAC check)
        expanded_roles = expand_roles(active_roles)
        role_objs = await Role.find({"organizationId": org.id, "slug": {"$in": expanded_roles}}).to_list()
        role_ids = [r.id for r in role_objs]

        if role_ids:
            role_perms = await RolePermission.find({"roleId": {"$in": role_ids}}).to_list()
            perm_ids = [rp.permission_id for rp in role_perms]
            perms = await Permission.find({"_id": {"$in": perm_ids}}).to_list()
            granted_permissions = [p.slug for p in perms]

            if any(match_wildcard(gp, permission) for gp in granted_permissions):
                logger.info(f"Access granted: RBAC permission '{permission}' resolved via roles {expanded_roles}.")
                return True

        # 5. Default Deny
        logger.warning(f"Access blocked: Default DENY reached for user '{user_id_str}' requesting '{permission}'.")
        await self._audit_authorization_failure(
            org.id, user.id, permission, "Default DENY fallback reached"
        )
        return False

    async def _audit_authorization_failure(
        self,
        org_id: PydanticObjectId,
        user_id: PydanticObjectId,
        permission: str,
        reason: str
    ) -> None:
        try:
            count = await SecurityEvent.find({}).count()
            event = SecurityEvent(
                securityEventId=f"SEC_{count + 1:06d}",
                organizationId=org_id,
                userId=user_id,
                type=SecurityEventType.PASSWORD_CHANGED, # placeholder for audit
                severity=SecurityEventSeverity.WARNING,
                metadata={
                    "message": f"Authorization failure for permission '{permission}'. Reason: {reason}.",
                    "permission": permission,
                    "reason": reason
                }
            )
            await event.insert()
        except Exception as e:
            logger.error(f"Failed to record authorization failure audit log: {e}")
