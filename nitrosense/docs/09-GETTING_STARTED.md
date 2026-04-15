# Getting Started with NitroSense Ultimate v3.1.0

Professional thermal and fan control application for Acer Nitro 5 and compatible laptops on Ubuntu 24.04

## What is NitroSense Ultimate?

NitroSense Ultimate is a comprehensive thermal management system for Linux laptops with:
- **Real-time thermal monitoring** - CPU, GPU, and fan RPM tracking
- **Intelligent fan control** - Predictive thermal management with AI
- **Beautiful dashboard** - Multi-page UI with live temperature graphs
- **Automatic dependency installation** - Smart detection and setup

---

## 🚀 Quick Installation (Recommended - 1 minute)

The easiest way to get started:

```bash
git clone https://github.com/your-repo/nitrosense-ultimate.git
cd nitrosense-ultimate
python3 main.py
```

The application will **automatically detect and install any missing dependencies**!

**First run requires root to initialize EC module**:
```bash
sudo python3 main.py
```

---

## 📦 Manual Installation (If Automatic Setup Fails)

### Step 1: Install System Dependencies

**On Ubuntu 24.04:**
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-dev python3.12-venv build-essential
sudo apt install -y nbfc nvidia-driver-535 lm-sensors
```

### Step 2: Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run the Application

```bash
# First time (requires root for EC module)
sudo python3 main.py

# Subsequent times (no sudo needed if EC module loaded)
python3 main.py
```

---

## 🔧 System Requirements

- **OS**: Ubuntu 24.04 LTS
- **Python**: 3.10+
- **Hardware**: Acer Nitro 5 or compatible laptop
- **GPU**: NVIDIA (for full GPU monitoring)
- **RAM**: 150 MB minimum
- **Disk**: 100 MB for installation

---

## ✨ Key Features

### Hardware Management
- EC Module control with write support
- Thread-safe NBFC communication
- Exponential backoff retry logic
- Hardware ID validation
- Multi-device support

### Thermal Intelligence
- Thermal derivative calculation (dT/dt)
- Predictive fan speed adjustment
- Emergency protocol (100% fan at 95°C)
- Gaming/workload detection
- Process profile auto-adjustment

### User Experience
- Multi-page dashboard (Home, Status, Config, Labs)
- Live temperature graphs
- 6-point health indicator LED grid
- Frost Mode (120s max cooling)
- Configuration import/export

### Reliability & Safety
- Global exception handler with detailed logging
- Professional rotating file handler (5MB limit)
- Configuration snapshots and backups
- Watchdog monitoring for fan stalls
- Graceful degradation with missing dependencies

---

## 🏃 First Time Setup

### 1. Start the Application
```bash
sudo python3 main.py
```

### 2. Set Up NBFC Profile
- Go to **Config** tab
- Select your laptop model (auto-detected)
- Click "Apply Profile"

### 3. Configure Temperature Thresholds (Optional)
- Low: 50°C
- Mid: 65°C
- High: 80°C
- Adjustable in Config tab

### 4. Enable Autostart (Optional)
- Go to **Labs** tab
- Check "Start with System"
- Application will launch on boot

---

## 💻 Hardware Detection

### Supported Laptops
- Acer Nitro 5 (AN515-51, AN515-52, etc.)
- Other Acer models with EC module support
- Compatible devices via NBFC profiles

### Auto-Detected Hardware
- CPU temperature (via lm-sensors)
- GPU temperature (if NVIDIA driver installed)
- Fan RPM (via NBFC)
- System RAM usage
- Disk usage

---

## 🔐 Security & Permissions

### Root Access
- **Required for**: Initializing EC module (first run only)
- **Not required for**: Normal operation after EC module is loaded

### Passwordless Sudo (Optional, for auto-installation)
To enable automatic dependency installation without password prompts:

```bash
sudo visudo
```

Add at the end:
```
%sudo ALL=(ALL) NOPASSWD: /usr/bin/apt
%sudo ALL=(ALL) NOPASSWD: /usr/bin/pip
```

---

## ✅ Verify Installation

### Check NBFC Status
```bash
sudo nbfc status
```

Should show:
- EC module loaded
- Current fan speed
- Thermal curve applied

### Check Sensors
```bash
sensors
```

Should display CPU and GPU temperatures

### Run Application
```bash
python3 main.py
```

Should show home screen with real-time monitoring

---

## 🆘 Troubleshooting

### Application won't start
- Ensure you have Python 3.10+: `python3 --version`
- Check if PyQt6 is installed: `pip list | grep PyQt6`
- Run with verbose output: `python3 main.py -v 2>&1 | head -50`

### Fan control not working
- Verify NBFC installed: `which nbfc`
- Check NBFC status: `sudo nbfc status`
- Ensure EC module loaded: `lsmod | grep ec_`

### Missing dependencies
- Let the app auto-install, OR
- Manually run: `pip install -r requirements.txt`

### Permission errors
- First run needs root: `sudo python3 main.py`
- Subsequent runs may not need sudo

---

## 📚 Next Steps

- **Read [CRITICAL_ACTIONS.md](CRITICAL_ACTIONS.md)** for must-do configurations
- **Read [IMPLEMENTATION.md](IMPLEMENTATION.md)** for feature explanations
- **Read [DEBUGGING_GUIDE.md](../DEBUGGING_GUIDE.md)** for development info
- **Check [PROJECT_STATUS.md](PROJECT_STATUS.md)** for version history

---

## 📞 Support

For issues and troubleshooting:
1. Check [DEBUGGING_GUIDE.md](../DEBUGGING_GUIDE.md)
2. Review logs: `~/.config/nitrosense/logs/`
3. Check git issues: `https://github.com/your-repo/nitrosense-ultimate/issues`

---

**Version**: 3.1.0  
**Last Updated**: 14 April 2026  
**Status**: Production Ready
