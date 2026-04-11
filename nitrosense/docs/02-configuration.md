# ⚙️ Configuration Guide

Learn how to customize NitroSense for your needs.

## Thermal Configuration

### Understanding the Curve

NitroSense uses a **3-point thermal curve** to control fan speed:

```
Temperature Thresholds → Fan Speed Mapping
   50°C (Low)       →  30%
   65°C (Mid)       →  60%
   80°C (High)      → 100%
```

Between thresholds, fan speed is **interpolated** (smooth transition).

### Gaming Profile

For maximum cooling during gaming:
```
Low:  40°C  →  50%
Mid:  55°C  →  75%
High: 70°C  → 100%
```

### Quiet Profile

For office work, prioritize silence:
```
Low:  60°C  →  20%
Mid:  75°C  →  50%
High: 90°C  → 100%
```

## Advanced Settings

### Frost Mode Duration
- Default: 120 seconds
- Set in **Config Page** → Frost Mode Duration
- While active: Fan runs at 100% regardless of temperature

### AI Sensitivity
- Controls how aggressively the thermal algorithm reacts
- Range: 0.5x to 2.0x
- Higher = faster fan speed boost on temperature spikes

### Log Level
- **INFO** (default): Normal operation logs
- **DEBUG**: Verbose logging for troubleshooting
- Logs saved to: `~/.config/nitrosense/nitrosense.log`

## Snapshot/Backup

### Export Settings
1. Go to **Config Page**
2. Click **"Export Backup"**
3. File saved as `NitroSense_backup.nsbackup`

### Restore Settings
1. Click **"Import Backup"**
2. Select your `.nsbackup` file
3. Settings restored automatically

---

**Tip**: Save a backup after finding your ideal thermal curve!
