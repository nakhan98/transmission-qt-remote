import logging
import os
from typing import Tuple

try:
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtWidgets import QStyledItemDelegate, QToolTip

    _has_qt = True
except ImportError:
    QEvent = Qt = QStyledItemDelegate = QToolTip = None
    _has_qt = False

# qdarkstyle import removed - not used in this file

from IP2Location import database as ip2location

# Path to IP2Location database - this should be downloaded separately
IP2LOCATION_DB_PATH = os.getenv("IP2LOCATION_DB_PATH", "./IP2LOCATION-LITE-DB1.BIN")

# Initialize IP2Location database
ip2location_db = None
try:
    if os.path.exists(IP2LOCATION_DB_PATH):
        logging.info(f"Initializing IP2Location database from: {IP2LOCATION_DB_PATH}")
        logging.info(
            f"Database file size: {os.path.getsize(IP2LOCATION_DB_PATH)} bytes"
        )

        # Create the IP2Location object with the database file
        ip2location_db = ip2location.IP2Location()
        ip2location_db.open(IP2LOCATION_DB_PATH)

        # Test lookup with a known IP address (Google DNS)
        test_ip = "8.8.8.8"
        test_record = ip2location_db.get_all(test_ip)
        logging.info(
            f"Test lookup for {test_ip}: {test_record.country_short}, {test_record.country_long}"
        )

        # Add a direct test for the specific IP mentioned
        test_ip2 = "93.230.115.183"
        test_record2 = ip2location_db.get_all(test_ip2)
        logging.info(
            f"Test lookup for {test_ip2}: {test_record2.country_short}, {test_record2.country_long}"
        )
    else:
        logging.warning(f"IP2Location database not found at {IP2LOCATION_DB_PATH}")
except Exception as e:
    logging.error(f"Error initializing IP2Location database: {e}", exc_info=True)


# Custom Delegate for showing tooltips on table cells
if _has_qt:

    class TooltipDelegate(QStyledItemDelegate):
        def __init__(self, parent=None):
            super().__init__(parent)

        def helpEvent(self, event, view, option, index):
            if not event or not view:
                return False

            if event.type() == QEvent.ToolTip:
                tooltip = index.data(Qt.ToolTipRole)
                if tooltip:
                    QToolTip.showText(event.globalPos(), tooltip, view)
                    return True

            return super().helpEvent(event, view, option, index)
else:
    TooltipDelegate = None


# Function to get country code from IP address
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


def get_country_info(ip_address: str) -> Tuple[str, str]:
    """Get country code and name for an IP address using IP2Location.

    Args:
        ip_address: The IP address to look up

    Returns:
        A tuple containing (country_code, country_name)
        If the country is unknown, returns ("??", "Unknown")
    """
    # Skip local/private IPs
    if ip_address.startswith(("10.", "172.", "192.168.", "127.", "::1", "fc00:", "fd")):
        return ("--", "Local Network")

    try:
        # Try to lookup the IP if database is initialized
        if ip2location_db:
            # Add debug logging
            logging.debug(f"Looking up country for IP: {ip_address}")

            # Get the record from IP2Location
            record = ip2location_db.get_all(ip_address)

            # Log the record details for debugging
            if record:
                logging.debug(
                    f"IP2Location record: country_short={record.country_short}, country_long={record.country_long}"
                )

                # Check if we got a valid country code
                if record.country_short and record.country_short != "-":
                    return (record.country_short, record.country_long or "Unknown")

        # Return unknown if database isn't available or lookup failed
        logging.debug(f"No valid country found for IP: {ip_address}")
        return ("??", "Unknown (IP2Location DB not found or lookup failed)")

    except Exception as e:
        logging.debug(f"Could not determine country for IP {ip_address}: {e}")
        return ("??", "Unknown")
