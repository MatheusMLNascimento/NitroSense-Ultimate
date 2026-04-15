# Step-by-Step Implementation Guide for Critical Fixes

## Overview

This guide provides exact code examples for the **4 Critical Action Items** needed to bring NitroSense Ultimate to production-ready status.

**Total Time Estimate:** 12-18 hours
**Difficulty:** Medium
**Risk Level:** Low (confined changes)

---

## STEP 1: UI Integration with NitroSenseSystem (4-6 hours)

### File: `nitrosense/ui/main_window.py`

#### Current Code (Lines 1-30):
```python
class NitroSenseApp(QMainWindow):
    def __init__(self, hardware_manager, config_manager):
        super().__init__()
        self.hw_manager = hardware_manager
        self.config_manager = config_manager
        # ...
```

#### New Code:
```python
from nitrosense.system import NitroSenseSystem
from nitrosense.core.error_codes import ErrorCode, is_critical, get_error_description

class NitroSenseApp(QMainWindow):
    def __init__(self, system: 'NitroSenseSystem'):
        super().__init__()
        self.system = system
        
        # Build convenience references
        self.hw_manager = system.hardware_manager
        self.config_manager = system.config_manager
        self.monitoring = system.monitoring
        self.ai = system.ai_engine
        self.security = system.security
        
        # Connect monitoring signals for error handling
        if self.monitoring:
            self.monitoring.error_occurred.connect(self._on_monitoring_error)
        
        logger.info("UI initialized with integrated system")
        self.setup_ui()
```

#### Add New Error Handler:
```python
def _on_monitoring_error(self, error_code: ErrorCode):
    """Handle errors from monitoring subsystem."""
    description = get_error_description(error_code)
    
    if is_critical(error_code):
        logger.critical(f"Critical error from monitoring: {error_code}")
        self._show_critical_dialog(error_code, description)
    else:
        logger.warning(f"Warning from monitoring: {error_code}")
        self.statusBar().showMessage(description, 5000)  # 5s timeout

def _show_critical_dialog(self, error_code: ErrorCode, description: str):
    """Display critical error to user."""
    msg = QMessageBox(self)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("🔴 Critical Error")
    msg.setText(f"Error {error_code}\n\n{description}")
    msg.setDetailedText(f"Error Code: {error_code}\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    msg.exec()

def closeEvent(self, event):
    """Graceful shutdown."""
    logger.info("Application closing...")
    err, msg = self.system.shutdown()
    if err != ErrorCode.SUCCESS:
        logger.warning(f"Shutdown warning: {get_error_description(err)}")
    event.accept()
```

#### Update main_window.py Signal Connections:

In the `__init__` method, update all signal connections to use new system object:

```python
# OLD
self.hw_manager.status_changed.connect(self.update_status)

# NEW
if self.monitoring:
    self.monitoring.metrics_updated.connect(self._on_metrics_updated)
    if hasattr(self.monitoring, 'error_occurred'):
        self.monitoring.error_occurred.connect(self._on_monitoring_error)

def _on_metrics_updated(self, metrics: dict):
    """Update UI with new metrics."""
    # Forward to pages
    self.pages['home'].update_metrics(metrics)
    self.pages['status'].update_health(metrics)
```

---

## STEP 2: HardwareManager ErrorCode Refactor (2-3 hours)

### File: `nitrosense/hardware/manager.py`

#### Updated Imports:
```python
from ..core.error_codes import ErrorCode, SafeOperation

# Add this import at top
from typing import Tuple
```

#### Replace run_nbfc() method:

**Current Code (Lines 150-170):**
```python
def run_nbfc(self, args: str) -> Tuple[bool, str]:
    """Execute NBFC command with protection."""
    try:
        cmd = ["nbfc"] + args.split()
        result = self._run_protected_command(cmd)
        return result.returncode == 0, result.stdout
    except Exception as e:
        logger.error(f"NBFC command failed: {e}")
        return False, ""
```

**New Code:**
```python
@SafeOperation(ErrorCode.NBFC_TIMEOUT)
def run_nbfc(self, args: str) -> Tuple[ErrorCode, str]:
    """
    Execute NBFC command with protection and error code return.
    
    Args:
        args: NBFC command arguments
        
    Returns:
        (ErrorCode, output_string) tuple
    """
    try:
        cmd = ["nbfc"] + args.split()
        result = self._run_protected_command(cmd)
        
        if result.returncode == 0:
            logger.debug(f"✅ NBFC success: {args}")
            return ErrorCode.SUCCESS, result.stdout
        else:
            logger.error(f"❌ NBFC failed: {result.stderr}")
            return ErrorCode.NBFC_COMMAND_FAILED, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏱️ NBFC timeout: {args}")
        return ErrorCode.NBFC_TIMEOUT, ""
        
    except PermissionError:
        logger.error("🔒 NBFC permission denied (need root)")
        return ErrorCode.PERMISSION_DENIED, ""
        
    except Exception as e:
        logger.error(f"NBFC error: {e}")
        # SafeOperation decorator will catch and return default ErrorCode
        raise
```

