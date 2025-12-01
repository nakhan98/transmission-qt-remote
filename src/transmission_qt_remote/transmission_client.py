"""
TransmissionQtRemote

This application is a graphical user interface (GUI) for interacting with a
Transmission torrent server. Built using PySide6, it displays torrent details
such as name, status, size, and speeds in a table format. Users can toggle the
visibility of specific columns to customize their view. The application also
supports periodic data refreshes and integrates with the system tray for easy
access.

Environment variables:
- TRANSMISSION_URL: URL of the Transmission server (default: http://localhost:9091/transmission/rpc)
- TRANSMISSION_USER: Username for Transmission authentication
- TRANSMISSION_PASS: Password for Transmission authentication
"""

import logging
import os
import sys

from dotenv import load_dotenv

# qdarkstyle import removed - not used in this file

# Conditionally import Qt components
try:
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication

    _has_qt = True
except ImportError:
    QIcon = QPixmap = QApplication = None
    _has_qt = False

# Conditionally import Qt-dependent modules
if _has_qt:
    from .dialogs.torrent_detail import (
        TorrentDetailDialog,  # noqa: F401 - re-exported for backward compatibility
    )
    from .main_window import (  # noqa: F401 - re-exported for backward compatibility
        TrackerButton,
        TransmissionClient,
    )
else:
    TorrentDetailDialog = None
    TrackerButton = None
    TransmissionClient = None

from .dialogs.utils import (
    get_country_info,  # noqa: F401 - re-exported for backward compatibility
)

logging.basicConfig(
    level=logging.DEBUG,  # Set log level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Define log format
)

# Load environment variables
load_dotenv()

TRANSMISSION_URL = os.getenv(
    "TRANSMISSION_URL", "http://localhost:9091/transmission/rpc"
)
TRANSMISSION_USER = os.getenv("TRANSMISSION_USER", "")
TRANSMISSION_PASS = os.getenv("TRANSMISSION_PASS", "")
REFRESH_INTERVAL = 5000  # Default interval when the window is visible
MINIMIZED_REFRESH_INTERVAL = 30000  # Default interval when the window is minimized


# TODO: Are these 2 global variable still needed? I see them in config.py too
APP_NAME = "Transmission QT Remote"
ICON_FILE = "./black_t.svg"


def extract_hostname(url: str) -> str:
    """Extract hostname and port from a URL.

    Args:
        url: Full URL to parse

    Returns:
        The hostname with port (if present) from the URL
    """
    try:
        # Handle empty strings or None values
        if not url:
            return ""

        # Try to parse the URL
        if url.startswith("http"):
            # Standard HTTP URL
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            # Keep the port if present
            return parsed_url.netloc
        elif url.startswith("udp://"):
            # UDP URL - keep the host:port part
            parts = url[6:].split("/")
            hostname_port = parts[0]
            return hostname_port
        else:
            # For other protocols - try to get hostname:port
            if "/" in url:
                parts = url.split("/")
                if len(parts) > 2:
                    return parts[2]  # This will include port if present
            return url
    except Exception as e:
        logging.error(f"Error extracting hostname from {url}: {e}")
        return url


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(QPixmap(ICON_FILE)))
    client = TransmissionClient()
    client.show()
    sys.exit(app.exec())
