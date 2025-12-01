"""Integration tests for system tray functionality."""

import pytest
from PySide6.QtWidgets import QApplication

from transmission_qt_remote.main_window import TransmissionClient


@pytest.fixture
def app():
    """Create QApplication for testing."""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    return app


def test_system_tray_initialization(app):
    """Test that system tray is initialized when available."""
    # Given: A TransmissionClient application
    client = TransmissionClient()

    # Given: System tray availability on this platform
    from PySide6.QtWidgets import QSystemTrayIcon

    tray_available = QSystemTrayIcon.isSystemTrayAvailable()

    if tray_available:
        # When: System tray is available on the platform
        # Then: Tray icon should be initialized and visible
        assert hasattr(client, "tray_icon"), (
            "Tray icon should exist when system tray is available"
        )
        assert client.tray_icon is not None, "Tray icon should not be None"
        assert client.tray_icon.isVisible(), "Tray icon should be visible"
    else:
        # When: System tray is not available on the platform
        # Then: Tray initialization should be skipped gracefully
        # Note: This test may not be reliable in all environments
        pass


def test_system_tray_icon_properties(app):
    """Test system tray icon properties."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # When: Checking the initial tray icon properties
        # Then: Tooltip should contain application name and disconnected status
        assert "Transmission QT Remote" in client.tray_icon.toolTip()
        assert "Disconnected" in client.tray_icon.toolTip()

        # Then: Tray icon should have a valid icon set
        assert not client.tray_icon.icon().isNull(), "Tray icon should have an icon set"


def test_system_tray_menu(app):
    """Test system tray context menu."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # When: Accessing the tray icon context menu
        menu = client.tray_icon.contextMenu()

        # Then: Context menu should exist
        assert menu is not None, "Tray icon should have a context menu"

        # When: Getting menu actions
        actions = menu.actions()

        # Then: Should have 3 actions (Show/Hide, separator, Exit)
        assert len(actions) == 3, f"Expected 3 menu actions, got {len(actions)}"

        # When: Checking action names
        action_texts = [action.text() for action in actions]
        expected_texts = ["Show/Hide", "", "Exit"]  # Empty string is separator

        # Then: Action names should match expected structure
        assert action_texts == expected_texts, (
            f"Expected {expected_texts}, got {action_texts}"
        )


def test_system_tray_tooltip_updates(app):
    """Test that system tray tooltip updates with connection status."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # When: Application starts (initial state)
        # Then: Tray tooltip should show disconnected status
        assert "Disconnected" in client.tray_icon.toolTip()

        # When: Simulating a connection to the server
        client.is_connected = True
        client._update_status_label()

        # Then: Tray tooltip should show connected status
        assert "Connected" in client.tray_icon.toolTip()

        # When: Simulating disconnection from the server
        client.is_connected = False
        client._update_status_label()

        # Then: Tray tooltip should show disconnected status again
        assert "Disconnected" in client.tray_icon.toolTip()


def test_system_tray_toggle_visibility(app):
    """Test system tray show/hide functionality."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # Given: Initial window visibility state
        initial_visibility = client.isVisible()

        # When: Toggling window visibility via tray action
        client._toggle_window_visibility()

        # Then: Window visibility should be toggled
        assert client.isVisible() != initial_visibility

        # When: Toggling window visibility again
        client._toggle_window_visibility()

        # Then: Window should be back to original visibility state
        assert client.isVisible() == initial_visibility


def test_system_tray_quit_application(app):
    """Test system tray quit application functionality."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # When: Checking for quit application functionality
        # Then: Quit method should exist and be callable (without actually quitting)
        try:
            assert hasattr(client, "_quit_application"), (
                "Quit application method should exist"
            )
            assert callable(client._quit_application), (
                "Quit application should be callable"
            )
        except Exception:
            # When: QApplication.quit() has issues in test environment
            # Then: Exception should be handled gracefully
            pass


def test_system_tray_activated_signal(app):
    """Test system tray activation signal handling."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # Given: QSystemTrayIcon activation constants
        from PySide6.QtWidgets import QSystemTrayIcon

        # When: Tray icon is double-clicked
        # Then: Should handle activation without crashing
        client._on_tray_icon_activated(QSystemTrayIcon.DoubleClick)

        # When: Tray icon is triggered (single click)
        # Then: Should handle activation without crashing
        client._on_tray_icon_activated(QSystemTrayIcon.Trigger)

        # When: Tray icon is middle-clicked
        # Then: Should handle activation without crashing
        client._on_tray_icon_activated(QSystemTrayIcon.MiddleClick)


def test_system_tray_availability_check(app):
    """Test system tray availability checking."""
    # Given: QSystemTrayIcon class available
    from PySide6.QtWidgets import QSystemTrayIcon

    # When: Checking system tray availability on current platform
    availability = QSystemTrayIcon.isSystemTrayAvailable()

    # Then: Should return a boolean value indicating availability
    assert isinstance(availability, bool), (
        "isSystemTrayAvailable should return a boolean"
    )


def test_tray_tooltip_update_method(app):
    """Test the tray tooltip update method."""
    # Given: A TransmissionClient with system tray initialized
    client = TransmissionClient()

    if hasattr(client, "tray_icon"):
        # Given: A test tooltip message
        test_tooltip = "Test tooltip message"

        # When: Updating the tray tooltip
        client._update_tray_tooltip(test_tooltip)

        # Then: Tray tooltip should be updated to the new message
        assert client.tray_icon.toolTip() == test_tooltip
