import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests
from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .config import (
    APP_NAME,
    CONNECTION_TIMEOUT_SEC,
    DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS,
    DEFAULT_REFRESH_INTERVAL_MS,
    TRANSMISSION_PASS,
    TRANSMISSION_URL,
    TRANSMISSION_USER,
)
from .credential_manager import CredentialManager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TableColumn:
    display_name: str
    field_name: str


class TorrentStatus(Enum):
    STOPPED = 0
    CHECK_PENDING = 1
    CHECKING = 2
    DOWNLOADING = 3
    DOWNLOAD_PENDING = 4
    SEED_PENDING = 5
    SEEDING = 6

    def display_text(self) -> str:
        return {
            0: "Stopped",
            1: "Check pending",
            2: "Checking",
            3: "Downloading",
            4: "Download pending",
            5: "Seed pending",
            6: "Seeding",
        }.get(self.value, "Unknown")


class TrackerButton(QPushButton):
    """Stub for test_integration.py."""

    def __init__(self, hostname: str):
        # Truncate long hostnames for display
        if len(hostname) <= 12:
            display_name = hostname
        else:
            parts = hostname.split(".")
            display_name = ".".join(parts[:2]) + "...."
        super().__init__(display_name)
        self.hostname = hostname
        self.setCheckable(True)
        self.setToolTip(hostname)


