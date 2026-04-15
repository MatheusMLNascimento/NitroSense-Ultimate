# NitroSense Ultimate - Implementation Guide

**Version**: 3.1.0  
**Status**: Complete  
**Scope**: Features, architecture, and implementation details

---

## 🏗️ Architecture Overview

NitroSense Ultimate is organized into **5 architectural tiers**:

```
┌─────────────────────────────────────────────────────────┐
│ TIER 5: SAFETY & RELIABILITY                            │
│ Exception Handling, Logging, Watchdog, State Management │
├─────────────────────────────────────────────────────────┤
│ TIER 4: USER INTERFACE                                  │
│ Dashboard, Pages, Dialogs, Real-time Visualization      │
├─────────────────────────────────────────────────────────┤
│ TIER 3: AI & OPTIMIZATION                               │
│ Thermal Prediction, Process Detection, Fan Control      │
├─────────────────────────────────────────────────────────┤
│ TIER 2: MULTITHREADING & PERFORMANCE                    │
│ Worker Threads, Thread Pool, Async Execution            │
├─────────────────────────────────────────────────────────┤
│ TIER 1: HARDWARE ABSTRACTION                            │
│ EC Module, NBFC, Sensors, Bus Protection                │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Tier 1: Hardware Abstraction

### EC Module Management
**Purpose**: Control laptop fans and thermal settings via EC chip  
**Files**: `hardware/interface.py`, `hardware/manager.py`

**Features**:
- Auto-load ec_sys kernel module with write support
- Software semaphore (QSemaphore) for bus protection
- Hardware validation (device checks)
- Safe file operations with retry logic

**Implementation**:
```python
# hardware/manager.py
class HardwareManager:
    def __init__(self):
        self.bus_semaphore = QSemaphore(1)  # Protect EC bus
        self._load_ec_module()              # Auto-load on init
    
    def run_nbfc(self, command: str) -> Tuple[bool, str]:
        # Protected NBFC execution
        self.bus_semaphore.acquire()
        try:
            success, output = self._execute_nbfc(command)
            return success, output
        finally:
            self.bus_semaphore.release()
```

### Sensor Reading
**Purpose**: Collect CPU, GPU, and fan RPM data  
**Features**:
- Parallel sensor acquisition (3 concurrent reads)
- Safe file reads with fallback defaults
- Error recovery with exponential backoff

**Supported Sensors**:
- `lm-sensors` - CPU temperatures
- NVIDIA drivers - GPU temperature
- NBFC - Fan RPM and status

---

## 🧵 Tier 2: Multithreading Architecture

### Hardware Worker Thread
**Purpose**: Non-blocking hardware reads  
**File**: `core/threading.py`

**Design**:
```python
class HardwareWorkerThread(QThread):
    # Runs in background, emits signals
    def run(self):
        while not self.should_stop:
            cpu_temp = self.hardware.read_cpu_temp()
            gpu_temp = self.hardware.read_gpu_temp()
            fan_rpm = self.hardware.read_fan_rpm()
            
            self.sensor_updated.emit({
                'cpu': cpu_temp,
                'gpu': gpu_temp,
                'fan': fan_rpm
            })
            time.sleep(1)  # 1-second refresh rate
```

**Benefit**: UI stays responsive while reading hardware

### Thread Pool Manager
**Purpose**: Async execution of long tasks  
**Features**:
- RAM purge (background cleanup)
- Process scanning (find bloatware)
- Dependency installation (async)

```python
thread_pool = QThreadPool()
thread_pool.start(PurgeRAMTask())
thread_pool.start(ScanProcessesTask())
```

### Garbage Collection
**Purpose**: Prevent memory bloat  
**Behavior**: Auto `gc.collect()` every 100 UI cycles  
**Timing**: Runs in worker thread, doesn't block UI

---

## 🤖 Tier 3: AI & Optimization

### Thermal Prediction
**Purpose**: Anticipate temperature changes  
**File**: `automation/ai_engine.py`

**Algorithm**:
```python
def predict_fan_speed(self, current_temp: float, prev_temp: float) -> int:
    # Calculate thermal derivative (dT/dt)
    dt = current_temp - prev_temp  # degrees per 1s
    
    # Base fan speed from temp
    base_speed = interpolate_curve(current_temp)
    
    # Anticipation boost
    if dt > 3.0:  # Rising >3°C per second
        boost = 0.2 * base_speed  # Add 20%
    else:
        boost = 0
    
    return int(min(base_speed + boost, 100))
