"""
Tests for helpers module.
"""

import pytest
from nitrosense.utils.helpers import get_color_for_temperature, hex_to_rgb, rgb_to_hex, interpolate_color


def test_get_color_for_temperature_cold():
    """Test getting color for cold temperature."""
    color = get_color_for_temperature(40)
    assert color == "#0099ff"  # TEMP_COLORS["cold"]


def test_get_color_for_temperature_normal():
    """Test getting color for normal temperature."""
    color = get_color_for_temperature(50)
    assert color == "#34c759"  # TEMP_COLORS["normal"]


def test_get_color_for_temperature_hot():
    """Test getting color for hot temperature."""
    color = get_color_for_temperature(80)
    assert color == "#ff3b30"


def test_get_color_for_temperature_critical():
    """Test getting color for critical temperature."""
    color = get_color_for_temperature(95)
    assert color == "#ff0033"


def test_hex_to_rgb():
    """Test converting hex to RGB."""
    rgb = hex_to_rgb("#ff0000")
    assert rgb == (255, 0, 0)


def test_rgb_to_hex():
    """Test converting RGB to hex."""
    hex_color = rgb_to_hex((255, 0, 0))
    assert hex_color == "#ff0000"


def test_interpolate_color():
    """Test interpolating colors."""
    result = interpolate_color("#000000", "#ffffff", 0.5)
    assert result == "#7f7f7f"  # Gray (127, 127, 127)