# NitroSense Ultimate v3.6 Realistic Roadmap

**Advanced Analytics + Plugin System + Cross-Platform**

---

## Upgrade Summary

- **Version:** 3.0.5 → 3.6
- **Focus:** Analytics persistence + plugin extensibility + cross-platform support
- **New Components:** 6 major features (analytics, plugins, platforms, workload detection)
- **Analytics:** 30-day rolling window thermal history with SQLite persistence
- **Plugin Architecture:** Extensible hardware/automation profiles (JSON-based)
- **Workload Detection:** Process-based classification (no ML required)
- **CPU Target:** Monitoring + analytics <1.5% background (minimal overhead)
- **Cross-Platform:** Ubuntu 24.04, Fedora 40, Debian 12 support

---

## Architecture Layers (v3.6)

### Layer 0: Plugin & Extensibility Framework (NEW)

- **Plugin Registry:** JSON-manifest based module discovery
- **Hardware Profiles:** Custom EC/NBFC implementations per device
- **Automation Rules:** User-defined thermal curves and thresholds
- **Configuration Schema:** JSON schema validation for all configs
- **Profile Management:** Load/save/activate hardware profiles
- **Plugin Lifecycle:** Load/unload/enable/disable management

### Layer 1: Thermal Analytics Engine (NEW)

- **Metrics Persistence:** SQLite database (30-day rolling window)
- **Hourly Aggregation:** Average/peak/sustained metrics per hour
- **Trend Analysis:** Time-of-day patterns, daily avg trends
- **Historical Reports:** CSV/PDF export (monthly summaries)
- **Anomaly Detection:** Simple variance-based (no ML)
- **Performance Metrics:** Fan efficiency vs temperature outcomes

### Layer 2: Advanced Monitoring (ENHANCED)

- **Process-Level:** Per-process CPU/GPU usage attribution
- **Workload Detection:** Gaming/video/coding/office classification
- **System Metrics:** Battery health, thermal throttling events
- **Network Telemetry:** (Optional) Bandwidth monitoring
- **Disk Thermal:** SSD temperature monitoring
- **Health Status:** Real-time system diagnostics

### Layer 3: Cross-Platform Support (ENHANCED)

- **Ubuntu 24.04:** Primary (EC module native)
- **Fedora 40:** Secondary (SELinux profiles)
- **Debian 12:** Tertiary (minimal dependencies)
- **Hardware Profiles:** Acer Nitro 5, ASUS TUF, Dell XPS templates
- **Dependency Auto-Detection:** Handles variations across distros
- **Systemd Integration:** Service/timer units for all platforms

### Layer 4: Resilience & Safety Framework (from v3.0.5, ENHANCED)

- **Signal Hub:** Extended for plugin events
- **State Machine:** Plugin-aware state management
- **Watchdog:** Enhanced failure detection
- **Auto-Recovery:** Graceful degradation if plugins fail
- **Crash Recovery:** Session state snapshots
- **Data Integrity:** SQLite transaction safety

### Layer 5: User Interface (ENHANCED)

- **Home Page:** Traditional metrics (no ML overlay)
- **Analytics Page:** NEW 30-day history with CSV export
- **Profile Manager:** Install/configure/toggle profiles
- **Settings Page:** Cross-platform settings
- **Advanced Labs:** Benchmarking tools, hardware diagnostics
- **Workload Indicator:** Real-time workload display

---

## v3.6 New Major Components

### [1] Plugin System & Registry ✅

**File:** `nitrosense/plugins/plugin_registry.py` (250 lines)

**Purpose:** Allow users to extend app with custom hardware profiles and automation rules

