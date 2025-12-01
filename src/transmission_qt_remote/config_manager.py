"""
Configuration manager for TransmissionQtRemote.

Supports loading configuration from JSON, JSONC, or YAML files with priority:
1. Project directory config files
2. XDG_HOME/<app_name>/ config files
3. Environment variables (fallback)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import commentjson
import yaml

# Avoid circular import by defining APP_NAME locally
APP_NAME = "Transmission QT Remote"

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when there's an error with configuration files."""

    pass


class ConfigManager:
    """Manages application configuration from files and environment variables."""

    SUPPORTED_EXTENSIONS = {".json", ".jsonc", ".yaml", ".yml"}

    def __init__(self) -> None:  # type: ignore[reportMissingSuperCall]
        self._config: Dict[str, Any] = {}
        self._config_file_path: Optional[Path] = None
        self._load_config()

    def _get_config_search_paths(self) -> List[Path]:
        """Get list of directories to search for config files, in priority order."""
        paths = []

        # Project directory (highest priority)
        project_dir = Path.cwd()
        paths.append(project_dir)

        # XDG config directory
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            paths.append(Path(xdg_config_home) / APP_NAME.lower().replace(" ", "_"))
        else:
            # Fallback to ~/.config/<app_name>
            home = Path.home()
            paths.append(home / ".config" / APP_NAME.lower().replace(" ", "_"))

        return paths

    def _find_config_file(self) -> Optional[Path]:
        """Find the config file to use, following priority rules."""
        for search_path in self._get_config_search_paths():
            if not search_path.exists():
                continue

            config_files = []
            for ext in self.SUPPORTED_EXTENSIONS:
                config_file = search_path / f"config{ext}"
                if config_file.exists():
                    config_files.append(config_file)

            if len(config_files) > 1:
                raise ConfigError(
                    f"Multiple config file types found in {search_path}: {[f.name for f in config_files]}. Please use only one type."
                )
            elif len(config_files) == 1:
                return config_files[0]

        return None

    def _load_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from a file."""
        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()

            if config_path.suffix in {".yaml", ".yml"}:
                return yaml.safe_load(content) or {}
            elif config_path.suffix == ".jsonc":
                return commentjson.loads(content) or {}
            else:  # .json
                return json.loads(content) or {}

        except (
            json.JSONDecodeError,
            yaml.YAMLError,
            commentjson.JSONLibraryException,
        ) as e:
            raise ConfigError(f"Failed to parse config file {config_path}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read config file {config_path}: {e}") from e

    def _load_config(self) -> None:
        """Load configuration from file and merge with defaults."""
        try:
            config_file = self._find_config_file()
            if config_file:
                self._config = self._load_config_file(config_file)
                self._config_file_path = config_file
                logger.info("Loaded configuration from %s", config_file)
            else:
                self._config = {}
                logger.info(
                    "No config file found, using defaults and environment variables"
                )
        except ConfigError as e:
            logger.error("Configuration error: %s", e)
            # Continue with empty config, will fall back to environment variables
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value, falling back to environment variables."""
        # First check config file
        if key in self._config:
            return self._config[key]

        # Fall back to environment variable
        env_key = key.upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            # Try to convert string values to appropriate types
            if env_value.lower() in ("true", "false"):
                return env_value.lower() == "true"
            try:
                # Try to parse as number
                if "." in env_value:
                    return float(env_value)
                return int(env_value)
            except ValueError:
                return env_value

        return default

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value in memory."""
        self._config[key] = value

    def save(self) -> None:
        """Save current configuration to file."""
        if not self._config_file_path:
            # Default to project directory config.json
            self._config_file_path = Path.cwd() / "config.json"

        try:
            # Ensure directory exists
            self._config_file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)

            logger.info("Saved configuration to %s", self._config_file_path)

        except OSError as e:
            raise ConfigError(
                f"Failed to save config file {self._config_file_path}: {e}"
            ) from e

    @property
    def config_file_path(self) -> Optional[Path]:
        """Get the path to the current config file."""
        return self._config_file_path

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()

    def get_servers(self) -> List[Dict[str, Any]]:
        """Get list of configured servers."""
        return self._config.get("servers", [])

    def set_servers(self, servers: List[Dict[str, Any]]) -> None:
        """Set the list of configured servers."""
        self._config["servers"] = servers
        self.save()

    def add_server(self, server: Dict[str, Any]) -> None:
        """Add a server configuration."""
        servers = self.get_servers()
        servers.append(server)
        self.set_servers(servers)

    def remove_server(self, server_name: str) -> bool:
        """Remove a server configuration by name."""
        servers = self.get_servers()
        for i, server in enumerate(servers):
            if server.get("name") == server_name:
                servers.pop(i)
                self.set_servers(servers)
                return True
        return False

    def update_server(self, server_name: str, updated_server: Dict[str, Any]) -> bool:
        """Update a server configuration by name."""
        servers = self.get_servers()
        for i, server in enumerate(servers):
            if server.get("name") == server_name:
                servers[i] = updated_server
                self.set_servers(servers)
                return True
        return False

    def get_auto_connect_enabled(self) -> bool:
        """Get whether auto-connect is enabled."""
        return self._config.get("auto_connect_enabled", False)

    def set_auto_connect_enabled(self, enabled: bool) -> None:
        """Set whether auto-connect is enabled."""
        self._config["auto_connect_enabled"] = enabled
        self.save()

    def get_last_connected_server_name(self) -> Optional[str]:
        """Get the name of the last connected server."""
        return self._config.get("last_connected_server_name")

    def set_last_connected_server_name(self, server_name: Optional[str]) -> None:
        """Set the name of the last connected server."""
        if server_name is None:
            self._config.pop("last_connected_server_name", None)
        else:
            self._config["last_connected_server_name"] = server_name
        self.save()
