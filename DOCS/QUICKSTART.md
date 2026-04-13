"""
Quick Start Guide for NitroSense Ultimate

This guide will help you get NitroSense Ultimate running on your Acer Nitro 5.
"""

# =============================================================================
# INSTALLATION STEPS
# =============================================================================

## Step 1: Install Dependencies

### On Ubuntu 24.04:

```bash
# Update package list
sudo apt update

# Install Python 3.12 and development tools
sudo apt install -y python3.12 python3.12-dev python3.12-venv build-essential

# Install NBFC (Fan Control Service)
sudo apt install -y nbfc

# Install NVIDIA Drivers (if you have NVIDIA GPU)
sudo apt install -y nvidia-driver-535

# Install lm-sensors (CPU temperature)
sudo apt install -y lm-sensors

# Copy NBFC configuration for Acer Nitro
sudo cp /path/to/nitrosense/configs/acer-nitro-an515.nbfc \
  /etc/nbfc/Configs/

# Enable NBFC service
sudo systemctl enable --now nbfc_service
```

## Step 2: Setup Python Environment

```bash
# Navigate to project directory
cd ~/Downloads/"NitroSense Ultimate"

# Create virtual environment
python3.12 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

## Step 3: Run the Application

```bash
# First run requires root to initialize EC module
sudo ~/path/to/NitroSense/venv/bin/python3 main.py
```

---

# =============================================================================
# FIRST-TIME SETUP
# =============================================================================

When you launch NitroSense for the first time, the app will:

1. ✅ Load the EC kernel module (requires root)
2. ✅ Verify NBFC service is running
3. ✅ Check all dependencies
4. ✅ Initialize configuration files
5. ✅ Display splash screen with status

### What to Expect:

- **Splash Screen**: Shows initialization progress
- **Hardware Detection**: Should find your Nitro 5
- **Main Dashboard**: Home page with temperature display
- **Status Page**: Shows system health

### If You Get Warnings:

```
⚠️ Some dependencies are missing
   Please install: nvidia-smi
```

→ Install the missing tools:
```bash
sudo apt install nvidia-driver-535
```

---

# =============================================================================
# BASIC USAGE
# =============================================================================

### Home Dashboard
- Shows real-time CPU temperature
- GPU temperature (if available)
- Fan RPM
- History graph with last 30 readings
- Frost Mode button for emergency cooling

### Status Page
- 6 health indicators (green = OK, red = problem)
- NBFC service status
- NVIDIA GPU status
- Sensor status
- Fan hardware status
- Memory and disk usage

### Configuration Page
- Adjust thermal curve (3 levels: Low, Mid, High)
- Set temperature thresholds (default: 50°C, 65°C, 80°C)
- Set corresponding fan speeds (default: 30%, 60%, 100%)
- **Display & Behavior**: Theme selection, UI layout, scale, hide graph option
- **Notifications**: Toggle alerts for critical temp, fan stall, throttling, updates
- **Advanced Controls**: AI sensitivity, battery limit, maintenance scheduler, debug mode
- Save, reset, or export configuration

### Labs Page
- Run diagnostic tests
- Check NBFC responses
- Verify GPU communication
- Test sensors

---

# =============================================================================
# THERMAL CONFIGURATION
# =============================================================================

### Default Thermal Curve:

| Level | Temperature | Fan Speed |
|-------|-------------|-----------|
| Low   | 50°C        | 30%       |
| Mid   | 65°C        | 60%       |
| High  | 80°C        | 100%      |

### Recommended Adjustments:

**Gaming/Heavy Load:**
```
Low:  45°C → 40%
Mid:  60°C → 70%
High: 75°C → 100%
```

**Quiet/Office Work:**
```
Low:  55°C → 20%
Mid:  70°C → 50%
High: 85°C → 100%
```

**Performance/Cooling Priority:**
```
Low:  40°C → 50%
Mid:  55°C → 80%
High: 70°C → 100%
```

---

# =============================================================================
# EMERGENCY PROTOCOLS
# =============================================================================

### Predictive Anticipation
When temperature rises rapidly:
```
If dT/dt > 3°C per 1.5 seconds
→ Fan speed increases by 20%
```

**Scenario**: Starting a heavy game
```
60°C → Detects rapid rise
→ Automatically boosts fan to 72% (60% + 20%)
→ Prevents thermal spike
```

### Emergency Shutdown (T ≥ 95°C)
If CPU exceeds 95°C:
```
✅ Automatically kills non-essential processes
✅ Forces fan to 100%
✅ Displays critical alert
✅ Logs severe thermal event
```

**Killed Processes**: Steam, Chrome, Firefox, VS Code

---

# =============================================================================
# TROUBLESHOOTING
# =============================================================================

### Issue: "NBFC service not responding"

**Solution 1**: Restart service
```bash
sudo systemctl restart nbfc_service
```

**Solution 2**: Check if running
```bash
sudo systemctl status nbfc_service
```

**Solution 3**: Reload configuration
```bash
sudo nbfc config --apply "Acer Nitro AN515-54"
```

---

### Issue: "GPU temperature not available"

**Solution**: Install NVIDIA drivers
```bash
sudo apt install nvidia-driver-535
nvidia-smi  # Verify installation
```

---

### Issue: "Sensors not found"

**Solution**: Setup lm-sensors
```bash
sudo apt install lm-sensors
sudo sensors-detect --auto
sensors  # Test
```

---

### Issue: "Permission denied" on startup

**Solution**: Run with sudo
```bash
sudo python3 main.py
```

Or add application to sudoers:
```bash
sudo visudo
# Add line: yourusername ALL=(ALL) NOPASSWD: /path/to/nitrosense/venv/bin/python3
```

---

### Issue: "Application freezes"

**Causes:**
- Hardware command timeout
- NBFC service unresponsive
- Memory pressure

**Solution:**
```bash
# Check NBFC
systemctl status nbfc_service