```python
class PluginMetadata:
    """Plugin manifest structure"""
    name: str
    version: str
    author: str
    description: str
    hardware_model: str  # "acer_nitro_5", "asus_tuf_gaming", etc.
    config_schema: Dict[str, Any]  # JSON schema for settings
    thermal_curves: Dict[str, List[Tuple[int, int]]]  # temp -> fan%
    compatibility: List[str]  # ["3.6", "3.7"]

class PluginRegistry:
    """Central plugin registry with lifecycle management"""
    
    def __init__(self, plugins_dir: str):
        self.plugins_dir = Path(plugins_dir)
        self.loaded = {}
        self.metadata = {}
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """Scan plugins directory for manifest.json files"""
        plugins = []
        for plugin_dir in self.plugins_dir.iterdir():
            manifest_path = plugin_dir / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    metadata = json.load(f)
                    plugins.append(metadata)
                    self.metadata[metadata["name"]] = metadata
        return plugins
    
    def load_profile(self, name: str) -> Dict:
        """Load hardware profile from plugin"""
        try:
            metadata = self.metadata[name]
            return metadata  # Return as working profile
        except Exception as e:
            logger.error(f"Profile load failed {name}: {e}")
            return None
    
    def get_thermal_curves(self, profile_name: str) -> Dict[str, List]:
        """Get thermal curves for given profile"""
        if profile_name in self.metadata:
            return self.metadata[profile_name].get("thermal_curves", {})
        return {}
```

**Example plugin (manifest.json):**

```json
{
    "name": "acer_nitro_5_profile",
    "version": "1.0",
    "author": "NitroSense Team",
    "description": "Optimized curves for Acer Nitro 5",
    "hardware_model": "acer_nitro_5",
    "thermal_curves": {
        "performance": [[50, 30], [60, 50], [75, 80], [95, 100]],
        "balanced": [[50, 25], [65, 40], [80, 70], [95, 100]],
        "quiet": [[50, 20], [70, 35], [85, 60], [95, 100]]
    }
}
```

**Usage:**

```python
registry = PluginRegistry("~/.config/nitrosense/plugins")
registry.discover_plugins()
curves = registry.get_thermal_curves("acer_nitro_5_profile")
```

---

### [2] Thermal Analytics Engine ✅

**File:** `nitrosense/analytics/thermal_history_db.py` (200 lines)

**Purpose:** Persistent storage of hourly thermal metrics (30-day rolling window)

```python
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

class ThermalHistoryDB:
    """SQLite database for thermal metrics"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thermal_history (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME NOT NULL UNIQUE,
                    cpu_temp_avg REAL,
                    cpu_temp_peak REAL,
                    gpu_temp_avg REAL,
                    gpu_temp_peak REAL,
                    fan_rpm_avg INTEGER,
                    fan_speed_avg INTEGER,
                    cpu_util_avg REAL,
                    gpu_util_avg REAL,
                    power_draw_avg REAL,
                    throttling_events INTEGER,
                    workload TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for fast timestamp queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON thermal_history(timestamp)
            """)
            
            conn.commit()
    
    def insert_hourly_metrics(self, metrics: Dict[str, Any]):
        """Save hourly aggregated metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO thermal_history 
                (timestamp, cpu_temp_avg, cpu_temp_peak, gpu_temp_avg, gpu_temp_peak,
                 fan_rpm_avg, fan_speed_avg, cpu_util_avg, gpu_util_avg, 
                 power_draw_avg, throttling_events, workload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.get('timestamp'),
                metrics.get('cpu_temp_avg'),
                metrics.get('cpu_temp_peak'),
                metrics.get('gpu_temp_avg'),
                metrics.get('gpu_temp_peak'),
                metrics.get('fan_rpm_avg'),
                metrics.get('fan_speed_avg'),
                metrics.get('cpu_util_avg'),
                metrics.get('gpu_util_avg'),
                metrics.get('power_draw_avg'),
                metrics.get('throttling_events'),
                metrics.get('workload')
            ))
            conn.commit()
    
    def query_date_range(self, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
        """Query thermal data for date range"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM thermal_history
                WHERE DATE(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp
            """
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            return df
    
    def get_statistics(self, days: int = 30) -> Dict[str, float]:
        """Get statistics for last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT 
                    AVG(cpu_temp_avg) as avg_cpu,
                    MAX(cpu_temp_peak) as peak_cpu,
                    AVG(fan_speed_avg) as avg_fan,
                    SUM(throttling_events) as total_throttle
                FROM thermal_history
                WHERE timestamp > ?
            """, (cutoff,)).fetchone()
        
        return {
            "avg_cpu_temp": results[0],
            "peak_cpu_temp": results[1],
            "avg_fan_speed": results[2],
            "total_throttle_events": results[3]
        }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove data older than N days (rolling window)"""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM thermal_history WHERE timestamp < ?", 
                (cutoff,)
            )
            conn.commit()
            logger.info(f"✅ Cleaned up analytics data older than {days_to_keep} days")
```

