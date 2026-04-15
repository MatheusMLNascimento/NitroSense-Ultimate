"""
NitroSense Ultimate - Professional Fan & Thermal Control for Acer Nitro 5
Version: 2.0.0
Python: 3.12+
Framework: PyQt6
Target: Ubuntu 24.04 + Acer Nitro 5 (AN515-54)
"""

__VERSION__ = "2.0.0"
__AUTHOR__ = "NitroSense Development Team"
__LICENSE__ = "GPL-3.0"

from .core.config import ConfigManager
from .core.logger import setup_logging
from .core.app_exceptions import setup_global_exception_handlers as setup_exception_handler

__all__ = [
    "ConfigManager",
    "setup_logging",
    "setup_exception_handler",
]
