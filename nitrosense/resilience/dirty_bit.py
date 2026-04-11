"""
Dirty Bit Logic - Render Optimization
Only repaint UI if values actually changed
"""

from typing import Any, Dict, Optional
from ..core.logger import logger


class DirtyBitCache:
    """
    Cache layer that tracks which values changed.
    UI widgets only repaint if their value's dirty bit is set.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._dirty_bits: Dict[str, bool] = {}
        logger.info("✅ DirtyBitCache initialized")
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached value without marking dirty."""
        return self._cache.get(key)
    
    def is_dirty(self, key: str) -> bool:
        """Check if value changed since last check."""
        result = self._dirty_bits.get(key, False)
        self._dirty_bits[key] = False  # Reset after check
        return result
    
    def update_cache(self, key: str, new_value: Any) -> bool:
        """
        Update cache and mark dirty if value changed.
        Returns True if value changed (dirty bit set).
        """
        old_value = self._cache.get(key)
        
        # Check if actually changed (handles floats with tolerance)
        if isinstance(new_value, float) and isinstance(old_value, float):
            if abs(new_value - old_value) < 0.1:  # 0.1°C tolerance
                return False
        elif old_value == new_value:
            return False
        
        # Value changed
        self._cache[key] = new_value
        self._dirty_bits[key] = True
        return True
    
    def get_dirty_keys(self) -> list:
        """Get list of all keys that are dirty."""
        return [k for k, v in self._dirty_bits.items() if v]
    
    def reset_all(self):
        """Reset all dirty bits."""
        self._dirty_bits = {k: False for k in self._dirty_bits}


# Singleton instance
_cache = DirtyBitCache()

def get_dirty_bit_cache() -> DirtyBitCache:
    """Get global dirty bit cache."""
    return _cache
