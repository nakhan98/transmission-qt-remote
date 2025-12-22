"""Tests for system_tray module."""

from unittest.mock import MagicMock, patch

import pytest

from src.transmission_qt_remote.ui.system_tray import SystemTrayManager


class TestSystemTrayManager:
    """Test cases for SystemTrayManager."""

    @pytest.fixture
    def mock_parent(self):
        """Create a mock parent window."""
        parent = MagicMock()
        parent.windowIcon.return_value.isNull.return_value = False
        parent.windowIcon.return_value = MagicMock()
        parent.isVisible.return_value = False
        parent.style.return_value.standardIcon.return_value = MagicMock()
        return parent

    @pytest.fixture
    def tray_manager(self, mock_parent):
        """Create a SystemTrayManager instance."""
        return SystemTrayManager(mock_parent)

    def test_init(self, tray_manager, mock_parent):
        """Test SystemTrayManager initialization."""
        assert tray_manager.parent == mock_parent
        assert tray_manager.tray_icon is None
        # assert tray_manager.tray_menu is None  # TODO: Fix this assertion

    @patch(
        "src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=True,
    )
    @patch("src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon")
    @patch("src.transmission_qt_remote.ui.system_tray.QMenu")
    def test_setup_tray_success(
        self,
        mock_qmenu,
        mock_tray_icon_class,
        mock_available,
        tray_manager,
        mock_parent,
    ):
        """Test successful system tray setup."""
        mock_tray_icon = MagicMock()
        mock_tray_icon_class.return_value = mock_tray_icon

        mock_menu = MagicMock()
        mock_qmenu.return_value = mock_menu

        tray_manager.setup_tray()

        # Verify tray icon was created and configured
        mock_tray_icon_class.assert_called_once_with(mock_parent)
        mock_tray_icon.setIcon.assert_called_once()
        mock_tray_icon.setToolTip.assert_called_once_with(
            "Transmission QT Remote - Disconnected"
        )
        mock_tray_icon.setContextMenu.assert_called_once_with(mock_menu)
        mock_tray_icon.show.assert_called_once()

        # Verify menu was created
        mock_qmenu.assert_called_once()

        # Verify connections
        assert tray_manager.tray_icon == mock_tray_icon
        assert tray_manager.tray_menu == mock_menu

    @patch(
        "src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=False,
    )
    def test_setup_tray_not_available(self, mock_available, tray_manager):
        """Test system tray setup when tray is not available."""
        tray_manager.setup_tray()

        # Should not create tray icon when not available
        assert tray_manager.tray_icon is None
        assert tray_manager.tray_menu is None

    @patch(
        "src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=True,
    )
    @patch("src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon")
    @patch("src.transmission_qt_remote.ui.system_tray.QMenu")
    def test_setup_tray_fallback_icon(
        self,
        mock_qmenu,
        mock_tray_icon_class,
        mock_available,
        tray_manager,
        mock_parent,
    ):
        """Test system tray setup with fallback icon when window icon is null."""
        mock_parent.windowIcon.return_value.isNull.return_value = True

        mock_tray_icon = MagicMock()
        mock_tray_icon_class.return_value = mock_tray_icon

        mock_menu = MagicMock()
        mock_qmenu.return_value = mock_menu

        tray_manager.setup_tray()

        # Should use fallback icon from style
        mock_parent.style.return_value.standardIcon.assert_called_once()

    def test_update_tooltip(self, tray_manager):
        """Test tooltip updates."""
        mock_tray_icon = MagicMock()
        tray_manager.tray_icon = mock_tray_icon

        tray_manager.update_tooltip("New tooltip")

        mock_tray_icon.setToolTip.assert_called_once_with("New tooltip")

    def test_update_tooltip_no_tray(self, tray_manager):
        """Test tooltip updates when no tray icon exists."""
        tray_manager.tray_icon = None

        # Should not raise an error
        tray_manager.update_tooltip("New tooltip")

    def test_show_hide_tray(self, tray_manager):
        """Test showing and hiding the tray icon."""
        mock_tray_icon = MagicMock()
        tray_manager.tray_icon = mock_tray_icon

        tray_manager.show()
        mock_tray_icon.show.assert_called_once()

        tray_manager.hide()
        mock_tray_icon.hide.assert_called_once()

    @patch(
        "src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=True,
    )
    @patch("src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon")
    @patch("src.transmission_qt_remote.ui.system_tray.QMenu")
    def test_toggle_window_visibility_hide(
        self,
        mock_qmenu,
        mock_tray_icon_class,
        mock_available,
        tray_manager,
        mock_parent,
    ):
        """Test toggling window visibility when window is visible."""
        mock_parent.isVisible.return_value = True

        tray_manager._toggle_window_visibility()

        mock_parent.hide.assert_called_once()
        mock_parent.show.assert_not_called()

    @patch(
        "src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon.isSystemTrayAvailable",
        return_value=True,
    )
    @patch("src.transmission_qt_remote.ui.system_tray.QSystemTrayIcon")
    @patch("src.transmission_qt_remote.ui.system_tray.QMenu")
    def test_toggle_window_visibility_show(
        self,
        mock_qmenu,
        mock_tray_icon_class,
        mock_available,
        tray_manager,
        mock_parent,
    ):
        """Test toggling window visibility when window is hidden."""
        mock_parent.isVisible.return_value = False

        tray_manager._toggle_window_visibility()

        mock_parent.show.assert_called_once()
        mock_parent.raise_.assert_called_once()
        mock_parent.activateWindow.assert_called_once()
        mock_parent.hide.assert_not_called()

    @patch("PySide6.QtWidgets.QApplication")
    def test_quit_application(self, mock_qapp, tray_manager):
        """Test quitting the application."""
        tray_manager._quit_application()

        mock_qapp.quit.assert_called_once()

    def test_on_tray_icon_activated_double_click(self, tray_manager, mock_parent):
        """Test tray icon activation on double click."""
        from PySide6.QtWidgets import QSystemTrayIcon

        mock_parent.isVisible.return_value = False

        tray_manager._on_tray_icon_activated(QSystemTrayIcon.DoubleClick)

        mock_parent.show.assert_called_once()

    def test_on_tray_icon_activated_single_click(self, tray_manager, mock_parent):
        """Test tray icon activation on single click (should not toggle visibility)."""
        from PySide6.QtWidgets import QSystemTrayIcon

        tray_manager._on_tray_icon_activated(QSystemTrayIcon.Trigger)

        mock_parent.show.assert_not_called()
        mock_parent.hide.assert_not_called()
