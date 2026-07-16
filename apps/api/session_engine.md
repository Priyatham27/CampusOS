# Session & Device Management Engine

This document provides a technical specification of the **Session & Device Management Engine** built for CampusOS (Story 2.4).

---

## 1. Architecture Overview

The Session Engine acts as the central state-management authority for authenticated requests. While the Authentication Engine validates initial credentials, the Session Engine tracks active sessions, devices, rotation, and security contexts over time.

```mermaid
graph TD
    A[Incoming Request] --> B[TenantMiddleware]
    B --> C[IdentityMiddleware]
    C --> D{JWT Present?}
    D -- No --> E[Proceed as Anonymous]
    D -- Yes --> F[Decode Access Token]
    F --> G[Validate Session Timeouts]
    G --> H[Query Cache / MongoDB]
    H --> I[Map User, Org, Roles & Permissions]
    I --> J[Construct IdentityContext]
    J --> K[Bind to ContextVar & Request]
    K --> L[Forward to Downstream Handlers]
```

---

## 2. Identity Context Layout

Every authenticated request resolves to a consolidated `IdentityContext` made available via thread-safe ContextVars and FastAPI dependencies:

```python
class IdentityContext(BaseModel):
    user: User                     # Active Beanie User record
    organization: Organization     # Active Organization record
    active_roles: List[str]        # Slugs of user's active RBAC Roles
    active_session: Session        # Current active Session document
    device: Optional[Device]       # Recognized client Device profile
    permissions: List[str]         # Flat list of RBAC privilege slugs
    locale: str                    # Client browser locale preference
    timezone: str                  # Scoped organization timezone
    feature_flags: Dict[str, bool] # Active runtime flag definitions
```

---

## 3. Refresh Token Rotation (RTR) & Replay Prevention

Refresh Token Rotation ensures refresh keys can only be used once. If a compromised/rotated refresh token is re-sent, a replay attack is detected and the system instantly revokes the entire session family.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client Browser
    participant API as Sessions Router
    participant Service as Session Service
    participant Cache as Redis Cache
    participant DB as MongoDB Atlas

    Client->>API: POST /sessions/refresh (token_A)
    API->>Service: refresh_session(token_A)
    Service->>Cache: Query refresh:token_A
    Cache-->>Service: Token Record (revoked = False)
    
    Note over Service: 1. Rotate token_A -> token_B
    Service->>DB: Update token_A (revoked = True)
    Service->>Cache: Delete refresh:token_A
    
    Service->>DB: Insert token_B (revoked = False)
    Service->>Cache: Set refresh:token_B (TTL)
    Service-->>Client: New Access Token + token_B
    
    Note over Client: --- REPLAY ATTACK BY ATTACKER ---
    Client->>API: POST /sessions/refresh (token_A again!)
    API->>Service: refresh_session(token_A)
    Service->>DB: Query token_A (finds revoked = True!)
    
    Note over Service: 2. Replay detected! Revoke family.
    Service->>DB: Delete all active sessions for User
    Service->>Cache: Delete user sessions cache keys
    Service-->>Client: HTTP 401 Unauthorized (Replay Attack)
```

---

## 4. Timeout Policies

### 4.1. Absolute Timeout
Configured via `security.sessions.absolute_timeout_minutes` (default 7 days). Exceeding this window triggers immediate session deletion regardless of user activity.

### 4.2. Idle Timeout
Configured via `security.sessions.idle_timeout_minutes` (default 30 minutes). Every request updates `last_activity`. If the duration between requests exceeds this value, the session is invalidated.
