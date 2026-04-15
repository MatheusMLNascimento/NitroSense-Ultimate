"""
Emoji Theme for NitroSense Ultimate UI.
Provides consistent emoji usage across all pages without external dependencies.
"""

# Navigation emojis
NAV_EMOJIS = {
    "home": "🏠",
    "status": "📊",
    "config": "⚙️",
    "labs": "🧪",
    "docs": "📖",
}

# Status indicator emojis
STATUS_EMOJIS = {
    "ok": "🟢",
    "success": "✅",
    "warning": "🟡",
    "critical": "🔴",
    "error": "❌",
}

# Hardware emojis
HARDWARE_EMOJIS = {
    "cpu": "🖥️",
    "gpu": "📐",
    "fan": "🌀",
    "temp": "🌡️",
    "memory": "💾",
    "disk": "💿",
    "power": "⚡",
}

# Feature emojis
FEATURE_EMOJIS = {
    "frost_mode": "❄️",
    "performance": "🚀",
    "quiet": "🔇",
    "gaming": "🎮",
    "thermal": "🔥",
    "cooling": "❄️",
    "ai": "🤖",
    "watchdog": "👁️",
    "protection": "🛡️",
}

# Action emojis
ACTION_EMOJIS = {
    "check": "✅",
    "alert": "⚠️",
    "info": "ℹ️",
    "start": "▶️",
    "stop": "⏹️",
    "restart": "🔄",
    "settings": "⚙️",
    "save": "💾",
    "export": "📤",
    "import": "📥",
    "delete": "🗑️",
    "refresh": "🔄",
}

# Temperature-based emojis
TEMP_EMOJIS = {
    "very_cold": "❄️",      # <40°C
    "cold": "🟦",           # 40-55°C
    "normal": "🟩",         # 55-70°C
    "warm": "🟧",           # 70-80°C
    "hot": "🟥",            # 80-90°C
    "critical": "🔥",       # >90°C
}


def get_emoji(category: str, name: str) -> str:
    """Get emoji by category and name."""
    emojis = {
        "nav": NAV_EMOJIS,
        "status": STATUS_EMOJIS,
        "hardware": HARDWARE_EMOJIS,
        "feature": FEATURE_EMOJIS,
        "action": ACTION_EMOJIS,
        "temp": TEMP_EMOJIS,
    }
    
    return emojis.get(category, {}).get(name, "❓")


def get_temp_emoji(temp: float) -> str:
    """Get emoji based on temperature value."""
    if temp < 40:
        return TEMP_EMOJIS["very_cold"]
    elif temp < 55:
        return TEMP_EMOJIS["cold"]
    elif temp < 70:
        return TEMP_EMOJIS["normal"]
    elif temp < 80:
        return TEMP_EMOJIS["warm"]
    elif temp < 90:
        return TEMP_EMOJIS["hot"]
    else:
        return TEMP_EMOJIS["critical"]


def get_status_emoji(error_code: int) -> str:
    """Get emoji based on error code status."""
    if error_code == 0:  # SUCCESS
        return STATUS_EMOJIS["success"]
    elif error_code < 200:  # Hardware errors (warnings)
        return STATUS_EMOJIS["warning"]
    else:  # Critical errors
        return STATUS_EMOJIS["error"]
