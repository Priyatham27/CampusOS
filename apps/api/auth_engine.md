# Authentication Engine Documentation

This document describes the design, implementation, and future directions of the **CampusOS Authentication Engine**.

---

## 1. Architectural Strategy Pattern

Following the CTO Design Decisions, the Authentication Engine is decoupled from how users prove their identity. It implements the **Strategy Pattern** where the `AuthenticationService` delegates credentials verification to an pluggable `AuthenticationProvider`.

```mermaid
classDiagram
    class AuthenticationService {
        +providers: dict
        +login(org_id, payload, user_agent, ip) Dict
        +refresh_access_token(token) Dict
        +logout(session_id, ip) None
    }
    class AuthenticationProvider {
        <<interface>>
        +authenticate(user, payload, ip) bool
    }
    class PasswordAuthenticationProvider {
        +credential_service: CredentialService
        +authenticate(user, payload, ip) bool
    }
    class OAuthAuthenticationProvider {
        +oauth_service: OAuthService
        +authenticate(user, payload, ip) bool
    }
    class PasskeyAuthenticationProvider {
        +passkey_service: PasskeyService
        +authenticate(user, payload, ip) bool
    }

    AuthenticationService *-- AuthenticationProvider : delegates to
    AuthenticationProvider <|-- PasswordAuthenticationProvider
    AuthenticationProvider <|-- OAuthAuthenticationProvider
    AuthenticationProvider <|-- PasskeyAuthenticationProvider
```

---

## 2. Authentication Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Router as API Router
    participant Tenant as Tenant Middleware
    participant Auth as Auth Service
    participant Provider as Auth Provider
    participant DB as MongoDB Atlas

    User->>Router: POST /api/v1/auth/login (credentials)
    Router->>Tenant: Intercept and resolve Tenant Context
    Tenant-->>Router: Set active organizationId
    Router->>Auth: login(organizationId, payload, agent, ip)
    Auth->>DB: Find User by email/username in Org
    DB-->>Auth: User record (status active?)
    
    Auth->>Provider: authenticate(user, payload, ip)
    Note over Provider: PasswordProvider asks CredentialService
    Provider-->>Auth: True (verification success)
    
    Auth->>DB: Create Session & RefreshToken references
    Auth->>Auth: Issue short-lived JWT Access Token
    Auth->>DB: Insert Successful Login Audit Event
    Auth-->>Router: Auth data (accessToken, refreshToken, expiresIn, user)
    Router->>User: Set HttpOnly Cookies & Return JSON Response
```

---

## 3. JWT Claims & Lifecycle Diagram

### Access Token Claims Layout
The access token is short-lived (configured in platform settings, typically 15 minutes). It contains the following custom claims:
- `sub`: User ID
- `userId`: User ID
- `organizationId`: Scoped Organization ID
- `roles`: Scoped list of role slugs (e.g. `["student"]`)
- `permissions`: Minimal list of permission slugs (e.g. `["settings:read"]`)
- `sessionId`: Session reference ID
- `iat`: Timestamp issued at
- `exp`: Timestamp expires at
- `iss`: Issuer ("CampusOS")
- `aud`: Audience ("campusos-api")

### JWT Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Issued : Login Request Authenticated
    Issued --> Active : Token not expired
    Active --> Expired : Exceeded expiration time (15 mins)
    Expired --> Refreshed : POST /auth/refresh with valid Refresh Token
    Refreshed --> Issued : Generate new short-lived Access Token
    Active --> Revoked : POST /auth/logout (Revokes Refresh reference and deletes session)
    Revoked --> [*]
```

---

## 4. Future Integrations

Because of the Strategy pattern, future login methods plug seamlessly into the Authentication Engine.

### 4.1. Future Multi-Factor Authentication (MFA)
1. **Verification**: During password or OAuth verification, if `user.mfa_enabled` is `True`, instead of returning session tokens, return a partial authentication response:
   ```json
   {
     "success": true,
     "message": "MFA challenge required.",
     "data": {
       "mfaRequired": true,
       "mfaToken": "temporary_mfa_sign_token"
     }
   }
   ```
2. **Resolution**: The client submits the TOTP code to `/api/v1/auth/mfa/verify` along with the `mfaToken`. A `MFAAuthenticationProvider` validates the TOTP code, and upon success, triggers final session and JWT issuance.

### 4.2. Future OAuth Providers (Google, Microsoft)
1. Register a `GoogleAuthenticationProvider` inside the `AuthenticationService`.
2. The endpoint receives `provider = "google"` and `payload = {"idToken": "google_jwt_token"}`.
3. The provider verifies the Google ID token signature, extracts the user email, maps it to a user and org, and completes the login if verification succeeds.

### 4.3. Future Passkey (WebAuthn) Provider
1. Register a `PasskeyAuthenticationProvider`.
2. The login payload submits the WebAuthn assertion signature challenge.
3. The provider verifies the signature challenge against the public key stored in the user's passkey `Credential` document, completing authentication.
