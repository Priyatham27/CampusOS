from typing import List

ROLE_HIERARCHY = {
    "super-admin": ["org-admin", "faculty", "event-coordinator", "volunteer", "student", "guest"],
    "org-admin": ["faculty", "event-coordinator", "volunteer", "student", "guest"],
    "faculty": ["event-coordinator", "volunteer", "student", "guest"],
    "event-coordinator": ["volunteer", "student", "guest"],
    "volunteer": ["student", "guest"],
    "student": ["guest"],
    "guest": [],
    
    # Standard underscore variants to maximize parsing compatibility
    "super_admin": ["org_admin", "faculty", "event_coordinator", "volunteer", "student", "guest"],
    "org_admin": ["faculty", "event_coordinator", "volunteer", "student", "guest"],
    "organization_admin": ["faculty", "event_coordinator", "volunteer", "student", "guest"],
    "event_coordinator": ["volunteer", "student", "guest"],
}

def expand_roles(roles: List[str]) -> List[str]:
    """
    Expands a given list of role slugs to include all inherited sub-roles
    in the defined CampusOS role hierarchy.
    """
    expanded = set()
    for role in roles:
        expanded.add(role)
        inherited = ROLE_HIERARCHY.get(role.lower(), [])
        for r in inherited:
            expanded.add(r)
    return list(expanded)
