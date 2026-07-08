# Changelog

All notable changes to the CampusOS codebase will be documented in this file.

## [1.2.0] - 2026-07-08

### Added
- **Branding Bounded Context**: Fully decoupled institutional branding engines from core Organization CRUD APIs.
- **Branding models**:
  - `Branding`: Extended model with custom Hex color validators, image URL checks, and support for over 30 properties (detailed colors, radii, fonts, support details, and landing assets).
  - `BrandingRevision`: Change audit history tracking documents.
- **Branding Repository (`BrandingRepository`)**:
  - CRUD operations including `get`, `update`, `reset`, `uploadLogo`, `uploadBanner`, `deleteLogo`, and `history`.
  - Generic alias translation for robust queries over Pydantic field names.
- **Branding Service (`BrandingService`)**:
  - Logic layers for publishes, preview mode buffers (`preview_config`), resets, and linear rollbacks.
  - Pillow-backed dimensions/aspect-ratio validation logic for institutional logos and landscape banners.
  - CSS custom properties generator and Tailwind extend JSON token compile engine.
- **Branding Router (`BrandingRouter`)**:
  - Nested router mounted on `/api/v1/organizations/{organizationId}/branding`.
  - Endpoints for retrieval, partial updates, resets, logo/banner uploads, deletes, history logs, and rollback executions.
  - Structured activity logging inside compliance audit trail collections.
- **Automated Tests**:
  - Repository lifecycle tests (`tests/test_branding_repository.py`).
  - Service logic and format validation tests (`tests/test_branding_service.py`).
  - API HTTP integration lifecycle tests (`tests/test_branding_api.py`).

### Fixed
- **Primary Key Object ID resolution**: Modified model configuration alias generator in `BaseDocument` to ignore `id` mappings to prevent loading retrieved documents with `id=None`.
- **Database Casing Mappings**: Modified indexes inside Branding Beanie models to use camelCase aliases (`organizationId`) matching the MongoDB physical schemas to avoid unique key index duplicates on nulls.

## [1.3.0] - 2026-07-08

### Added
- **Academic Structure Context**: Built isolated academic structure contexts to map organization department, curriculum, and sequential calendars.
- **Academic Models Refinement**: Extended `Branch`, `Section`, and `Course` schemas to include `organization_id` (aliased as `organizationId`) and added multi-tenant unique constraint compound indices.
- **Academic Repositories (`AcademicYearRepository`, etc.)**: Added individual collection repositories in `repositories/academic.py` supporting filters, counts, sorting, pagination, and bulk inserts.
- **Academic Service (`AcademicService`)**: Created business rules validator in `services/academic.py`:
  - Restricts current Academic Years to one active instance per organization.
  - Validates chronological start/end dates.
  - Implements sequence validations on Semesters, restricting deletes/creates to chronological sequences.
  - Validates unique code values and references on Programs, Branches, Sections, and Courses.
  - Handles transactional bulk creates and updates with non-replica set local fallbacks.
- **Academic Router (`academic_router`)**: Created REST endpoints in `api/v1/academic.py` matching organization routes:
  - Scopes all queries and writes inside the Organization.
  - Adds `/bulk` endpoints for POST/PATCH/DELETE actions.
  - Ensures `/bulk` endpoints are registered before details `{id}` endpoints to prevent FastAPI path parameter matching collisions.
  - Logs compliance events for creations, updates, soft-deletes, and bulk transactions inside the compliance audit trails collection.
- **Automated Tests**:
  - Added repository lifecycle tests (`tests/test_academic_repository.py`).
  - Added business validation rules and sequential semester sequence checks (`tests/test_academic_service.py`).
  - Added REST integration and bulk endpoint test suite (`tests/test_academic_api.py`).

## [1.4.0] - 2026-07-08

### Added
- **Capabilities Registry Context**: Built Modules & Capabilities engine to allow decoupled, plugin-based capability installations and validation.
- **Capabilities Database Model (`Capability`)**: Designed Beanie ODM document with category, status, visibility, and license tier enums, scoped by tenant with compound unique indexes.
- **Exceptions Definition**: Created specialized capability exception handlers (`CapabilityNotFound`, `DependencyMissing`, `CircularDependency`, `LicenseViolation`, `CompatibilityViolation`, `CoreModuleProtected`).
- **Capabilities Repository (`CapabilityRepository`)**: Implemented standard CRUD, finders, exist checks, lists, and counts.
- **Capabilities Service (`CapabilityService`)**: Implemented business validation and dependency resolution logic:
  - DFS circular dependency checker with recursive traversal path loops detection.
  - License validation algorithm mapping subscription plan levels to license tier numeric values.
  - Active dependent disable validation block preventing shutting down capabilities required by other active tools.
  - Core system capabilities protection block preventing deletion/disablement of standard platform nodes.
  - Seeding utility dynamically building the 20 standard capabilities for educational tenants.
- **Capabilities Router (`capability_router`)**: Created REST endpoints in `api/v1/capability.py` mounted on `/api/v1/capabilities`:
  - List capability catalogs with pagination, sorting, and categories/enabled/installed filters.
  - Seed, install, enable, disable, and get individual items.
  - Log audit trace lines.
- **Automated Tests**:
  - Added repository tests (`test_capability_repository.py`).
  - Added service tests (`test_capability_service.py`) covering cycles, licenses, and disable rules.
  - Added API integration tests (`test_capability_api.py`) validating JSON outputs and REST methods.


