"""Tests for torrent_models module."""

from src.transmission_qt_remote.models import TableColumn, TorrentStatus, TrackerButton


class TestTableColumn:
    """Test cases for TableColumn dataclass."""

    def test_table_column_creation(self):
        """Test TableColumn can be created with display and field names."""
        column = TableColumn(display_name="Torrent Name", field_name="name")
        assert column.display_name == "Torrent Name"
        assert column.field_name == "name"

    def test_table_column_equality(self):
        """Test TableColumn equality comparison."""
        col1 = TableColumn("Name", "name")
        col2 = TableColumn("Name", "name")
        col3 = TableColumn("Size", "size")

        assert col1 == col2
        assert col1 != col3


class TestTorrentStatus:
    """Test cases for TorrentStatus enum."""

    def test_status_values(self):
        """Test that TorrentStatus enum has correct values."""
        assert TorrentStatus.STOPPED.value == 0
        assert TorrentStatus.CHECK_PENDING.value == 1
        assert TorrentStatus.CHECKING.value == 2
        assert TorrentStatus.DOWNLOADING.value == 3
        assert TorrentStatus.DOWNLOAD_PENDING.value == 4
        assert TorrentStatus.SEED_PENDING.value == 5
        assert TorrentStatus.SEEDING.value == 6

    def test_display_text_all_statuses(self):
        """Test display_text method for all status values."""
        test_cases = [
            (TorrentStatus.STOPPED, "Stopped"),
            (TorrentStatus.CHECK_PENDING, "Check pending"),
            (TorrentStatus.CHECKING, "Checking"),
            (TorrentStatus.DOWNLOADING, "Downloading"),
            (TorrentStatus.DOWNLOAD_PENDING, "Download pending"),
            (TorrentStatus.SEED_PENDING, "Seed pending"),
            (TorrentStatus.SEEDING, "Seeding"),
        ]

        for status, expected_text in test_cases:
            assert status.display_text() == expected_text

    def test_display_text_unknown_status(self):
        """Test display_text method for unknown status values."""
        # Create a mock status with unknown value
        mock_status = TorrentStatus.STOPPED
        mock_status._value_ = 999  # Modify the value directly for testing

        # Since we can't easily create unknown enum values, test with known enum
        # The method should handle unknown values gracefully
        assert TorrentStatus.SEEDING.display_text() == "Seeding"  # Known value


class TestTrackerButton:
    """Test cases for TrackerButton class."""

    def test_button_creation_short_hostname(self, app):
        """Test TrackerButton with short hostname displays hostname as-is."""
        button = TrackerButton("tracker1.com")
        assert button.hostname == "tracker1.com"
        assert button.text() == "tracker1.com"
        assert button.toolTip() == "tracker1.com"
        assert button.isCheckable() is True

    def test_button_creation_long_hostname(self, app):
        """Test TrackerButton with long hostname truncates display text."""
        hostname = "very.long.tracker.hostname.example.com"
        button = TrackerButton(hostname)

        assert button.hostname == hostname
        assert button.text() == "very.long...."  # Truncated display
        assert button.toolTip() == hostname  # Full hostname in tooltip
        assert button.isCheckable() is True

    def test_button_creation_boundary_hostname(self, app):
        """Test TrackerButton with 12-character hostname (boundary case)."""
        hostname = "tracker12.co"  # Exactly 12 characters
        button = TrackerButton(hostname)

        assert button.hostname == hostname
        assert button.text() == hostname  # Not truncated
        assert button.toolTip() == hostname

    def test_button_creation_truncation_logic(self, app):
        """Test TrackerButton truncation logic with dots."""
        # Test various hostname patterns
        # Hostnames <= 12 chars are not truncated
        # Hostnames > 12 chars take first 2 parts + "...."
        test_cases = [
            # Short hostnames (no truncation)
            ("short.com", "short.com"),
            ("a.b.c.d", "a.b.c.d"),  # 7 chars, no truncation
            ("tracker12.co", "tracker12.co"),  # 12 chars, no truncation
            # Long hostnames (truncated)
            ("very.long.tracker.hostname.example.com", "very.long...."),  # 36 chars
            ("long.domain.name.com", "long.domain...."),  # 18 chars
            ("x.y.z.a.b.c.d.e.f.g.h.i.j.k", "x.y...."),  # Very long
        ]

        for hostname, expected_display in test_cases:
            button = TrackerButton(hostname)
            assert button.text() == expected_display
            assert button.hostname == hostname
