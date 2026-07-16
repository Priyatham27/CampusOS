from typing import Dict, Any

def validate_profile_completeness(profile_data: Dict[str, Any]) -> None:
    """Validate that the profile contains required completeness fields."""
    first_name = profile_data.get("first_name") or profile_data.get("firstName")
    last_name = profile_data.get("last_name") or profile_data.get("lastName")

    if not first_name or not first_name.strip():
        raise ValueError("Profile completeness validation failed: 'firstName' is required and cannot be empty.")
    if not last_name or not last_name.strip():
        raise ValueError("Profile completeness validation failed: 'lastName' is required and cannot be empty.")
