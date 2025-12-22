"""Tests for torrent_table module."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint

from src.transmission_qt_remote.models import TableColumn
from src.transmission_qt_remote.ui.torrent_table import TorrentTableWidget


class TestTorrentTableWidget:
    """Test cases for TorrentTableWidget."""

    @pytest.fixture
    def columns(self):
        """Create test table columns."""
        return [
            TableColumn("Name", "name"),
            TableColumn("Status", "status"),
            TableColumn("Size (MB)", "totalSize"),
            TableColumn("Progress", "percentDone"),
        ]

    @pytest.fixture
    def torrent_table(self, columns):
        """Create a TorrentTableWidget instance."""
        return TorrentTableWidget(columns)

    @pytest.fixture
    def sample_torrents(self):
        """Create sample torrent data for testing."""
        return [
            {
                "id": 1,
                "name": "Ubuntu ISO",
                "status": 3,  # Downloading
                "totalSize": 1073741824,  # 1 GB
                "percentDone": 0.5,
                "rateDownload": 102400,  # 100 KB/s
                "addedDate": 1609459200,  # 2021-01-01
                "trackerStats": [
                    {
                        "announce": "http://tracker1.com",
                        "seederCount": 10,
                        "leecherCount": 5,
                    }
                ],
            },
            {
                "id": 2,
                "name": "Fedora ISO",
                "status": 6,  # Seeding
                "totalSize": 2147483648,  # 2 GB
                "percentDone": 1.0,
                "rateUpload": 51200,  # 50 KB/s
                "addedDate": 1609545600,  # 2021-01-02
                "trackerStats": [
                    {
                        "announce": "http://tracker2.com",
                        "seederCount": 20,
                        "leecherCount": 2,
                    }
                ],
            },
        ]

    def test_init(self, torrent_table, columns):
        """Test TorrentTableWidget initialization."""
        assert torrent_table.columns == columns
        assert torrent_table.displayed_torrents == []
        assert torrent_table.search_text == ""
        assert torrent_table.active_tracker is None
        assert torrent_table.active_trackers == []
        assert torrent_table.rowCount() == 0
        assert torrent_table.columnCount() == len(columns)

    def test_update_torrents(self, torrent_table, sample_torrents):
        """Test updating torrents in the table."""
        torrent_table.update_torrents(sample_torrents)

        assert torrent_table.displayed_torrents == sample_torrents
        assert torrent_table.rowCount() == 2
        assert torrent_table.columnCount() == 4

        # Check first row values
        assert torrent_table.item(0, 0).text() == "Ubuntu ISO"
        assert torrent_table.item(0, 1).text() == "Downloading"
        assert torrent_table.item(0, 2).text() == "1024.0"  # 1 GB in MB
        assert torrent_table.item(0, 3).text() == "50.0%"  # 0.5 * 100

    def test_filter_by_text(self, torrent_table, sample_torrents):
        """Test text-based filtering."""
        torrent_table.update_torrents(sample_torrents)

        # Filter for "Ubuntu"
        torrent_table.filter_by_text("Ubuntu")

        # First row should be visible, second hidden
        assert not torrent_table.isRowHidden(0)
        assert torrent_table.isRowHidden(1)

    def test_filter_by_text_case_insensitive(self, torrent_table, sample_torrents):
        """Test case-insensitive text filtering."""
        torrent_table.update_torrents(sample_torrents)

        # Filter for "ubuntu" (lowercase)
        torrent_table.filter_by_text("ubuntu")

        # First row should be visible
        assert not torrent_table.isRowHidden(0)

    def test_filter_by_tracker(self, torrent_table, sample_torrents):
        """Test tracker-based filtering."""
        torrent_table.update_torrents(sample_torrents)

        # Filter by tracker1
        torrent_table.filter_by_tracker("http://tracker1.com")

        # First row should be visible, second hidden
        assert not torrent_table.isRowHidden(0)
        assert torrent_table.isRowHidden(1)

    def test_filter_by_tracker_all(self, torrent_table, sample_torrents):
        """Test showing all torrents when filter is 'All'."""
        torrent_table.update_torrents(sample_torrents)
        torrent_table.filter_by_tracker("http://tracker1.com")  # Hide second row

        # Now show all
        torrent_table.filter_by_tracker("All")

        # Both rows should be visible
        assert not torrent_table.isRowHidden(0)
        assert not torrent_table.isRowHidden(1)

    def test_clear_filters(self, torrent_table, sample_torrents):
        """Test clearing all filters."""
        torrent_table.update_torrents(sample_torrents)
        torrent_table.filter_by_text("Ubuntu")
        torrent_table.filter_by_tracker("http://tracker1.com")

        torrent_table.clear_filters()

        # Both rows should be visible
        assert not torrent_table.isRowHidden(0)
        assert not torrent_table.isRowHidden(1)
        assert torrent_table.search_text == ""
        assert torrent_table.active_tracker is None

    def test_combined_filters(self, torrent_table, sample_torrents):
        """Test combining text and tracker filters."""
        torrent_table.update_torrents(sample_torrents)

        # Filter for "ISO" (matches both) but tracker1 (only first)
        torrent_table.filter_by_text("ISO")
        torrent_table.filter_by_tracker("http://tracker1.com")

        # Only first row should match both filters
        assert not torrent_table.isRowHidden(0)
        assert torrent_table.isRowHidden(1)

    def test_toggle_column_visibility(self, torrent_table):
        """Test toggling column visibility."""
        # Hide the "Status" column
        torrent_table.toggle_column_visibility("Status", False)

        # Find the Status column index (should be 1)
        status_column_index = None
        for i, col in enumerate(torrent_table.columns):
            if col.display_name == "Status":
                status_column_index = i
                break

        assert status_column_index == 1
        assert torrent_table.isColumnHidden(status_column_index)

        # Show it again
        torrent_table.toggle_column_visibility("Status", True)
        assert not torrent_table.isColumnHidden(status_column_index)

    def test_get_selected_torrent_ids(self, torrent_table, sample_torrents, qtbot):
        """Test getting selected torrent IDs."""
        torrent_table.update_torrents(sample_torrents)

        # Select first row
        torrent_table.selectRow(0)

        selected_ids = torrent_table.get_selected_torrent_ids()
        assert selected_ids == [1]

    def test_get_selected_torrent_single(self, torrent_table, sample_torrents):
        """Test getting single selected torrent."""
        torrent_table.update_torrents(sample_torrents)

        # Select first row
        torrent_table.selectRow(0)

        selected_torrent = torrent_table.get_selected_torrent()
        assert selected_torrent == sample_torrents[0]

    def test_get_selected_torrent_multiple(self, torrent_table, sample_torrents):
        """Test getting selected torrent when multiple are selected."""
        torrent_table.update_torrents(sample_torrents)

        # Select both rows using setSelectionMode to allow multiple selection
        from PySide6.QtWidgets import QTableWidget

        torrent_table.setSelectionMode(QTableWidget.MultiSelection)

        torrent_table.selectRow(0)
        torrent_table.selectRow(1)

        selected_torrent = torrent_table.get_selected_torrent()
        assert selected_torrent is None  # Should return None for multiple selection

    def test_get_selected_torrent_none(self, torrent_table, sample_torrents):
        """Test getting selected torrent when nothing is selected."""
        torrent_table.update_torrents(sample_torrents)

        selected_torrent = torrent_table.get_selected_torrent()
        assert selected_torrent is None

    def test_update_tracker_options(self, torrent_table, sample_torrents):
        """Test updating tracker options from torrent data."""
        torrent_table.update_tracker_options(sample_torrents)

        # Should have extracted trackers
        assert hasattr(torrent_table, "available_trackers")
        assert "All" in torrent_table.available_trackers
        assert "http://tracker1.com" in torrent_table.available_trackers
        assert "http://tracker2.com" in torrent_table.available_trackers

    def test_format_cell_value_total_size(self, torrent_table):
        """Test formatting total size values."""
        torrent = {"totalSize": 1073741824}  # 1 GB
        formatted = torrent_table._format_cell_value(1073741824, "totalSize", torrent)
        assert formatted == "1024.0"

    def test_format_cell_value_rates(self, torrent_table):
        """Test formatting download/upload rate values."""
        torrent = {}
        formatted = torrent_table._format_cell_value(
            102400, "rateDownload", torrent
        )  # 100 KB/s
        assert formatted == "100.0"

    def test_format_cell_value_percentage(self, torrent_table):
        """Test formatting percentage values."""
        torrent = {}
        formatted = torrent_table._format_cell_value(0.75, "percentDone", torrent)
        assert formatted == "75.0%"

    def test_format_cell_value_date(self, torrent_table):
        """Test formatting date values."""
        timestamp = 1609459200  # 2021-01-01 00:00:00 UTC
        torrent = {}
        formatted = torrent_table._format_cell_value(timestamp, "addedDate", torrent)
        # Should be formatted as date (exact format depends on local timezone)
        assert "2021" in formatted
        assert ":" in formatted  # Should contain time

    def test_format_cell_value_seeders_leechers(self, torrent_table):
        """Test formatting seeder/leecher counts from tracker stats."""
        torrent = {
            "trackerStats": [
                {"seederCount": 10, "leecherCount": 5},
                {"seederCount": 5, "leecherCount": 3},
            ]
        }

        seeders = torrent_table._format_cell_value(None, "seeders", torrent)
        leechers = torrent_table._format_cell_value(None, "leechers", torrent)

        assert seeders == "15"  # 10 + 5
        assert leechers == "8"  # 5 + 3

    def test_format_cell_value_status(self, torrent_table):
        """Test formatting status code values."""
        torrent = {}
        formatted = torrent_table._format_cell_value(3, "status", torrent)
        assert formatted == "Downloading"

    def test_signals_emitted(self, torrent_table, sample_torrents, qtbot):
        """Test that signals are emitted correctly."""
        torrent_table.update_torrents(sample_torrents)

        # Test double-click signal
        with qtbot.waitSignal(torrent_table.torrent_double_clicked) as blocker:
            # Simulate double-click on first row
            item = torrent_table.item(0, 0)  # First cell of first row
            torrent_table._on_double_clicked(item)

        assert blocker.args == [1]  # Should emit torrent ID 1

        # Test selection changed signal
        with qtbot.waitSignal(torrent_table.torrent_selection_changed) as blocker:
            torrent_table.selectRow(0)

        assert blocker.args == [[1]]  # Should emit list with torrent ID 1

        # Test context menu signal
        with qtbot.waitSignal(torrent_table.torrent_context_menu_requested) as blocker:
            # Simulate right-click on first row
            position = QPoint(10, 10)
            torrent_table._on_context_menu_requested(position)

        assert blocker.args[0] == 1  # First arg should be torrent ID 1
        assert isinstance(blocker.args[1], QPoint)  # Second arg should be QPoint

    def test_empty_table_handling(self, torrent_table):
        """Test behavior with empty torrent list."""
        torrent_table.update_torrents([])

        assert torrent_table.rowCount() == 0
        assert torrent_table.displayed_torrents == []

    def test_invalid_row_access(self, torrent_table, sample_torrents):
        """Test handling of invalid row access."""
        torrent_table.update_torrents(sample_torrents)

        # Test double-click on invalid row
        mock_item = MagicMock()
        mock_item.row.return_value = 999  # Invalid row

        # Should not crash or emit signal
        torrent_table._on_double_clicked(mock_item)