#### Update Other Methods That Call run_nbfc():

Search for all calls to `run_nbfc()` in the file and update error handling:

**OLD Pattern:**
```python
success, output = self.hw_manager.run_nbfc("some command")
if success:
    # ...
else:
    logger.error("Failed")
```

**NEW Pattern:**
```python
err, output = self.hw_manager.run_nbfc("some command")
if err == ErrorCode.SUCCESS:
    # ...
elif is_critical(err):
    logger.critical(f"NBFC critical: {get_error_description(err)}")
    # Trigger fallback
else:
    logger.warning(f"NBFC warning: {get_error_description(err)}")
```

---

## STEP 3: Config Page Integration (3-4 hours)

### File: `nitrosense/ui/pages/config_page.py`

#### New Imports:
```python
from nitrosense.core.advanced_config import AdvancedConfigManager
from nitrosense.core.error_codes import ErrorCode, get_error_description
```

#### Updated `__init__` Method:

**Current Code:**
```python
class ConfigPage(QWidget):
    def __init__(self, hw_manager, config_manager):
        super().__init__()
        self.hw = hw_manager
        self.config = config_manager
        self.setup_ui()
```

**New Code:**
```python
class ConfigPage(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.hw = system.hardware_manager
        self.config = system.config_manager
        
        # Initialize advanced config manager
        self.advanced_config = AdvancedConfigManager(self.config)
        
        logger.info("ConfigPage initialized")
        self.setup_ui()
        self._connect_config_signals()
```

#### Add Signal Connections:

```python
def _connect_config_signals(self):
    """Connect UI controls to config manager."""
    
    # Temperature threshold slider (if exists)
    if hasattr(self, 'temp_threshold_slider'):
        self.temp_threshold_slider.valueChanged.connect(
            lambda v: self._on_temp_threshold_changed(v)
        )
    
    # Fan speed slider
    if hasattr(self, 'fan_speed_slider'):
        self.fan_speed_slider.valueChanged.connect(
            lambda v: self._on_fan_speed_changed(v)
        )
    
    # Theme selector combo box
    if hasattr(self, 'theme_combo'):
        self.theme_combo.currentTextChanged.connect(
            lambda t: self._on_theme_changed(t)
        )
    
    # Frost mode duration
    if hasattr(self, 'frost_duration_spin'):
        self.frost_duration_spin.valueChanged.connect(
            lambda v: self._on_frost_duration_changed(v)
        )
    
    # AI sensitivity
    if hasattr(self, 'ai_sensitivity_slider'):
        self.ai_sensitivity_slider.valueChanged.connect(
            lambda v: self._on_ai_sensitivity_changed(v / 100.0)
        )
    
    # Listen for config changes
    self.advanced_config.config_changed.connect(self._on_config_changed)
    
    logger.info("Config signals connected")

def _on_temp_threshold_changed(self, value: int):
    """Handle temperature threshold change."""
    err, result = self.advanced_config.set_temp_threshold("High", value)
    
    if err == ErrorCode.SUCCESS:
        logger.info(f"Temperature threshold set to {value}°C")
        self.statusBar().showMessage(f"Updated: High threshold → {value}°C")
    else:
        logger.error(f"Failed to set threshold: {get_error_description(err)}")
        self.show_error_notification(err)

def _on_fan_speed_changed(self, value: int):
    """Handle fan speed threshold change."""
    err, result = self.advanced_config.set_speed_threshold("High", value)
    
    if err == ErrorCode.SUCCESS:
        logger.info(f"Fan speed threshold set to {value}%")
    else:
        logger.error(f"Failed to set fan speed: {get_error_description(err)}")

def _on_theme_changed(self, theme_name: str):
    """Handle theme selection."""
    err, result = self.advanced_config.set_theme(theme_name)
    
    if err == ErrorCode.SUCCESS:
        logger.info(f"Theme changed to {theme_name}")
        # Apply theme immediately
        self.apply_theme(theme_name)
    else:
        logger.error(f"Theme change failed: {get_error_description(err)}")

def _on_frost_duration_changed(self, seconds: int):
    """Handle Frost Mode duration change."""
    err, result = self.advanced_config.set_frost_mode_duration(seconds)
    
    if err == ErrorCode.SUCCESS:
        logger.info(f"Frost Mode duration: {seconds}s")
    else:
        logger.error(f"Frost duration update failed: {get_error_description(err)}")

def _on_ai_sensitivity_changed(self, sensitivity: float):
    """Handle AI sensitivity slider."""
    err, result = self.advanced_config.set_ai_sensitivity(sensitivity)
    
    if err == ErrorCode.SUCCESS:
        logger.info(f"AI sensitivity set to {sensitivity:.2f}x")
    else:
        logger.error(f"AI sensitivity update failed: {get_error_description(err)}")

def _on_config_changed(self, key: str, value: any):
    """Handle config changes from other parts of app."""
    logger.info(f"Config updated externally: {key} = {value}")
    self.refresh_ui_from_config()

def refresh_ui_from_config(self):
    """Sync UI with current config values."""
    config_data = self.config.load_config()
    
    if config_data:
        # Update sliders to match config
        if 'thermal_thresholds' in config_data:
            high_temp = config_data['thermal_thresholds'].get('High', 80)
            if hasattr(self, 'temp_threshold_slider'):
                self.temp_threshold_slider.setValue(high_temp)
        
        if 'speed_thresholds' in config_data:
            high_speed = config_data['speed_thresholds'].get('High', 100)
            if hasattr(self, 'fan_speed_slider'):
                self.fan_speed_slider.setValue(high_speed)

def show_error_notification(self, error_code: ErrorCode):
    """Display error notification to user."""
    description = get_error_description(error_code)
    
    # Create toast-style notification
    msg = QMessageBox()
    msg.setWindowTitle("⚠️ Configuration Error")
    msg.setText(description)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.exec()
```

