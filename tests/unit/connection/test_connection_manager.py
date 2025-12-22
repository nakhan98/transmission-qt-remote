"""Tests for connection_manager module."""

from unittest.mock import MagicMock, patch

import pytest

from src.transmission_qt_remote.connection import ConnectionManager


class TestConnectionManager:
    """Test cases for ConnectionManager."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager."""
        mock = MagicMock()
        mock.get_servers.return_value = []
        mock.get_auto_connect_enabled.return_value = False
        mock.get_last_connected_server_name.return_value = None
        return mock

    @pytest.fixture
    def mock_credential_manager(self):
        """Create a mock CredentialManager."""
        mock = MagicMock()
        mock.get_credentials.return_value = None
        mock.is_available.return_value = True
        return mock

    @pytest.fixture
    def connection_manager(self, mock_config_manager, mock_credential_manager):
        """Create a ConnectionManager instance with mocked dependencies."""
        return ConnectionManager(mock_config_manager, mock_credential_manager)

    def test_init(self, mock_config_manager, mock_credential_manager):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager(mock_config_manager, mock_credential_manager)

        assert not manager.is_connected
        assert manager.current_url == ""
        assert manager.current_username == ""
        assert manager.current_password == ""
        assert not manager.credentials_enabled
        assert manager._api_client is None

    def test_get_current_credentials(self, connection_manager):
        """Test get_current_credentials method."""
        connection_manager._current_username = "testuser"
        connection_manager._current_password = "testpass"

        username, password = connection_manager.get_current_credentials()

        assert username == "testuser"
        assert password == "testpass"

    @patch(
        "src.transmission_qt_remote.connection.connection_manager.TransmissionAPIClient"
    )
    def test_test_connection_success(self, mock_api_client_class, connection_manager):
        """Test successful connection testing."""
        mock_api_client = MagicMock()
        mock_api_client.test_connection.return_value = (True, "Success")
        mock_api_client_class.return_value = mock_api_client

        success, message = connection_manager.test_connection("http://test.com")

        assert success is True
        assert message == "Success"

    @patch(
        "src.transmission_qt_remote.connection.connection_manager.TransmissionAPIClient"
    )
    def test_connect_to_server_success(
        self,
        mock_api_client_class,
        connection_manager,
        mock_config_manager,
        mock_credential_manager,
    ):
        """Test successful connection to specific server."""
        server_config = {
            "name": "Test Server",
            "url": "http://test.com",
            "use_credentials": True,
            "username": "testuser",
            "remember_credentials": True,
        }

        mock_config_manager.get_servers.return_value = [server_config]
        mock_credential_manager.get_credentials.return_value = "testpass"

        mock_api_client = MagicMock()
        mock_api_client.test_connection.return_value = (True, "Success")
        mock_api_client_class.return_value = mock_api_client

        result = connection_manager.connect_to_server(server_config)

        assert result is True
        assert connection_manager.is_connected
        assert connection_manager.current_url == "http://test.com"
        assert connection_manager.current_username == "testuser"
        assert connection_manager.current_password == "testpass"
        assert connection_manager.credentials_enabled

    def test_disconnect_when_connected(self, connection_manager):
        """Test disconnecting when connected."""
        connection_manager._is_connected = True
        connection_manager._api_client = MagicMock()

        connection_manager.disconnect()

        assert not connection_manager.is_connected
        assert connection_manager._api_client is None
