# 🚀 Quick Start Guide

Get NitroSense running in 5 minutes.

## Installation

### 1. System Dependencies
```bash
sudo apt-get install -y python3.12 python3.12-venv nbfc nvidia-driver-535 lm-sensors
```

### 2. Create Virtual Environment
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the Application
```bash
sudo python3 main.py
```

## First Steps

1. **Home Page**: Monitor real-time CPU/GPU temperature and fan RPM
2. **Status Page**: Check system health indicators (6 LED indicators)
3. **Config Page**: Adjust thermal curve thresholds and fan speeds
4. **Labs Page**: Run diagnostics if something feels wrong

## Default Thermal Curve

| Level | Temperature | Fan Speed |
|-------|-------------|-----------|
| Low   | 50°C        | 30%       |
| Mid   | 65°C        | 60%       |
| High  | 80°C        | 100%      |

Customize these in **Config Page** → Thermal Thresholds.

## Emergency Features

- **Frost Mode**: Keeps laptop cool for 2 minutes at 100% fan (Home page button)
- **Emergency Protocol**: Auto-triggers at 95°C (kills processes, sets fan to 100%)

## Troubleshooting

**Issue**: App crashes on startup
- Solution: Run with `sudo`

**Issue**: Temperature not showing
- Solution: Install NVIDIA drivers: `sudo apt install nvidia-driver-535`

**Issue**: Fan not responding
- Solution: Go to Labs → "Check Dependencies" to diagnose

---

Need more help? See the **Configuration Guide** or **Troubleshooting** section.
