"""
Lazy Module Loading - Zero-Overhead Startup
Heavy modules (matplotlib, numpy) loaded on-demand
"""

import sys
import importlib
from typing import Optional, Any
from ..core.logger import logger


class LazyLoader:
    """
    Defer loading of heavy modules until needed.
    Keeps startup time < 2s by skipping unused dependencies.
    """
    
    _loaded_modules = {}
    
    @staticmethod
    def load_matplotlib() -> Optional[Any]:
        """Load matplotlib only when needed (Home page)."""
        if 'matplotlib' in LazyLoader._loaded_modules:
            return LazyLoader._loaded_modules['matplotlib']
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            logger.info("✅ matplotlib loaded (lazy)")
            LazyLoader._loaded_modules['matplotlib'] = plt
            return plt
        except ImportError as e:
            logger.error(f"Failed to load matplotlib: {e}")
            return None
    
    @staticmethod
    def load_numpy() -> Optional[Any]:
        """Load numpy only when needed (graphing)."""
        if 'numpy' in LazyLoader._loaded_modules:
            return LazyLoader._loaded_modules['numpy']
        
        try:
            import numpy as np
            logger.info("✅ numpy loaded (lazy)")
            LazyLoader._loaded_modules['numpy'] = np
            return np
        except ImportError as e:
            logger.error(f"Failed to load numpy: {e}")
            return None
    
    @staticmethod
    def load_smartctl() -> Optional[Any]:
        """Load smartctl interface (SSD monitoring)."""
        if 'smartctl' in LazyLoader._loaded_modules:
            return LazyLoader._loaded_modules['smartctl']
        
        try:
            import pySmart
            logger.info("✅ pySmart loaded (lazy)")
            LazyLoader._loaded_modules['smartctl'] = pySmart
            return pySmart
        except ImportError:
            logger.debug("pySmart not available (SSD monitoring disabled)")
            return None


def get_lazy_loader() -> LazyLoader:
    """Get lazy loader."""
    return LazyLoader