---

## STEP 4: Labs Page Integration (3-4 hours)

### File: `nitrosense/ui/pages/labs_page.py`

#### New Imports:
```python
from nitrosense.security.diagnostics import SecurityAndDiagnostics
from nitrosense.core.error_codes import ErrorCode, get_error_description
import time
```

#### Updated `__init__` Method:

**New Code:**
```python
class LabsPage(QWidget):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.security = system.security
        
        # Console for test output
        self.output_console = QPlainTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Monaco', monospace;
                font-size: 11pt;
            }
        """)
        
        logger.info("LabsPage initialized")
        self.setup_ui()
        self._setup_diagnostic_buttons()

def setup_ui(self):
    """Setup UI layout."""
    layout = QVBoxLayout(self)
    
    # Title
    title = QLabel("🔬 Diagnostic Suite")
    title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #007aff;")
    layout.addWidget(title)
    
    # Buttons group
    buttons_group = QGroupBox("Available Tests")
    buttons_layout = QGridLayout(buttons_group)
    
    # Test buttons will be added here
    layout.addWidget(buttons_group)
    
    # Output console
    console_group = QGroupBox("Test Output")
    console_layout = QVBoxLayout(console_group)
    console_layout.addWidget(self.output_console)
    layout.addWidget(console_group, 1)  # Stretch
    
    # Clear button
    clear_btn = QPushButton("Clear Output")
    clear_btn.clicked.connect(self.output_console.clear)
    layout.addWidget(clear_btn)
    
    self.setLayout(layout)

def _setup_diagnostic_buttons(self):
    """Add diagnostic test buttons."""
    
    tests = [
        ("Check Dependencies", self._test_dependencies, "Verify system requirements"),
        ("Fan Test (5s)", self._test_fans, "Test both fans at full speed"),
        ("EC Validation", self._test_ec, "Verify EC register access"),
        ("Stress Test 95°C", self._test_stress, "Simulate thermal spike"),
        ("Memory Leak Check", self._test_memory, "Check for memory leaks"),
        ("Network Ping", self._test_network, "Test network connectivity"),
        ("Kernel Check", self._test_kernel, "Verify kernel version"),
        ("Advanced Report", self._test_report, "Full system diagnostics"),
    ]
    
    # Create buttons with callbacks
    for label, callback, tooltip in tests:
        btn = QPushButton(label)
        btn.clicked.connect(callback)
        btn.setToolTip(tooltip)
        # Add to layout (implement button grid layout in setup_ui)
```

#### Add Test Methods:

