"""
Configuration Testing System for NitroSense Ultimate.

FEATURE #30: Testar Configuração
MOTIVO: Usuarios podem testar configs sem risco permanente.
- Timer de reversão automática (5 min) garante segurança
- Snapshot antes do teste permite restore exato
- Útil para calibrar thermal curves sem perder configs estáveis
- UX: "Vou testar por 5 min" vs "Perdi minha config"
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from pathlib import Path
from ..core.logger import logger
from ..core.config import ConfigManager


class ConfigTester:
    """
    Manages configuration testing with automatic rollback.
    Allows temporary config changes that revert after a timeout.
    """
    
    def __init__(self, config_manager: ConfigManager, timeout_seconds: int = 300):
        """
        Initialize config tester.
        
        Args:
            config_manager: The application config manager
            timeout_seconds: How long to test before reverting (default 5 min)
        """
        self.config = config_manager
        self.timeout_seconds = timeout_seconds
        
        # Testing state
        self.is_testing = False
        self.test_start_time: Optional[datetime] = None
        self.snapshot: Dict[str, Any] = {}
        self.test_changes: Dict[str, Any] = {}
        
        # Callbacks
        self.on_test_started = None
        self.on_test_reverted = None
        self.on_test_confirmed = None
        
        logger.info("ConfigTester initialized")
    
    def start_test(self, test_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Start a configuration test with automatic rollback timer.
        
        Args:
            test_config: Dictionary of config values to test
            
        Returns:
            (success: bool, message: str)
        """
        if self.is_testing:
            return False, "❌ Test already in progress"
        
        try:
            # Create snapshot of current config
            self.snapshot = self.config.get_all()
            self.test_start_time = datetime.now()
            self.test_changes = test_config.copy()
            self.is_testing = True
            
            # Apply test config
            for key, value in test_config.items():
                self.config.set(key, value)
            
            logger.info(f"Config test started for {len(test_config)} parameters")
            
            if self.on_test_started:
                self.on_test_started({
                    "timeout": self.timeout_seconds,
                    "changes": test_config
                })
            
            return True, f"✅ Test mode active for {self.timeout_seconds}s"
        
        except Exception as e:
            logger.error(f"Failed to start config test: {e}")
            return False, f"❌ Test start failed: {str(e)}"
    
    def confirm_test(self) -> Tuple[bool, str]:
        """
        Confirm test configuration and make it permanent.
        
        Returns:
            (success: bool, message: str)
        """
        if not self.is_testing:
            return False, "❌ No test in progress"
        
        try:
            self.is_testing = False
            self.snapshot.clear()
            self.test_changes.clear()
            self.test_start_time = None
            
            logger.info("Config test confirmed (made permanent)")
            
            if self.on_test_confirmed:
                self.on_test_confirmed()
            
            return True, "✅ Configuration confirmed permanently"
        
        except Exception as e:
            logger.error(f"Failed to confirm config test: {e}")
            return False, f"❌ Confirm failed: {str(e)}"
    
    def revert_test(self, reason: str = "User requested") -> Tuple[bool, str]:
        """
        Revert to pre-test configuration.
        
        Args:
            reason: Reason for reversion (logging)
            
        Returns:
            (success: bool, message: str)
        """
        if not self.is_testing:
            return False, "❌ No test in progress"
        
        try:
            # Restore snapshot
            for key, value in self.snapshot.items():
                self.config.set(key, value)
            
            logger.warning(f"Config test reverted: {reason}")
            
            self.is_testing = False
            reverted_count = len(self.test_changes)
            original_values = [
                f"{k}={v}" for k, v in list(self.test_changes.items())[:3]
            ]
            
            self.snapshot.clear()
            self.test_changes.clear()
            self.test_start_time = None
            
            if self.on_test_reverted:
                self.on_test_reverted({
                    "reason": reason,
                    "reverted_count": reverted_count
                })
            
            message = f"✅ Reverted {reverted_count} settings"
            return True, message
        
        except Exception as e:
            logger.error(f"Failed to revert config test: {e}")
            return False, f"❌ Revert failed: {str(e)}"
    
    def get_test_status(self) -> Dict[str, Any]:
        """
        Get current test status.
        
        Returns:
            Dictionary with test info
        """
        if not self.is_testing:
            return {
                "is_testing": False,
                "message": "No test in progress"
            }
        
        elapsed = (datetime.now() - self.test_start_time).total_seconds()
        remaining = self.timeout_seconds - elapsed
        
        return {
            "is_testing": True,
            "elapsed_seconds": int(elapsed),
            "remaining_seconds": int(max(0, remaining)),
            "timeout_seconds": self.timeout_seconds,
            "changes_count": len(self.test_changes),
            "changed_keys": list(self.test_changes.keys()),
            "test_will_revert": remaining > 0
        }
    
    def check_timeout(self) -> Optional[Tuple[bool, str]]:
        """
        Check if test timeout has been reached.
        Auto-revert if timeout exceeded.
        
        Returns:
            (reverted: bool, message: str) if timeout occurred, else None
        """
        if not self.is_testing or not self.test_start_time:
            return None
        
        elapsed = (datetime.now() - self.test_start_time).total_seconds()
        
        if elapsed > self.timeout_seconds:
            logger.warning(f"Config test timeout after {elapsed:.0f}s, auto-reverting")
            return self.revert_test(f"Automatic timeout after {self.timeout_seconds}s")
        
        return None
    
    def get_timeout_warning_info(self, warning_threshold: float = 30.0) -> Optional[Dict]:
        """
        Get info for displaying timeout warning (last 30 seconds).
        
        Args:
            warning_threshold: Seconds before timeout to show warning
            
        Returns:
            Warning info dict or None
        """
        if not self.is_testing or not self.test_start_time:
            return None
        
        elapsed = (datetime.now() - self.test_start_time).total_seconds()
        remaining = self.timeout_seconds - elapsed
        
        if 0 < remaining < warning_threshold:
            return {
                "show_warning": True,
                "remaining_seconds": int(remaining),
                "expires_at": (datetime.now() + timedelta(seconds=remaining)).isoformat(),
                "severity": "critical" if remaining < 10 else "warning"
            }
        
        return None
    
    def export_test_snapshot(self, filepath: Optional[Path] = None) -> Tuple[bool, str]:
        """
        Export current test snapshot for debugging/sharing.
        
        Args:
            filepath: Optional output file path
            
        Returns:
            (success: bool, message: str or filepath)
        """
        if not self.snapshot:
            return False, "❌ No snapshot available"
        
        try:
            if filepath is None:
                filepath = Path.home() / ".config" / "nitrosense" / "test_snapshot.json"
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            snapshot_data = {
                "timestamp": datetime.now().isoformat(),
                "testing": self.is_testing,
                "timeout_seconds": self.timeout_seconds,
                "snapshot": self.snapshot,
                "test_changes": self.test_changes,
            }
            
            with open(filepath, 'w') as f:
                json.dump(snapshot_data, f, indent=2)
            
            logger.info(f"Test snapshot exported to {filepath}")
            return True, f"✅ Snapshot saved: {filepath}"
        
        except Exception as e:
            logger.error(f"Failed to export snapshot: {e}")
            return False, f"❌ Export failed: {str(e)}"
    
    def create_test_preset(
        self, 
        name: str, 
        description: str,
        config_changes: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Create a named test preset for reusable configurations.
        
        Args:
            name: Preset name (e.g., "Gaming Mode Test")
            description: What this preset tests
            config_changes: Configuration values to apply
            
        Returns:
            (success: bool, message: str)
        """
        try:
            preset_file = Path.home() / ".config" / "nitrosense" / "test_presets.json"
            
            if preset_file.exists():
                with open(preset_file, 'r') as f:
                    presets = json.load(f)
            else:
                presets = {}
            
            presets[name] = {
                "description": description,
                "config": config_changes,
                "created_at": datetime.now().isoformat()
            }
            
            preset_file.parent.mkdir(parents=True, exist_ok=True)
            with open(preset_file, 'w') as f:
                json.dump(presets, f, indent=2)
            
            logger.info(f"Test preset created: {name}")
            return True, f"✅ Preset '{name}' saved"
        
        except Exception as e:
            logger.error(f"Failed to create preset: {e}")
            return False, f"❌ Preset creation failed: {str(e)}"
