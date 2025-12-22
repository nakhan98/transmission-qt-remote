"""Data models and enums for the Transmission QT Remote application."""

from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import QPushButton


@dataclass
class TableColumn:
    """Represents a column definition for the torrent table."""

    display_name: str
    field_name: str


class TorrentStatus(Enum):
    """Enum representing Transmission torrent status codes."""

    STOPPED = 0
    CHECK_PENDING = 1
    CHECKING = 2
    DOWNLOADING = 3
    DOWNLOAD_PENDING = 4
    SEED_PENDING = 5
    SEEDING = 6

    def display_text(self) -> str:
        """Convert status code to human-readable text."""
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
        """Initialize tracker button with hostname.

        Args:
            hostname: The hostname to display on the button.
        """
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
