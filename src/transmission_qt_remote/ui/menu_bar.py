"""Menu bar management for Transmission QT Remote."""

import logging
from typing import TYPE_CHECKING, Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenuBar

if TYPE_CHECKING:
    from .main_window import TransmissionClient

logger = logging.getLogger(__name__)


class MenuBarManager(QObject):
    """Manages the application menu bar and its actions.

    This class creates and manages all menu bar items including File, Edit,
    View, and Torrent menus, along with their associated actions and keyboard
    shortcuts.

    Signals:
        connection_settings_requested(): Emitted when connection settings is selected
        torrent_details_requested(): Emitted when torrent details is selected
        theme_changed(theme: str): Emitted when theme is changed ("light", "dark", "auto")
        start_requested(): Emitted when start torrent is selected
        force_start_requested(): Emitted when force start torrent is selected
        pause_requested(): Emitted when pause torrent is selected
        verify_requested(): Emitted when verify torrent is selected
    """

    # Signals emitted when menu actions are triggered
    connection_settings_requested = Signal()
    torrent_details_requested = Signal()
    theme_changed = Signal(str)  # theme: "light", "dark", "auto"
    start_requested = Signal()
    force_start_requested = Signal()
    pause_requested = Signal()
    verify_requested = Signal()

    def __init__(self, parent: "TransmissionClient"):
        """Initialize the menu bar manager.

        Args:
            parent: The main window instance that owns this menu bar.
        """
        super().__init__()
        self.parent = parent
        self.menubar: Optional[QMenuBar] = None

        # Menu action references for state management
        self.torrent_details_action: QAction = QAction(self.parent)
        self.torrent_start_action: QAction = QAction(self.parent)
        self.torrent_force_start_action: QAction = QAction(self.parent)
        self.torrent_pause_action: QAction = QAction(self.parent)
        self.torrent_verify_action: QAction = QAction(self.parent)
        self.torrent_delete_action: QAction = QAction(self.parent)
        self.torrent_delete_data_action: QAction = QAction(self.parent)

        # Theme actions for menu checkmarks
        self.theme_actions: Optional[Dict[str, QAction]] = None
        self.current_theme = "auto"

    def setup_menu_bar(self) -> None:
        """Set up the complete menu bar with all menus and actions."""
        self.menubar = self.parent.menuBar()

        self._create_edit_menu()
        self._create_view_menu()
        self._create_torrent_menu()

        logger.info("Menu bar initialized")

    def update_torrent_actions(self, torrent_status: Optional[int]) -> None:
        """Update torrent menu action enabled states based on torrent status.

        Args:
            torrent_status: Current status of the selected torrent (Transmission status code)
        """
        if not all(
            [
                self.torrent_start_action,
                self.torrent_force_start_action,
                self.torrent_pause_action,
                self.torrent_verify_action,
            ]
        ):
            return

        if torrent_status is None:
            # No torrent selected - disable all actions
            self._disable_torrent_actions()
            return

        # Enable actions based on torrent status
        # Stopped (0), Download pending (4), Seed pending (5) -> can start
        can_start = torrent_status in [0, 4, 5]
        self.torrent_start_action.setEnabled(can_start)
        self.torrent_force_start_action.setEnabled(can_start)

        # Active torrents -> can pause
        can_pause = torrent_status not in [0, 4, 5]  # Not stopped/pending
        self.torrent_pause_action.setEnabled(can_pause)

        # Verify is always available for selected torrents
        self.torrent_verify_action.setEnabled(True)

    def set_torrent_details_enabled(self, enabled: bool) -> None:
        """Enable or disable the torrent details menu action.

        Args:
            enabled: Whether the torrent details action should be enabled
        """
        if self.torrent_details_action:
            self.torrent_details_action.setEnabled(enabled)

    def set_current_theme(self, theme: str) -> None:
        """Set the current theme and update menu checkmarks.

        Args:
            theme: Theme name ("light", "dark", "auto")
        """
        self.current_theme = theme

        # Update menu checkmarks
        if self.theme_actions:
            for theme_name, action in self.theme_actions.items():
                action.setChecked(theme_name == theme)

    def _create_edit_menu(self) -> None:
        """Create the Edit menu with connection settings."""
        if not self.menubar:
            return

        edit_menu = self.menubar.addMenu("&Edit")

        # Connection Settings action
        connection_settings_action = QAction("&Connection Settings...", self.parent)
        connection_settings_action.setShortcut("Ctrl+,")
        connection_settings_action.triggered.connect(self.connection_settings_requested)
        edit_menu.addAction(connection_settings_action)

    def _create_view_menu(self) -> None:
        """Create the View menu with torrent details and theme options."""
        if not self.menubar:
            return

        view_menu = self.menubar.addMenu("&View")

        # Torrent Details action
        self.torrent_details_action = QAction("&Torrent Details", self.parent)
        self.torrent_details_action.setShortcut("Ctrl+D")
        self.torrent_details_action.triggered.connect(self.torrent_details_requested)
        self.torrent_details_action.setEnabled(False)  # Initially disabled
        view_menu.addAction(self.torrent_details_action)

        view_menu.addSeparator()

        # Theme submenu
        self._create_theme_submenu(view_menu)

    def _create_theme_submenu(self, view_menu: QMenuBar) -> None:
        """Create the theme submenu with light/dark/auto options."""
        theme_menu = view_menu.addMenu("&Theme")
        theme_group = QActionGroup(self.parent)
        theme_group.setExclusive(True)

        # Light theme
        light_action = QAction("&Light", self.parent)
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self._on_theme_changed("light"))
        theme_menu.addAction(light_action)
        theme_group.addAction(light_action)

        # Dark theme
        dark_action = QAction("&Dark", self.parent)
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self._on_theme_changed("dark"))
        theme_menu.addAction(dark_action)
        theme_group.addAction(dark_action)

        # Auto theme
        auto_action = QAction("&Auto", self.parent)
        auto_action.setCheckable(True)
        auto_action.setChecked(True)  # Default to auto
        auto_action.triggered.connect(lambda: self._on_theme_changed("auto"))
        theme_menu.addAction(auto_action)
        theme_group.addAction(auto_action)

        # Store theme actions for later use
        self.theme_actions = {
            "light": light_action,
            "dark": dark_action,
            "auto": auto_action,
        }

    def _create_torrent_menu(self) -> None:
        """Create the Torrent menu with all torrent actions."""
        if not self.menubar:
            return

        torrent_menu = self.menubar.addMenu("&Torrent")

        # Start action
        self.torrent_start_action = QAction("&Start", self.parent)
        self.torrent_start_action.setShortcut("Ctrl+S")
        self.torrent_start_action.triggered.connect(self.start_requested)
        self.torrent_start_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(self.torrent_start_action)

        # Force Start action
        self.torrent_force_start_action = QAction("Force &Start", self.parent)
        self.torrent_force_start_action.setShortcut("Ctrl+Shift+S")
        self.torrent_force_start_action.triggered.connect(self.force_start_requested)
        self.torrent_force_start_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(self.torrent_force_start_action)

        # Pause action
        self.torrent_pause_action = QAction("&Pause", self.parent)
        self.torrent_pause_action.setShortcut("Ctrl+P")
        self.torrent_pause_action.triggered.connect(self.pause_requested)
        self.torrent_pause_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(self.torrent_pause_action)

        torrent_menu.addSeparator()

        # Verify action
        self.torrent_verify_action = QAction("&Verify", self.parent)
        self.torrent_verify_action.setShortcut("Ctrl+R")
        self.torrent_verify_action.triggered.connect(self.verify_requested)
        self.torrent_verify_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(self.torrent_verify_action)

        torrent_menu.addSeparator()

        # Delete actions (disabled for read-only client)
        self.torrent_delete_action = QAction("&Delete", self.parent)
        self.torrent_delete_action.setEnabled(False)  # Read-only client
        self.torrent_delete_action.setToolTip(
            "Delete not available in read-only client"
        )
        torrent_menu.addAction(self.torrent_delete_action)

        self.torrent_delete_data_action = QAction("Delete with &Data", self.parent)
        self.torrent_delete_data_action.setEnabled(False)  # Read-only client
        self.torrent_delete_data_action.setToolTip(
            "Delete with data not available in read-only client"
        )
        torrent_menu.addAction(self.torrent_delete_data_action)

    def _disable_torrent_actions(self) -> None:
        """Disable all torrent menu actions."""
        if self.torrent_start_action:
            self.torrent_start_action.setEnabled(False)
        if self.torrent_force_start_action:
            self.torrent_force_start_action.setEnabled(False)
        if self.torrent_pause_action:
            self.torrent_pause_action.setEnabled(False)
        if self.torrent_verify_action:
            self.torrent_verify_action.setEnabled(False)

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change from menu.

        Args:
            theme: The selected theme ("light", "dark", "auto")
        """
        self.set_current_theme(theme)
        self.theme_changed.emit(theme)
