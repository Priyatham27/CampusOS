from apps.api.app.models.org_engine.organization import University, Organization, Branding, OrganizationSettings
from apps.api.app.models.org_engine.academic import AcademicYear, Semester, Department, Branch, Section
from apps.api.app.models.org_engine.curriculum import Program, Course
from apps.api.app.models.org_engine.extension import Module, FeatureFlag

ORG_ENGINE_MODELS = [
    University,
    Organization,
    Branding,
    OrganizationSettings,
    AcademicYear,
    Semester,
    Department,
    Branch,
    Section,
    Program,
    Course,
    Module,
    FeatureFlag
]

__all__ = [
    "University",
    "Organization",
    "Branding",
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
    "ORG_ENGINE_MODELS"
]
