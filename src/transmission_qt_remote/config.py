"""
Configuration constants for TransmissionQtRemote.
"""

from typing import Final

from .config_manager import ConfigManager

# Global config manager instance
_config_manager = ConfigManager()

# Configuration constants with fallback defaults
TRANSMISSION_URL: Final[str] = _config_manager.get(
    "transmission_url", "http://localhost:9091/transmission/rpc"
)
TRANSMISSION_USER: Final[str] = _config_manager.get("transmission_user", "")
TRANSMISSION_PASS: Final[str] = _config_manager.get("transmission_pass", "")
DEFAULT_REFRESH_INTERVAL_MS: Final[int] = _config_manager.get(
    "default_refresh_interval_ms", 5000
)
DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS: Final[int] = _config_manager.get(
    "default_minimized_refresh_interval_ms", 30000
)
APP_NAME: Final[str] = "Transmission QT Remote"
ICON_FILE: Final[str] = "./assets/black_t.svg"
IP2LOCATION_DB_PATH: Final[str] = _config_manager.get(
    "ip2location_db_path", "./IP2LOCATION-LITE-DB1.BIN"
)

# Connection timeout (new setting)
CONNECTION_TIMEOUT_SEC: Final[int] = _config_manager.get("connection_timeout_sec", 5)


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    return _config_manager