# Kill app and restart
killall python3
# Wait 5 seconds
sudo python3 main.py
```

---

# =============================================================================
# PERFORMANCE OPTIMIZATION
# =============================================================================

### For Cooler Operation:
1. Adjust Low threshold down to 45°C
2. Increase speeds by 10-20%
3. Fan will run more but temps stay lower

### For Quieter Operation:
1. Adjust thresholds up to 55°C, 70°C, 85°C
2. Reduce speeds by 10-15%
3. Fan runs less but temps will be higher

### For Gaming:
1. Set Low to 40°C with 50% speed
2. Frost Mode button for instant max cooling
3. Use Game Mode to prevent process kill

---

# =============================================================================
# LOGS & DIAGNOSTICS
# =============================================================================

### Application Logs

Location: `~/.config/nitrosense/logs/nitrosense.log`

```bash
# View logs in real-time
tail -f ~/.config/nitrosense/logs/nitrosense.log

# Search for errors
grep "ERROR" ~/.config/nitrosense/logs/nitrosense.log

# Last 50 lines
tail -50 ~/.config/nitrosense/logs/nitrosense.log
```

### Configuration File

Location: `~/.config/nitrosense/config.json`

```bash
# View current configuration
cat ~/.config/nitrosense/config.json | python3 -m json.tool
```

### Export Diagnostic Report

```bash
# From Config page: click "Export Backup"
# Creates: ~/NitroSense_backup.nsbackup

# Inspect backup
unzip -l ~/NitroSense_backup.nsbackup
```

---

# =============================================================================
# UNINSTALLATION
# =============================================================================

### Remove Application

```bash
# Remove application directory
rm -rf ~/Downloads/"NitroSense Ultimate"

# Remove configuration (optional)
rm -rf ~/.config/nitrosense

# Remove logs (optional)
rm -rf ~/.config/nitrosense/logs
```

### Keep NBFC

NBFC service will continue working independently:
```bash
# NBFC will remain
which nbfc
nbfc status -a
```

---

# =============================================================================
# GETTING HELP
# =============================================================================

### Check Documentation
- README.md - Main documentation
- IMPLEMENTATION_SUMMARY.md - Technical details
- This file - Quick start guide

### Run Diagnostics
1. Open application
2. Go to Labs page
3. Click each test button
4. Review console output

### Export Logs
```bash
# Create diagnostic archive
tar -czf nitrosense_diagnostic.tar.gz ~/.config/nitrosense/

# Share with support
```

---

# =============================================================================
# SECURITY NOTES
# =============================================================================

### Why Root Access?
- EC (Embedded Controller) module requires kernel write
- NBFC service state modification
- CPU frequency/throttle access

### Safe to Use?
Yes! NitroSense:
- ✅ Only executes system commands (no arbitrary code)
- ✅ Falls back gracefully if denied
- ✅ Validates all inputs
- ✅ Logs all operations

### Privacy
- ✅ No network communication
- ✅ No telemetry or tracking
- ✅ Data stored locally only
- ✅ Open source - can audit code

---

## Next Steps

1. ✅ Installation complete
2. 📊 Monitor temperatures in Home page
3. ⚙️ Adjust curve in Config page
4. 🧪 Run diagnostics in Labs page
5. 💾 Export backup of your settings

**Enjoy your optimized Nitro 5 fan control!**

For detailed technical information, see IMPLEMENTATION_SUMMARY.md or README.md.
