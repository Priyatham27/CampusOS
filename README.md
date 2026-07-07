# CampusOS

> **Production-grade white-label multi-tenant SaaS platform powering educational institutions.**

CampusOS is a platform that allows colleges and universities to run their own branded digital campus portal — events, attendance, clubs, certificates — all from a single codebase with per-institution customization.

---

## 🏗️ Architecture

```
CampusOS/
├── apps/
│   ├── api/              ← FastAPI Backend (Python 3.12)
│   │   ├── app/
│   │   │   ├── api/v1/   ← Route handlers
│   │   │   ├── core/     ← Config, DB, Security, Logging
│   │   │   ├── middleware/  ← Tenant resolver, Auth
│   │   │   ├── models/   ← Beanie ODM models (MongoDB)
│   │   │   ├── repositories/ ← Data access layer
│   │   │   ├── schemas/  ← Pydantic I/O schemas
│   │   │   └── services/ ← Business logic layer
│   │   └── tests/        ← Pytest async test suite
│   └── web/              ← Next.js Frontend (coming soon)
```

---

## 🚀 Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.12 |
| Database | MongoDB Atlas + Beanie ODM |
| Auth | JWT (HttpOnly cookies) |
| Cache | Redis (with InMemory fallback) |
| File Upload | Cloudinary (placeholder) |
| Frontend | Next.js 14 (planned) |

---

## ⚙️ Setup

### Prerequisites
- Python 3.12+
- MongoDB (local or Atlas)
- Redis (optional, falls back to in-memory)

### Backend Setup

```bash
cd apps/api

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with your MongoDB URI and secrets

# Run development server
uvicorn apps.api.app.main:app --reload --port 8000
```

### Environment Variables

Create `apps/api/.env`:
```env
MONGODB_URL=mongodb://localhost:27017/campusos
SECRET_KEY=your-production-secret-key-here
ENV=development
```

---

## 🧪 Running Tests

```bash
# From root directory
python -m pytest apps/api/tests/ -v
```

All 11 tests cover:
- Repository layer (CRUD, soft delete, conflict checks)
- Service layer (business logic, conflict detection)
- API integration (full HTTP lifecycle)

---

## 🏢 Multi-Tenancy Architecture

Every request resolves a **Tenant** via:
1. `X-Tenant-Slug` header (dev/debug)
2. Custom domain match (`portal.college.edu`)
3. Subdomain match (`college.campusos.com`)
4. Default fallback tenant

---

## 📦 Phase 1 — Platform Foundation ✅

- [x] Authentication (JWT via HttpOnly cookies)
- [x] Multi-tenancy (domain + header resolution)
- [x] Organization Engine (full CRUD + soft delete)
- [x] Users, Roles & Permissions (RBAC)
- [x] Audit Logging
- [x] System Settings
- [x] Feature Flags
- [x] File Upload (Cloudinary placeholder)

## 📦 Phase 2 — Org Engine (In Progress)

- [ ] Department, Program, Course models
- [ ] Academic Year & Semester management
- [ ] Branch & Section management

---

## 📐 API Standards

All endpoints follow:
```json
{
  "success": true,
  "message": "Human readable message",
  "data": {},
  "meta": { "page": 1, "limit": 10, "total": 100 },
  "errors": []
}
```

---

## 📄 License

Proprietary — CampusOS © 2025. All rights reserved.
