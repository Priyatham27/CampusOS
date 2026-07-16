from typing import Dict
from app.core.config import settings
from app.core.logger import logger

class FeatureFlagSystem:
    def __init__(self):
        self.default_flags = settings.FEATURE_FLAGS

    def is_enabled(self, flag_name: str, org_overrides: Dict[str, bool] = None) -> bool:
        """Check if a feature is enabled. Takes optional overrides from organization branding configurations."""
        if org_overrides and flag_name in org_overrides:
            return org_overrides[flag_name]
        
        # Fallback to system configuration
        enabled = self.default_flags.get(flag_name, False)
        return enabled

    def get_all_flags(self, org_overrides: Dict[str, bool] = None) -> Dict[str, bool]:
        """Get all feature flags with organization overrides applied."""
        flags = self.default_flags.copy()
        if org_overrides:
            flags.update(org_overrides)
        return flags

feature_flags = FeatureFlagSystem()