---

### [3] Analytics Dashboard Page ✅

**File:** `nitrosense/ui/pages/analytics_page.py` (300 lines)

**Purpose:** 30-day thermal history visualization and export

```python
class AnalyticsPage(QWidget):
    """Advanced analytics dashboard with historical data"""
    
    def __init__(self, system: NitroSenseSystem):
        super().__init__()
        self.system = system
        self.db = ThermalHistoryDB("~/.config/nitrosense/thermal_history.db")
        
        layout = QVBoxLayout()
        
        # Date range selector
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        date_layout.addWidget(self.date_from)
        
        date_layout.addWidget(QLabel("to"))
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_to)
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._refresh_analytics)
        date_layout.addWidget(btn_refresh)
        date_layout.addStretch()
        
        layout.addLayout(date_layout)
        
        # Matplotlib figure for temperature graph
        self.fig = Figure(figsize=(12, 5))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.label_avg_cpu = QLabel("Avg CPU: --°C")
        self.label_peak_cpu = QLabel("Peak CPU: --°C")
        self.label_avg_fan = QLabel("Avg Fan: --%")
        self.label_throttle = QLabel("Throttle Events: 0")
        
        stats_layout.addWidget(self.label_avg_cpu)
        stats_layout.addWidget(self.label_peak_cpu)
        stats_layout.addWidget(self.label_avg_fan)
        stats_layout.addWidget(self.label_throttle)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # Export buttons
        export_layout = QHBoxLayout()
        btn_csv = QPushButton("Export CSV")
        btn_csv.clicked.connect(self._export_csv)
        export_layout.addWidget(btn_csv)
        
        btn_pdf = QPushButton("Export PDF Summary")
        btn_pdf.clicked.connect(self._export_pdf)
        export_layout.addWidget(btn_pdf)
        export_layout.addStretch()
        
        layout.addLayout(export_layout)
        
        self.setLayout(layout)
        self._refresh_analytics()
    
    def _refresh_analytics(self):
        """Load and display thermal history"""
        start = self.date_from.date().toPyDate()
        end = self.date_to.date().toPyDate()
        
        try:
            data = self.db.query_date_range(start, end)
            
            if data.empty:
                QMessageBox.warning(self, "No Data", 
                    "No thermal data available for selected date range")
                return
            
            # Plot temperature history
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            
            ax.plot(data['timestamp'], data['cpu_temp_avg'], 
                   label='CPU Avg', color='red', linewidth=2)
            ax.plot(data['timestamp'], data['cpu_temp_peak'], 
                   label='CPU Peak', color='darkred', linestyle='--', linewidth=1)
            ax.plot(data['timestamp'], data['gpu_temp_avg'], 
                   label='GPU Avg', color='blue', linewidth=2)
            
            # Shade safe/danger zones
            ax.axhspan(0, 80, alpha=0.1, color='green', label='Safe')
            ax.axhspan(80, 100, alpha=0.1, color='red', label='Danger')
            
            ax.set_xlabel('Date & Time')
            ax.set_ylabel('Temperature (°C)')
            ax.set_title('30-Day Thermal History')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            
            self.fig.tight_layout()
            self.canvas.draw()
            
            # Update statistics
            stats = self.db.get_statistics(days=30)
            self.label_avg_cpu.setText(f"Avg CPU: {stats['avg_cpu_temp']:.1f}°C")
            self.label_peak_cpu.setText(f"Peak CPU: {stats['peak_cpu_temp']:.1f}°C")
            self.label_avg_fan.setText(f"Avg Fan: {stats['avg_fan_speed']:.0f}%")
            self.label_throttle.setText(f"Throttle Events: {stats['total_throttle_events']}")
            
        except Exception as e:
            logger.error(f"Analytics refresh failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load analytics: {e}")
```

