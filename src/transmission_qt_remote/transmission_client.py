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
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# qdarkstyle import removed - not used in this file

# Conditionally import Qt components
try:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    _has_qt = True
except ImportError:
    QIcon = QApplication = None
    _has_qt = False

# Conditionally import Qt-dependent modules
if _has_qt:
    from .dialogs.torrent_detail import (
        TorrentDetailDialog,  # type: ignore  # noqa: F401 - re-exported for backward compatibility
    )
    from .main_window import (  # type: ignore  # noqa: F401 - re-exported for backward compatibility
        TransmissionClient,
    )
    from .models import TrackerButton  # type: ignore
else:
    TorrentDetailDialog = None
    TrackerButton = None
    TransmissionClient = None

from .config import APP_NAME, ICON_FILE
from .dialogs.utils import (
    get_country_info,  # type: ignore  # noqa: F401 - re-exported for backward compatibility
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


def _resolve_icon_path(icon_file: str) -> Optional[str]:
    """Resolve the icon path across editable and installed environments."""
    candidate = Path(icon_file)
    candidate_paths = [candidate]

    if not candidate.is_absolute():
        candidate_paths.append(Path.cwd() / candidate)
        module_path = Path(__file__).resolve()
        for parent in module_path.parents:
            candidate_paths.append(parent / candidate)

    for path in candidate_paths:
        if path.exists():
            return str(path)

    logging.warning("Icon file %s not found; using default Qt icon", icon_file)
    return None


ICON_PATH = _resolve_icon_path(ICON_FILE)


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
    app = QApplication(sys.argv)  # type: ignore[union-attr]
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("TransmissionQtRemote")
    app.setOrganizationDomain("transmissionqtremote.dev")

    icon = QIcon(ICON_PATH) if ICON_PATH and QIcon is not None else None
    if icon is not None and not icon.isNull():
        app.setWindowIcon(icon)

    client = TransmissionClient()  # type: ignore[union-attr]
    if icon is not None and not icon.isNull():
        client.setWindowIcon(icon)
    client.show()  # type: ignore[union-attr]
    sys.exit(app.exec())  # type: ignore[union-attr]
