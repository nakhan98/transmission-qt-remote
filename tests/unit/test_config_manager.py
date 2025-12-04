"""
Unit tests for config_manager.py
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from transmission_qt_remote.config_manager import ConfigError, ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager class."""

    def test_init_no_config_file(self):
        """Test initialization when no config file exists."""
        with patch(
            "transmission_qt_remote.config_manager.ConfigManager._get_config_search_paths",
            return_value=[],
        ):
            manager = ConfigManager()
            assert manager._config == {}
            assert manager._config_file_path is None

    def test_get_config_search_paths(self):
        """Test config search path generation."""
        manager = ConfigManager()
        paths = manager._get_config_search_paths()

        # Should have at least project directory
        assert len(paths) >= 1
        assert paths[0] == Path.cwd()

        # Should include XDG config directory if set
        if os.getenv("XDG_CONFIG_HOME"):
            assert any("transmission_qt_remote" in str(p) for p in paths)

    def test_find_config_file_priority(self):
        """Test config file discovery with priority."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create config files in different locations
            project_config = temp_path / "config.json"
            project_config.write_text('{"test": "project"}')

            xdg_dir = temp_path / "xdg" / "transmission_test_qt_client"
            xdg_dir.mkdir(parents=True)
            xdg_config = xdg_dir / "config.json"
            xdg_config.write_text('{"test": "xdg"}')

            with patch(
                "transmission_qt_remote.config_manager.ConfigManager._get_config_search_paths",
                return_value=[temp_path, xdg_dir],
            ):
                manager = ConfigManager()
                found_file = manager._find_config_file()
                assert found_file == project_config  # Project dir has priority

    def test_find_config_file_multiple_types_error(self):
        """Test error when multiple config file types exist in same location."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple config file types in same directory
            (temp_path / "config.json").write_text("{}")
            (temp_path / "config.yaml").write_text("{}")

            with patch(
                "transmission_qt_remote.config_manager.ConfigManager._get_config_search_paths",
                return_value=[temp_path],
            ):
                manager = ConfigManager()
                with pytest.raises(ConfigError, match="Multiple config file types"):
                    manager._find_config_file()

    def test_load_config_file_json(self):
        """Test loading JSON config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            test_data = {"transmission_url": "http://test.com", "timeout": 30}
            config_file.write_text(json.dumps(test_data))

            manager = ConfigManager()
            loaded = manager._load_config_file(config_file)
            assert loaded == test_data

    def test_load_config_file_yaml(self):
        """Test loading YAML config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.yaml"
            test_data = {"transmission_url": "http://test.com", "timeout": 30}
            config_file.write_text(yaml.dump(test_data))

            manager = ConfigManager()
            loaded = manager._load_config_file(config_file)
            assert loaded == test_data

    def test_load_config_file_jsonc(self):
        """Test loading JSONC config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.jsonc"
            config_content = """
            {
                "transmission_url": "http://test.com", // comment
                "timeout": 30
            }
            """
            config_file.write_text(config_content)

            manager = ConfigManager()
            loaded = manager._load_config_file(config_file)
            assert loaded["transmission_url"] == "http://test.com"
            assert loaded["timeout"] == 30

    def test_load_config_file_invalid(self):
        """Test loading invalid config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"
            config_file.write_text("invalid json {")

            manager = ConfigManager()
            with pytest.raises(ConfigError, match="Failed to parse"):
                manager._load_config_file(config_file)

    def test_get_with_config_file(self):
        """Test getting values when config file exists."""
        test_config = {"transmission_url": "http://test.com", "timeout": 30}

        with patch.object(ConfigManager, "_load_config_file", return_value=test_config):
            with patch.object(
                ConfigManager, "_find_config_file", return_value=Path("test.json")
            ):
                manager = ConfigManager()
                assert manager.get("transmission_url") == "http://test.com"
                assert manager.get("timeout") == 30
                assert manager.get("nonexistent", "default") == "default"

    def test_get_fallback_to_env(self):
        """Test fallback to environment variables."""
        with patch.dict(os.environ, {"TEST_VAR": "env_value", "NUM_VAR": "42"}):
            with patch(
                "transmission_qt_remote.config_manager.ConfigManager._find_config_file",
                return_value=None,
            ):
                manager = ConfigManager()
                assert manager.get("test_var") == "env_value"
                assert manager.get("num_var") == 42
                assert manager.get("bool_var", False) is False

    def test_set_and_save(self):
        """Test setting values and saving to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.json"

            manager = ConfigManager()
            manager._config_file_path = config_file

            manager.set("test_key", "test_value")
            manager.set("number", 42)

            manager.save()

            # Verify file was written
            assert config_file.exists()
            with open(config_file) as f:
                saved_data = json.load(f)

            assert saved_data["test_key"] == "test_value"
            assert saved_data["number"] == 42

    def test_save_error(self):
        """Test save error handling."""
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            manager = ConfigManager()
            manager._config_file_path = Path("/invalid/path/config.json")

            with pytest.raises(ConfigError, match="Failed to save"):
                manager.save()

    def test_reload(self):
        """Test config reloading."""
        call_count = 0

        def mock_load(self):
            nonlocal call_count
            call_count += 1
            self._config = {"call": call_count}

        with patch.object(ConfigManager, "_load_config", mock_load):
            manager = ConfigManager()
            assert manager._config["call"] == 1

            manager.reload()
            assert manager._config["call"] == 2

    def test_get_auto_connect_enabled_default(self):
        """Test getting auto-connect enabled with default value."""
        from unittest.mock import patch

        # Mock to prevent loading real config file
        with patch.object(ConfigManager, "_find_config_file", return_value=None):
            cm = ConfigManager()
            assert cm.get_auto_connect_enabled() is False

    def test_set_auto_connect_enabled(self):
        """Test setting auto-connect enabled."""
        cm = ConfigManager()
        cm.set_auto_connect_enabled(True)
        assert cm.get_auto_connect_enabled() is True

        cm.set_auto_connect_enabled(False)
        assert cm.get_auto_connect_enabled() is False

    def test_get_last_connected_server_name_default(self):
        """Test getting last connected server name with default value."""
        from unittest.mock import patch

        # Mock to prevent loading real config file
        with patch.object(ConfigManager, "_find_config_file", return_value=None):
            cm = ConfigManager()
            assert cm.get_last_connected_server_name() is None

    def test_set_last_connected_server_name(self):
        """Test setting last connected server name."""
        cm = ConfigManager()
        cm.set_last_connected_server_name("My Server")
        assert cm.get_last_connected_server_name() == "My Server"

        cm.set_last_connected_server_name(None)
        assert cm.get_last_connected_server_name() is None
