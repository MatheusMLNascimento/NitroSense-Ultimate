# 🔧 Troubleshooting

Common issues and solutions.

## Startup Issues

### "Permission denied" error

**Cause**: App requires root to access EC (Embedded Controller)

**Solution**:
```bash
sudo python3 main.py
```

Or add to sudoers (optional):
```bash
sudo visudo
# Add this line:
yourusername ALL=(ALL) NOPASSWD: /path/to/python3
```

---

### "NBFC service not responding"

**Cause**: NBFC daemon crashed or not installed

**Solution 1**: Restart NBFC
```bash
sudo systemctl restart nbfc_service
sudo systemctl status nbfc_service
```

**Solution 2**: Verify installation
```bash
which nbfc
nbfc status -a
```

**Solution 3**: Reinstall NBFC
```bash
sudo apt remove nbfc
sudo apt install nbfc
```

---

## Runtime Issues

### Temperature not showing

**Cause**: Sensor not detected or NVIDIA driver missing

**Symptoms**: "N/A" on Home page

**Solution 1**: Install NVIDIA drivers
```bash
sudo apt install nvidia-driver-535
nvidia-smi  # Test
```

**Solution 2**: Install/configure lm-sensors
```bash
sudo apt install lm-sensors
sudo sensors-detect --auto
sensors  # Test
```

---

### Fan not responding to temperature changes

**Cause**: EC module not loaded or NBFC command failed

**Solution**: Go to **Labs Page** → Click **"Check Dependencies"**

This will diagnose:
- ✅ NBFC service status
- ✅ EC driver loaded
- ✅ NVIDIA GPU detected
- ✅ lm-sensors available

---

### Application freezes

**Cause**: Hardware command timeout or memory leak

**Solution**:
```bash
# Kill app
killall python3

# Wait 5 seconds
sleep 5

# Restart
sudo python3 main.py
```

If freezes persist, check logs:
```bash
tail -50 ~/.config/nitrosense/nitrosense.log
```

---

## Memory/CPU Issues

### High memory usage (>500MB)

**Solution**: Restart the app
- Memory is cleaned every 100 UI cycles (~3 minutes)
- If not resolving, check logs for leak indicators

### High CPU usage (>5%)

**Cause**: Monitoring loop working too hard

**Solution**: Reduce thermal curve complexity
- Go to **Config** and simplify your curve
- Or increase monitoring interval in **Labs** → Settings

---

## Diagnostics

### Export Diagnostic Report

1. Go to **Labs Page**
2. Click **"Generate Report"**
3. Saves to `~/.config/nitrosense/diagnostics.txt`

Share this file if reporting issues!

---

## Still having problems?

Check the **System Health** on Status page for LED indicators:
- 🟢 Green = OK
- 🔴 Red = Problem
- 🟠 Orange = Warning

Click each indicator for details.
