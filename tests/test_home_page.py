from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QLabel

from nitrosense.ui.pages.home_page import HomePage


class DummyHardware:
    def run_nbfc(self, command):
        return True, "ok"


class DummyMonitoring:
    def get_system_metrics(self):
        return {"cpu_temp": 42.0, "gpu_temp": 35.0, "fan_rpm": 1200}

    def get_temperature_delta(self):
        return 0.3

    def get_temperature_trend(self):
        return [40.0, 41.5, 42.0]


class DummyConfig(dict):
    def __init__(self):
        super().__init__(
            advanced_config={},
            theme="dark",
            thermal={"temp_thresholds": {"Low": 45, "Mid": 55, "High": 70}, "speed_thresholds": {"Low": 30, "Mid": 60, "High": 90}, "idle_speed": 20, "emergency_temp": 95, "emergency_speed": 100, "predictive_temp_delta": 3.0, "watchdog_fan_threshold": 60},
        )

    def get(self, key, default=None):
        return self[key] if key in self else default

    def get_thermal_config(self):
        return self["thermal"]


def test_homepage_widget_initialization(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())

    assert homepage.cpu_card.value_label.text() == "-- °C"
    assert homepage.fan_speed_slider.maximum() == 100
    assert homepage.pause_button.text() == "Pause Graph"
    assert homepage.theme_toggle_button.text() == "Dark Mode"

    homepage.cleanup()


def test_homepage_icon_fallback(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    label = QLabel()
    homepage._apply_icon_to_label(label, "missing_icon", "FALLBACK", QSize(32, 32))

    assert label.text() == "FALLBACK"
    homepage.cleanup()


def test_homepage_theme_toggle(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    initial_dark_mode = homepage.dark_mode

    homepage._toggle_theme()
    assert homepage.dark_mode != initial_dark_mode
    assert homepage.theme_toggle_button.text() in {"Light Mode", "Dark Mode"}
    homepage.cleanup()


def test_homepage_pause_button(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    homepage._toggle_pause()
    assert homepage.graph_paused is True
    assert homepage.pause_button.text() == "Resume Graph"
    homepage._toggle_pause()
    assert homepage.graph_paused is False
    assert homepage.pause_button.text() == "Pause Graph"
    homepage.cleanup()


def test_homepage_frost_mode(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    homepage._frost_mode()
    assert hasattr(homepage, 'fan_controller')
    homepage.cleanup()


def test_homepage_update_display_with_data(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    # Show the widget so update_display will actually execute
    homepage.show()
    homepage._update_display()
    # After _update_display, cpu_card should have been updated with the temperature from monitoring
    assert homepage.cpu_card.value_label.text() != "-- °C" or homepage.monitoring.get_system_metrics()["cpu_temp"] is None
    homepage.cleanup()


def test_homepage_update_color(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    homepage._update_color(40.0)
    # Verify the method executes without error
    assert homepage.cpu_card is not None
    homepage.cleanup()


def test_homepage_cleanup(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    homepage.cleanup()
    assert not homepage.update_timer.isActive()


def test_homepage_initialization_with_missing_services(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig())
    assert homepage.monitoring is not None
    homepage.cleanup()


def test_homepage_graph_update(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("nitrosense.ui.pages.home_page.QTimer.start", lambda self, *_: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", lambda name, size: None)
    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon", lambda name: None)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    homepage._update_graph()
    assert len(homepage.ax.lines) == 1
    homepage.cleanup()


def test_homepage_apply_icon_with_pixmap(monkeypatch):
    from PyQt6.QtGui import QPixmap
    app = QApplication.instance() or QApplication([])

    def mock_load_pixmap(name, size):
        return QPixmap(32, 32)  # Valid pixmap

    monkeypatch.setattr("nitrosense.ui.pages.home_page.load_icon_pixmap", mock_load_pixmap)

    homepage = HomePage(DummyHardware(), DummyConfig(), DummyMonitoring())
    label = QLabel()
    homepage._apply_icon_to_label(label, "test", "fallback", QSize(32, 32))
    # Should set pixmap, not text
    assert label.text() == ""
    homepage.cleanup()
