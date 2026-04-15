"""
Application Configuration and CLI Arguments

Handles command-line argument parsing and application-wide configuration.
Exported before QApplication initialization to prevent initialization errors.
"""

import argparse
import sys
from typing import NamedTuple


class AppConfig(NamedTuple):
    """Application runtime configuration."""
    no_splash: bool
    background: bool


def parse_args() -> AppConfig:
    """
    Parse command-line arguments.
    
    Returns:
        AppConfig with parsed arguments
        
    Examples:
        >>> config = parse_args()
        >>> if not config.no_splash:
        ...     print("Splash screen enabled")
    """
    parser = argparse.ArgumentParser(description="Run NitroSense Ultimate")
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="Skip the splash screen during startup",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Start the application in background mode (minimized)",
    )
    
    args = parser.parse_args()
    return AppConfig(
        no_splash=args.no_splash,
        background=args.background,
    )
