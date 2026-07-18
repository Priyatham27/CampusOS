import json
from typing import Optional, Any
from pydantic import BaseModel
from app.core.database import get_redis

class AcademicCacheLayer:
    """
    Lightweight Cache wrapper that interfaces with the platform's Redis client 
    or the in-memory fallback. Performs automated Pydantic model serialization.
    """
    def __init__(self):
        self.redis = get_redis()

    def _get_redis(self):
        if not self.redis:
            self.redis = get_redis()
        return self.redis

    async def get(self, key: str, model_cls: Optional[Any] = None) -> Optional[Any]:
        from app.academic.metrics import AcademicMetricsService
        try:
            r = self._get_redis()
            if not r:
                AcademicMetricsService.record_cache_miss()
                return None
            val = r.get(key)
            if val:
                AcademicMetricsService.record_cache_hit()
                data = json.loads(val)
                if model_cls and isinstance(data, dict):
                    return model_cls.model_validate(data)
                elif model_cls and isinstance(data, list):
                    return [model_cls.model_validate(item) for item in data]
                return data
            else:
                AcademicMetricsService.record_cache_miss()
        except Exception:
            AcademicMetricsService.record_cache_miss()
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            r = self._get_redis()
            if not r:
                return False
            
            if isinstance(value, BaseModel):
                serialized = value.model_dump_json(by_alias=True)
            elif isinstance(value, list) and all(isinstance(v, BaseModel) for v in value):
                serialized = json.dumps([v.model_dump(by_alias=True) for v in value])
            elif hasattr(value, "dict"):
                serialized = json.dumps(value.dict())
            else:
                serialized = json.dumps(value)
            
            r.set(key, serialized, ex=ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        try:
            r = self._get_redis()
            if r:
                r.delete(key)
                return True
        except Exception:
            pass
        return False