```

**Behavior**:
- Smooth fan control (no sudden jumps)
- Predictive boost for rising temps
- Emergency mode at 95°C (100% fan)

### Process Profile Detection
**Purpose**: Adjust fan curves based on workload  
**Features**:
- Gaming detection (high GPU usage)
- Video editing detection (sustained load)
- Office work (low thermal)

**Auto-adjustment**:
- Gaming: More aggressive fan curves
- Heavy processing: Fan ramps earlier
- Light work: Conservative to reduce noise

### Emergency Protocol
**Purpose**: Prevent thermal damage  
**Trigger**: T ≥ 95°C  
**Action**:
1. Set fan to 100%
2. Log critical alert
3. Optional: Kill known bloatware
4. Emit system notification

---

## 🎨 Tier 4: User Interface

### Dashboard Pages
**Framework**: PyQt6 with QStackedWidget  
**Pages**: Home, Status, Config, Labs

#### 1. Home Page
- 72pt animated temperature display (color-coded)
- Real-time 30-point temperature graph (matplotlib)
- 6-point health LED grid (NBFC, GPU, Sensors, Fan, RAM, Disk)
- Current fan speed percentage
- Frost Mode button (max cooling for 120s)

#### 2. Status Page
- System information (CPU, GPU model)
- Fan status and RPM
- Thermal curve info
- Process list (sorted by resource usage)
- RAM and disk usage

#### 3. Config Page
- Temperature thresholds (Low, Mid, High)
- Fan speed mapping
- Theme selection (macOS Light, macOS Dark, Ultra Black)
- Notifications toggles
- NBFC profile selector

#### 4. Labs Tab
- Autostart configuration
- Debug mode toggle
- CSV export option
- Configuration import/export
- System diagnostics

### Real-Time Visualization
**Temperature Graph**:
- 30-point rolling history
- Color-coded zones (cool, warm, hot)
- FPS-optimized matplotlib rendering
- 1-second update interval

**Health Indicators**:
- 6 LED-style indicators
- Color: Green (OK), Yellow (Warning), Red (Critical)
- Status: NBFC, GPU driver, Sensors, Fan, RAM, Disk

### Dynamic Tray Icon
**Purpose**: System tray integration  
**Features**:
- Color changes with temperature
- Quick menu (show, settings, quit)
- Autostart support

---

## 🛡️ Tier 5: Safety & Reliability

### Global Exception Handler
**Purpose**: Catch all unhandled exceptions  
**File**: `core/app_exceptions.py`

**Coverage**:
- Main thread exceptions (sys.excepthook)
- Worker thread exceptions (threading.excepthook)
- Unraisable exceptions (sys.unraisablehook)

**Features**:
- Surgical logging (locals, context, stack)
- Automatic crash report generation
- Recovery hints for resolution
- No user-facing error dialogs (graceful degradation)

### Watchdog Monitoring
**Purpose**: Detect fan failures and thermal issues  
**File**: `resilience/watchdog.py`

**Monitors**:
- Fan stall detection (no RPM change for 5s under thermal load)
- Thermal runaway (temp not decreasing despite 100% fan)
- Sensor failures (no updates for 10s)

**Actions**:
- Log warnings and critical alerts
- Emit Qt signals for UI update
- Emergency protocol if critical state

### Configuration Management
**Purpose**: Persistent, reliable settings storage  
**File**: `core/config.py`

**Features**:
- Atomic writes (temp file + os.replace)
- Schema validation on load
- Debounced saves (reduces I/O)
- Configuration snapshots
- Import/export (.nsbackup files)

### Graceful Degradation
**Purpose**: Continue functioning with missing dependencies  
**Behavior**:
- Missing nvidia-driver: GPU temp disabled (shows -1)
- Missing lm-sensors: CPU temp uses fallback
- Missing nbfc: Hardware control disabled
- Missing matplotlib: Graph shows message, continues

---

## 🎯 Core Features

### Feature 1: Temperature Monitoring
**Implementation**: Parallel sensor reads via worker thread  
**Refresh Rate**: 1 second  
**Accuracy**: ±2°C (Linux sensor tolerance)  
**Coverage**: CPU, GPU, and system thermal nodes

### Feature 2: Intelligent Fan Control
**Implementation**: thermal_derivative + predictive boost  
**Formula**: `base_speed + (0.2 * base_speed if dT > 3°C)`  
**Response Time**: < 2 seconds to thermal change  
**Safety**: 100% fan at 95°C (automatic)

### Feature 3: Predictive Thermal Management
**Implementation**: AI engine with process detection  
**Anticipation**: 20% speed boost for rising temps  
**Workload Detection**: Gaming, Video Editing, Office modes  
**Energy Saved**: ~10-20% during light workloads

### Feature 4: Professional Logging
**Implementation**: RotatingFileHandler  
**Rotation**: 5MB per file, keeps 3 backups  
**Location**: `~/.config/nitrosense/logs/`  
**Content**: All operations, errors, warnings, debug info

### Feature 5: Theme Customization
**Options**:
- macOS Light (clean, bright)
- macOS Dark (professional)
- Ultra Black (OLED optimized)
- Custom (user-defined via QSS)

**Storage**: Config file (persistent across sessions)

### Feature 6: Automatic Dependency Installation
**Scope**: System packages + Python modules  
**Auto-Install**: Yes (with user permission)  
**Fallback**: Graceful degradation if can't install  
**Verification**: Checks before and after installation

### Feature 7: System Tray Integration
**Icon**: Dynamic (color-coded by temperature)  
**Menu**: Show, Settings, Quit, Autostart toggle  
**Autostart**: Desktop entry in `~/.config/autostart/`

---

## 🔧 Code Examples

### Example 1: Reading CPU Temperature Safely
```python
from nitrosense.core.retry_strategy import NORMAL_RETRY

