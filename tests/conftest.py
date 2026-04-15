import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Ensure Qt can run in headless CI environments
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from nitrosense.core.config import ConfigManager


@pytest.fixture(autouse=True)
def reset_config_singleton():
    ConfigManager._instance = None
    yield
    ConfigManager._instance = None
