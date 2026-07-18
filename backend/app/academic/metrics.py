from typing import Dict, Any

class AcademicMetricsService:
    """
    Performance and diagnostic metrics aggregator for the Academic Platform.
    Tracks lookup latencies, resolver counts, caching hit ratios, and hierarchy blocks.
    """
    _resolutions_count = 0
    _cache_hits = 0
    _cache_misses = 0
    _violations_count = 0
    _total_latency_ms = 0.0

    @classmethod
    def record_resolution(cls, latency_ms: float):
        cls._resolutions_count += 1
        cls._total_latency_ms += latency_ms

    @classmethod
    def record_cache_hit(cls):
        cls._cache_hits += 1

    @classmethod
    def record_cache_miss(cls):
        cls._cache_misses += 1

    @classmethod
    def record_violation(cls):
        cls._violations_count += 1

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        avg_latency = (
            cls._total_latency_ms / cls._resolutions_count
            if cls._resolutions_count > 0
            else 0.0
        )
        total_cache = cls._cache_hits + cls._cache_misses
        hit_ratio = cls._cache_hits / total_cache if total_cache > 0 else 0.0
        
        return {
            "resolutionsCount": cls._resolutions_count,
            "cacheHits": cls._cache_hits,
            "cacheMisses": cls._cache_misses,
            "cacheHitRatio": round(hit_ratio, 4),
            "hierarchyViolationsBlocked": cls._violations_count,
            "averageResolutionLatencyMs": round(avg_latency, 2)
        }