---

### [4] Cross-Platform Support ✅

**File:** `nitrosense/platform/platform_detector.py` (150 lines)

**Purpose:** Handle differences between Ubuntu, Fedora, Debian

```python
class PlatformDetector:
    """Detect OS and adjust behavior accordingly"""
    
    @staticmethod
    def detect_distro() -> str:
        """Return distro: 'ubuntu', 'fedora', 'debian'"""
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('ID='):
                        distro = line.split('=')[1].strip().lower()
                        return distro
        except:
            pass
        
        return 'unknown'
    
    @staticmethod
    def get_package_manager() -> str:
        """Return package manager: 'apt', 'dnf'"""
        distro = PlatformDetector.detect_distro()
        if distro in ['ubuntu', 'debian']:
            return 'apt'
        elif distro in ['fedora']:
            return 'dnf'
        return 'apt'
    
    @staticmethod
    def install_dependency(package: str) -> bool:
        """Install system package"""
        pm = PlatformDetector.get_package_manager()
        
        try:
            if pm == 'apt':
                subprocess.run(['sudo', 'apt', 'install', '-y', package],
                             check=True, timeout=120)
            elif pm == 'dnf':
                subprocess.run(['sudo', 'dnf', 'install', '-y', package],
                             check=True, timeout=120)
            
            logger.info(f"✅ Installed {package}")
            return True
        except Exception as e:
            logger.error(f"Install failed for {package}: {e}")
            return False
    
    @staticmethod
    def get_distro_info() -> Dict[str, str]:
        """Get detailed OS information"""
        distro = PlatformDetector.detect_distro()
        
        try:
            result = subprocess.run(['lsb_release', '-ds'], 
                                  capture_output=True, text=True, timeout=5)
            description = result.stdout.strip() if result.stdout else distro
        except:
            description = distro
        
        return {
            "distro": distro,
            "description": description,
            "package_manager": PlatformDetector.get_package_manager()
        }
```

---

### [5] Workload Classification ✅

**File:** `nitrosense/automation/workload_classifier.py` (180 lines)

**Purpose:** Detect gaming/video/compilation without ML

```python
class WorkloadClassifier:
    """Process-based workload detection"""
    
    # Gaming signatures
    GAMING_PATTERNS = {
        'processes': ['steam', 'lutris', 'proton', 'wine', 'dxvk'],
        'keywords': ['csgo', 'elden ring', 'cyberpunk', 'minecraft', 'rust'],
    }
    
    # Video/Media signatures
    VIDEO_PATTERNS = {
        'processes': ['davinci', 'premiere', 'ffmpeg', 'handbrake', 'vlc', 'obs'],
        'keywords': ['rendering', 'encoding', 'transcoding']
    }
    
    # Development/Compilation signatures
    CODING_PATTERNS = {
        'processes': ['gcc', 'clang', 'cargo', 'cmake', 'make', 'ninja', 'python'],
        'keywords': ['compile', 'build', 'linking']
    }
    
    def __init__(self):
        self.current_workload = 'idle'
        self.workload_cache = {}
    
    def classify(self) -> str:
        """Return workload type: gaming/video/coding/office/idle/normal"""
        
        cpu_util = psutil.cpu_percent(interval=0.1)
        
        # Get running processes
        processes = []
        try:
            for proc in psutil.process_iter(['name']):
                processes.append(proc.info['name'].lower())
        except:
            pass
        
        process_str = ' '.join(processes)
        
        # Check for gaming
        if any(p in process_str for p in self.GAMING_PATTERNS['processes']):
            if cpu_util > 30:
                return 'gaming'
        
        # Check for video
        if any(p in process_str for p in self.VIDEO_PATTERNS['processes']):
            if cpu_util > 60:
                return 'video'
        
        # Check for coding
        if any(p in process_str for p in self.CODING_PATTERNS['processes']):
            if cpu_util > 50:
                return 'coding'
        
        # Check for office
        if any(p in ['firefox', 'chrome', 'libreoffice', 'thunderbird'] 
               for p in process_str.split()):
            if cpu_util < 40:
                return 'office'
        
        # Fallback to CPU-based classification
        if cpu_util < 10:
            return 'idle'
        elif cpu_util < 40:
            return 'normal'
        elif cpu_util < 70:
            return 'heavy'
        else:
            return 'extreme'
    
    def get_recommended_profile(self, workload: str) -> Dict[str, int]:
        """Return recommended fan curve for detected workload"""
        
        profiles = {
            'gaming': {50: 35, 60: 50, 75: 80, 90: 100},
            'video': {50: 40, 65: 60, 80: 85, 90: 100},
            'coding': {50: 30, 65: 50, 80: 70, 95: 100},
            'office': {50: 25, 70: 40, 85: 60, 95: 100},
            'idle': {50: 20, 70: 30, 80: 50, 95: 80},
            'normal': {50: 25, 65: 45, 80: 70, 95: 100}
        }
        
        return profiles.get(workload, profiles['normal'])
```

