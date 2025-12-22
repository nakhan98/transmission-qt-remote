"""Connection management for Transmission QT Remote."""

import logging
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from ..api import TransmissionAPIClient
from ..config_manager import ConfigManager
from ..credential_manager import CredentialManager

logger = logging.getLogger(__name__)


class ConnectionManager(QObject):
    """Manages Transmission server connections and credentials.

    This class handles all aspects of connecting to Transmission servers,
    including credential management, auto-connect functionality, and
    connection state tracking.

    Signals:
        connected(url: str): Emitted when successfully connected to a server
        disconnected(): Emitted when disconnected from server
        connection_failed(message: str): Emitted when connection attempt fails
    """

    # Qt signals
    connected = Signal(str)  # url
    disconnected = Signal()
    connection_failed = Signal(str)  # error message

    def __init__(
        self,
        config_manager: ConfigManager,
        credential_manager: CredentialManager,
    ):
        """Initialize the connection manager.

        Args:
            config_manager: ConfigManager instance for server configurations
            credential_manager: CredentialManager instance for secure credential storage
        """
        super().__init__()
        self.config_manager = config_manager
        self.credential_manager = credential_manager

        # Connection state
        self._is_connected = False
        self._current_url = ""
        self._current_username = ""
        self._current_password = ""
        self._credentials_enabled = False

        # API client (created when needed)
        self._api_client: Optional[TransmissionAPIClient] = None

        # Load initial credentials
        self._load_credentials()

    @property
    def is_connected(self) -> bool:
        """Get connection status."""
        return self._is_connected

    @property
    def current_url(self) -> str:
        """Get current server URL."""
        return self._current_url

    @property
    def current_username(self) -> str:
        """Get current username."""
        return self._current_username

    @property
    def current_password(self) -> str:
        """Get current password."""
        return self._current_password

    @property
    def credentials_enabled(self) -> bool:
        """Check if credentials are enabled."""
        return self._credentials_enabled

    def get_current_credentials(self) -> Tuple[str, str]:
        """Get current credentials as a tuple.

        Returns:
            Tuple of (username, password)
        """
        return (self._current_username, self._current_password)

    def auto_connect(self) -> bool:
        """Connect to the configured Transmission server.

        Attempts to connect using saved server configurations and credentials.

        Returns:
            True if connection successful, False otherwise
        """
        return self._connect()

    def connect_to_server(self, server_config: Dict[str, Any]) -> bool:
        """Connect to a specific server configuration.

        Args:
            server_config: Server configuration dictionary

        Returns:
            True if connection successful, False otherwise
        """
        url = server_config.get("url", "")
        username = None
        password = None

        if server_config.get("use_credentials"):
            username = server_config.get("username", "")
            if (
                server_config.get("remember_credentials")
                and CredentialManager.is_available()
            ):
                password = self.credential_manager.get_credentials(username)

        return self._connect_with_credentials(url, username, password)

    def disconnect(self) -> None:
        """Disconnect from the current server."""
        if self._is_connected:
            self._is_connected = False
            self._api_client = None
            logger.info("Disconnected from Transmission server")
            self.disconnected.emit()

    def attempt_auto_connect(self) -> None:
        """Attempt to auto-connect to the last connected server if enabled."""
        if not self.config_manager.get_auto_connect_enabled():
            return

        last_server_name = self.config_manager.get_last_connected_server_name()
        if not last_server_name:
            return

        servers = self.config_manager.get_servers()
        last_server = None
        for server in servers:
            if server.get("name") == last_server_name:
                last_server = server
                break

        if not last_server:
            logger.warning(
                "Last connected server '%s' not found in server list", last_server_name
            )
            return

        # Attempt to connect to the last server
        logger.info("Attempting auto-connect to last server: %s", last_server_name)
        if self.connect_to_server(last_server):
            logger.info("Auto-connected to Transmission server: %s", last_server["url"])
        else:
            logger.warning("Auto-connect failed to server %s", last_server.get("name"))

    def test_connection(
        self, url: str, username: Optional[str] = None, password: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Test connection to a Transmission server.

        Args:
            url: Server URL to test
            username: Optional username for authentication
            password: Optional password for authentication

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Create a temporary API client for testing
        api_client = TransmissionAPIClient(url, username, password)
        return api_client.test_connection()

    def _connect(self) -> bool:
        """Internal connection logic using saved configurations."""
        # Try to use saved server configuration first
        servers = self.config_manager.get_servers()

        if servers:
            # Try to use the last connected server first
            last_server_name = self.config_manager.get_last_connected_server_name()
            server = None

            if last_server_name:
                for s in servers:
                    if s.get("name") == last_server_name:
                        server = s
                        break

            # Fall back to first server if last connected not found
            if not server:
                server = servers[0]

            return self.connect_to_server(server)
        else:
            # Fall back to current configuration (if any)
            if self._current_url:
                return self._connect_with_credentials(
                    self._current_url,
                    self._current_username if self._credentials_enabled else None,
                    self._current_password if self._credentials_enabled else None,
                )
            else:
                self.connection_failed.emit("No server configuration available")
                return False

    def _connect_with_credentials(
        self, url: str, username: Optional[str], password: Optional[str]
    ) -> bool:
        """Connect using specific credentials.

        Args:
            url: Server URL
            username: Optional username
            password: Optional password

        Returns:
            True if connection successful, False otherwise
        """
        # Test the connection
        success, message = self.test_connection(url, username, password)

        if success:
            # Create API client
            self._api_client = TransmissionAPIClient(url, username, password)
            self._is_connected = True
            self._current_url = url
            if username and password:
                self._credentials_enabled = True
                self._current_username = username
                self._current_password = password

            # Update last connected server information
            self._update_last_connected_server(url)

            logger.info("Connected to Transmission server: %s", url)
            self.connected.emit(url)
            return True
        else:
            self.connection_failed.emit(message)
            return False

    def _update_last_connected_server(self, connected_url: str) -> None:
        """Update the last connected server information."""
        import time

        servers = self.config_manager.get_servers()

        # Find the server that matches the connected URL
        for server in servers:
            if server.get("url") == connected_url:
                # Update server with connection info
                server["last_connected"] = int(time.time())
                server["connection_count"] = server.get("connection_count", 0) + 1

                # Update the last connected server name in config
                self.config_manager.set_last_connected_server_name(server["name"])
                self.config_manager.set_servers(servers)
                break

    def _load_credentials(self) -> None:
        """Load credentials with enhanced fallback logic."""
        servers = self.config_manager.get_servers()

        if servers:
            # Load from first configured server (could be enhanced to load last used)
            first_server = servers[0]
            if first_server.get("use_credentials"):
                username = first_server.get("username", "")
                if username:
                    # Try to load from keyring first
                    stored_password = self.credential_manager.get_credentials(username)
                    if stored_password:
                        self._credentials_enabled = True
                        self._current_username = username
                        self._current_password = stored_password
                        logger.info(
                            "Loaded credentials from server profile: %s",
                            first_server["name"],
                        )
                        return

        # Fall back to environment variables if no server profiles or no credentials found
        self._load_environment_credentials()

    def _load_environment_credentials(self) -> None:
        """Load credentials from environment variables as fallback."""
        from ..config import TRANSMISSION_PASS, TRANSMISSION_USER

        env_username = TRANSMISSION_USER
        env_password = TRANSMISSION_PASS

        if env_username:
            # Check if credentials exist in keyring first (for secure storage)
            if CredentialManager.is_available():
                stored_password = self.credential_manager.get_credentials(env_username)
                if stored_password:
                    self._credentials_enabled = True
                    self._current_username = env_username
                    self._current_password = stored_password
                    logger.info("Loaded credentials from secure storage")
                    return

            # Fall back to environment variables
            if env_password:
                self._credentials_enabled = True
                self._current_username = env_username
                self._current_password = env_password
                logger.info("Loaded credentials from environment variables")
            else:
                # Username set but no password - might be incomplete config
                logger.warning("TRANSMISSION_USER set but TRANSMISSION_PASS not found")