class TransmissionClient(QMainWindow):
    """A class representing a Transmission client GUI application."""

    def __init__(self) -> None:
        """Initializes the TransmissionClient with default settings."""
        logger.info("MainWindow initialized")
        super().__init__()

        self.refresh_interval_ms = DEFAULT_REFRESH_INTERVAL_MS
        self.minimized_refresh_interval_ms = DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS

        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 900, 500)

        self._init_menu_bar()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(16, 8, 16, 16)
        self.central_widget.setLayout(self.layout)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.filter_summary_label = QLabel("Showing 0 torrents • Tracker: All")
        self.filter_summary_label.setObjectName("SummaryLabel")
        self.status_bar.addWidget(self.filter_summary_label)

        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("StatusLabel")
        self.status_bar.addPermanentWidget(self.status_label)

        # System tray
        self._setup_system_tray()

        # Torrent toolbar
        self.torrent_toolbar = QToolBar("Torrent Actions")
        self.torrent_toolbar.setMovable(False)
        self.torrent_toolbar.setIconSize(QSize(24, 24))

        # Open File button (far left, disabled for read-only client)
        self.toolbar_open_action = QAction("Open", self)
        self.toolbar_open_action.setIcon(QIcon.fromTheme("document-open"))
        self.toolbar_open_action.setToolTip(
            "Open torrent file (not available in read-only client)"
        )
        self.toolbar_open_action.setEnabled(False)  # Read-only client
        self.torrent_toolbar.addAction(self.toolbar_open_action)

        # Add separator after Open button
        self.torrent_toolbar.addSeparator()

        # Start button
        self.toolbar_start_action = QAction("Start", self)
        self.toolbar_start_action.setIcon(QIcon.fromTheme("media-playback-start"))
        self.toolbar_start_action.setToolTip("Start torrent (Ctrl+S)")
        self.toolbar_start_action.triggered.connect(self._start_selected_torrent)
        self.toolbar_start_action.setEnabled(False)  # Initially disabled
        self.torrent_toolbar.addAction(self.toolbar_start_action)

        # Force Start button
        self.toolbar_force_start_action = QAction("Force Start", self)
        self.toolbar_force_start_action.setIcon(QIcon.fromTheme("media-seek-forward"))
        self.toolbar_force_start_action.setToolTip("Force start torrent (Ctrl+Shift+S)")
        self.toolbar_force_start_action.triggered.connect(
            self._force_start_selected_torrent
        )
        self.toolbar_force_start_action.setEnabled(False)  # Initially disabled
        self.torrent_toolbar.addAction(self.toolbar_force_start_action)

        # Pause button
        self.toolbar_pause_action = QAction("Pause", self)
        self.toolbar_pause_action.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.toolbar_pause_action.setToolTip("Pause torrent (Ctrl+P)")
        self.toolbar_pause_action.triggered.connect(self._pause_selected_torrent)
        self.toolbar_pause_action.setEnabled(False)  # Initially disabled
        self.torrent_toolbar.addAction(self.toolbar_pause_action)

        # Add separator before Delete button
        self.torrent_toolbar.addSeparator()

        # Delete button (far right, disabled for read-only client)
        self.toolbar_delete_action = QAction("Delete", self)
        self.toolbar_delete_action.setIcon(QIcon.fromTheme("edit-delete"))
        self.toolbar_delete_action.setToolTip(
            "Delete torrent (not available in read-only client)"
        )
        self.toolbar_delete_action.setEnabled(False)  # Read-only client
        self.torrent_toolbar.addAction(self.toolbar_delete_action)

        # Create horizontal layout for toolbar and search controls
        toolbar_controls_layout = QHBoxLayout()
        toolbar_controls_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_controls_layout.setSpacing(0)

        # Add toolbar to horizontal layout
        toolbar_controls_layout.addWidget(self.torrent_toolbar)

        # Search, tracker, and action controls bar
        controls_frame = QFrame()
        controls_frame.setObjectName("ControlFrame")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(16, 10, 16, 10)
        controls_layout.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search torrents…")
        self.search_box.textChanged.connect(self.filter_table)
        controls_layout.addWidget(self.search_box, stretch=3)

        self.clear_filters_btn = QToolButton()
        self.clear_filters_btn.setToolTip("Clear Filters")
        self.clear_filters_btn.setIcon(
            self.style().standardIcon(QStyle.SP_DialogResetButton)
        )
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        controls_layout.addWidget(self.clear_filters_btn)

        tracker_label = QLabel("Tracker:")
        tracker_label.setObjectName("SmallLabel")
        controls_layout.addWidget(tracker_label)

        self.tracker_selector = QComboBox()
        self.tracker_selector.setEditable(False)
        self.tracker_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.tracker_selector.setMinimumWidth(220)
        self.tracker_selector.addItem("All")
        self.tracker_selector.setToolTip("Filter torrents by tracker hostname")
        self.tracker_selector.currentTextChanged.connect(self.select_tracker)
        controls_layout.addWidget(self.tracker_selector, stretch=1)

        self.connect_btn = QToolButton()
        self.connect_btn.setToolTip("Connect to server")
        self.connect_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        self.connect_btn.clicked.connect(self._toggle_connection)
        controls_layout.addWidget(self.connect_btn)

        self.connection_settings_btn = QToolButton()
        self.connection_settings_btn.setToolTip("Connection Settings")
        self.connection_settings_btn.setIcon(
            self.style().standardIcon(QStyle.SP_ComputerIcon)
        )
        self.connection_settings_btn.clicked.connect(self.open_connection_settings)
        controls_layout.addWidget(self.connection_settings_btn)

        # Add controls frame to horizontal layout
        toolbar_controls_layout.addWidget(controls_frame, stretch=1)

        # Add the horizontal layout to main layout
        self.layout.addLayout(toolbar_controls_layout)

        self.tracker_options: List[str] = ["All"]
        self.tracker_buttons: Dict[str, TrackerButton] = {}
        self.active_tracker: Optional[str] = None
        self.active_trackers: List[str] = []

        # Divider

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(divider)

        # Torrent table
        self.table = QTableWidget()
        self.table.doubleClicked.connect(self.on_torrent_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_torrent_context_menu)
        self.layout.addWidget(self.table)

        self.columns: List[TableColumn] = [
            TableColumn("Torrent Name", "name"),
            TableColumn("State", "status"),
            TableColumn("Size (MB)", "totalSize"),
            TableColumn("Date Added", "addedDate"),
            TableColumn("Seeders", "seeders"),
            TableColumn("Leechers", "leechers"),
            TableColumn("Progress", "percentDone"),
            TableColumn("Status", "status"),
            TableColumn("Download Speed (KB/s)", "rateDownload"),
            TableColumn("Upload Speed (KB/s)", "rateUpload"),
        ]

        self.visible_columns: Dict[str, bool] = {
            col.display_name: True for col in self.columns
        }

        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([col.display_name for col in self.columns])

        self.session_id: Optional[str] = None
        self.last_torrents: List[Dict[str, Any]] = []
        self.displayed_torrents: List[Dict[str, Any]] = []
        self.current_url = TRANSMISSION_URL
        self.is_connected: bool = False
        self.timer: QTimer = QTimer()

        # Load credentials with enhanced fallback logic
        self.current_credentials_enabled = False
        self.current_username = ""
        self.current_password = ""
        self.credentials_remembered = False

        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials with enhanced fallback logic."""
        from .config_manager import ConfigManager

        config_manager = ConfigManager()
        servers = config_manager.get_servers()

        if servers:
            # Load from first configured server (could be enhanced to load last used)
            first_server = servers[0]
            if first_server.get("use_credentials"):
                username = first_server.get("username", "")
                if username:
                    # Try to load from keyring first
                    stored_password = CredentialManager.get_credentials(username)
                    if stored_password:
                        self.current_credentials_enabled = True
                        self.current_username = username
                        self.current_password = stored_password
                        self.credentials_remembered = first_server.get(
                            "remember_credentials", False
                        )
                        logging.info(
                            "Loaded credentials from server profile: %s",
                            first_server["name"],
                        )
                        return

        # Fall back to environment variables if no server profiles or no credentials found
        self._load_environment_credentials()

    def _load_environment_credentials(self) -> None:
        """Load credentials from environment variables as fallback."""
        env_username = TRANSMISSION_USER
        env_password = TRANSMISSION_PASS

        if env_username:
            # Check if credentials exist in keyring first (for secure storage)
            if CredentialManager.is_available():
                stored_password = CredentialManager.get_credentials(env_username)
                if stored_password:
                    self.current_credentials_enabled = True
                    self.current_username = env_username
                    self.current_password = stored_password
                    self.credentials_remembered = True
                    logging.info("Loaded credentials from secure storage")
                    return

            # Fall back to environment variables
            if env_password:
                self.current_credentials_enabled = True
                self.current_username = env_username
                self.current_password = env_password
                logging.info("Loaded credentials from environment variables")
            else:
                # Username set but no password - might be incomplete config
                logging.warning("TRANSMISSION_USER set but TRANSMISSION_PASS not found")

    def _setup_system_tray(self) -> None:
        """Set up system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform")
            return

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Set tray icon (use application icon)
        if hasattr(self, "windowIcon") and not self.windowIcon().isNull():
            self.tray_icon.setIcon(self.windowIcon())
        else:
            # Fallback to a default icon
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        # Set initial tooltip
        self.tray_icon.setToolTip("Transmission QT Remote - Disconnected")

        # Create tray menu
        tray_menu = QMenu()

        # Show/Hide action
        show_hide_action = QAction("Show/Hide", self)
        show_hide_action.triggered.connect(self._toggle_window_visibility)
        tray_menu.addAction(show_hide_action)

        tray_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(exit_action)

        # Set the context menu
        self.tray_icon.setContextMenu(tray_menu)

        # Connect double-click to show/hide
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

        # Show the tray icon
        self.tray_icon.show()

        logger.info("System tray icon initialized")

    def _toggle_window_visibility(self) -> None:
        """Toggle main window visibility."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _quit_application(self) -> None:
        """Quit the application."""
        from PySide6.QtWidgets import QApplication

        QApplication.quit()

    def _on_tray_icon_activated(
        self, reason: "QSystemTrayIcon.ActivationReason"
    ) -> None:  # type: ignore[name-defined]
        """Handle tray icon activation (double-click, etc.)."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_window_visibility()

    def _update_tray_tooltip(self, tooltip: str) -> None:
        """Update the system tray tooltip."""
        if hasattr(self, "tray_icon"):
            self.tray_icon.setToolTip(tooltip)

    def showEvent(self, event: "QShowEvent") -> None:  # type: ignore[name-defined]
        """Handle window show event."""
        super().showEvent(event)
        # Attempt auto-connect after window is shown and Qt event loop is running
        QTimer.singleShot(100, self._attempt_auto_connect)

    def changeEvent(self, event: "QEvent") -> None:  # type: ignore[name-defined]
        """Handle window state changes like minimization/restoration."""
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                logger.info(
                    "Application window minimized - switching to slower refresh rate"
                )
            elif event.oldState() & Qt.WindowMinimized:
                logger.info(
                    "Application window restored - switching to normal refresh rate"
                )
            # Update timer interval when window state changes
            self.set_timer_interval()

    def _init_menu_bar(self) -> None:
        """Initialize the application menu bar."""
        from PySide6.QtGui import QAction, QActionGroup

        # Create menu bar
        menubar = self.menuBar()

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        connection_settings_action = QAction("&Connection Settings...", self)
        connection_settings_action.setShortcut("Ctrl+,")
        connection_settings_action.triggered.connect(self.open_connection_settings)
        edit_menu.addAction(connection_settings_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Torrent Details action
        torrent_details_action = QAction("&Torrent Details", self)
        torrent_details_action.setShortcut("Ctrl+D")
        torrent_details_action.triggered.connect(self._show_torrent_details)
        torrent_details_action.setEnabled(False)  # Initially disabled
        view_menu.addAction(torrent_details_action)
        self.torrent_details_action = torrent_details_action

        view_menu.addSeparator()

        # Theme submenu
        theme_menu = view_menu.addMenu("&Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        # Light theme
        light_action = QAction("&Light", self)
        light_action.setCheckable(True)
        light_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_action)
        theme_group.addAction(light_action)

        # Dark theme
        dark_action = QAction("&Dark", self)
        dark_action.setCheckable(True)
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_action)
        theme_group.addAction(dark_action)

        # Auto theme
        auto_action = QAction("&Auto", self)
        auto_action.setCheckable(True)
        auto_action.setChecked(True)  # Default to auto
        auto_action.triggered.connect(lambda: self.set_theme("auto"))
        theme_menu.addAction(auto_action)
        theme_group.addAction(auto_action)

        # Store theme actions for later use
        self.theme_actions = {
            "light": light_action,
            "dark": dark_action,
            "auto": auto_action,
        }

        # Set initial theme to auto
        self.current_theme = "auto"

        # Torrent menu
        torrent_menu = menubar.addMenu("&Torrent")

        # Start action
        start_action = QAction("&Start", self)
        start_action.setShortcut("Ctrl+S")
        start_action.triggered.connect(self._start_selected_torrent)
        start_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(start_action)
        self.torrent_start_action = start_action

        # Force Start action
        force_start_action = QAction("Force &Start", self)
        force_start_action.setShortcut("Ctrl+Shift+S")
        force_start_action.triggered.connect(self._force_start_selected_torrent)
        force_start_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(force_start_action)
        self.torrent_force_start_action = force_start_action

        # Pause action
        pause_action = QAction("&Pause", self)
        pause_action.setShortcut("Ctrl+P")
        pause_action.triggered.connect(self._pause_selected_torrent)
        pause_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(pause_action)
        self.torrent_pause_action = pause_action

        torrent_menu.addSeparator()

        # Verify action
        verify_action = QAction("&Verify", self)
        verify_action.setShortcut("Ctrl+R")
        verify_action.triggered.connect(self._verify_selected_torrent)
        verify_action.setEnabled(False)  # Initially disabled
        torrent_menu.addAction(verify_action)
        self.torrent_verify_action = verify_action

        torrent_menu.addSeparator()

        # Delete actions (greyed out for read-only client)
        delete_action = QAction("&Delete", self)
        delete_action.setEnabled(False)  # Read-only client
        delete_action.setToolTip("Delete not available in read-only client")
        torrent_menu.addAction(delete_action)
        self.torrent_delete_action = delete_action

        delete_data_action = QAction("Delete with &Data", self)
        delete_data_action.setEnabled(False)  # Read-only client
        delete_data_action.setToolTip(
            "Delete with data not available in read-only client"
        )
        torrent_menu.addAction(delete_data_action)
        self.torrent_delete_data_action = delete_data_action

    def _show_torrent_details(self) -> None:
        """Show torrent details for the currently selected torrent."""
        logger.debug("Opening torrent details from menu")
        # Get selected rows
        if not hasattr(self, "table"):
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        logger.debug(f"Selected rows: {selected_rows}")

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row]["id"]
                # Fetch detailed torrent data including files
                torrent = self.fetch_torrent_details(torrent_id)
                if torrent:
                    logger.debug(
                        f"Opening torrent details dialog for torrent ID: {torrent_id}"
                    )
                    from .dialogs.torrent_detail import TorrentDetailDialog

                    dialog = TorrentDetailDialog(self, torrent)
                    dialog.exec()

    def set_theme(self, theme: str) -> None:
        """Set and apply a new theme (session-only, no persistence)."""
        self.current_theme = theme
        self.apply_theme()

        # Update menu checkmarks
        if hasattr(self, "theme_actions"):
            for theme_name, action in self.theme_actions.items():
                action.setChecked(theme_name == theme)

    def _toggle_connection(self) -> None:
        """Toggle connection state."""
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        """Attempt to connect to the current server configuration."""
        from .config_manager import ConfigManager

        # Try to use saved server configuration first
        config_manager = ConfigManager()
        servers = config_manager.get_servers()

        if servers:
            # Try to use the last connected server first
            last_server_name = config_manager.get_last_connected_server_name()
            server = None

            if last_server_name:
                for s in servers:
                    if s.get("name") == last_server_name:
                        server = s
                        break

            # Fall back to first server if last connected not found
            if not server:
                server = servers[0]

            url = server["url"]

            # Load credentials from keyring if needed
            username = None
            password = None
            if server.get("use_credentials"):
                username = server.get("username", "")
                if (
                    server.get("remember_credentials")
                    and CredentialManager.is_available()
                ):
                    password = CredentialManager.get_credentials(username)
                    if not password:
                        # Fall back to current credentials if keyring fails
                        if (
                            self.current_credentials_enabled
                            and self.current_username == username
                        ):
                            password = self.current_password
                elif (
                    self.current_credentials_enabled
                    and self.current_username == username
                ):
                    # Use current session credentials
                    password = self.current_password
        else:
            # Fall back to current configuration
            url = self.current_url
            username = (
                self.current_username if self.current_credentials_enabled else None
            )
            password = (
                self.current_password if self.current_credentials_enabled else None
            )

        # Test the connection
        success, message = self._test_connection_settings(url, username, password)

        if success:
            self.is_connected = True
            self._update_connect_button()
            # Update current connection info
            self.current_url = url
            if username and password:
                self.current_credentials_enabled = True
                self.current_username = username
                self.current_password = password

            # Update last connected server information
            self._update_last_connected_server(url)

            self.refresh_data()  # Start data refresh
            logging.info("Connected to Transmission server: %s", url)
        else:
            QMessageBox.warning(self, "Connection Failed", message)
            # If authentication failed, suggest opening connection settings
            if "authentication" in message.lower() or "401" in message:
                reply = QMessageBox.question(
                    self,
                    "Configure Credentials?",
                    "The server requires authentication. Would you like to open Connection Settings to configure credentials?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.open_connection_settings()

    def _update_last_connected_server(self, connected_url: str) -> None:
        """Update the last connected server information."""
        import time

        from .config_manager import ConfigManager

        config_manager = ConfigManager()
        servers = config_manager.get_servers()

        # Find the server that matches the connected URL
        for server in servers:
            if server.get("url") == connected_url:
                # Update server with connection info
                server["last_connected"] = int(time.time())
                server["connection_count"] = server.get("connection_count", 0) + 1

                # Update the last connected server name in config
                config_manager.set_last_connected_server_name(server["name"])
                config_manager.set_servers(servers)
                break

    def _attempt_auto_connect(self) -> None:
        """Attempt to auto-connect to the last connected server if enabled."""
        from .config_manager import ConfigManager

        config_manager = ConfigManager()
        if not config_manager.get_auto_connect_enabled():
            return

        last_server_name = config_manager.get_last_connected_server_name()
        if not last_server_name:
            return

        servers = config_manager.get_servers()
        last_server = None
        for server in servers:
            if server.get("name") == last_server_name:
                last_server = server
                break

        if not last_server:
            logging.warning(
                "Last connected server '%s' not found in server list", last_server_name
            )
            return

        # Attempt to connect to the last server
        logging.info("Attempting auto-connect to last server: %s", last_server_name)
        self._connect_to_server(last_server)

    def _connect_to_server(self, server: Dict[str, Any]) -> None:
        """Connect to a specific server configuration."""
        url = server["url"]
        username = None
        password = None

        if server.get("use_credentials"):
            username = server.get("username", "")
            if server.get("remember_credentials") and CredentialManager.is_available():
                password = CredentialManager.get_credentials(username)

        # Test the connection
        success, message = self._test_connection_settings(url, username, password)

        if success:
            self.is_connected = True
            self._update_connect_button()
            # Update current connection info
            self.current_url = url
            if username and password:
                self.current_credentials_enabled = True
                self.current_username = username
                self.current_password = password

            # Update last connected server information
            self._update_last_connected_server(url)

            self.refresh_data()  # Start data refresh
            logging.info("Auto-connected to Transmission server: %s", url)
        else:
            logging.warning(
                "Auto-connect failed to server %s: %s", server.get("name"), message
            )

    def _disconnect(self) -> None:
        """Disconnect from the current server."""
        self.is_connected = False
        self._update_connect_button()
        # Stop the timer to prevent further requests
        self.timer.stop()
        logging.info("Disconnected from Transmission server")

    def _update_connect_button(self) -> None:
        """Update the connect button appearance based on connection state."""
        if self.is_connected:
            self.connect_btn.setToolTip("Disconnect from server")
            self.connect_btn.setIcon(
                self.style().standardIcon(QStyle.SP_DialogCancelButton)
            )
        else:
            self.connect_btn.setToolTip("Connect to server")
            self.connect_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))

        # Update status label when connection state changes
        self._update_status_label()

    def _update_status_label(self, refresh_time: Optional[str] = None) -> None:
        """Update the status label and tray tooltip based on connection state."""
        if self.is_connected:
            if refresh_time:
                # Show actual refresh time
                self.status_label.setText(f"Last refresh: {refresh_time}")
                self._update_tray_tooltip(
                    f"Transmission QT Remote - Connected (Last refresh: {refresh_time})"
                )
            else:
                # Connected but no refresh yet
                self.status_label.setText("Last refresh: --:--:--")
                self._update_tray_tooltip("Transmission QT Remote - Connected")
        else:
            # When disconnected, show disconnected status
            self.status_label.setText("Disconnected")
            self._update_tray_tooltip("Transmission QT Remote - Disconnected")

    def fetch_torrents(self) -> List[Dict[str, Any]]:
        """Fetch torrent data from Transmission server."""
        try:
            response = requests.post(
                self.current_url,
                headers={"X-Transmission-Session-Id": getattr(self, "session_id", "")},
                auth=(self.current_username, self.current_password)
                if self.current_credentials_enabled
                else None,
                json={
                    "method": "torrent-get",
                    "arguments": {
                        "fields": [
                            "id",
                            "name",
                            "status",
                            "percentDone",
                            "rateDownload",
                            "rateUpload",
                            "eta",
                            "sizeWhenDone",
                            "totalSize",
                            "peersConnected",
                            "peersSendingToUs",
                            "peersGettingFromUs",
                            "trackerStats",
                            "addedDate",
                            "doneDate",
                            "error",
                            "errorString",
                        ]
                    },
                },
                timeout=CONNECTION_TIMEOUT_SEC,
            )

            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                return self.fetch_torrents()

            if response.status_code == 200:
                return response.json().get("arguments", {}).get("torrents", [])

        except requests.RequestException:
            pass

        return []

    def fetch_torrent_details(self, torrent_id: int) -> Optional[Dict[str, Any]]:
        """Fetch detailed torrent data including files for a specific torrent."""
        logger.debug(f"Fetching detailed data for torrent ID: {torrent_id}")
        try:
            response = requests.post(
                self.current_url,
                headers={"X-Transmission-Session-Id": getattr(self, "session_id", "")},
                auth=(self.current_username, self.current_password)
                if self.current_credentials_enabled
                else None,
                json={
                    "method": "torrent-get",
                    "arguments": {
                        "fields": [
                            "id",
                            "name",
                            "status",
                            "percentDone",
                            "rateDownload",
                            "rateUpload",
                            "eta",
                            "sizeWhenDone",
                            "totalSize",
                            "peersConnected",
                            "peersSendingToUs",
                            "peersGettingFromUs",
                            "trackerStats",
                            "addedDate",
                            "doneDate",
                            "error",
                            "errorString",
                            "files",
                            "fileStats",
                            "metadataPercentComplete",
                        ],
                    },
                },
                timeout=CONNECTION_TIMEOUT_SEC,
            )

            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                return self.fetch_torrent_details(torrent_id)

            if response.status_code == 200:
                data = response.json()
                torrents = data.get("arguments", {}).get("torrents", [])
                if torrents:
                    torrent = torrents[0]
                    logger.debug(f"Torrent data keys: {list(torrent.keys())}")
                    logger.info(
                        f"Retrieved detailed data for torrent: {torrent.get('name', 'Unknown')}"
                    )
                    logger.debug(
                        f"Files available: {'files' in torrent}, FileStats available: {'fileStats' in torrent}"
                    )
                    if "files" in torrent:
                        logger.debug(f"Files count: {len(torrent['files'])}")
                    if "fileStats" in torrent:
                        logger.debug(f"FileStats count: {len(torrent['fileStats'])}")
                    return torrent
                logger.warning("No torrent data received from API")
                return None
            else:
                logger.error(
                    f"API request failed with status {response.status_code}: {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Network error fetching torrent details: {e}")
            return None

    def set_file_priority(
        self, torrent_id: int, file_indices: List[int], priority: int
    ) -> bool:
        """Set priority for specific files in a torrent.

        Args:
            torrent_id: ID of the torrent.
            file_indices: List of file indices to modify.
            priority: Priority value (-1=Low, 0=Normal, 1=High).

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.post(
                self.current_url,
                headers={"X-Transmission-Session-Id": getattr(self, "session_id", "")},
                auth=(self.current_username, self.current_password)
                if self.current_credentials_enabled
                else None,
                json={
                    "method": "torrent-set",
                    "arguments": {
                        "ids": [torrent_id],
                        "priority-low": file_indices if priority == -1 else [],
                        "priority-normal": file_indices if priority == 0 else [],
                        "priority-high": file_indices if priority == 1 else [],
                    },
                },
                timeout=CONNECTION_TIMEOUT_SEC,
            )

            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                return self.set_file_priority(torrent_id, file_indices, priority)

            return response.status_code == 200

        except requests.RequestException:
            return False

    def set_file_wanted(
        self, torrent_id: int, file_indices: List[int], wanted: bool
    ) -> bool:
        """Set wanted status for specific files in a torrent.

        Args:
            torrent_id: ID of the torrent.
            file_indices: List of file indices to modify.
            wanted: Whether files should be wanted.

        Returns:
            True if successful, False otherwise.
        """
        try:
            response = requests.post(
                self.current_url,
                headers={"X-Transmission-Session-Id": getattr(self, "session_id", "")},
                auth=(self.current_username, self.current_password)
                if self.current_credentials_enabled
                else None,
                json={
                    "method": "torrent-set",
                    "arguments": {
                        "ids": [torrent_id],
                        "files-wanted": file_indices if wanted else [],
                        "files-unwanted": file_indices if not wanted else [],
                    },
                },
                timeout=CONNECTION_TIMEOUT_SEC,
            )

            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                return self.set_file_wanted(torrent_id, file_indices, wanted)

            return response.status_code == 200

        except requests.RequestException:
            return False

    def refresh_data(self) -> None:
        """Refresh torrent data and update UI."""
        logger.debug("Refreshing torrent data")
        if not self.is_connected:
            logger.debug("Not connected, skipping refresh")
            return

        try:
            torrents = self.fetch_torrents()
            logger.info(f"Fetched {len(torrents) if torrents else 0} torrents")
            self.last_torrents = torrents
            self.displayed_torrents = torrents

            # Update table if it exists
            if hasattr(self, "table"):
                self._update_table()

            # Update status
            self._update_status_label(time.strftime("%H:%M:%S"))
            self.filter_summary_label.setText(
                f"Showing {len(torrents)} torrents • Tracker: All"
            )

        except Exception as e:
            logging.error("Failed to refresh data: %s", e)

    def filter_table(self, text: str = "") -> None:
        """Filter the torrent table based on search text and tracker filters."""
        if not hasattr(self, "table") or not self.displayed_torrents:
            return

        # Get search text from search box if not provided
        if not text and hasattr(self, "search_box"):
            text = self.search_box.text()

        for row in range(self.table.rowCount()):
            if row >= len(self.displayed_torrents):
                continue

            torrent = self.displayed_torrents[row]

            # Text search filter
            text_match = True
            if text:
                torrent_name = torrent.get("name", "").lower()
                text_match = text.lower() in torrent_name

            # Tracker filter
            tracker_match = True
            if self.active_tracker or self.active_trackers:
                torrent_trackers = set()
                for stat in torrent.get("trackerStats", []):
                    announce_url = stat.get("announce", "")
                    if announce_url:
                        torrent_trackers.add(announce_url)

                # Check both active_tracker (for direct setting) and active_trackers (for select_tracker)
                filter_strings = set()
                if self.active_tracker:
                    filter_strings.add(self.active_tracker)
                filter_strings.update(self.active_trackers)

                # Check if any filter string is contained in any torrent tracker URL
                tracker_match = any(
                    any(filter_str in announce_url for announce_url in torrent_trackers)
                    for filter_str in filter_strings
                )

            # Show row if both filters match
            visible = text_match and tracker_match
            self.table.setRowHidden(row, not visible)

    def select_tracker(self, tracker: str) -> None:
        """Filter torrents by tracker."""
        if tracker == "All":
            self.active_tracker = None
            self.active_trackers = []
        else:
            self.active_tracker = tracker
            self.active_trackers = [tracker]
        self.filter_table()

    def clear_filters(self) -> None:
        """Clear all filters."""
        if hasattr(self, "search_box"):
            self.search_box.clear()
        self.select_tracker("All")

    def toggle_column(self, column_name: str, visible: bool) -> None:
        """Toggle column visibility."""
        if column_name in self.visible_columns:
            self.visible_columns[column_name] = visible
            # Find column index and hide/show it
            for i, column in enumerate(self.columns):
                if column.display_name == column_name:
                    if hasattr(self, "table"):
                        self.table.setColumnHidden(i, not visible)
                    break

    def update_tracker_buttons(self, torrents: List[Dict[str, Any]]) -> None:
        """Update tracker filter buttons based on torrent data."""
        # Extract unique trackers from torrent data
        trackers = set()
        for torrent in torrents:
            for stat in torrent.get("trackerStats", []):
                announce_url = stat.get("announce", "")
                if announce_url:
                    trackers.add(announce_url)

        # Update tracker options
        self.tracker_options = ["All"] + sorted(trackers)

        # Update combo box if it exists
        if hasattr(self, "tracker_selector"):
            current_text = self.tracker_selector.currentText()
            self.tracker_selector.clear()
            self.tracker_selector.addItems(self.tracker_options)

            # Restore selection if it still exists
            if current_text in self.tracker_options:
                self.tracker_selector.setCurrentText(current_text)

    def get_status_text(self, status_code: int) -> str:
        """Convert Transmission status code to human-readable text."""
        try:
            status = TorrentStatus(status_code)
            return status.display_text()
        except ValueError:
            return "Unknown"

    def set_timer_interval(self) -> None:
        """Set timer interval based on window minimization state."""
        # Use appropriate interval based on window state
        interval = (
            self.minimized_refresh_interval_ms
            if self.windowState() & Qt.WindowMinimized
            else self.refresh_interval_ms
        )
        self.timer.setInterval(interval)
        logger.info(
            f"Refresh interval set to {interval}ms ({'minimized' if self.windowState() & Qt.WindowMinimized else 'normal'} mode)"
        )

    def apply_theme(self) -> None:
        """Apply the current theme to the application."""
        # Placeholder - would apply theme colors and styles
        pass

    def _on_table_selection_changed(self) -> None:
        """Handle table selection changes to update menu action states."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        # Enable torrent details action only when exactly one row is selected
        if hasattr(self, "torrent_details_action"):
            self.torrent_details_action.setEnabled(len(selected_rows) == 1)

        # Update torrent menu actions based on selection
        if len(selected_rows) == 1:
            # Get the selected torrent
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent = self.displayed_torrents[row]
                torrent_status = torrent.get("status", 0)

                # Enable actions based on torrent status
                if hasattr(self, "torrent_start_action"):
                    self.torrent_start_action.setEnabled(
                        torrent_status in [0, 4, 5]
                    )  # Stopped, Download pending, Seed pending
                if hasattr(self, "torrent_force_start_action"):
                    self.torrent_force_start_action.setEnabled(
                        torrent_status in [0, 4, 5]
                    )  # Stopped, Download pending, Seed pending
                if hasattr(self, "torrent_pause_action"):
                    self.torrent_pause_action.setEnabled(
                        torrent_status not in [0, 4, 5]
                    )  # Active torrents
                if hasattr(self, "torrent_verify_action"):
                    self.torrent_verify_action.setEnabled(True)

                # Update toolbar actions
                if hasattr(self, "toolbar_start_action"):
                    self.toolbar_start_action.setEnabled(
                        torrent_status in [0, 4, 5]
                    )  # Stopped, Download pending, Seed pending
                if hasattr(self, "toolbar_force_start_action"):
                    self.toolbar_force_start_action.setEnabled(
                        torrent_status in [0, 4, 5]
                    )  # Stopped, Download pending, Seed pending
                if hasattr(self, "toolbar_pause_action"):
                    self.toolbar_pause_action.setEnabled(
                        torrent_status not in [0, 4, 5]
                    )  # Active torrents
            else:
                # Disable all actions if row is invalid
                self._disable_torrent_menu_actions()
        else:
            # Disable all actions if no single torrent is selected
            self._disable_torrent_menu_actions()

        # Debug logging
        logger.debug(f"Selection changed: {len(selected_rows)} rows selected")
        if len(selected_rows) == 1 and hasattr(self, "torrent_start_action"):
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent = self.displayed_torrents[row]
                torrent_status = torrent.get("status", 0)
                logger.debug(
                    f"Torrent status: {torrent_status}, Start enabled: {self.torrent_start_action.isEnabled()}"
                )

    def _disable_torrent_menu_actions(self) -> None:
        """Disable all torrent menu actions."""
        if hasattr(self, "torrent_start_action"):
            self.torrent_start_action.setEnabled(False)
        if hasattr(self, "torrent_force_start_action"):
            self.torrent_force_start_action.setEnabled(False)
        if hasattr(self, "torrent_pause_action"):
            self.torrent_pause_action.setEnabled(False)
        if hasattr(self, "torrent_verify_action"):
            self.torrent_verify_action.setEnabled(False)

        # Disable toolbar actions
        if hasattr(self, "toolbar_start_action"):
            self.toolbar_start_action.setEnabled(False)
        if hasattr(self, "toolbar_force_start_action"):
            self.toolbar_force_start_action.setEnabled(False)
        if hasattr(self, "toolbar_pause_action"):
            self.toolbar_pause_action.setEnabled(False)

    def on_torrent_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle double-click on torrent item."""
        row = item.row()
        if row < len(self.displayed_torrents):
            torrent_id = self.displayed_torrents[row]["id"]
            # Fetch detailed torrent data including files
            torrent = self.fetch_torrent_details(torrent_id)
            if not torrent:
                # Fall back to cached data if fetch fails
                torrent = self.displayed_torrents[row]

            # Create and show torrent detail dialog
            from .dialogs.torrent_detail import TorrentDetailDialog

            dialog = TorrentDetailDialog(self, torrent)
            dialog.exec()

    def _update_table(self) -> None:
        """Update the torrent table with current data."""
        if not hasattr(self, "table") or not self.displayed_torrents:
            return

        # Clear existing content
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.displayed_torrents))

        for row, torrent in enumerate(self.displayed_torrents):
            for col, column in enumerate(self.columns):
                # Get the value from torrent data
                value = torrent.get(column.field_name, "")

                # Format the value based on field type
                if column.field_name == "totalSize" and value:
                    # Convert bytes to MB
                    value = f"{value / (1024 * 1024):.1f}"
                elif column.field_name in ["rateDownload", "rateUpload"] and value:
                    # Convert bytes/s to KB/s
                    value = f"{value / 1024:.1f}"
                elif column.field_name == "addedDate" and value:
                    # Convert timestamp to readable date
                    try:
                        value = time.strftime("%Y-%m-%d %H:%M", time.localtime(value))
                    except (ValueError, OSError):
                        value = str(value)
                elif column.field_name == "percentDone" and isinstance(
                    value, (int, float)
                ):
                    # Format as percentage
                    value = f"{value * 100:.1f}%"
                elif column.field_name == "seeders" or column.field_name == "leechers":
                    # Extract from tracker stats if available
                    tracker_stats = torrent.get("trackerStats", [])
                    if tracker_stats:
                        if column.field_name == "seeders":
                            value = sum(
                                stat.get("seederCount", 0) for stat in tracker_stats
                            )
                        else:  # leechers
                            value = sum(
                                stat.get("leecherCount", 0) for stat in tracker_stats
                            )
                    else:
                        value = 0
                elif column.field_name == "status" and isinstance(value, int):
                    value = self.get_status_text(value)
                elif not value:
                    value = ""

                # Create table item
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)

        # Resize columns to content
        self.table.resizeColumnsToContents()

    def _test_connection_settings(
        self, url: str, username: Optional[str], password: Optional[str]
    ) -> Tuple[bool, str]:
        """Test connection settings and return success status with message."""
        request_data = {"method": "session-get"}
        auth = (username, password) if username and password else None

        try:
            response = requests.post(
                url, auth=auth, json=request_data, timeout=CONNECTION_TIMEOUT_SEC
            )
            if response.status_code in {200, 409}:
                return True, "Successfully connected to Transmission."
            elif response.status_code == 401:
                if auth:
                    return (
                        False,
                        "Authentication failed. Please check your username and password.",
                    )
                else:
                    return (
                        False,
                        "Server requires authentication. Please configure credentials in Connection Settings.",
                    )
            else:
                return (
                    False,
                    f"Server returned status {response.status_code}: {response.text[:100]}",
                )
        except requests.RequestException as exc:
            return False, str(exc)

    def open_connection_settings(self) -> None:
        """Displays the connection settings dialog and applies user entries."""
        # Get current auto-connect setting
        from .config_manager import ConfigManager
        from .dialogs.connection_settings import ConnectionSettingsDialog

        config_manager = ConfigManager()
        current_auto_connect = config_manager.get_auto_connect_enabled()

        dialog = ConnectionSettingsDialog(
            self,
            current_url=self.current_url,
            use_credentials=self.current_credentials_enabled,
            username=self.current_username,
            password=self.current_password,
            refresh_interval_sec=self.refresh_interval_ms // 1000,
            minimized_interval_sec=self.minimized_refresh_interval_ms // 1000,
            connection_timeout_sec=CONNECTION_TIMEOUT_SEC,
            test_callback=self._test_connection_settings,
            remember_credentials=self.credentials_remembered,
            auto_connect_enabled=current_auto_connect,
        )

        if dialog.exec() == 1:  # QDialog.Accepted
            (
                self.current_url,
                self.current_credentials_enabled,
                self.current_username,
                self.current_password,
                refresh_interval_sec,
                minimized_interval_sec,
                _connection_timeout_sec,
                self.credentials_remembered,
                auto_connect_enabled,
            ) = dialog.get_settings()

            # Save auto-connect setting
            from .config_manager import ConfigManager

            config_manager = ConfigManager()
            config_manager.set_auto_connect_enabled(auto_connect_enabled)

            # Update refresh intervals
            old_refresh = self.refresh_interval_ms
            old_minimized = self.minimized_refresh_interval_ms
            self.refresh_interval_ms = refresh_interval_sec * 1000
            self.minimized_refresh_interval_ms = minimized_interval_sec * 1000

            if (
                old_refresh != self.refresh_interval_ms
                or old_minimized != self.minimized_refresh_interval_ms
            ):
                logger.info(
                    f"Refresh intervals updated - normal: {self.refresh_interval_ms}ms, minimized: {self.minimized_refresh_interval_ms}ms"
                )
                # Update timer interval immediately if connected
                if self.is_connected:
                    self.set_timer_interval()

    def _show_torrent_context_menu(self, position: "QPoint") -> None:  # type: ignore[name-defined]
        """Show right-click context menu for torrent actions."""
        # Get the torrent at the clicked position
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        if row >= len(self.displayed_torrents):
            return

        torrent = self.displayed_torrents[row]
        torrent_id = torrent["id"]
        torrent_status = torrent.get("status", 0)

        # Create context menu
        menu = QMenu(self)

        # Start/Stop action
        if torrent_status in [0, 4, 5]:  # Stopped, Download pending, Seed pending
            start_action = QAction("Start", self)
            start_action.triggered.connect(lambda: self.start_torrent(torrent_id))
            menu.addAction(start_action)

            force_start_action = QAction("Force Start", self)
            force_start_action.triggered.connect(
                lambda: self.force_start_torrent(torrent_id)
            )
            menu.addAction(force_start_action)
        else:  # Active torrents
            pause_action = QAction("Pause", self)
            pause_action.triggered.connect(lambda: self.pause_torrent(torrent_id))
            menu.addAction(pause_action)

        menu.addSeparator()

        # Verify action
        verify_action = QAction("Verify", self)
        verify_action.triggered.connect(lambda: self.verify_torrent(torrent_id))
        menu.addAction(verify_action)

        menu.addSeparator()

        # Delete actions (greyed out for read-only client)
        delete_action = QAction("Delete", self)
        delete_action.setEnabled(False)  # Read-only client
        delete_action.setToolTip("Delete not available in read-only client")
        menu.addAction(delete_action)

        delete_data_action = QAction("Delete with Data", self)
        delete_data_action.setEnabled(False)  # Read-only client
        delete_data_action.setToolTip(
            "Delete with data not available in read-only client"
        )
        menu.addAction(delete_data_action)

        # Show menu at cursor position
        menu.exec(self.table.mapToGlobal(position))

    def _start_selected_torrent(self) -> None:
        """Start the currently selected torrent."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row]["id"]
                self.start_torrent(torrent_id)

    def _force_start_selected_torrent(self) -> None:
        """Force start the currently selected torrent."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row]["id"]
                self.force_start_torrent(torrent_id)

    def _pause_selected_torrent(self) -> None:
        """Pause the currently selected torrent."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row]["id"]
                self.pause_torrent(torrent_id)

    def _verify_selected_torrent(self) -> None:
        """Verify the currently selected torrent."""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row]["id"]
                self.verify_torrent(torrent_id)

    def start_torrent(self, torrent_id: int) -> None:
        """Start a torrent."""
        self._execute_torrent_action("torrent-start", torrent_id, "Torrent started")

    def force_start_torrent(self, torrent_id: int) -> None:
        """Force start a torrent."""
        self._execute_torrent_action(
            "torrent-start", torrent_id, "Torrent force started", force=True
        )

    def pause_torrent(self, torrent_id: int) -> None:
        """Pause a torrent."""
        self._execute_torrent_action("torrent-stop", torrent_id, "Torrent paused")

    def verify_torrent(self, torrent_id: int) -> None:
        """Verify torrent data."""
        self._execute_torrent_action(
            "torrent-verify", torrent_id, "Torrent verification started"
        )

    def _execute_torrent_action(
        self, method: str, torrent_id: int, success_message: str, force: bool = False
    ) -> None:
        """Execute a torrent action with proper error handling."""
        if not self.is_connected:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to the Transmission server first.",
            )
            return

        try:
            # Prepare request data
            request_data = {"method": method, "arguments": {"ids": [torrent_id]}}

            # Add force parameter if needed
            if force and method == "torrent-start":
                request_data["arguments"]["force"] = True

            response = requests.post(
                self.current_url,
                headers={"X-Transmission-Session-Id": getattr(self, "session_id", "")},
                auth=(self.current_username, self.current_password)
                if self.current_credentials_enabled
                else None,
                json=request_data,
                timeout=CONNECTION_TIMEOUT_SEC,
            )

            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                self._execute_torrent_action(method, torrent_id, success_message, force)
                return

            if response.status_code == 200:
                # Refresh data to show updated state
                self.refresh_data()
                QMessageBox.information(self, "Success", success_message)
            else:
                QMessageBox.warning(
                    self,
                    "Action Failed",
                    f"Failed to execute action. Server returned status {response.status_code}.",
                )

        except requests.Timeout:
            QMessageBox.warning(
                self,
                "Timeout",
                "Server did not respond within the timeout period. Please check your connection and try again.",
            )
        except requests.RequestException as e:
            QMessageBox.warning(
                self, "Network Error", f"Network error occurred: {str(e)}"
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Error", f"An unexpected error occurred: {str(e)}"
            )
