# NitroSense Ultimate - Debugging & Development Guide

**Last Updated**: 14 de abril de 2026
**Version**: 3.1
**Target**: Python 3.12+, PyQt6, Linux (Debian/Ubuntu)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Structure](#module-structure)
3. [Setting Up Development Environment](#setting-up-development-environment)
4. [Type Checking with MyPy](#type-checking-with-mypy)
5. [Common Errors & Solutions](#common-errors--solutions)
6. [Debugging Techniques](#debugging-techniques)
7. [Testing Strategy](#testing-strategy)
8. [Performance Profiling](#performance-profiling)

---

## Architecture Overview

```
NitroSense Ultimate
├── main.py (Entry point, 250 lines)
│   ├── app_config.py: CLI argument parsing
│   ├── app_state.py: Session lock & crash detection
│   ├── app_exceptions.py: Global exception handlers
│   └── app_lifecycle.py: Signal handlers & cleanup
│
├── nitrosense/
│   ├── core/ (System, config, errors)
│   │   ├── logger.py
│   │   ├── error_handler.py
│   │   ├── constants.py
│   │   ├── startup.py
│   │   └── ...
│   ├── ui/ (User interface)
│   │   ├── main_window.py
│   │   ├── splash.py
│   │   ├── log_viewer.py
│   │   └── ...
│   ├── hardware/ (Hardware abstraction)
│   │   ├── manager.py
│   │   ├── interface.py
│   │   └── ...
│   ├── automation/ (AI & fan control)
│   │   ├── fan_control.py
│   │   └── ai_engine.py
│   ├── resilience/ (Error recovery)
│   │   ├── watchdog.py
│   │   ├── dependency_installer.py
│   │   └── ...
│   └── system.py (Main orchestrator)
│
└── tests/ (Unit tests with pytest)
```

### Critical Lifecycle

```
1. parse_args() → AppConfig
2. check_previous_crash() → bool
3. SingleInstanceLock.acquire()
4. QApplication()
5. ensure_session_lock()
6. setup_global_exception_handlers()
7. setup_signal_handlers()
8. create_splash_screen()
9. StartupManager.start() → background thread
10. app.exec() → Qt event loop
```

**CRITICAL**: If any step fails, it MUST:
- Log to file (not stdout, which may not flush before crash)
- Show user-facing error in splash screen
- Call `handle_startup_failure()` for graceful exit

---

## Module Structure

### `main.py` (Refactored)

**Purpose**: Application entry point and orchestration

**Size**: ~250 lines (down from 600+)

**Key Classes**:
- `NitroSenseApplication(QApplication)`: State container for long-lived objects

**Key Functions**:
- `main() -> int`: Entry point, returns exit code
- Dependency handling via slots

**When to Edit**:
- CLI argument parsing → edit `app_config.py`
- Session management → edit `app_state.py`
- Exception handlers → edit `app_exceptions.py`
- Signal handlers → edit `app_lifecycle.py`

### `app_config.py` (NEW)

**Purpose**: CLI argument parsing

```python
from nitrosense.core.app_config import parse_args, AppConfig

config = parse_args()
if not config.no_splash:
    print("Show splash screen")
```

### `app_state.py` (NEW)

**Purpose**: Session management, crash detection

```python
from nitrosense.core.app_state import (
    ensure_session_lock,
    clear_session_lock,
    check_previous_crash,
)

if check_previous_crash():
    print("Previous run crashed! Enabling recovery mode")
```

### `app_exceptions.py` (NEW)

**Purpose**: Global exception handlers for main thread, workers, and unraisable exceptions

```python
from nitrosense.core.app_exceptions import setup_global_exception_handlers

setup_global_exception_handlers(app)
# Now ALL unhandled exceptions are logged surgically
```

### `app_lifecycle.py` (NEW)

**Purpose**: Signal handlers (SIGTERM, SIGINT) and atexit cleanup

```python
from nitrosense.core.app_lifecycle import (
    setup_signal_handlers,
    setup_atexit_cleanup,
)

setup_signal_handlers(app)
setup_atexit_cleanup()
```

### `ui/log_viewer.py` (NEW)

**Purpose**: Log file viewer dialog

```python
from nitrosense.ui.log_viewer import LogViewerDialog
from pathlib import Path

dialog = LogViewerDialog(Path.home() / ".local/share/nitrosense/nitrosense.log")
dialog.exec()
```

---

## Setting Up Development Environment

### 1. Clone & Setup Python Virtual Environment

```bash
cd ~/Documentos/NitroSense\ Ultimate
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Development Tools

```bash
pip install mypy pytest pytest-cov black isort flake8
```

### 3. Verify Installation

```bash
python -c "import nitrosense; print('✓ Package imports correctly')"
```

---

## Type Checking with MyPy

### Why MyPy?

`mypy` is a static type checker that catches bugs **before runtime**:
- ✅ Missing type hints
- ✅ Function signature mismatches
- ✅ Optional/None type errors
- ✅ Attribute access errors

### Basic Usage

```bash
# Check entire project
mypy nitrosense/ main.py

# Check specific file
mypy nitrosense/core/logger.py --show-error-codes

# With strict mode (recommended)
mypy nitrosense/ main.py --strict
```

### Configuration: `mypy.ini`

```ini
[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False  # Too strict, start with False
disallow_incomplete_defs = True
check_untyped_defs = True
```

### Common MyPy Errors & Fixes

#### Error: Type mismatch in assignment

```python
# ❌ WRONG
system: NitroSenseSystem = None  # 'None' is not assignable to 'NitroSenseSystem'

# ✅ CORRECT
system: Optional[NitroSenseSystem] = None
```

#### Error: "X" has no attribute "Y"

```python
# ❌ WRONG
app.system.fan_controller.enable()  # app.system might be None!

# ✅ CORRECT
if app.system is not None:
    if hasattr(app.system, 'fan_controller'):
        app.system.fan_controller.enable()
```

#### Error: Method signature mismatch

```python
# In app_exceptions.py
def _global_exception_hook(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_traceback
) -> None:

# Register it
sys.excepthook = _global_exception_hook  # ✓ Correct signature
```

### Gradual Typing Strategy

1. **Phase 1**: Enable `check_untyped_defs` (catch obvious bugs)
2. **Phase 2**: Add type hints to critical modules (logger, error_handler, config)
3. **Phase 3**: Enable `disallow_incomplete_defs` (all funcs need return types)
4. **Phase 4**: Enable `strict` mode (full type safety)

---

## Common Errors & Solutions

### 1. **Silent App Crashes (No Error Message)**

#### Symptom
Application exits with code 1, but no error appears in logs or console.

#### Cause
Exception occurred before logging is initialized, OR exception in exception handler itself.

#### Solution

1. **Check if logging is initialized**:
   ```bash
   grep "setup_logging" main.py  # Should be near top
   ```

2. **Add early logging to main()**:
   ```python
   import sys
   print(f"DEBUG: Python {sys.version}", file=sys.stderr)  # Prints to stderr
   logger.info("Starting application")
   ```

3. **Check log file directly**:
   ```bash
   tail -n 50 ~/.local/share/nitrosense/nitrosense.log
   ```

4. **Run with stderr capture**:
   ```bash
   python main.py 2>&1 | tee debug.log
   ```

### 2. **QApplication Already Exists**

#### Symptom
```
RuntimeError: Please instantiate the QApplication before using this module
```

#### Cause
Trying to use PyQt6 widgets before creating `QApplication()`.

#### Solution

Ensure order:
```python
# ✗ WRONG
from nitrosense.ui.main_window import NitroSenseApp  # Imports QWidget
app = QApplication(sys.argv)

# ✓ CORRECT
app = QApplication(sys.argv)  # FIRST
from nitrosense.ui.main_window import NitroSenseApp  # Then imports
```

### 3. **Type Checker Doesn't Find Module**

#### Symptom
```
mypy: Cannot find implementation or library stub for module named "nitrosense"
```

#### Solution

```bash
# Create py.typed file if missing
touch nitrosense/py.typed

# Run mypy with PYTHONPATH
PYTHONPATH=. mypy nitrosense/ main.py
```

### 4. **ImportError: No module named 'nitrosense'**

#### Cause
Python path not setup correctly.

#### Solution

```python
# In main.py (already done)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### 5. **Hardware Permission Denied**

#### Symptom
```
PermissionError: /sys/class/power_supply: Permission denied
```

#### Solution

Run with `sudo`:
```bash
sudo source venv/bin/activate
sudo python main.py
```

Or setup udev rules:
```bash
sudo cat > /etc/udev/rules.d/99-nitrosense.rules << EOF
SUBSYSTEM=="power_supply", RUN+="/bin/chmod 644 %S%p/status"
EOF

sudo udevadm control --reload
```

---

## Debugging Techniques

### 1. **Surgical Exception Logging**

All unhandled exceptions now include:
- Module name
- Function name
- File and line number
- Last 5 local variables
- Full traceback

```python
# Automatically caught by setup_global_exception_handlers()
def risky_function():
    x = get_sensor_data()  # May fail
    return x["fan_speed"]  # May be KeyError
```

When this crashes, log shows:
```
UNHANDLED EXCEPTION - SURGICAL ERROR LOG
Module: nitrosense.hardware.manager
Function: risky_function
Line 123: /path/to/manager.py
Exception Type: KeyError
Exception Message: 'fan_speed'
Local variables (last 5):
  x = {'status': 'ok'}
  self = <HardwareManager object>
  ...
```

### 2. **Log Viewer in UI**

Press Ctrl+Shift+L to open log viewer (if hotkey registered):

```python
from nitrosense.ui.log_viewer import LogViewerDialog
from pathlib import Path

log_path = Path.home() / ".local/share/nitrosense/nitrosense.log"
viewer = LogViewerDialog(log_path)
viewer.exec()
```

Or programmatically:
```bash
# View last 100 lines
tail -n 100 ~/.local/share/nitrosense/nitrosense.log

# Search for errors
grep "ERROR\|CRITICAL" ~/.local/share/nitrosense/nitrosense.log

# Follow in real-time
tail -f ~/.local/share/nitrosense/nitrosense.log
```

### 3. **Debugging with PyCharm/VS Code**

#### PyCharm

1. **Set Python Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Select `venv/bin/python`

2. **Configure Run**:
   - Run → Edit Configurations
   - Script path: `main.py`
   - Working directory: project root

3. **Debug**:
   - Set breakpoint: Click line number
   - Debug → Debug 'main.py'
   - Step through code with F10/F11

#### VS Code

1. **Install Python extension**:
   ```
   ms-python.python
   ```

2. **Create `.vscode/launch.json`**:
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
         "name": "NitroSense",
         "type": "python",
         "request": "launch",
         "program": "${workspaceFolder}/main.py",
         "console": "integratedTerminal",
         "python": "${workspaceFolder}/venv/bin/python",
         "cwd": "${workspaceFolder}"
       }
     ]
   }
   ```

3. **Debug**:
   - F5 to start debugging
   - Click to set breakpoints

### 4. **Print Debugging (Simple)**

```python
from nitrosense.core.logger import logger

# NOT: print()  - won't flush before crash!
# YES: logger.info()  - goes to file immediately

logger.info(f"Debug: sensor_value={sensor_value}")
logger.warning(f"Unexpected state: {app.system}")
logger.error(f"Operation failed: {e}")
```

### 5. **Thread Debugging**

```python
import threading

# Log all threads
def log_threads():
    for thread in threading.enumerate():
        logger.info(f"Thread: {thread.name} (daemon={thread.daemon})")

# In main thread
log_threads()

# Output:
# Thread: MainThread (daemon=False)
# Thread: QThread (daemon=True)
# Thread: Worker (daemon=False)
```

---

## Testing Strategy

### Unit Tests with Pytest

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_logger.py::test_setup_logging

# Show print statements
pytest tests/ -s

# Coverage report
pytest tests/ --cov=nitrosense --cov-report=html
```

### Test Examples

```python
# tests/test_app_config.py
from nitrosense.core.app_config import parse_args
import sys

def test_parse_args_no_splash(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--no-splash"])
    config = parse_args()
    assert config.no_splash is True
    assert config.background is False

def test_parse_args_background(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--background"])
    config = parse_args()
    assert config.background is True
    assert config.no_splash is False
```

### Pytest Best Practices

```python
# Use fixtures for setup/teardown
@pytest.fixture
def temp_log_file(tmp_path):
    log_file = tmp_path / "test.log"
    yield log_file
    log_file.unlink(missing_ok=True)

def test_logging(temp_log_file):
    # Tests now have isolated temp file
    pass

# Use monkeypatch for mocking
def test_hardware_mock(monkeypatch):
    from nitrosense.hardware.interface import HardwareFactory
    
    monkeypatch.setenv("HARDWARE_MOCK", "true")
    hw = HardwareFactory.create()
    assert hw.is_mock
```

---

## Performance Profiling

### 1. **Measure Startup Time**

```python
import time

def main() -> int:
    start = time.monotonic()
    logger.info(f"Startup began at {start}")
    
    # ... initialization code ...
    
    finish = time.monotonic()
    logger.info(f"Startup completed in {finish - start:.2f}s")
    return 0
```

### 2. **Profile with cProfile**

```bash
# Generate profile
python -m cProfile -o profile.out main.py

# View profile
python -m pstats profile.out
  >>> sort cumulative
  >>> stats 20  # Top 20 functions
```

### 3. **Memory Profiling**

```bash
pip install memory-profiler

# Add decorator
@profile
def risky_function():
    large_list = list(range(1000000))  # 1MB
    return sum(large_list)

# Run with memory profiler
python -m memory_profiler main.py
```

### 4. **Qt-Specific Profiling**

```python
from PyQt6.QtCore import QTimer

def profile_qt_loop():
    timer = QTimer()
    timer.timeout.connect(lambda: logger.info("Qt loop tick"))
    timer.start(100)  # Log every 100ms
```

---

## Quick Reference

### Files Changed in This Refactor

| File | Status | Changes |
|------|--------|---------|
| `main.py` | ✏️ Modified | 600 lines → 250 lines, imports from modules |
| `app_config.py` | ✨ New | CLI argument parsing |
| `app_state.py` | ✨ New | Session lock & crash detection |
| `app_exceptions.py` | ✨ New | Global exception handlers |
| `app_lifecycle.py` | ✨ New | Signal & cleanup handlers |
| `ui/log_viewer.py` | ✨ New | Log file viewer dialog |

### Most Common Operations

```bash
# Type check
mypy nitrosense/ main.py

# Run tests
pytest tests/ -v

# Format code
black nitrosense/ main.py tests/

# Check style
flake8 nitrosense/ main.py

# Full startup with debug log
python main.py --no-splash 2>&1 | tee startup.log

# View last 20 errors
grep "ERROR\|CRITICAL" ~/.local/share/nitrosense/nitrosense.log | tail -20
```

### Custom Breakpoints (PyCharm)

```python
# Add `import pdb; pdb.set_trace()` to pause execution
if system is None:
    import pdb; pdb.set_trace()  # Execution stops here
    # Now type "n" to step, "c" to continue, etc.
```

---

## Additional Resources

- **PyQt6 Docs**: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **MyPy Docs**: https://mypy.readthedocs.io/
- **Pytest Docs**: https://docs.pytest.org/
- **Python Logging**: https://docs.python.org/3/library/logging.html

---

## Support & Questions

For debugging help:
1. Check last 50 lines of log file
2. Run `mypy` to catch type errors
3. Review crash report: `~/.local/share/nitrosense/last_crash_report.txt`
4. Check if previous crash (weak symbols in session lock)

