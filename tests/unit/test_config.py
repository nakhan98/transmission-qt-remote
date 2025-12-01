"""Unit tests for config.py module."""

import os
from unittest.mock import patch

from transmission_qt_remote import config


class TestConfig:
    """Test cases for configuration constants."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_transmission_url(self):
        """Test default Transmission URL when no env var is set."""
        # Reload the module to pick up new env vars
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_URL == "http://localhost:9091/transmission/rpc"

    @patch.dict(os.environ, {"TRANSMISSION_URL": "http://custom:9091/rpc"})
    def test_custom_transmission_url(self):
        """Test custom Transmission URL from environment."""
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_URL == "http://custom:9091/rpc"

    @patch.dict(os.environ, {"TRANSMISSION_USER": ""}, clear=False)
    def test_default_transmission_user(self):
        """Test default Transmission user when no env var is set."""
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_USER == ""

    @patch.dict(os.environ, {"TRANSMISSION_USER": "testuser"})
    def test_custom_transmission_user(self):
        """Test custom Transmission user from environment."""
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_USER == "testuser"

    @patch.dict(os.environ, {"TRANSMISSION_PASS": ""}, clear=False)
    def test_default_transmission_pass(self):
        """Test default Transmission password when no env var is set."""
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_PASS == ""

    @patch.dict(os.environ, {"TRANSMISSION_PASS": "secret123"})
    def test_custom_transmission_pass(self):
        """Test custom Transmission password from environment."""
        import importlib

        importlib.reload(config)

        assert config.TRANSMISSION_PASS == "secret123"

    def test_default_refresh_intervals(self):
        """Test default refresh interval constants."""
        assert config.DEFAULT_REFRESH_INTERVAL_MS == 5000
        assert config.DEFAULT_MINIMIZED_REFRESH_INTERVAL_MS == 30000

    def test_app_constants(self):
        """Test application constant values."""
        assert config.APP_NAME == "Transmission QT Remote"
        assert config.ICON_FILE == "./assets/black_t.svg"

    @patch.dict(os.environ, {}, clear=True)
    def test_default_ip2location_path(self):
        """Test default IP2Location database path."""
        import importlib

        importlib.reload(config)

        assert config.IP2LOCATION_DB_PATH == "./IP2LOCATION-LITE-DB1.BIN"

    @patch.dict(os.environ, {"IP2LOCATION_DB_PATH": "/custom/path/db.bin"})
    def test_custom_ip2location_path(self):
        """Test custom IP2Location database path from environment."""
        import importlib

        importlib.reload(config)

        assert config.IP2LOCATION_DB_PATH == "/custom/path/db.bin"