```python
def _log_test_result(self, test_name: str, error_code: ErrorCode, details: str = ""):
    """Log test result to console."""
    timestamp = time.strftime("%H:%M:%S")
    description = get_error_description(error_code)
    
    output = f"[{timestamp}] {test_name}\n"
    output += f"  Status: {description}\n"
    if details:
        output += f"  Details: {details}\n"
    output += "\n"
    
    self.output_console.appendPlainText(output)

def _test_dependencies(self):
    """Test 1: Check system dependencies."""
    self.output_console.clear()
    self.output_console.appendPlainText("🔍 Checking system dependencies...\n")
    
    err, deps = self.security.system_dependency_check()
    
    output = "DEPENDENCIES:\n"
    for tool, available in deps.items():
        status = "✅" if available else "❌"
        output += f"  {status} {tool}\n"
    
    self._log_test_result("Dependency Check", err, output)

def _test_fans(self):
    """Test 2: Individual fan test."""
    self.output_console.clear()
    self.output_console.appendPlainText("🌀 Testing fans (5 seconds each)...\n")
    
    for fan_id in [1, 2]:
        err, success = self.security.individual_fan_test(fan_id)
        self._log_test_result(f"Fan {fan_id} Test", err, f"Success: {success}")
        time.sleep(1)

def _test_ec(self):
    """Test 3: EC validation."""
    self.output_console.clear()
    self.output_console.appendPlainText("🔧 Validating EC access...\n")
    
    err, success = self.security.ec_register_validation_test()
    self._log_test_result("EC Validation", err, f"EC Accessible: {success}")

def _test_stress(self):
    """Test 4: Stress test 95°C."""
    self.output_console.clear()
    self.output_console.appendPlainText("🌡️ Starting stress test...\n")
    self.output_console.appendPlainText("⚠️  This simulates 95°C thermal condition.\n\n")
    
    err, result = self.security.simulate_stress_test_95c(enable=True)
    self._log_test_result("Stress Test 95°C", err, f"Test Triggered: {result}")

def _test_memory(self):
    """Test 5: Memory leak detector."""
    self.output_console.clear()
    self.output_console.appendPlainText("🧠 Checking memory usage...\n")
    
    err, memory_mb = self.security.memory_leak_detector()
    self._log_test_result("Memory Check", err, f"RSS: {memory_mb:.1f}MB")

def _test_network(self):
    """Test 6: Network ping quality."""
    self.output_console.clear()
    self.output_console.appendPlainText("📡 Testing network ping...\n")
    
    err, packet_loss = self.security.network_ping_quality()
    self._log_test_result("Network Ping", err, f"Packet Loss: {packet_loss:.1f}%")

def _test_kernel(self):
    """Test 7: Kernel version check."""
    self.output_console.clear()
    self.output_console.appendPlainText("🐧 Checking kernel version...\n")
    
    err, kernel_version = self.security.kernel_version_check()
    self._log_test_result("Kernel Check", err, f"Kernel: {kernel_version}")

def _test_report(self):
    """Test 8: Advanced diagnostics report."""
    self.output_console.clear()
    self.output_console.appendPlainText("📊 Generating advanced diagnostics...\n\n")
    
    err, report = self.security.advanced_diagnostics_report()
    
    if err == ErrorCode.SUCCESS:
        import json
        report_text = json.dumps(report, indent=2)
        self.output_console.appendPlainText(report_text)
    
    self._log_test_result("Advanced Report", err)
```

---

## Testing Checklist After Fixes

After implementing all 4 critical fixes, verify:

### Verification Steps:

```bash
# 1. Test startup
python3 main.py

# 2. Check logs
tail -50 ~/.config/nitrosense/nitrosense.log

# 3. Run diagnostics (from Labs tab in UI)
# - Check Dependencies
# - Fan Test
# - EC Validation
# - Stress Test 95°C
# - Memory Check
# - Advanced Report

# 4. Verify config persistence
# - Change theme
# - Change temperature threshold
# - Check config file updated
cat ~/.config/nitrosense/config.json

# 5. Stress test (12+ hours)
# Monitor for:
# - Memory growth
# - CPU usage
# - Fan responsiveness
# - Crash log entries
```

### Success Criteria:

✅ No Python exceptions
✅ All error codes returned correctly
✅ UI responsive to errors
✅ Monitoring loop stable
✅ Config saves/loads
✅ Tests complete successfully
✅ Memory stable < 50MB/hour growth

---

## Estimated Timeline

| Task | Time | Difficulty |
|------|------|-----------|
| Step 1: UI Integration | 4-6h | Medium |
| Step 2: HardwareManager | 2-3h | Low |
| Step 3: Config Page | 3-4h | Medium |
| Step 4: Labs Page | 3-4h | Medium |
| Testing & Verification | 4-6h | Low |
| **TOTAL** | **16-23h** | **Medium** |

---

**Good Luck! 🚀 This will bring NitroSense to production-ready status.**
