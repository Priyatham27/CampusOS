import pytest
import hashlib
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from httpx import AsyncClient

from apps.api.app.models.identity.user import User, UserStatus
from apps.api.app.models.identity.credential import Credential, CredentialType
from apps.api.app.models.identity.security import SecurityEvent, SecurityEventType, PasswordResetToken
from apps.api.app.services.credential import CredentialService
from apps.api.app.core.security import hash_password_argon2, verify_password_argon2
from apps.api.app.core.credential_exceptions import (
    CredentialException,
    CredentialNotFound,
    CredentialAlreadyExists,
    InvalidPassword,
    PasswordPolicyViolation,
    CredentialLocked,
    EmailNotVerified
)

pytestmark = pytest.mark.asyncio

@pytest.fixture
def credential_service():
    return CredentialService()

async def create_test_user(email="test@avanthi.edu", email_verified=True) -> User:
    org_id = PydanticObjectId()
    user = User(
        userId="USR_111111",
        organizationId=org_id,
        username="test.user.auth",
        email=email,
        status=UserStatus.ACTIVE,
        emailVerified=email_verified
    )
    return await user.insert()

async def test_argon2_hashing():
    plain = "SecurePass123!"
    hashed = hash_password_argon2(plain)
    assert hashed.startswith("$argon2id$")
    assert verify_password_argon2(plain, hashed) is True
    assert verify_password_argon2("wrongpass", hashed) is False

async def test_create_credential_success(credential_service):
    user = await create_test_user()
    
    cred = await credential_service.create_credential(
        user_id_str=str(user.id),
        password="Password123!"
    )
    
    assert cred.credential_id.startswith("CRD_")
    assert cred.user_id == user.id
    assert cred.type == CredentialType.PASSWORD
    assert verify_password_argon2("Password123!", cred.password_hash) is True
    assert len(cred.password_history) == 1

async def test_create_credential_unverified_email_fails(credential_service):
    user = await create_test_user(email_verified=False)
    
    with pytest.raises(EmailNotVerified):
        await credential_service.create_credential(
            user_id_str=str(user.id),
            password="Password123!"
        )

async def test_create_duplicate_credential_fails(credential_service):
    user = await create_test_user()
    await credential_service.create_credential(user_id_str=str(user.id), password="Password123!")
    
    with pytest.raises(CredentialAlreadyExists):
        await credential_service.create_credential(user_id_str=str(user.id), password="Password456!")

async def test_change_password_success(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="OldPassword123!")
    
    updated_cred = await credential_service.change_password(
        user_id_str=str(user.id),
        current_password="OldPassword123!",
        new_password="NewPassword456!"
    )
    
    assert verify_password_argon2("NewPassword456!", updated_cred.password_hash) is True
    assert len(updated_cred.password_history) == 2
    assert updated_cred.failed_login_attempts == 0
    
    # Check security event is logged
    events = await SecurityEvent.find(SecurityEvent.user_id == user.id).to_list()
    assert len(events) >= 1
    assert events[-1].type == SecurityEventType.PASSWORD_CHANGED

async def test_change_password_reuse_fails(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="OldPassword123!")
    
    with pytest.raises(Exception) as exc_info:
        await credential_service.change_password(
            user_id_str=str(user.id),
            current_password="OldPassword123!",
            new_password="OldPassword123!"
        )
    assert "reuse" in str(exc_info.value).lower() or "same" in str(exc_info.value).lower()

async def test_change_password_policy_violation_fails(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="OldPassword123!")
    
    # Too short
    with pytest.raises(PasswordPolicyViolation):
        await credential_service.change_password(
            user_id_str=str(user.id),
            current_password="OldPassword123!",
            new_password="short"
        )

async def test_failed_attempts_lockout(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="CorrectPassword123!")
    
    # Try wrong passwords
    for i in range(4):
        with pytest.raises(InvalidPassword):
            await credential_service.change_password(
                user_id_str=str(user.id),
                current_password="WrongPassword",
                new_password="SomeNewPassword1!"
            )
            
    # The 5th failed attempt triggers account lockout
    with pytest.raises(CredentialLocked):
        await credential_service.change_password(
            user_id_str=str(user.id),
            current_password="WrongPassword",
            new_password="SomeNewPassword1!"
        )
        
    # Verify account is locked
    cred_db = await Credential.find_one(Credential.user_id == user.id)
    assert cred_db.is_locked is True
    assert cred_db.locked_until is not None
    assert cred_db.failed_login_attempts >= 5
    
    # Check locked security event is logged
    events = await SecurityEvent.find(
        SecurityEvent.user_id == user.id,
        SecurityEvent.type == SecurityEventType.ACCOUNT_LOCKED
    ).to_list()
    assert len(events) >= 1

async def test_reset_password_token(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="OldPassword123!")
    
    # Generate token
    token_str = "abc123xyz"
    token_hash_val = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
    
    token_doc = PasswordResetToken(
        resetTokenId="PRT_000001",
        userId=user.id,
        tokenHash=token_hash_val,
        expiresAt=datetime.utcnow() + timedelta(hours=1),
        used=False
    )
    await token_doc.insert()
    
    # Reset password
    res = await credential_service.reset_password(
        user_id_str=str(user.id),
        token=token_str,
        new_password="TokenResetPassword456!"
    )
    
    assert verify_password_argon2("TokenResetPassword456!", res.password_hash) is True
    
    # Assert token marked used
    updated_token = await PasswordResetToken.find_one(PasswordResetToken.id == token_doc.id)
    assert updated_token.used is True

async def test_force_password_reset(credential_service):
    user = await create_test_user()
    cred = await credential_service.create_credential(user_id_str=str(user.id), password="OldPassword123!")
    
    res = await credential_service.force_password_reset(
        user_id_str=str(user.id),
        new_password="ForcedPassword123!"
    )
    
    assert verify_password_argon2("ForcedPassword123!", res.password_hash) is True
    assert res.requires_password_change is True

async def test_api_routes(async_client, credential_service):
    user = await create_test_user(email="api_test@avanthi.edu")
    
    # 1. Create Credential
    payload = {
        "userId": str(user.id),
        "password": "ApiPassword123!",
        "type": "password"
    }
    response = await async_client.post("/api/v1/credentials", json=payload)
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["userId"] == str(user.id)
    assert "passwordHash" not in res_data["data"]  # Ensure hash is never exposed!
    
    # 2. Get Credential
    response = await async_client.get(f"/api/v1/credentials/{str(user.id)}")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["data"]["userId"] == str(user.id)
    
    # 3. Change Password
    payload_change = {
        "userId": str(user.id),
        "currentPassword": "ApiPassword123!",
        "newPassword": "NewApiPassword123!"
    }
    response = await async_client.post("/api/v1/credentials/change-password", json=payload_change)
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 4. Patch Credential
    payload_patch = {
        "isLocked": True,
        "requiresPasswordChange": True
    }
    response = await async_client.patch(f"/api/v1/credentials/{str(user.id)}", json=payload_patch)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["isLocked"] is True
    assert res_data["data"]["requiresPasswordChange"] is True
