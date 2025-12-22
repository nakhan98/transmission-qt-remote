"""System tray management for Transmission QT Remote."""

import logging
from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QMenu, QSystemTrayIcon

if TYPE_CHECKING:
    from .main_window import TransmissionClient

logger = logging.getLogger(__name__)


class SystemTrayManager:
    """Manages the system tray icon and menu for the application.

    This class encapsulates all system tray functionality including
    icon display, menu creation, and window visibility toggling.
    """

    def __init__(self, parent: "TransmissionClient"):
        """Initialize the system tray manager.

        Args:
            parent: The main window instance that owns this tray manager.
        """
        super().__init__()
        self.parent = parent
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_menu: Optional[QMenu] = None

    def setup_tray(self) -> None:
        """Set up the system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform")
            return

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.parent)

        # Set tray icon (use application icon if available)
        if hasattr(self.parent, "windowIcon") and not self.parent.windowIcon().isNull():
            self.tray_icon.setIcon(self.parent.windowIcon())
        else:
            # Fallback to a default icon
            from PySide6.QtWidgets import QStyle

            self.tray_icon.setIcon(
                self.parent.style().standardIcon(QStyle.SP_ComputerIcon)
            )

        # Set initial tooltip
        self.update_tooltip("Transmission QT Remote - Disconnected")

        # Create tray menu
        self._create_tray_menu()

        # Connect double-click to show/hide
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

        # Show the tray icon
        self.tray_icon.show()

        logger.info("System tray icon initialized")

    def update_tooltip(self, tooltip: str) -> None:
        """Update the system tray tooltip.

        Args:
            tooltip: New tooltip text to display.
        """
        if self.tray_icon:
            self.tray_icon.setToolTip(tooltip)

    def show(self) -> None:
        """Show the system tray icon."""
        if self.tray_icon:
            self.tray_icon.show()

    def hide(self) -> None:
        """Hide the system tray icon."""
        if self.tray_icon:
            self.tray_icon.hide()

    def _create_tray_menu(self) -> None:
        """Create the system tray context menu."""
        if not self.tray_icon:
            return

        self.tray_menu = QMenu()

        # Show/Hide action
        show_hide_action = self.tray_menu.addAction("Show/Hide")
        show_hide_action.triggered.connect(self._toggle_window_visibility)

        self.tray_menu.addSeparator()

        # Exit action
        exit_action = self.tray_menu.addAction("Exit")
        exit_action.triggered.connect(self._quit_application)

        # Set the context menu
        self.tray_icon.setContextMenu(self.tray_menu)

    def _toggle_window_visibility(self) -> None:
        """Toggle the main window visibility."""
        if self.parent.isVisible():
            self.parent.hide()
        else:
            self.parent.show()
            self.parent.raise_()
            self.parent.activateWindow()

    def _quit_application(self) -> None:
        """Quit the application."""
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation events.

        Args:
            reason: The activation reason (double-click, etc.).
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_window_visibility()
