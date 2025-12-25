"""Torrent table widget for displaying and managing torrents."""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget

from ..models import TableColumn

logger = logging.getLogger(__name__)


class TorrentTableWidget(QTableWidget):
    """A table widget for displaying and managing torrents.

    This widget provides a comprehensive interface for torrent management including:
    - Display of torrent information in a tabular format
    - Text-based filtering of torrents
    - Tracker-based filtering
    - Selection management
    - Context menu support
    - Double-click handling

    Signals:
        torrent_double_clicked(torrent_id: int): Emitted when a torrent is double-clicked
        torrent_selection_changed(torrent_ids: List[int]): Emitted when selection changes
        torrent_context_menu_requested(torrent_id: int, position: QPoint): Emitted for context menu
    """

    # Signals emitted by the table widget
    torrent_double_clicked = Signal(int)  # torrent_id
    torrent_selection_changed = Signal(list)  # torrent_ids
    torrent_context_menu_requested = Signal(int, QPoint)  # torrent_id, global_position

    def __init__(self, columns: List[TableColumn], parent: Optional[QWidget] = None):
        """Initialize the torrent table widget.

        Args:
            columns: List of TableColumn definitions for the table
            parent: Parent widget
        """
        super().__init__(parent)

        self.columns = columns
        self.displayed_torrents: List[Dict[str, Any]] = []
        self.visible_columns: Dict[str, bool] = {
            col.display_name: True for col in self.columns
        }

        # Search and filter state
        self.search_text: str = ""
        self.active_tracker: Optional[str] = None
        self.active_trackers: List[str] = []

        self._setup_table()
        self._connect_signals()

    def _setup_table(self) -> None:
        """Set up the table widget configuration."""
        # Configure table properties
        self.setColumnCount(len(self.columns))
        self.setHorizontalHeaderLabels([col.display_name for col in self.columns])

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # Set selection behavior
        self.setSelectionBehavior(QTableWidget.SelectRows)

    def _connect_signals(self) -> None:
        """Connect widget signals to internal handlers."""
        self.doubleClicked.connect(self._on_double_clicked)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.customContextMenuRequested.connect(self._on_context_menu_requested)

    def update_torrents(self, torrents: List[Dict[str, Any]]) -> None:
        """Update the table with new torrent data.

        Args:
            torrents: List of torrent dictionaries from the API
        """
        logger.debug(f"Updating table with {len(torrents)} torrents")
        self.displayed_torrents = torrents.copy()
        self._update_table_display()

    def filter_by_text(self, text: str) -> None:
        """Filter torrents by search text.

        Args:
            text: Search text to filter by
        """
        self.search_text = text
        self._apply_filters()

    def filter_by_tracker(self, tracker: str) -> None:
        """Filter torrents by tracker.

        Args:
            tracker: Tracker URL to filter by, or "All" to show all
        """
        if tracker == "All":
            self.active_tracker = None
            self.active_trackers = []
        else:
            self.active_tracker = tracker
            self.active_trackers = [tracker]
        self._apply_filters()

    def clear_filters(self) -> None:
        """Clear all active filters."""
        self.search_text = ""
        self.active_tracker = None
        self.active_trackers = []
        self._apply_filters()

    def toggle_column_visibility(self, column_name: str, visible: bool) -> None:
        """Toggle visibility of a table column.

        Args:
            column_name: Name of the column to toggle
            visible: Whether the column should be visible
        """
        if column_name in self.visible_columns:
            self.visible_columns[column_name] = visible
            # Find column index and hide/show it
            for i, column in enumerate(self.columns):
                if column.display_name == column_name:
                    self.setColumnHidden(i, not visible)
                    break

    def get_selected_torrent_ids(self) -> List[int]:
        """Get IDs of currently selected torrents.

        Returns:
            List of torrent IDs that are currently selected
        """
        selected_ids = []
        for item in self.selectedItems():
            row = item.row()
            if row < len(self.displayed_torrents):
                torrent_id = self.displayed_torrents[row].get("id")
                if torrent_id is not None and torrent_id not in selected_ids:
                    selected_ids.append(torrent_id)
        return selected_ids

    def get_selected_torrent(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected torrent.

        Returns:
            Torrent dictionary if exactly one torrent is selected, None otherwise
        """
        selected_rows = set()
        for item in self.selectedItems():
            selected_rows.add(item.row())

        if len(selected_rows) == 1:
            row = list(selected_rows)[0]
            if row < len(self.displayed_torrents):
                return self.displayed_torrents[row]
        return None

    def update_tracker_options(self, torrents: List[Dict[str, Any]]) -> None:
        """Update available tracker filter options based on torrent data.

        Args:
            torrents: List of torrent dictionaries to extract trackers from
        """
        # Extract unique trackers from torrent data
        trackers = set()
        for torrent in torrents:
            for stat in torrent.get("trackerStats", []):
                announce_url = stat.get("announce", "")
                if announce_url:
                    trackers.add(announce_url)

        # Store tracker options for potential future use
        # (This could be used by a parent component to populate filter dropdowns)
        self.available_trackers = ["All"] + sorted(trackers)

    def _apply_filters(self) -> None:
        """Apply current filters to the table display."""
        for row in range(self.rowCount()):
            if row >= len(self.displayed_torrents):
                continue

            torrent = self.displayed_torrents[row]
            visible = self._torrent_matches_filters(torrent)
            self.setRowHidden(row, not visible)

    def _torrent_matches_filters(self, torrent: Dict[str, Any]) -> bool:
        """Check if a torrent matches the current filters.

        Args:
            torrent: Torrent dictionary to check

        Returns:
            True if torrent matches all active filters
        """
        # Text search filter
        text_match = True
        if self.search_text:
            torrent_name = torrent.get("name", "").lower()
            text_match = self.search_text.lower() in torrent_name

        # Tracker filter
        tracker_match = True
        if self.active_tracker or self.active_trackers:
            torrent_trackers = set()
            for stat in torrent.get("trackerStats", []):
                announce_url = stat.get("announce", "")
                if announce_url:
                    torrent_trackers.add(announce_url)

            # Check if any filter string is contained in any torrent tracker URL
            filter_strings = set()
            if self.active_tracker:
                filter_strings.add(self.active_tracker)
            filter_strings.update(self.active_trackers)

            tracker_match = any(
                any(filter_str in announce_url for announce_url in torrent_trackers)
                for filter_str in filter_strings
            )

        return text_match and tracker_match

    def _update_table_display(self) -> None:
        """Update the table display with current torrent data."""
        if not self.displayed_torrents:
            self.setRowCount(0)
            return

        # Clear existing content
        self.setRowCount(0)
        self.setRowCount(len(self.displayed_torrents))

        for row, torrent in enumerate(self.displayed_torrents):
            for col, column in enumerate(self.columns):
                # Get the value from torrent data
                value = torrent.get(column.field_name, "")

                # Format the value based on field type
                formatted_value = self._format_cell_value(
                    value, column.field_name, torrent
                )

                # Create table item
                item = QTableWidgetItem(str(formatted_value))
                self.setItem(row, col, item)

        # Resize columns to content
        self.resizeColumnsToContents()

    def _format_cell_value(
        self, value: Any, field_name: str, torrent: Dict[str, Any]
    ) -> str:
        """Format a cell value for display.

        Args:
            value: Raw value from torrent data
            field_name: Name of the field being formatted
            torrent: Full torrent dictionary for context

        Returns:
            Formatted string value for display
        """

        # Format based on field type
        if field_name == "totalSize" and value:
            # Convert bytes to MB
            try:
                return f"{value / (1024 * 1024):.1f}"
            except (TypeError, ValueError):
                return str(value)

        elif field_name in ["rateDownload", "rateUpload"] and value:
            # Convert bytes/s to KB/s
            try:
                return f"{value / 1024:.1f}"
            except (TypeError, ValueError):
                return str(value)

        elif field_name == "addedDate" and value:
            # Convert timestamp to readable date
            try:
                import time

                return time.strftime("%Y-%m-%d %H:%M", time.localtime(value))
            except (ValueError, OSError):
                return str(value)

        elif field_name == "percentDone" and isinstance(value, (int, float)):
            # Format as percentage
            return f"{value * 100:.1f}%"

        elif field_name in ["seeders", "leechers"]:
            # Always extract from tracker stats (overwrites any passed value)
            tracker_stats = torrent.get("trackerStats", [])
            if tracker_stats:
                if field_name == "seeders":
                    value = sum(stat.get("seederCount", 0) for stat in tracker_stats)
                else:  # leechers
                    value = sum(stat.get("leecherCount", 0) for stat in tracker_stats)
            else:
                value = 0
            return str(value)

        elif field_name == "status" and isinstance(value, int):
            # Convert status code to text
            from ..models import TorrentStatus

            try:
                status = TorrentStatus(value)
                return status.display_text()
            except ValueError:
                return "Unknown"

        elif not value:
            value = ""

        return str(value)

    def _on_double_clicked(self, item: QTableWidgetItem) -> None:
        """Handle double-click on table item.

        Args:
            item: The table item that was double-clicked
        """
        row = item.row()
        if row < len(self.displayed_torrents):
            torrent_id = self.displayed_torrents[row].get("id")
            if torrent_id is not None:
                logger.debug(f"Torrent double-clicked: ID {torrent_id}")
                self.torrent_double_clicked.emit(torrent_id)

    def _on_selection_changed(self) -> None:
        """Handle table selection changes."""
        selected_ids = self.get_selected_torrent_ids()
        logger.debug(f"Table selection changed: {len(selected_ids)} torrents selected")
        self.torrent_selection_changed.emit(selected_ids)

    def _on_context_menu_requested(self, position: QPoint) -> None:
        """Handle context menu request.

        Args:
            position: Local position where context menu was requested
        """
        # Find the torrent at the clicked position
        item = self.itemAt(position)
        if not item:
            return

        row = item.row()
        if row >= len(self.displayed_torrents):
            return

        torrent_id = self.displayed_torrents[row].get("id")
        if torrent_id is not None:
            global_position = self.mapToGlobal(position)
            logger.debug(f"Context menu requested for torrent ID {torrent_id}")
            self.torrent_context_menu_requested.emit(torrent_id, global_position)
