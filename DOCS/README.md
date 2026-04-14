# NitroSense Ultimate v3.1.0

Professional thermal and fan control application for Acer Nitro 5 and compatible laptops on Ubuntu 24.04

## Features

### 🔧 Hardware Layer (Tier 1)
- **EC Module Management**: Automatic loading of ec_sys kernel module with write support
- **Semaphore Bus Protection**: Thread-safe NBFC communication with QSemaphore
- **Exponential Backoff Retry**: Intelligent error recovery with progressive delays
- **Hardware ID Validation**: Device compatibility checking
- **Multi-Device Support**: Automatic detection and profile selection for compatible laptops
- **Circuit Breaker Pattern**: Prevents infinite retries on persistent hardware failures

### 🧵 Multithreading Architecture (Tier 2)
- **Hardware Worker Thread**: Non-blocking sensor reading
- **Thread Pool Manager**: Async task execution (RAM purge, process scanning)
- **Parallel Sensor Reading**: Concurrent CPU/GPU/RPM data acquisition
- **Async Process Execution**: QProcess for long-running commands
- **Garbage Collection**: Automatic memory cleanup every 100 UI cycles

### 🤖 AI & Predictive Logic (Tier 3)
- **Thermal Derivative**: dT/dt calculation for predictive fan speed
- **Anticipation Mode**: 20% speed boost if temp rising > 3°C/1.5s
- **Emergency Protocol**: Auto-kill bloatware + 100% fan at T ≥ 95°C
- **Process Profile Detection**: Auto-adjust for gaming, video editing, etc.

### 📊 User Interface (Tier 4)
- **Multi-Page Dashboard**: Home, Status, Config, Labs via QStackedWidget
- **LCD Temperature Display**: 72pt animated display with color gradients
- **Real-time Graphs**: 30-point temperature history with matplotlib
- **Status LED Grid**: 6 health indicators (NBFC, GPU, Sensors, Fan, RAM, Disk)
- **Frost Mode**: Button for 120s of 100% cooling
- **Automatic Dependency Installation**: Smart detection and installation of missing system/Python dependencies
- **Debounced Configuration Saves**: Prevents UI lag from rapid settings changes

### 🛡️ Safety & Reliability (Tier 5)
- **Global Exception Handler**: Custom error dialogs with full traceback
- **Professional Logging**: RotatingFileHandler limited to 5MB
- **Configuration Snapshots**: Export/import .nsbackup files
- **Watchdog Monitoring**: Detects fan stalls under thermal load
- **Dependency Graceful Degradation**: App continues with limited functionality when dependencies are missing
- **Input Validation**: Range checking and schema validation for all settings

## Installation

### 🚀 Quick Start (Recommended)

**One-command installation**:
```bash
git clone https://github.com/your-repo/nitrosense-ultimate.git
cd nitrosense-ultimate
python3 main.py
```

The application will **automatically detect and offer to install** any missing dependencies during startup!

### 📦 Manual Installation

If you prefer manual installation or automatic installation is not available:

**Ubuntu 24.04**:
```bash
sudo apt-get install python3.12 python3.12-dev python3.12-venv
sudo apt-get install nbfc nvidia-driver-535 lm-sensors
```

**Create Virtual Environment**:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 🔧 Automatic Dependency Installation

The app includes **smart dependency detection** that can automatically install missing components:

- **System Tools**: nbfc, nvidia-driver-535, lm-sensors
- **Python Packages**: PyQt6, psutil, matplotlib, numpy, pynput

**Requirements for Auto-Installation**:
- Passwordless sudo access (configure with `sudo visudo`)
- Internet connection
- pip installed

**How it works**:
1. App detects missing dependencies during startup
2. Shows a dialog asking for installation permission
3. Automatically installs missing components
4. Remembers your choice for future startups
5. Continues with full functionality

### 🎯 Running the Application

```bash
python3 main.py
```

**First run requires root to initialize EC module:**
```bash
sudo python3 main.py
```

## Architecture