---

## Critical Changes & Integration

This section documents the key code changes required to upgrade from v3.0.5 to v3.6.
All examples use realistic implementations (no ML/deep learning).

### Change #1: Plugin Registry Integration

**Location:** `nitrosense/ui/main_window.py` (app initialization)

Add plugin system initialization:

```python
# In __init__:
self.plugin_registry = PluginRegistry(
    plugins_dir=Path.home() / ".config" / "nitrosense" / "plugins"
)

# Discover and load all plugins
try:
    discovered = self.plugin_registry.discover_plugins()
    logger.info(f"Found {len(discovered)} plugin(s)")
    
    for plugin_meta in discovered:
        if self.plugin_registry.load_profile(plugin_meta['name']):
            logger.info(f"✅ Loaded profile: {plugin_meta['name']}")
            self.ui.profiles_dropdown.addItem(plugin_meta['name'])
except Exception as e:
    logger.error(f"Plugin initialization failed: {e}")
```

**Benefits:**
- ✅ Users can add hardware profiles without code changes
- ✅ Custom thermal curves via JSON manifest
- ✅ Extensible architecture for future plugins

---

### Change #2: Thermal Analytics Database Integration

**Location:** `nitrosense/core/monitoring.py` (add analytics collection)

Add hourly metrics aggregation:

```python
class SystemMonitor:
    def __init__(self):
        self.db = ThermalHistoryDB("~/.config/nitrosense/thermal_history.db")
        self.hourly_timer = QTimer()
        self.hourly_timer.timeout.connect(self._save_hourly_metrics)
        self.hourly_timer.start(3600000)  # Every hour
        
        self.current_hour_metrics = {
            'temps': [],
            'fans': [],
            'cpu_utils': [],
            'gpu_utils': []
        }
    
    def on_update(self, metrics: Dict):
        """Called every ~1 second by monitoring loop"""
        # Collect data for hourly aggregation
        self.current_hour_metrics['temps'].append(metrics['cpu_temp'])
        self.current_hour_metrics['fans'].append(metrics['fan_speed'])
        self.current_hour_metrics['cpu_utils'].append(metrics['cpu_util'])
        self.current_hour_metrics['gpu_utils'].append(metrics['gpu_util'])
    
    def _save_hourly_metrics(self):
        """Aggregate and save hourly snapshot"""
        if not self.current_hour_metrics['temps']:
            return
        
        import numpy as np
        
        aggregated = {
            'timestamp': datetime.now().replace(minute=0, second=0),
            'cpu_temp_avg': np.mean(self.current_hour_metrics['temps']),
            'cpu_temp_peak': np.max(self.current_hour_metrics['temps']),
            'fan_speed_avg': np.mean(self.current_hour_metrics['fans']),
            'cpu_util_avg': np.mean(self.current_hour_metrics['cpu_utils']),
            'gpu_util_avg': np.mean(self.current_hour_metrics['gpu_utils']),
            'throttling_events': self._count_throttle_events()
        }
        
        self.db.insert_hourly_metrics(aggregated)
        
        # Clean old data (30-day rolling window)
        self.db.cleanup_old_data(days_to_keep=30)
        
        # Reset for next hour
        self.current_hour_metrics = {
            'temps': [], 'fans': [], 'cpu_utils': [], 'gpu_utils': []
        }
```

