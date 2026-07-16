import logging
from datetime import datetime, time
from typing import Optional, List, Dict, Any

from app.models.identity.policy import Policy

logger = logging.getLogger("campusos.core.policy_engine")

def match_wildcard(pattern: str, value: str) -> bool:
    """
    Checks if a pattern (supporting '*' wildcards) matches a target value.
    For example: 'events.*' matches 'events.create'
    """
    if pattern == "*":
        return True
    if "*" in pattern:
        prefix = pattern.split("*")[0]
        return value.startswith(prefix)
    return pattern == value

class PolicyEngine:
    """
    Matches and evaluates policy conditions (e.g. time range, department filters,
    and subjects/actions/resources wildcard evaluation).
    """
    @staticmethod
    def evaluate_conditions(policy: Policy, context_data: Dict[str, Any]) -> bool:
        """
        Validates if all specific conditions (time, department) of a policy are met.
        """
        if not policy.conditions:
            return True

        # 1. Time range constraint
        if "time_range" in policy.conditions:
            time_cfg = policy.conditions["time_range"]
            start_str = time_cfg.get("start")
            end_str = time_cfg.get("end")
            if start_str and end_str:
                try:
                    now_time = None
                    if "time" in context_data:
                        t_parts = context_data["time"].split(":")
                        now_time = time(int(t_parts[0]), int(t_parts[1]))
                    else:
                        now_time = datetime.utcnow().time()

                    s_parts = start_str.split(":")
                    e_parts = end_str.split(":")
                    start_time = time(int(s_parts[0]), int(s_parts[1]))
                    end_time = time(int(e_parts[0]), int(e_parts[1]))

                    if not (start_time <= now_time <= end_time):
                        logger.info(f"Policy '{policy.name}' blocked: current time {now_time} outside {start_str}-{end_str}.")
                        return False
                except Exception as e:
                    logger.warning(f"Error parsing time range conditions for policy '{policy.name}': {e}")
                    return False

        # 2. Department constraints
        if "departments" in policy.conditions:
            allowed_deps = policy.conditions["departments"]
            user_dep = context_data.get("department")
            if not user_dep or user_dep not in allowed_deps:
                logger.info(f"Policy '{policy.name}' blocked: user department '{user_dep}' not in {allowed_deps}.")
                return False

        return True

    def matches_policy(
        self,
        policy: Policy,
        user_id_str: str,
        active_roles: List[str],
        permission: str,
        resource: str
    ) -> bool:
        """
        Determines if a policy matches the subject, action, and resource criteria.
        """
        # Subject match: matches user_id, active_roles, or wildcard '*'
        subject_matched = False
        if "*" in policy.subjects:
            subject_matched = True
        else:
            for s in policy.subjects:
                if match_wildcard(s, user_id_str):
                    subject_matched = True
                    break
                for role in active_roles:
                    if match_wildcard(s, role):
                        subject_matched = True
                        break
                if subject_matched:
                    break

        if not subject_matched:
            return False

        # Action (permission) match: e.g. events.create
        action_matched = any(match_wildcard(a, permission) for a in policy.actions)
        if not action_matched:
            return False

        # Resource match
        resource_matched = any(match_wildcard(r, resource) for r in policy.resources)
        if not resource_matched:
            return False

        return True
