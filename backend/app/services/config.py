import logging
import hashlib
import json
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from beanie import PydanticObjectId

from app.core.exceptions import (
    ConfigurationNotFound, DuplicateConfiguration, InvalidScope,
    InvalidEnvironment, RolloutConflict, FeatureNotFound, OrganizationNotFound
)
from app.models.org_engine.config import (
    Configuration, FeatureFlag, ConfigScope, ConfigEnvironment, ReleaseChannel
)
from app.models.org_engine.organization import Organization
from app.repositories.config import ConfigurationRepository, FeatureFlagRepository
from app.core.database import get_db, get_redis

logger = logging.getLogger("campusos.config")

class ConfigurationService:
    """
    Central brain of runtime behavior and feature flags in CampusOS.
    Handles hierarchy override resolution, deterministic cohort rollouts, and cache invalidation.
    """
    def __init__(self):
        self.cfg_repo = ConfigurationRepository()
        self.flg_repo = FeatureFlagRepository()
        self.redis = get_redis()

    async def _resolve_org(self, org_id_str: Optional[str], session=None) -> Optional[Organization]:
        if not org_id_str:
            return None
        org = None
        try:
            obj_id = PydanticObjectId(org_id_str)
            org = await Organization.find_one(
                Organization.id == obj_id,
                Organization.is_deleted == False,
                session=session
            )
        except Exception:
            pass

        if not org:
            org = await Organization.find_one(
                Organization.organization_id == org_id_str,
                Organization.is_deleted == False,
                session=session
            )

        if not org:
            raise OrganizationNotFound(f"Organization '{org_id_str}' not found.")
        return org

    async def _run_transactional(self, func):
        db = get_db()
        client = db.client
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await func(session)
        except Exception as e:
            if "replica set" in str(e).lower() or "transaction numbers" in str(e).lower() or "sessions are not supported" in str(e).lower():
                logger.warning("Transactions are not supported. Falling back to non-transactional execution.")
                return await func(None)
            else:
                logger.error(f"Configuration transaction failure: {e}")
                raise e

    # ==========================================
    # CACHING ENGINE
    # ==========================================

    def _get_cache(self, key: str) -> Optional[str]:
        try:
            return self.redis.get(key)
        except Exception:
            return None

    def _set_cache(self, key: str, value: str, ttl: int = 300) -> None:
        try:
            self.redis.set(key, value, ex=ttl)
        except Exception:
            pass

    def _delete_cache(self, key: str) -> None:
        try:
            self.redis.delete(key)
        except Exception:
            pass

    def _env_str(self, env: Any) -> str:
        if hasattr(env, "value"):
            return str(env.value)
        return str(env)

    def _get_cfg_version(self, org_id: Optional[PydanticObjectId], key: str, env: Any) -> str:
        org_key = str(org_id) if org_id else "system"
        env_str = self._env_str(env)
        v_key = f"cfgver:{org_key}:{key}:{env_str}"
        return self._get_cache(v_key) or "1"

    def _bump_cfg_version(self, org_id: Optional[PydanticObjectId], key: str, env: Any) -> None:
        org_key = str(org_id) if org_id else "system"
        env_str = self._env_str(env)
        v_key = f"cfgver:{org_key}:{key}:{env_str}"
        current = int(self._get_cache(v_key) or "1")
        self._set_cache(v_key, str(current + 1), ttl=86400)

    def _get_flg_version(self, org_id: Optional[PydanticObjectId], key: str, env: Any) -> str:
        org_key = str(org_id) if org_id else "system"
        env_str = self._env_str(env)
        v_key = f"flgver:{org_key}:{key}:{env_str}"
        return self._get_cache(v_key) or "1"

    def _bump_flg_version(self, org_id: Optional[PydanticObjectId], key: str, env: Any) -> None:
        org_key = str(org_id) if org_id else "system"
        env_str = self._env_str(env)
        v_key = f"flgver:{org_key}:{key}:{env_str}"
        current = int(self._get_cache(v_key) or "1")
        self._set_cache(v_key, str(current + 1), ttl=86400)

    # ==========================================
    # CONFIGURATION APIS
    # ==========================================

    def _validate_scope_constraints(self, scope: ConfigScope, org_id: Optional[PydanticObjectId], module: Optional[str], user_id: Optional[str]) -> None:
        if scope in (ConfigScope.GLOBAL, ConfigScope.SYSTEM):
            if org_id is not None or module is not None or user_id is not None:
                raise InvalidScope("GLOBAL/SYSTEM scopes must not specify organization, module, or user fields.")
        elif scope == ConfigScope.ORGANIZATION:
            if org_id is None or module is not None or user_id is not None:
                raise InvalidScope("ORGANIZATION scope requires an organization ID, and must leave module and user fields blank.")
        elif scope == ConfigScope.MODULE:
            if org_id is None or not module or user_id is not None:
                raise InvalidScope("MODULE scope requires both organization ID and module slug, and must leave user field blank.")
        elif scope == ConfigScope.USER:
            if org_id is None or not module or not user_id:
                raise InvalidScope("USER scope requires organization ID, module slug, and user ID.")

    async def create_config(self, org_id_str: Optional[str], data: dict) -> Configuration:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        scope = ConfigScope(data.get("scope", ConfigScope.ORGANIZATION))
        env = ConfigEnvironment(data.get("environment", ConfigEnvironment.PRODUCTION))
        key = data["key"]
        module = data.get("module")
        user_id = data.get("userId")

        self._validate_scope_constraints(scope, org_id, module, user_id)

        async def _create(session):
            existing = await self.cfg_repo.find_by_key_and_context(key, org_id, env, scope, module, session=session)
            if existing:
                raise DuplicateConfiguration(f"Configuration key '{key}' already exists in {str(scope)} scope.")

            count = await self.cfg_repo.count(org_id, session=session)
            cfg_id = f"CFG_{count + 1:06d}"

            config = Configuration(
                configId=cfg_id,
                organizationId=org_id,
                module=module,
                userId=user_id,
                key=key,
                value=data["value"],
                type=data.get("type", "string"),
                scope=scope,
                encrypted=data.get("encrypted", False),
                environment=env,
                configVersion=data.get("configVersion", "1.0.0")
            )
            res = await self.cfg_repo.create(config, session=session)
            self._bump_cfg_version(org_id, key, str(env))
            logger.info(f"Configuration '{key}' created in scope '{str(scope)}'.")
            return res

        return await self._run_transactional(_create)

    async def get_config(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> Configuration:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        config = await Configuration.find_one(
            Configuration.key == key,
            Configuration.organization_id == org_id,
            Configuration.environment == env,
            Configuration.is_deleted == False
        )
        if not config:
            raise ConfigurationNotFound(f"Configuration key '{key}' not found.")
        return config

    async def update_config(self, org_id_str: Optional[str], key: str, update_data: dict, env: str = "PRODUCTION") -> Configuration:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        config = await Configuration.find_one(
            Configuration.key == key,
            Configuration.organization_id == org_id,
            Configuration.environment == env,
            Configuration.is_deleted == False
        )
        if not config:
            raise ConfigurationNotFound(f"Configuration key '{key}' not found.")

        # Key, scope, and env are immutable on update
        if "key" in update_data and update_data["key"] != config.key:
            raise DuplicateConfiguration("Configuration keys are immutable.")

        res = await self.cfg_repo.update(config, update_data)
        self._bump_cfg_version(org_id, config.key, str(config.environment))
        logger.info(f"Configuration ID '{config.config_id}' updated.")
        return res

    async def delete_config(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> bool:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        config = await Configuration.find_one(
            Configuration.key == key,
            Configuration.organization_id == org_id,
            Configuration.environment == env,
            Configuration.is_deleted == False
        )
        if not config:
            raise ConfigurationNotFound(f"Configuration key '{key}' not found.")

        await self.cfg_repo.delete(config)
        self._bump_cfg_version(org_id, config.key, str(config.environment))
        logger.info(f"Configuration ID '{config.config_id}' soft deleted.")
        return True

    # ==========================================
    # CONFIGURATION RESOLUTION HIERARCHY
    # ==========================================

    async def resolve_configuration(
        self,
        org_id_str: Optional[str],
        key: str,
        environment: str = "PRODUCTION",
        module: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolves the configuration value for a key based on hierarchy:
        System Baseline -> Organization Override -> Module Override -> User Override.
        """
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        env_val = ConfigEnvironment(environment)

        # 1. Read through cache
        ver = self._get_cfg_version(org_id, key, env_val)
        user_cache_key = user_id or "anonymous"
        module_cache_key = module or "global"
        env_str = self._env_str(env_val)
        cache_key = f"cfgres:{str(org_id) if org_id else 'system'}:{module_cache_key}:{key}:{env_str}:{user_cache_key}:{ver}"

        cached = self._get_cache(cache_key)
        if cached:
            return json.loads(cached)

        # 2. Query matching configuration hierarchy matches
        configs = await self.cfg_repo.find_hierarchy_matches(key, org_id, env_val, module)

        # 3. Resolve priority order
        resolved_val = None
        resolved_scope = None
        resolved_type = "string"

        # Separate items by scope
        by_scope = {}
        for c in configs:
            if c.scope == ConfigScope.USER and c.user_id != user_id:
                continue
            by_scope[c.scope] = c

        # Evaluate hierarchy: System -> Org -> Module -> User
        scopes_priority = [
            ConfigScope.GLOBAL, ConfigScope.SYSTEM,
            ConfigScope.ORGANIZATION, ConfigScope.MODULE,
            ConfigScope.USER
        ]
        for sc in scopes_priority:
            if sc in by_scope:
                resolved_val = by_scope[sc].value
                resolved_scope = str(by_scope[sc].scope)
                resolved_type = by_scope[sc].type

        if resolved_scope is None:
            raise ConfigurationNotFound(f"Configuration path '{key}' not found in runtime tree.")

        result = {
            "key": key,
            "value": resolved_val,
            "scope": resolved_scope,
            "type": resolved_type
        }

        # 4. Cache resolved value
        self._set_cache(cache_key, json.dumps(result))
        return result

    # ==========================================
    # FEATURE FLAGS APIS
    # ==========================================

    async def create_feature_flag(self, org_id_str: Optional[str], data: dict) -> FeatureFlag:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        key = data["key"]
        env = ConfigEnvironment(data.get("environment", ConfigEnvironment.PRODUCTION))

        async def _create(session):
            # Check duplicate flag in org + environment
            existing = await self.flg_repo.find_by_key(key, org_id, env, session=session)
            if existing and existing.organization_id == org_id:
                raise DuplicateConfiguration(f"Feature flag key '{key}' already exists in this environment.")

            count = await self.flg_repo.count(org_id, session=session)
            flag_id = f"FLG_{count + 1:06d}"

            flag = FeatureFlag(
                flagId=flag_id,
                organizationId=org_id,
                key=key,
                name=data["name"],
                description=data.get("description"),
                category=data.get("category", "General"),
                enabled=data.get("enabled", False),
                defaultValue=data.get("defaultValue", False),
                environment=env,
                rolloutPercentage=data.get("rolloutPercentage", 100),
                allowedRoles=data.get("allowedRoles", []),
                allowedUsers=data.get("allowedUsers", []),
                allowedDepartments=data.get("allowedDepartments", []),
                allowedPrograms=data.get("allowedPrograms", []),
                allowedSemesters=data.get("allowedSemesters", []),
                conditions=data.get("conditions", []),
                expiresAt=data.get("expiresAt"),
                metadata=data.get("metadata", {})
            )
            res = await self.flg_repo.create(flag, session=session)
            self._bump_flg_version(org_id, key, str(env))
            logger.info(f"Feature flag '{key}' created.")
            return res

        return await self._run_transactional(_create)

    async def get_feature_flag(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> FeatureFlag:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        flag = await self.flg_repo.find_by_key(key, org_id, ConfigEnvironment(env))
        if not flag:
            raise FeatureNotFound(f"Feature flag '{key}' not found.")
        return flag

    async def update_feature_flag(self, org_id_str: Optional[str], key: str, update_data: dict, env: str = "PRODUCTION") -> FeatureFlag:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        flag = await self.flg_repo.find_by_key(key, org_id, ConfigEnvironment(env))
        if not flag:
            raise FeatureNotFound(f"Feature flag '{key}' not found.")

        # Key is immutable
        if "key" in update_data and update_data["key"] != flag.key:
            raise DuplicateConfiguration("Feature flag keys are immutable.")

        res = await self.flg_repo.update(flag, update_data)
        self._bump_flg_version(org_id, flag.key, str(flag.environment))
        logger.info(f"Feature flag key '{key}' updated.")
        return res

    async def delete_feature_flag(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> bool:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        flag = await self.flg_repo.find_by_key(key, org_id, ConfigEnvironment(env))
        if not flag:
            raise FeatureNotFound(f"Feature flag '{key}' not found.")

        await self.flg_repo.delete(flag)
        self._bump_flg_version(org_id, flag.key, str(flag.environment))
        logger.info(f"Feature flag key '{key}' soft deleted.")
        return True

    async def enable_feature_flag(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> FeatureFlag:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        flag = await self.flg_repo.find_by_key(key, org_id, ConfigEnvironment(env))
        if not flag:
            raise FeatureNotFound(f"Feature flag '{key}' not found.")

        flag.enabled = True
        res = await flag.save()
        self._bump_flg_version(org_id, flag.key, str(flag.environment))
        logger.info(f"Feature flag '{key}' enabled.")
        return res

    async def disable_feature_flag(self, org_id_str: Optional[str], key: str, env: str = "PRODUCTION") -> FeatureFlag:
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None
        flag = await self.flg_repo.find_by_key(key, org_id, ConfigEnvironment(env))
        if not flag:
            raise FeatureNotFound(f"Feature flag '{key}' not found.")

        flag.enabled = False
        res = await flag.save()
        self._bump_flg_version(org_id, flag.key, str(flag.environment))
        logger.info(f"Feature flag '{key}' disabled.")
        return res

    # ==========================================
    # FEATURE EVALUATION ENGINE
    # ==========================================

    async def evaluate_feature_flag(
        self,
        org_id_str: Optional[str],
        key: str,
        context: Optional[dict] = None
    ) -> bool:
        """
        Evaluates a feature flag based on context cohorts, schedules, environments, and rollouts.
        """
        org = await self._resolve_org(org_id_str)
        org_id = org.id if org else None

        ctx = context or {}
        env_str = ctx.get("environment", "PRODUCTION")
        env_val = ConfigEnvironment(env_str)

        # 1. Read through cache
        ver = self._get_flg_version(org_id, key, env_val)
        ctx_hash = hashlib.md5(json.dumps(ctx, sort_keys=True).encode("utf-8")).hexdigest()
        env_str = self._env_str(env_val)
        cache_key = f"flgeval:{str(org_id) if org_id else 'system'}:{key}:{env_str}:{ctx_hash}:{ver}"

        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached == "true"

        # 2. Fetch flag
        flag = await self.flg_repo.find_by_key(key, org_id, env_val)
        if not flag:
            return False

        # Evaluation checks
        def _evaluate() -> bool:
            # Check enabled
            if not flag.enabled:
                return flag.default_value

            # Check expired
            if flag.expires_at and datetime.utcnow() > flag.expires_at:
                logger.warning(f"Feature flag '{key}' has expired.")
                return flag.default_value

            # Check users
            user_id = ctx.get("userId")
            if flag.allowed_users:
                if not user_id or user_id not in flag.allowed_users:
                    return False

            # Check roles
            role = ctx.get("role")
            if flag.allowed_roles:
                if not role or role not in flag.allowed_roles:
                    return False

            # Check departments
            dept = ctx.get("department")
            if flag.allowed_departments:
                if not dept or dept not in flag.allowed_departments:
                    return False

            # Check programs
            prog = ctx.get("program")
            if flag.allowed_programs:
                if not prog or prog not in flag.allowed_programs:
                    return False

            # Check semesters
            sem = ctx.get("semester")
            if flag.allowed_semesters:
                if not sem or sem not in flag.allowed_semesters:
                    return False

            # Percentage Rollout
            if flag.rollout_percentage < 100:
                if not user_id:
                    # Anonymous request can't get percentage rollout if it checks user ID
                    return False
                # Calculate deterministic hash
                hash_in = f"{user_id}:{key}"
                hash_hex = hashlib.md5(hash_in.encode("utf-8")).hexdigest()
                hash_int = int(hash_hex, 16)
                user_pct = hash_int % 100
                if user_pct >= flag.rollout_percentage:
                    return False

            return True

        resolved = _evaluate()

        # 3. Set Cache
        self._set_cache(cache_key, "true" if resolved else "false")
        return resolved

def get_config_service() -> ConfigurationService:
    return ConfigurationService()
