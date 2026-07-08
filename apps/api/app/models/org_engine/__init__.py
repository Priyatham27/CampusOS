from apps.api.app.models.org_engine.organization import University, Organization, Branding, BrandingRevision, OrganizationSettings
from apps.api.app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from apps.api.app.models.org_engine.curriculum import Program, Course
from apps.api.app.models.org_engine.extension import Module, FeatureFlag
from apps.api.app.models.org_engine.capability import Capability

ORG_ENGINE_MODELS = [
    University,
    Organization,
    Branding,
    BrandingRevision,
    OrganizationSettings,
    AcademicYear,
    Semester,
    Department,
    Branch,
    Section,
    Program,
    Course,
    Module,
    FeatureFlag,
    Capability
]

__all__ = [
    "University",
    "Organization",
    "Branding",
    "BrandingRevision",
    "OrganizationSettings",
    "AcademicYear",
    "Semester",
    "Department",
    "Branch",
    "Section",
    "Program",
    "Course",
    "Module",
    "FeatureFlag",
    "Capability",
    "ORG_ENGINE_MODELS"
]
