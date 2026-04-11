# 🎯 Advanced Features

Deep dive into NitroSense capabilities.

## Predictive Thermal Algorithm

### dT/dt Calculation

NitroSense monitors **rate of temperature change** to anticipate fan needs.

```
If temperature rising >3°C per 1.5 seconds:
  → Boost fan speed by +20% immediately
  → Prevents thermal spike during load transition
```

**Example**: Starting a game
```
Frame 1: CPU at 60°C
Frame 2: CPU at 62°C (+2°C)
Frame 3: CPU at 65°C (+3°C) ← Boost triggered!
Frame 4: CPU at 67°C, but fan already at +20% boost
```

---

## Emergency Protocol (95°C)

When CPU exceeds **95°C**:

1. **Automatic process termination** (non-essential apps):
   - Google Chrome
   - Firefox
   - VS Code
   - Steam
   - VLC

2. **Fan forced to 100%** (max cooling)

3. **Critical alert displayed** with thermal summary

4. **Event logged** for diagnostics

⚠️ **This is a safety feature** - use Frost Mode for manual control.

---

## Hardware Watchdog

NitroSense monitors EC bus health every 10 seconds.

### If EC bus hangs:
1. System detects (heartbeat timeout)
2. AUTO-RECOVERY:
   - Kill NBFC
   - Reload EC module
   - Restart NBFC
   - Notify user

**You see**: Yellow warning on Status page, but app keeps running!

---

## Performance Optimization

### Dirty Bit Cache
- Prevents redundant UI repaints
- Temperature <0.1°C change = no screen update
- Reduces CPU usage from ~3% to <0.5%

### Lazy Loading
- Matplotlib loaded only when Home page opened
- Startup time: 7s → 2s

### Thread Isolation
- Monitoring runs on separate thread (IdlePriority)
- Gaming FPS not affected
- UI always responsive

---

## Statistics & Monitoring

### Available Metrics (Home Page)

- **CPU Temperature** (via NBFC/EC)
- **GPU Temperature** (via nvidia-smi)
- **Fan RPM** (current speed)
- **Thermal Trend** (rising/stable/falling)
- **System Uptime** (since boot)

### History Graph
- Last 30 temperature readings
- Click to zoom
- Export as CSV

---

## Error Handling

NitroSense uses **error codes** instead of crashes.

### Error Code System

- `0`: SUCCESS (normal operation)
- `101-107`: Hardware errors (EC, NBFC, GPU)
- `201-210`: Configuration errors
- `301-310`: Threading errors

**You benefit**: App never crashes, always recovers gracefully.

Check **Labs** → **View Error Log** for recent codes.

---

## Customization

### Keyboard Shortcuts (Future)
- `Ctrl+F`: Frost Mode toggle
- `Ctrl+E`: Export backup
- `Ctrl+,`: Open settings

### Custom Profiles
- Save multiple thermal curves
- Switch between Gaming/Quiet/Performance

---

**Want to explore more?** Check the source code at `nitrosense/automation/ai_engine.py` for thermal algorithms!
