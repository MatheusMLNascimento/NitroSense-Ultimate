"""
Utility functions for NitroSense Ultimate.
Helper functions for color conversion, validation, etc.
"""

from typing import Tuple
from ..core.constants import TEMP_COLORS


def get_color_for_temperature(temp: float) -> str:
    """
    Get color code for temperature value.
    Uses interpolation between predefined thresholds.
    
    Args:
        temp: Temperature in Celsius
        
    Returns:
        Hex color code
    """
    if temp < 45:
        return TEMP_COLORS["cold"]
    elif temp < 60:
        return TEMP_COLORS["normal"]
    elif temp < 75:
        return TEMP_COLORS["warm"]
    elif temp < 90:
        return TEMP_COLORS["hot"]
    else:
        return TEMP_COLORS["critical"]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color."""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def interpolate_color(start_hex: str, end_hex: str, factor: float) -> str:
    """
    Interpolate between two colors.
    
    Args:
        start_hex: Starting color (hex)
        end_hex: Ending color (hex)
        factor: Interpolation factor (0.0 to 1.0)
        
    Returns:
        Interpolated color (hex)
    """
    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    interpolated = tuple(
        int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * factor)
        for i in range(3)
    )

    return rgb_to_hex(interpolated)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def validate_fan_speed(speed: int) -> int:
    """Validate and clamp fan speed."""
    return clamp(int(speed), 0, 100)


def validate_temperature(temp: float) -> float:
    """Validate temperature value."""
    return clamp(float(temp), -50, 150)


def format_uptime(seconds: int) -> str:
    """Format uptime in human-readable format."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    return f"{days}d {hours}h {minutes}m"


def format_temperature(temp: float, precision: int = 1) -> str:
    """Format temperature with units."""
    return f"{temp:.{precision}f}°C"


def format_percentage(value: float, precision: int = 1) -> str:
    """Format percentage value."""
    return f"{value:.{precision}f}%"


def parse_nbfc_status(output: str) -> dict:
    """Parse NBFC status command output."""
    data = {
        "temperature": None,
        "rpm": None,
        "speed": None,
    }

    for line in output.split("\n"):
        if "Temperature" in line and "°C" in line:
            try:
                temp_str = line.split(":")[-1].replace("°C", "").strip()
                data["temperature"] = float(temp_str)
            except ValueError:
                pass

        if "RPM" in line or "Speed" in line:
            try:
                speed_str = line.split(":")[-1].replace("RPM", "").strip()
                data["rpm"] = int(float(speed_str))
            except ValueError:
                pass

    return data
