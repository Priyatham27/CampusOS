from fastapi import APIRouter, Depends, status, Path
from typing import List
from beanie import PydanticObjectId

from apps.api.app.core.identity_context import IdentityContext, get_current_identity
from apps.api.app.schemas.schemas import APIResponse
from apps.api.app.schemas.authorization_schemas import (
    PolicyCreate,
    PolicyResponse,
    PolicyUpdate
)
from apps.api.app.services.authorization import AuthorizationService
from apps.api.app.repositories.authorization import AuthorizationRepository

router = APIRouter()

def get_auth_service() -> AuthorizationService:
    return AuthorizationService()

@router.get(
    "",
    response_model=APIResponse[List[PolicyResponse]],
    summary="List all organization policies"
)
async def list_policies(
    context: IdentityContext = Depends(get_current_identity),
    repo: AuthorizationRepository = Depends(AuthorizationRepository)
):
    policies = await repo.list_policies(context.organization.id)
    responses = [PolicyResponse.model_validate(p) for p in policies]
    return APIResponse(
        success=True,
        message="Policies resolved successfully.",
        data=responses
    )

@router.post(
    "",
    response_model=APIResponse[PolicyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create organization policy"
)
async def create_policy(
    payload: PolicyCreate,
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service)
):
    policy = await service.create_policy(
        name=payload.name,
        effect=payload.effect,
        subjects=payload.subjects,
        actions=payload.actions,
        resources=payload.resources,
        organization_id=context.organization.id,
        priority=payload.priority,
        description=payload.description,
        conditions=payload.conditions
    )
    return APIResponse(
        success=True,
        message="Policy created successfully.",
        data=PolicyResponse.model_validate(policy)
    )

@router.patch(
    "/{policyId}",
    response_model=APIResponse[PolicyResponse],
    summary="Update organization policy properties"
)
async def update_policy(
    payload: PolicyUpdate,
    policy_id: str = Path(..., alias="policyId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service),
    repo: AuthorizationRepository = Depends(AuthorizationRepository)
):
    policy = await repo.get_policy_by_id(policy_id)
    if not policy or policy.organization_id != context.organization.id:
        from apps.api.app.core.authorization_exceptions import PolicyViolation
        raise PolicyViolation("Policy not found or access denied.")

    if policy.is_system:
        from apps.api.app.core.authorization_exceptions import ImmutableRole
        raise ImmutableRole("System policies cannot be modified.")

    policy.name = payload.name
    policy.effect = payload.effect
    policy.priority = payload.priority
    policy.subjects = payload.subjects
    policy.actions = payload.actions
    policy.resources = payload.resources
    policy.conditions = payload.conditions
    policy.description = payload.description
    policy.is_active = payload.is_active

    updated = await repo.update_policy(policy)
    return APIResponse(
        success=True,
        message="Policy updated successfully.",
        data=PolicyResponse.model_validate(updated)
    )

@router.delete(
    "/{policyId}",
    response_model=APIResponse[None],
    summary="Delete organization policy"
)
async def delete_policy(
    policy_id: str = Path(..., alias="policyId"),
    context: IdentityContext = Depends(get_current_identity),
    service: AuthorizationService = Depends(get_auth_service),
    repo: AuthorizationRepository = Depends(AuthorizationRepository)
):
    policy = await repo.get_policy_by_id(policy_id)
    if not policy or policy.organization_id != context.organization.id:
        from apps.api.app.core.authorization_exceptions import PolicyViolation
        raise PolicyViolation("Policy not found or access denied.")

    if policy.is_system:
        from apps.api.app.core.authorization_exceptions import ImmutableRole
        raise ImmutableRole("System policies cannot be deleted.")

    await repo.delete_policy(policy_id)
    return APIResponse(
        success=True,
        message="Policy deleted successfully.",
        data=None
    )
