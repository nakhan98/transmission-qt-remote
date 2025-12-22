"""Torrent toolbar widget for managing torrent actions."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QToolBar, QWidget

from ..models import TorrentStatus


class TorrentToolbar(QToolBar):
    """A toolbar widget for torrent management actions.

    This toolbar provides buttons for common torrent operations like
    start, pause, force start, and delete. It emits signals when actions
    are triggered and can update button states based on torrent status.

    Signals:
        start_requested(): Emitted when start button is clicked
        force_start_requested(): Emitted when force start button is clicked
        pause_requested(): Emitted when pause button is clicked
        open_requested(): Emitted when open button is clicked
        delete_requested(): Emitted when delete button is clicked
    """

    # Signals emitted when toolbar actions are triggered
    start_requested = Signal()
    force_start_requested = Signal()
    pause_requested = Signal()
    open_requested = Signal()
    delete_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the torrent toolbar.

        Args:
            parent: Parent widget
        """
        super().__init__("Torrent Actions", parent)
        self.setObjectName("Torrent Actions")
        self.setMovable(False)
        self.setIconSize(self.iconSize())  # Use default icon size

        # Create actions
        self._create_actions()
        self._setup_toolbar()

    def _create_actions(self) -> None:
        """Create all toolbar actions."""
        # Open File button (far left, disabled for read-only client)
        self.open_action = QAction("Open", self)
        self.open_action.setIcon(QIcon.fromTheme("document-open"))
        self.open_action.setToolTip(
            "Open torrent file (not available in read-only client)"
        )
        self.open_action.setEnabled(False)  # Read-only client
        self.open_action.triggered.connect(self.open_requested)

        # Start button
        self.start_action = QAction("Start", self)
        self.start_action.setIcon(QIcon.fromTheme("media-playback-start"))
        self.start_action.setToolTip("Start torrent (Ctrl+S)")
        self.start_action.triggered.connect(self.start_requested)
        self.start_action.setEnabled(False)  # Initially disabled

        # Force Start button
        self.force_start_action = QAction("Force Start", self)
        self.force_start_action.setIcon(QIcon.fromTheme("media-seek-forward"))
        self.force_start_action.setToolTip("Force start torrent (Ctrl+Shift+S)")
        self.force_start_action.triggered.connect(self.force_start_requested)
        self.force_start_action.setEnabled(False)  # Initially disabled

        # Pause button
        self.pause_action = QAction("Pause", self)
        self.pause_action.setIcon(QIcon.fromTheme("media-playback-pause"))
        self.pause_action.setToolTip("Pause torrent (Ctrl+P)")
        self.pause_action.triggered.connect(self.pause_requested)
        self.pause_action.setEnabled(False)  # Initially disabled

        # Delete button (far right, disabled for read-only client)
        self.delete_action = QAction("Delete", self)
        self.delete_action.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_action.setToolTip(
            "Delete torrent (not available in read-only client)"
        )
        self.delete_action.setEnabled(False)  # Read-only client
        self.delete_action.triggered.connect(self.delete_requested)

    def _setup_toolbar(self) -> None:
        """Set up the toolbar layout and add actions."""
        # Add Open button (far left)
        self.addAction(self.open_action)

        # Add separator after Open button
        self.addSeparator()

        # Add Start button
        self.addAction(self.start_action)

        # Add Force Start button
        self.addAction(self.force_start_action)

        # Add Pause button
        self.addAction(self.pause_action)

        # Add separator before Delete button
        self.addSeparator()

        # Add Delete button (far right)
        self.addAction(self.delete_action)

    def update_actions(self, torrent_status: Optional[int]) -> None:
        """Update action enabled states based on torrent status.

        Args:
            torrent_status: Current status of the selected torrent (Transmission status code)
        """
        if torrent_status is None:
            # No torrent selected - disable all actions
            self.start_action.setEnabled(False)
            self.force_start_action.setEnabled(False)
            self.pause_action.setEnabled(False)
            return

        # Enable actions based on torrent status
        # Stopped (0), Download pending (4), Seed pending (5) -> can start
        can_start = torrent_status in [0, 4, 5]
        self.start_action.setEnabled(can_start)
        self.force_start_action.setEnabled(can_start)

        # Active torrents -> can pause
        can_pause = torrent_status not in [0, 4, 5]  # Not stopped/pending
        self.pause_action.setEnabled(can_pause)

    def enable_actions(self, enabled: bool) -> None:
        """Enable or disable all torrent actions.

        Args:
            enabled: Whether to enable or disable all actions
        """
        self.start_action.setEnabled(enabled)
        self.force_start_action.setEnabled(enabled)
        self.pause_action.setEnabled(enabled)
        # Note: open_action and delete_action remain disabled (read-only client)

    @staticmethod
    def can_start_torrent(status: int) -> bool:
        """Check if a torrent can be started based on its status.

        Args:
            status: Torrent status code

        Returns:
            True if the torrent can be started
        """
        return status in [
            TorrentStatus.STOPPED.value,
            TorrentStatus.DOWNLOAD_PENDING.value,
            TorrentStatus.SEED_PENDING.value,
        ]

    @staticmethod
    def can_pause_torrent(status: int) -> bool:
        """Check if a torrent can be paused based on its status.

        Args:
            status: Torrent status code

        Returns:
            True if the torrent can be paused
        """
        return status not in [
            TorrentStatus.STOPPED.value,
            TorrentStatus.DOWNLOAD_PENDING.value,
            TorrentStatus.SEED_PENDING.value,
        ]
