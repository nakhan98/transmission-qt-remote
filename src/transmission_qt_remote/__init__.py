"""
TransmissionQtRemote

A graphical user interface for interacting with Transmission torrent servers.
Built with PySide6 for cross-platform compatibility.
"""

__version__ = "0.1.0"
__author__ = "Nasef Khan"
__email__ = "nakhan98@gmail.com"
__license__ = "GPL-3.0"

# Package exports for convenient importing
# Only import GUI components if PySide6 is available
try:
    from .main_window import TransmissionClient

    _HAS_QT = True
except ImportError:
    TransmissionClient = None
    _HAS_QT = False

from .transmission_client import (
    APP_NAME,
    ICON_FILE,
    extract_hostname,
    load_dotenv,
    logging,
)

# Conditionally include GUI components in exports
__all__ = [
    "APP_NAME",
    "ICON_FILE",
    "extract_hostname",
    "__version__",
    "__author__",
    "__license__",
]

if _HAS_QT:
    __all__.append("TransmissionClient")