**Benefits:**
- ✅ Persistent thermal history for trend analysis
- ✅ 30-day rolling window (automatic cleanup)
- ✅ Foundation for future analytics dashboard
- ✅ No ML required (pure aggregation)

---

### Change #3: Workload Detection & Dynamic Profiles

**Location:** `nitrosense/automation/fan_control.py` (add workload detection)

Add automatic profile switching:

```python
class IntelligentFanController:
    def __init__(self, hardware_manager, config):
        self.hardware = hardware_manager
        self.config = config
        self.classifier = WorkloadClassifier()
        self.current_workload = 'normal'
        self.workload_timer = QTimer()
        self.workload_timer.timeout.connect(self._detect_workload)
        self.workload_timer.start(10000)  # Every 10 seconds
    
    def _detect_workload(self):
        """Detect active workload and switch profile if needed"""
        detected = self.classifier.classify()
        
        if detected != self.current_workload:
            logger.info(f"Workload changed: {self.current_workload} → {detected}")
            self.current_workload = detected
            
            # Get recommended profile for this workload
            recommended_profile = self.classifier.get_recommended_profile(detected)
            self._apply_profile(recommended_profile)
            
            # Emit signal to update UI
            self.workload_changed.emit(detected)
    
    def _apply_profile(self, profile: Dict[int, int]):
        """Apply temperature-to-fan-speed mapping"""
        current_temp = self.hardware.get_cpu_temperature()
        
        # Interpolate fan speed from profile
        temps = sorted(profile.keys())
        speeds = [profile[t] for t in temps]
        
        fan_speed = np.interp(current_temp, temps, speeds)
        self.hardware.set_fan_speed(int(fan_speed))
```

**Benefits:**
- ✅ Automatic profile selection based on running processes
- ✅ No user intervention needed (set and forget)
- ✅ Process-based detection (no ML/neural networks)
- ✅ Smooth transitions between workloads

---

## Success Criteria

v3.6 release is complete when the following criteria are met:

### Core Functionality
- ☑ All existing v3.0.5 features work identically
- ☑ No regressions in thermal control
- ☑ Fan curves behave as expected
- ☑ Emergency protocols (95°C throttle) work
- ☑ Configuration backward compatible

### Plugin System
- ☑ PluginRegistry discovers JSON plugins
- ☑ Plugins can define custom thermal curves
- ☑ Plugin enable/disable toggle works
- ☑ Example hardware profile plugin included
- ☑ Documentation for plugin development

### Analytics & Persistence
- ☑ ThermalHistoryDB creates SQLite database
- ☑ Hourly metrics aggregation works
- ☑ 30-day rolling window cleanup removes old data
- ☑ Analytics page renders 30-day graph
- ☑ CSV export includes all metrics
- ☑ PDF export readable and formatted

### Workload Detection
- ☑ Gaming workload detected (Steam, Lutris, Proton)
- ☑ Video editing detected (FFmpeg, DaVinci, Premiere)
- ☑ Coding workload detected (GCC, Cargo, CMake)
- ☑ Office/light load detected (Firefox, LibreOffice)
- ☑ Process list scanning works reliably
- ☑ Recommended profiles apply correctly

### Cross-Platform Support
- ☑ Ubuntu 24.04 detection works
- ☑ Fedora 40 detection works
- ☑ Debian 12 detection works
- ☑ Package manager detection (apt vs dnf)
- ☑ Dependency installation automated
- ☑ Systemd service works on all distros
- ☑ Configuration directory created correctly

