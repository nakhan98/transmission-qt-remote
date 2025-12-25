"""Main window for Transmission QT Remote - Coordinator Pattern Implementation."""

import logging
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .api import TransmissionAPIClient
from .config import (
    APP_NAME,
    DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS,
    DEFAULT_REFRESH_INTERVAL_MS,
)
from .config_manager import ConfigManager
from .connection import ConnectionManager
from .credential_manager import CredentialManager
from .models import TableColumn
from .ui import MenuBarManager, SystemTrayManager, TorrentTableWidget, TorrentToolbar

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TransmissionClient(QMainWindow):
    """A class representing a Transmission client GUI application.

    This main window acts as a coordinator, delegating specific responsibilities
    to specialized component managers for clean separation of concerns.
    """

    def __init__(self) -> None:
        """Initializes the TransmissionClient with default settings."""
        logger.info("MainWindow initialized")
        super().__init__()

        self.refresh_interval_ms = DEFAULT_REFRESH_INTERVAL_MS
        self.minimized_refresh_interval_ms = DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS
        self.current_theme = "light"

        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 900, 500)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(16, 8, 16, 16)
        self.central_widget.setLayout(self.main_layout)

        # Initialize component managers
        self._init_managers()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.filter_summary_label = QLabel("Showing 0 torrents • Tracker: All")
        self.filter_summary_label.setObjectName("SummaryLabel")
        self.status_bar.addWidget(self.filter_summary_label)

        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("StatusLabel")
        self.status_bar.addPermanentWidget(self.status_label)

        # Connect component signals
        self._connect_signals()

    def _init_managers(self) -> None:
        """Initialize all component managers."""
        # Initialize config and credential managers
        self.config_manager = ConfigManager()
        self.credential_manager = CredentialManager()

        # Initialize connection manager
        self.connection_manager = ConnectionManager(
            self.config_manager, self.credential_manager
        )

        # Initialize API client (will be set when connected)
        self.api_client: Optional[TransmissionAPIClient] = None

        # Initialize UI components
        self._init_ui_components()

        # Initialize timer for data refresh
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_data)

    def _init_ui_components(self) -> None:
        """Initialize UI component managers."""
        # Menu bar manager
        self.menu_bar_manager = MenuBarManager(self)
        self.menu_bar_manager.setup_menu_bar()

        # System tray manager
        self.system_tray_manager = SystemTrayManager(self)
        self.system_tray_manager.setup_tray()

        # Torrent toolbar
        self.torrent_toolbar = TorrentToolbar(self)

        # Torrent table columns
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

        # Torrent table widget
        self.torrent_table = TorrentTableWidget(self.columns, self)

        # Add components to layout
        self._setup_ui_layout()

    def _setup_ui_layout(self) -> None:
        """Set up the UI layout with toolbar and table."""
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
        self.search_box.textChanged.connect(self.torrent_table.filter_by_text)
        controls_layout.addWidget(self.search_box, stretch=3)

        self.clear_filters_btn = QToolButton()
        self.clear_filters_btn.setToolTip("Clear Filters")
        self.clear_filters_btn.setIcon(
            self.style().standardIcon(QStyle.SP_DialogResetButton)
        )
        self.clear_filters_btn.clicked.connect(self.torrent_table.clear_filters)
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
        self.tracker_selector.currentTextChanged.connect(
            self.torrent_table.filter_by_tracker
        )
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
        self.main_layout.addLayout(toolbar_controls_layout)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(divider)

        # Add torrent table
        self.main_layout.addWidget(self.torrent_table)

    def _connect_signals(self) -> None:
        """Connect signals between components."""
        # Connection manager signals
        self.connection_manager.connected.connect(self._on_connected)
        self.connection_manager.disconnected.connect(self._on_disconnected)
        self.connection_manager.connection_failed.connect(self._on_connection_failed)

        # Menu bar signals
        self.menu_bar_manager.connection_settings_requested.connect(
            self.open_connection_settings
        )
        self.menu_bar_manager.torrent_details_requested.connect(
            self._show_torrent_details
        )
        self.menu_bar_manager.theme_changed.connect(self._on_theme_changed)
        self.menu_bar_manager.start_requested.connect(self._start_selected_torrent)
        self.menu_bar_manager.force_start_requested.connect(
            self._force_start_selected_torrent
        )
        self.menu_bar_manager.pause_requested.connect(self._pause_selected_torrent)
        self.menu_bar_manager.verify_requested.connect(self._verify_selected_torrent)

        # Toolbar signals
        self.torrent_toolbar.start_requested.connect(self._start_selected_torrent)
        self.torrent_toolbar.force_start_requested.connect(
            self._force_start_selected_torrent
        )
        self.torrent_toolbar.pause_requested.connect(self._pause_selected_torrent)
        self.torrent_toolbar.open_requested.connect(self._open_torrent_file)
        self.torrent_toolbar.delete_requested.connect(self._delete_selected_torrent)

        # Table signals
        self.torrent_table.torrent_double_clicked.connect(
            self._on_torrent_double_clicked
        )
        self.torrent_table.torrent_selection_changed.connect(
            self._on_torrent_selection_changed
        )
        self.torrent_table.torrent_context_menu_requested.connect(
            self._on_context_menu_requested
        )

    def _on_connected(self, url: str) -> None:
        """Handle successful connection."""
        self.api_client = TransmissionAPIClient(
            url,
            self.connection_manager.current_username,
            self.connection_manager.current_password,
        )
        self.status_label.setText(f"Connected to {url}")
        self.connect_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))
        self.connect_btn.setToolTip("Disconnect from server")
        self._start_refresh_timer()

    def _on_disconnected(self) -> None:
        """Handle disconnection."""
        self.api_client = None
        self.status_label.setText("Disconnected")
        self.connect_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon))
        self.connect_btn.setToolTip("Connect to server")
        self._stop_refresh_timer()

    def _on_connection_failed(self, message: str) -> None:
        """Handle connection failure."""
        self.status_label.setText(f"Connection failed: {message}")
        QMessageBox.warning(self, "Connection Failed", message)

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change."""
        self.set_theme(theme)

    def _on_torrent_double_clicked(self, torrent_id: int) -> None:
        """Handle torrent double-click."""
        self._show_torrent_details()

    def _on_torrent_selection_changed(self, torrent_ids: List[int]) -> None:
        """Handle torrent selection changes."""
        # Update toolbar and menu actions based on selection
        selected_torrent = self.torrent_table.get_selected_torrent()
        status = selected_torrent.get("status") if selected_torrent else None

        self.torrent_toolbar.update_actions(status)
        self.menu_bar_manager.update_torrent_actions(status)

        # Update menu bar torrent details availability
        self.menu_bar_manager.set_torrent_details_enabled(len(torrent_ids) > 0)

    def _on_context_menu_requested(self, torrent_id: int, position: QPoint) -> None:
        """Handle context menu request."""
        self._show_torrent_context_menu(position)

    def _show_torrent_context_menu(self, position: QPoint) -> None:
        """Show context menu for torrent actions at the given position."""
        from PySide6.QtWidgets import QMenu

        # For now, just show a basic menu - can be expanded later
        menu = QMenu(self)

        # Add torrent actions
        start_action = menu.addAction("Start")
        force_start_action = menu.addAction("Force Start")
        pause_action = menu.addAction("Pause")
        verify_action = menu.addAction("Verify")

        # Connect actions
        start_action.triggered.connect(self._start_selected_torrent)
        force_start_action.triggered.connect(self._force_start_selected_torrent)
        pause_action.triggered.connect(self._pause_selected_torrent)
        verify_action.triggered.connect(self._verify_selected_torrent)

        # Disable actions based on torrent status
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            status = selected_torrent.get("status", 0)
            start_action.setEnabled(status in [0, 4, 5])
            force_start_action.setEnabled(status in [0, 4, 5])
            pause_action.setEnabled(status not in [0, 4, 5])
            verify_action.setEnabled(True)
        else:
            # No torrent selected
            start_action.setEnabled(False)
            force_start_action.setEnabled(False)
            pause_action.setEnabled(False)
            verify_action.setEnabled(False)

        # Show menu
        menu.exec(position)

    def _open_torrent_file(self) -> None:
        """Open torrent file (placeholder for read-only client)."""
        QMessageBox.information(
            self,
            "Not Available",
            "Opening torrent files is not available in read-only client.",
        )

    def _delete_selected_torrent(self) -> None:
        """Delete selected torrent (placeholder for read-only client)."""
        QMessageBox.information(
            self,
            "Not Available",
            "Deleting torrents is not available in read-only client.",
        )

    def _start_refresh_timer(self) -> None:
        """Start the data refresh timer."""
        self.set_timer_interval()

    def _stop_refresh_timer(self) -> None:
        """Stop the data refresh timer."""
        self.timer.stop()

    def _show_torrent_details(self) -> None:
        """Show details for the selected torrent."""
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            # TODO: Implement torrent details dialog
            details = (
                f"Torrent: {selected_torrent.get('name', 'Unknown')}\n"
                f"Status: {selected_torrent.get('status', 'Unknown')}\n"
                f"Size: {selected_torrent.get('totalSize', 0)} bytes"
            )
            QMessageBox.information(self, "Torrent Details", details)
        else:
            QMessageBox.information(
                self, "No Selection", "Please select a torrent first."
            )

    def refresh_data(self) -> None:
        """Refresh torrent data and update UI."""
        logger.debug("Refreshing torrent data")
        if not self.connection_manager.is_connected or not self.api_client:
            logger.debug("Not connected, skipping refresh")
            return

        try:
            torrents = self.api_client.fetch_torrents()
            logger.info(f"Fetched {len(torrents) if torrents else 0} torrents")

            # Update torrent table
            self.torrent_table.update_torrents(torrents)

            # Update tracker options
            self.torrent_table.update_tracker_options(torrents)

            # Update status
            self._update_status_label(time.strftime("%H:%M:%S"))

            # Update filter summary - this should be done by the table widget
            visible_count = sum(
                1
                for row in range(self.torrent_table.rowCount())
                if not self.torrent_table.isRowHidden(row)
            )
            tracker_filter = "All"  # TODO: Get current tracker filter from table
            self.filter_summary_label.setText(
                f"Showing {visible_count} torrents • Tracker: {tracker_filter}"
            )

        except Exception as e:
            logger.error("Failed to refresh data: %s", e)

    def _update_status_label(self, refresh_time: Optional[str] = None) -> None:
        """Update the status label and tray tooltip based on connection state."""
        if self.connection_manager.is_connected:
            if refresh_time:
                # Show actual refresh time
                self.status_label.setText(f"Last refresh: {refresh_time}")
                self.system_tray_manager.update_tooltip(
                    f"Transmission QT Remote - Connected (Last refresh: {refresh_time})"
                )
            else:
                # Connected but no refresh yet
                self.status_label.setText("Last refresh: --:--:--")
                self.system_tray_manager.update_tooltip(
                    "Transmission QT Remote - Connected"
                )
        else:
            # When disconnected, show disconnected status
            self.status_label.setText("Disconnected")
            self.system_tray_manager.update_tooltip(
                "Transmission QT Remote - Disconnected"
            )

    def set_timer_interval(self) -> None:
        """Set timer interval based on window minimization state and start if connected."""
        # Use appropriate interval based on window state
        interval = (
            self.minimized_refresh_interval_ms
            if self.windowState() & Qt.WindowMinimized
            else self.refresh_interval_ms
        )
        self.timer.setInterval(interval)
        if self.connection_manager.is_connected and not self.timer.isActive():
            self.timer.start()
        logger.info(
            f"Refresh interval set to {interval}ms ({'minimized' if self.windowState() & Qt.WindowMinimized else 'normal'} mode)"
        )

    def _toggle_connection(self) -> None:
        """Toggle connection state."""
        if self.connection_manager.is_connected:
            self.connection_manager.disconnect()
        else:
            self.connection_manager.auto_connect()

    def open_connection_settings(self) -> None:
        """Open connection settings dialog."""
        # TODO: Implement connection settings dialog
        QMessageBox.information(
            self,
            "Connection Settings",
            "Connection settings dialog not yet implemented.",
        )

    def showEvent(self, event: QShowEvent) -> None:
        """Handle window show event."""
        super().showEvent(event)
        # Attempt auto-connect after window is shown and Qt event loop is running
        QTimer.singleShot(100, self.connection_manager.attempt_auto_connect)

    def changeEvent(self, event: QEvent) -> None:
        """Handle window state changes like minimization/restoration."""
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.set_timer_interval()  # Switch to minimized refresh rate

    def _start_selected_torrent(self) -> None:
        """Start the currently selected torrent."""
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            torrent_id = selected_torrent["id"]
            self.start_torrent(torrent_id)

    def _force_start_selected_torrent(self) -> None:
        """Force start the currently selected torrent."""
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            torrent_id = selected_torrent["id"]
            self.force_start_torrent(torrent_id)

    def _pause_selected_torrent(self) -> None:
        """Pause the currently selected torrent."""
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            torrent_id = selected_torrent["id"]
            self.pause_torrent(torrent_id)

    def _verify_selected_torrent(self) -> None:
        """Verify the currently selected torrent."""
        selected_torrent = self.torrent_table.get_selected_torrent()
        if selected_torrent:
            torrent_id = selected_torrent["id"]
            self.verify_torrent(torrent_id)

    def start_torrent(self, torrent_id: int) -> None:
        """Start a torrent."""
        if self.api_client:
            self.api_client.start_torrent(torrent_id)

    def force_start_torrent(self, torrent_id: int) -> None:
        """Force start a torrent."""
        if self.api_client:
            self.api_client.force_start_torrent(torrent_id)

    def pause_torrent(self, torrent_id: int) -> None:
        """Pause a torrent."""
        if self.api_client:
            self.api_client.pause_torrent(torrent_id)

    def verify_torrent(self, torrent_id: int) -> None:
        """Verify torrent data."""
        if self.api_client:
            self.api_client.verify_torrent(torrent_id)

    def clear_filters(self) -> None:
        """Clear all filters."""
        self.search_box.clear()
        self.torrent_table.clear_filters()
        self.select_tracker("All")

    def select_tracker(self, tracker: str) -> None:
        """Select tracker filter."""
        self.torrent_table.filter_by_tracker(tracker)

    def update_tracker_buttons(self, torrents: List[Dict[str, Any]]) -> None:
        """Update tracker filter buttons."""
        self.torrent_table.update_tracker_options(torrents)

    def filter_table(self) -> None:
        """Filter the torrent table based on current criteria."""
        # This method is kept for backward compatibility
        # Filtering is now handled automatically via signals
        pass

    def set_theme(self, theme: str) -> None:
        """Set application theme."""
        self.current_theme = theme
        self.menu_bar_manager.set_current_theme(theme)
        self._apply_theme(theme)

    def _apply_theme(self, theme: str) -> None:
        """Apply the theme to the application."""
        # TODO: Implement actual theme switching
        logger.info(f"Theme changed to: {theme}")
