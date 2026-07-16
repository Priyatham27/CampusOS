from app.models.org_engine.organization import University, Organization, Branding, BrandingRevision, OrganizationSettings
from app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from app.models.org_engine.curriculum import Program, Course
from app.models.org_engine.extension import Module, FeatureFlag
from app.models.org_engine.capability import Capability
from app.models.org_engine.config import Configuration

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
    Capability,
    Configuration
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
    "Configuration",
    "ORG_ENGINE_MODELS"
]