### Performance
- ☑ Analytics queries <500ms on large dataset
- ☑ Background monitoring <2% CPU usage
- ☑ Plugin loading <2s for 10 plugins
- ☑ Workload detection scanning <100ms
- ☑ No memory leaks over 24-hour run

### Testing
- ☑ Plugin discovery tests passing
- ☑ Analytics database CRUD tests passing
- ☑ Workload classifier unit tests passing
- ☑ Export (CSV/PDF) integration tests passing
- ☑ Cross-platform detection tests passing
- ☑ No test coverage regression vs v3.0.5

---

## Deployment Checklist (v3.6)

### Plugin System
- ☐ Create `nitrosense/plugins/` directory structure
- ☐ Implement PluginRegistry class
- ☐ Create example Acer Nitro 5 profile plugin
- ☐ Plugin manifest.json schema validated
- ☐ Plugin enable/disable UI toggle implemented
- ☐ Plugin discovery scanning tested
- ☐ Plugin lifecycle (load/unload) clean

### Analytics
- ☐ Implement ThermalHistoryDB with SQLite
- ☐ Hourly aggregation timer integration
- ☐ AnalyticsPage with temperature graph
- ☐ 30-day history queries optimized
- ☐ CSV export tested (correct column headers)
- ☐ PDF export tested (ReportLab formatting)
- ☐ Old data cleanup scheduled (30-day window)

### Workload Detection
- ☐ WorkloadClassifier process detection working
- ☐ Gaming signatures comprehensive (Steam, Proton, etc)
- ☐ Video editing signatures complete (FFmpeg, OBS, etc)
- ☐ Coding signatures included (GCC, Cargo, Make, etc)
- ☐ Process list scanning reliable
- ☐ Recommended profile logic tested
- ☐ False positive rate acceptable (<5%)

### Cross-Platform
- ☐ Distro detection tested (Ubuntu/Fedora/Debian)
- ☐ Package manager detection (apt/dnf/yum)
- ☐ Auto-install dependency mechanism working
- ☐ Systemd service file for v3.6 created
- ☐ SELinux policy defined (if needed for Fedora)
- ☐ Configuration directories created automatically
- ☐ Permissions setup correct (config, plugins, data)

### Dependencies
- ☐ requirements.txt updated with new packages:
  - `pandas>=1.5.0` (data aggregation/analysis)
  - `reportlab>=4.0.0` (PDF generation)
  - `sqlite3` (bundled with Python)
- ☐ PyTorch/TensorFlow NOT in v3.6 (deferred to v4.0)
- ☐ No tensorflow dependency
- ☐ No scikit-learn for v3.6
- ☐ Optional numpy (some systems may already have)

---

## Migration Path (v3.0.5 → v3.6)

### Phase 1: Backward Compatibility ✅ CRITICAL

