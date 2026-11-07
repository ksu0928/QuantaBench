"""Result caching service for deterministic demo behavior.

This module provides disk-based caching of optimization results keyed by
problem parameters. This ensures that repeated runs with the same parameters
return cached results instantly, making demos reliable and fast.
"""

import hashlib
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import get_settings


class ResultCache:
    """Disk-based cache for optimization results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize result cache.
        
        Args:
            cache_dir: Cache directory path (uses config if None)
        """
        settings = get_settings()
        self.cache_dir = cache_dir or settings.cache_path
        self.ttl_hours = settings.cache_ttl_hours
        self.enabled = settings.cache_enabled

        # Create cache directory if it doesn't exist
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters.
        
        Strategy: Hash a canonical JSON representation of parameters.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            Cache key (hex string)
        """
        # Sort keys for consistent ordering
        canonical = json.dumps(params, sort_keys=True, default=str)
        # Hash to fixed-length key
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{key}.pkl"

    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cached result is expired.
        
        Args:
            cache_path: Path to cache file
            
        Returns:
            True if expired
        """
        if not cache_path.exists():
            return True

        # Check modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime

        return age > timedelta(hours=self.ttl_hours)

    def get(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve cached result.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            Cached result dict, or None if not found/expired
        """
        if not self.enabled:
            return None

        key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(key)

        # Check if exists and not expired
        if not cache_path.exists() or self._is_expired(cache_path):
            return None

        try:
            with open(cache_path, "rb") as f:
                cached = pickle.load(f)

            # Add cache metadata
            cached["_cache_hit"] = True
            cached["_cached_at"] = datetime.fromtimestamp(
                cache_path.stat().st_mtime
            ).isoformat()

            return cached

        except Exception as e:
            print(f"Warning: Failed to load cache: {e}")
            return None

    def set(self, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Store result in cache.
        
        Args:
            params: Parameter dictionary
            result: Result to cache
        """
        if not self.enabled:
            return

        key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(key)

        try:
            # Add cache metadata
            result_with_meta = result.copy()
            result_with_meta["_cache_key"] = key
            result_with_meta["_cached_at"] = datetime.now().isoformat()

            with open(cache_path, "wb") as f:
                pickle.dump(result_with_meta, f)

        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")

    def invalidate(self, params: Dict[str, Any]) -> bool:
        """Invalidate cached result.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            True if cache was invalidated
        """
        if not self.enabled:
            return False

        key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            return True

        return False

    def clear_all(self) -> int:
        """Clear all cached results.
        
        Returns:
            Number of cache files deleted
        """
        if not self.enabled:
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
            count += 1

        return count

    def clear_expired(self) -> int:
        """Clear only expired cache entries.
        
        Returns:
            Number of expired entries deleted
        """
        if not self.enabled:
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            if self._is_expired(cache_file):
                cache_file.unlink()
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        if not self.enabled:
            return {
                "enabled": False,
                "cache_dir": str(self.cache_dir),
            }

        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)

        # Count expired
        expired_count = sum(1 for f in cache_files if self._is_expired(f))

        return {
            "enabled": True,
            "cache_dir": str(self.cache_dir),
            "num_entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "expired_entries": expired_count,
            "ttl_hours": self.ttl_hours,
        }


def build_cache_params(
    problem_type: str,
    problem_params: Dict[str, Any],
    solvers: list,
    qaoa_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build cache parameter dict from request parameters.
    
    Args:
        problem_type: Problem type
        problem_params: Problem parameters
        solvers: List of solver names
        qaoa_params: QAOA parameters (if applicable)
        
    Returns:
        Canonical parameter dict for caching
    """
    cache_params = {
        "problem_type": problem_type,
        "problem_params": problem_params,
        "solvers": sorted(solvers),  # Sort for consistency
    }

    if qaoa_params is not None:
        # Only include parameters that affect results
        cache_params["qaoa_params"] = {
            "p": qaoa_params.get("p"),
            "backend": qaoa_params.get("backend"),
            # Don't include shots in cache key - results should be similar
        }

    return cache_params


# Global cache instance
_cache_instance: Optional[ResultCache] = None


def get_cache() -> ResultCache:
    """Get global cache instance.
    
    Returns:
        ResultCache singleton
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResultCache()
    return _cache_instance


def clear_cache() -> int:
    """Clear all cache entries (convenience function).
    
    Returns:
        Number of entries cleared
    """
    return get_cache().clear_all()
