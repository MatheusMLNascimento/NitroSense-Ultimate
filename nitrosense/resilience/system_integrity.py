"""
Multi-Stage System Integrity Check (3 levels)
Detects and auto-repairs hardware/software issues
"""

import subprocess
import platform
from pathlib import Path
from typing import Any, Dict, Tuple
import shutil
from ..core.logger import logger
from ..core.error_codes import ErrorCode


class SystemIntegrityCheck:
    """
    Three-level diagnostic and auto-repair system.
    """
    
    @staticmethod
    def level_1_binary_check() -> Dict[str, bool]:
        """Level 1: Check critical binaries (nbfc, nvidia-smi, sensors, pkexec)."""
        logger.info("🔍 Level 1: Binary dependency check...")
        
        binaries = ["nbfc", "nvidia-smi", "sensors", "pkexec"]
        results = {}
        
        for binary in binaries:
            found = shutil.which(binary) is not None
            results[binary] = found
            status = "✅" if found else "❌"
            logger.debug(f"{status} {binary}: {found}")
        
        return results
    
    @staticmethod
    def level_2_kernel_check() -> Tuple[bool, str]:
        """
        Level 2: Check kernel EC module and auto-enable write support.
        If /sys/module/ec_sys/parameters/write_support is 'N', reload with write_support=1.
        """
        logger.info("🔍 Level 2: Kernel EC module check...")
        
        try:
            ec_param_path = Path("/sys/module/ec_sys/parameters/write_support")
            
            if not ec_param_path.exists():
                logger.warning("⚠️  EC module not loaded")
                return False, "EC_MODULE_NOT_LOADED"
            
            current_value = ec_param_path.read_text().strip()
            
            if current_value == "N":
                logger.info("🔧 Reloading EC module with write_support=1...")
                
                # Remove module
                subprocess.run(
                    ["sudo", "modprobe", "-r", "ec_sys"],
                    capture_output=True,
                    timeout=10
                )
                
                # Reload with write support
                result = subprocess.run(
                    ["sudo", "modprobe", "ec_sys", "write_support=1"],
                    capture_output=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info("✅ EC module reloaded with write support")
                    return True, "EC_WRITE_SUPPORT_ENABLED"
                else:
                    logger.error("❌ Failed to reload EC module")
                    return False, "EC_RELOAD_FAILED"
            
            logger.info("✅ EC module OK (write_support=1)")
            return True, "EC_OK"
            
        except Exception as e:
            logger.warning(f"Level 2 check failed: {e}")
            return False, str(e)
    
    @staticmethod
    def level_3_python_check() -> Dict[str, Tuple[bool, str]]:
        """
        Level 3: Check Python module availability.
        psutil, PyQt6 must exist. matplotlib/numpy may be lazy-loaded.
        """
        logger.info("🔍 Level 3: Python module check...")
        
        modules = {
            "psutil": True,       # Critical
            "PyQt6": True,        # Critical
            "matplotlib": False,  # Optional (lazy-load)
            "numpy": False,       # Optional (lazy-load)
        }
        
        results = {}
        
        for module, critical in modules.items():
            try:
                __import__(module)
                results[module] = (True, "OK")
                logger.debug(f"✅ {module}")
            except ImportError:
                if critical:
                    logger.error(f"❌ {module} MISSING (CRITICAL)")
                    results[module] = (False, "MISSING_CRITICAL")
                else:
                    logger.debug(f"⚠️  {module} not available (will lazy-load)")
                    results[module] = (False, "WILL_LAZY_LOAD")
        
        return results
    
    @staticmethod
    def full_integrity_check() -> Dict[str, Any]:
        """Run all 3 levels and return comprehensive report."""
        logger.info("=" * 60)
        logger.info("🏥 FULL SYSTEM INTEGRITY CHECK (3 LEVELS)")
        logger.info("=" * 60)
        
        report = {
            "level_1_binaries": SystemIntegrityCheck.level_1_binary_check(),
            "level_2_kernel": SystemIntegrityCheck.level_2_kernel_check(),
            "level_3_python": SystemIntegrityCheck.level_3_python_check(),
            "status": "OK"
        }
        
        # Determine overall status
        if False in report["level_1_binaries"].values():
            report["status"] = "WARNING_BINARIES_MISSING"
        
        level_3_critical = [v for k, v in report["level_3_python"].items() 
                           if k in ["psutil", "PyQt6"]]
        if any(not v[0] for v in level_3_critical):
            report["status"] = "CRITICAL_MODULES_MISSING"
        
        logger.info(f"📊 Integrity Check Result: {report['status']}")
        logger.info("=" * 60)
        
        return report