- Existing config files (v3.0.5) auto-migrate to v3.6 format
- Old thermal curves preserved and loaded
- Plugin system is additive (doesn't break existing code)
- Analytics DB created only on first run (not retroactive)
- Existing app behavior unchanged if plugins/analytics disabled

### Phase 2: New Dependencies Update

Add to requirements.txt (NO ML frameworks):

```
pandas>=1.5.0           # Data analysis & aggregation
reportlab>=4.0.0        # PDF generation
numpy>=1.20.0           # Optional (some may have it)
```

**DO NOT ADD:**
- ✗ torch (TensorFlow) - Deferred to v4.0
- ✗ scipy - Not needed for v3.6
- ✗ scikit-learn - Deferred to v4.0
- ✗ tensorflow - Deferred to v4.0+

### Phase 3: Database Migration

- SQLite database created automatically on first run
- v3.6 config schema adds plugin_registry section
- No migration needed for existing v3.0.5 data
- Analytics data isolated in separate DB file

### Phase 4: Configuration Update

Old v3.0.5 config → v3.6 Enhanced config:

```ini
[existing]
theme = dark

[new_in_v3.6]
enable_plugins = true
enable_analytics = true
analytics_retention_days = 30
workload_detection = auto
```

**No User Action Required:** Defaults are sensible

---

## Testing Strategy (v3.6)

### Unit Tests (pytest)

- ✅ `PluginRegistry.discover_plugins()` with test manifest files
- ✅ `PluginRegistry.load_profile()` returns correct metadata
- ✅ `ThermalHistoryDB.insert_hourly_metrics()` and `query_date_range()`
- ✅ `WorkloadClassifier.classify()` with mocked process list
- ✅ `PlatformDetector.detect_distro()` with different `/etc/os-release` files
- ✅ Analytics export: CSV contains correct columns/data
- ✅ Analytics export: PDF generates valid PDF format

### Integration Tests

- ✅ Plugin discovers, loads, and applies thermal curves
- ✅ Analytics page renders correctly with 30-day data
- ✅ Hourly metrics aggregation persists to database
- ✅ Workload detection changes UI status correctly
- ✅ CSV export produces valid CSV file
- ✅ PDF export produces valid PDF file
- ✅ 30-day cleanup removes old analytics data

### Performance Tests

- ✅ Analytics query <500ms on 30,000+ hourly records
- ✅ Plugin loading <2s for 10 plugins
- ✅ Workload detection scan <100ms per cycle
- ✅ Background monitoring <2% CPU (no ML overhead)
- ✅ Memory stable over 24-hour continuous run

### Platform Tests

- ✅ Ubuntu 24.04: apt install works, service starts
- ✅ Fedora 40: dnf install works, SELinux OK
- ✅ Debian 12: apt install works, dependencies resolve
- ✅ Config directories created correctly
- ✅ Permissions set correctly (user read/write)

### Edge Cases

- ✅ Handle missing processes gracefully (no app crash)
- ✅ Handle corrupted analytics DB (recreate)
- ✅ Handle malformed plugin manifest (skip plugin)
- ✅ Handle disk full during analytics save (log warning)
- ✅ Handle missing pandas/reportlab (GUI warning, app still runs)

---

## Summary

> **v3.6 is REALISTIC without ML**  
> **ML capabilities deferred to v4.0+ for solid architecture**  
> **v3.6 focus: Plugins, Analytics, Cross-Platform**  
> **Status: v3.6 READY FOR REALISTIC IMPLEMENTATION**

### 📦 Major New Components (Implementable in v3.6)

- plugin_registry.py (250 lines) - Hardware profile system
- thermal_history_db.py (200 lines) - SQLite analytics storage
- analytics_page.py (300 lines) - Dashboard with 30-day history
- workload_classifier.py (180 lines) - Process-based detection
- platform_detector.py (150 lines) - Cross-platform support

### ✨ New Analytics Features

- 30-day thermal history persistence
- Hourly metrics aggregation
- CSV data export
- PDF report generation
- Temperature trend visualization
- Workload detection & automatic profile switching

### 🔧 Extensibility Improvements

- Plugin system with JSON manifests
- Custom hardware profiles without code changes
- User-definable thermal curves via plugins
- Open architecture for future extensions

### ⚙️ Smart Workload Detection (Process-Based)

- Gaming detection (Steam, Proton, Lutris)
- Video editing detection (FFmpeg, OBS, DaVinci)
- Development detection (GCC, Cargo, CMake)
- Office detection (Firefox, LibreOffice)
- Automatic profile switching based on workload

### 🌍 Cross-Platform Support

- Ubuntu 24.04 with automatic apt-based install
- Fedora 40 with automatic dnf-based install
- Debian 12 with apt support
- Automatic package manager detection
- Distro-specific optimizations

### 📈 Performance Targets

- Analytics queries <500ms (no ML overhead)
- Workload detection <100ms per scan
- Background monitoring <2% CPU
- Plugin loading <2s for 10 plugins
- No memory leaks over 24-hour runs

### 🚀 Future Roadmap (v4.0+)

- ⏳ Machine Learning engine (LSTM thermal prediction)
- ⏳ PyTorch/TensorFlow integration
- ⏳ Advanced anomaly detection
- ⏳ ML-based performance advisor
- ⏳ Energy efficiency recommendations