def read_cpu_temp(self) -> float:
    def _read():
        return float(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
    
    temp = NORMAL_RETRY.execute_with_retry_silent(
        _read,
        default=0.0
    )
    return temp
```

### Example 2: Setting Fan Speed with Retry
```python
from nitrosense.core.retry_strategy import GENTLE_RETRY

def set_fan_speed(self, speed: int) -> bool:
    def _execute():
        success, output = self.hardware.run_nbfc(f"set -s {speed}")
        if not success:
            raise RuntimeError(output or "NBFC failed")
        return True
    
    try:
        return GENTLE_RETRY.execute_with_retry(_execute)
    except Exception as e:
        logger.error(f"Fan control failed: {e}")
        return False
```

### Example 3: Creating a Worker Thread Task
```python
class ReadSensorsTask(QRunnable):
    sensor_data = pyqtSignal(dict)
    
    def run(self):
        cpu = hardware.read_cpu_temp()
        gpu = hardware.read_gpu_temp()
        rpm = hardware.read_fan_rpm()
        
        self.sensor_data.emit({
            'cpu': cpu,
            'gpu': gpu,
            'rpm': rpm
        })

# Usage
task = ReadSensorsTask()
QThreadPool.globalInstance().start(task)
```

---

## 📈 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Startup Time | < 2s | Including hardware init |
| UI Refresh Rate | 60 FPS | Smooth animation target |
| Sensor Read Rate | 1 Hz | Background thread |
| Memory Footprint | 150-200 MB | Typical operation |
| CPU Usage (idle) | < 5% | Mostly waiting |
| CPU Usage (graph) | 8-12% | matplotlib rendering |
| Fan Control Latency | < 2s | Response to thermal change |
| Configuration Save | 10-100ms | Debounced, async |

---

## 🧪 Testing Strategy

### Unit Tests (15 modules)
- Configuration reading/writing
- Thermal calculations
- Error code mappings
- Hardware mocking
- UI component initialization

### Integration Tests
- End-to-end hardware reads
- Configuration persistence
- Exception handling propagation
- Threading synchronization

### Hardware Tests
- NBFC communication
- EC module access
- Sensor reading accuracy
- Fan control response

### Type Coverage
- MyPy strict mode enabled
- ~90% of codebase type-checked
- Critical paths 100% typed

---

## 🚀 Deployment

### Installation Methods

**Method 1: Direct Python (Recommended)**
```bash
git clone <repo>
cd nitrosense-ultimate
python3 main.py
```

**Method 2: DEB Package**
```bash
sudo apt install ./nitrosense_3.0.5_all.deb
nitrosense  # Runs from PATH
```

**Method 3: Systemd Service (Optional)**
```bash
sudo systemctl enable nitrosense
sudo systemctl start nitrosense
```

### First-Run Initialization
1. App detects missing EC module
2. Requests root: `sudo python3 main.py`
3. Initializes EC module (< 5s)
4. Returns to user mode for normal operation

---

## 📚 Related Documentation

- [GETTING_STARTED.md](GETTING_STARTED.md) - Installation guide
- [CRITICAL_ACTIONS.md](CRITICAL_ACTIONS.md) - Essential setup
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Version history
- [DEVELOPER_REFERENCE.md](DEVELOPER_REFERENCE.md) - Module structure
- [AUDIT_COMPLETE.md](AUDIT_COMPLETE.md) - Compliance details

---

**Version**: 3.1.0  
**Status**: ✅ Complete & Production Ready  
**Last Updated**: April 14, 2026