```
nitrosense/
├── core/                 # Foundation layer
│   ├── constants.py     # Global constants & config maps
│   ├── config.py        # Singleton config manager
│   ├── logger.py        # Professional logging
│   ├── error_handler.py # Global exception handling
│   ├── monitoring.py    # Hardware metrics engine
│   └── threading.py     # Thread pool & workers
├── hardware/            # Low-level system access
│   └── manager.py       # EC, NBFC, semaphore protection
├── automation/          # AI & control logic
│   ├── ai_engine.py     # Predictive algorithms
│   └── fan_control.py   # Direct fan speed commands
├── ui/                  # User interface
│   ├── main_window.py   # Main application window
│   └── pages/           # Individual pages
│       ├── home_page.py
│       ├── status_page.py
│       ├── config_page.py
│       └── labs_page.py
└── assets/              # Icons, themes, resources
```

## Configuration

Settings are stored in `~/.config/nitrosense/config.json`:

```json
{
  "thermal": {
    "temp_thresholds": {"Low": 50, "Mid": 65, "High": 80},
    "speed_thresholds": {"Low": 30, "Mid": 60, "High": 100},
    "idle_speed": 20,
    "emergency_temp": 95
  },
  "advanced_config": {
    "theme": "macOS_Dark",
    "ui_layout_type": "column",
    "ui_scale": 1.0,
    "ping_target": "8.8.8.8",
    "frost_duration": 120,
    "notifications": {
      "critical_temp": true,
      "fan_stall": true,
      "throttling": true,
      "update_available": false
    },
    "log_directory": "~/.config/nitrosense/logs",
    "start_minimized": false,
    "hide_graph": false,
    "auto_curve_enabled": false,
    "ai_sensitivity": 1.0,
    "battery_charge_limit": 100,
    "maintenance_scheduler_enabled": false,
    "maintenance_hour": 4,
    "debug_mode": false,
    "export_csv_enabled": false
  }
}
```

### Advanced Configuration Options

- **Theme**: Choose between macOS_Dark, Ultra_Black, or Light themes
- **UI Layout**: Column, row, or compact layout options
- **UI Scale**: Adjust interface size (0.75x to 1.5x)
- **Hide Graph**: Hide the temperature history graph on the home page
- **Auto Fan Curve**: Enable automatic curve adjustment based on usage
- **AI Sensitivity**: Adjust predictive AI responsiveness (0.1 to 2.0)
- **Battery Charge Limit**: Set maximum battery charge percentage
- **Start Minimized**: Launch app minimized to system tray
- **Debug Mode**: Enable detailed logging for troubleshooting
- **CSV Export**: Allow exporting monitoring data to CSV files

## Safety Features

### Emergency Protocol (T ≥ 95°C)
1. Auto-kill background processes (Steam, Chrome, VS Code, etc.)
2. Force fan to 100%
3. Display critical alert with thermal summary
4. Throttle CPU if needed

### Watchdog Monitoring
- Alerts if fan not spinning above 75°C
- Detects potential hardware failure
- Triggers system notification

### Predictive Anticipation
- Monitors temperature rate of change (dT/dt)
- If rising > 3°C per 1.5s, boost fan speed by 20%
- Prevents thermal spikes during load transitions

## Troubleshooting

### NBFC Command Timeout
```
Error Code 101: NBFC_TIMEOUT after 5 retries
```
→ Check if nbfc_service is running: `systemctl status nbfc_service`

### EC Module Not Available
```
EC module not loaded - limited functionality
```
→ Requires root permissions initially. Run with `sudo python3 main.py`

### NVIDIA GPU Not Detected
```
GPU temperature read failed
```
→ Install nvidia-driver: `sudo apt-get install nvidia-driver-535`

## Performance Metrics

- **UI Update Rate**: 2000ms (configurable)
- **Hardware Scan Rate**: 1500ms
- **Thread Pool**: 4 concurrent workers
- **Graph History**: 30 temperature samples
- **Memory Cache**: Last 5 readings averaged
- **GC Interval**: Every 100 UI updates (~3.3 minutes)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

### Running in Debug Mode

```python
# In main.py, change LOG_CONFIG["log_level"] to "DEBUG"
```

### Testing Individual Components

```python
from nitrosense.hardware.manager import HardwareManager
from nitrosense.core.monitoring import MonitoringEngine

hardware = HardwareManager()
monitoring = MonitoringEngine(hardware)
metrics = monitoring.get_system_metrics()
print(metrics)
```

## License

GPL-3.0 - See LICENSE file

## Support

For issues, feature requests, or updates:
- GitHub Issues: [repository/issues]
- System Requirements: Ubuntu 24.04, Python 3.12+, Acer Nitro 5

---

**NitroSense Ultimate v2.0.0**  
*Professional Thermal Management for Linux Gaming Laptops*
