"""Tests for transmission_api module."""

from unittest.mock import MagicMock, patch

import pytest

from src.transmission_qt_remote.api import TransmissionAPIClient


class TestTransmissionAPIClient:
    """Test cases for TransmissionAPIClient."""

    @pytest.fixture
    def api_client(self):
        """Create a test API client."""
        return TransmissionAPIClient(
            url="http://localhost:9091/transmission/rpc",
            username="testuser",
            password="testpass",
        )

    def test_init(self, api_client):
        """Test API client initialization."""
        assert api_client.url == "http://localhost:9091/transmission/rpc"
        assert api_client.username == "testuser"
        assert api_client.password == "testpass"
        assert api_client.session_id is None
        assert api_client._timeout == 5  # From config

    def test_init_no_auth(self):
        """Test API client initialization without authentication."""
        client = TransmissionAPIClient("http://localhost:9091/transmission/rpc")
        assert client.username is None
        assert client.password is None

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_fetch_torrents_success(self, mock_post, api_client):
        """Test successful torrent fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "arguments": {
                "torrents": [
                    {"id": 1, "name": "Test Torrent", "status": 3},
                    {"id": 2, "name": "Another Torrent", "status": 6},
                ]
            }
        }
        mock_post.return_value = mock_response

        torrents = api_client.fetch_torrents()

        assert len(torrents) == 2
        assert torrents[0]["name"] == "Test Torrent"
        assert torrents[1]["name"] == "Another Torrent"

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:9091/transmission/rpc"
        assert "torrent-get" in call_args[1]["json"]["method"]

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_fetch_torrents_request_exception(self, mock_post, api_client):
        """Test torrent fetching with network error."""
        import requests

        mock_post.side_effect = requests.RequestException("Network error")

        torrents = api_client.fetch_torrents()

        assert torrents == []

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_fetch_torrent_details_success(self, mock_post, api_client):
        """Test successful torrent details fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "arguments": {
                "torrents": [
                    {
                        "id": 1,
                        "name": "Test Torrent",
                        "status": 3,
                        "files": [{"name": "file1.txt", "length": 100}],
                        "fileStats": [{"wanted": True, "priority": 0}],
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        torrent = api_client.fetch_torrent_details(1)

        assert torrent is not None
        assert torrent["id"] == 1
        assert torrent["name"] == "Test Torrent"
        assert len(torrent["files"]) == 1
        assert len(torrent["fileStats"]) == 1

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_fetch_torrent_details_not_found(self, mock_post, api_client):
        """Test torrent details fetching when torrent not found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"arguments": {"torrents": []}}
        mock_post.return_value = mock_response

        torrent = api_client.fetch_torrent_details(999)

        assert torrent is None

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_start_torrent_success(self, mock_post, api_client):
        """Test successful torrent start."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.start_torrent(1)

        assert result is True
        # Verify the request contained torrent-start
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "torrent-start"
        assert call_args[1]["json"]["arguments"]["ids"] == [1]

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_force_start_torrent_success(self, mock_post, api_client):
        """Test successful torrent force start."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.force_start_torrent(1)

        assert result is True
        # Verify force parameter was set
        call_args = mock_post.call_args
        assert call_args[1]["json"]["arguments"]["force"] is True

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_pause_torrent_success(self, mock_post, api_client):
        """Test successful torrent pause."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.pause_torrent(1)

        assert result is True
        # Verify the request contained torrent-stop
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "torrent-stop"

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_verify_torrent_success(self, mock_post, api_client):
        """Test successful torrent verification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.verify_torrent(1)

        assert result is True
        # Verify the request contained torrent-verify
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "torrent-verify"

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_set_file_priority_success(self, mock_post, api_client):
        """Test successful file priority setting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.set_file_priority(1, [0, 1], 1)  # High priority

        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "torrent-set"
        assert call_args[1]["json"]["arguments"]["priority-high"] == [0, 1]

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_set_file_wanted_success(self, mock_post, api_client):
        """Test successful file wanted status setting."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.set_file_wanted(1, [0, 1], False)  # Unwanted

        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]["json"]["method"] == "torrent-set"
        assert call_args[1]["json"]["arguments"]["files-unwanted"] == [0, 1]

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_test_connection_success(self, mock_post, api_client):
        """Test successful connection test."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        success, message = api_client.test_connection()

        assert success is True
        assert "Successfully connected" in message

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_test_connection_failure(self, mock_post, api_client):
        """Test connection test failure."""
        import requests

        mock_post.side_effect = requests.RequestException("Connection refused")

        success, message = api_client.test_connection()

        assert success is False
        assert message == "Connection refused"

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_session_id_refresh(self, mock_post, api_client):
        """Test automatic session ID refresh on 409 conflict."""
        # First call returns 409 with new session ID
        conflict_response = MagicMock()
        conflict_response.status_code = 409
        conflict_response.headers = {"X-Transmission-Session-Id": "new-session-id"}

        # Second call succeeds
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"result": "success"}

        mock_post.side_effect = [conflict_response, success_response]

        result = api_client.start_torrent(1)

        assert result is True
        assert api_client.session_id == "new-session-id"
        assert mock_post.call_count == 2

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_request_with_existing_session_id(self, mock_post, api_client):
        """Test that existing session ID is included in headers."""
        api_client.session_id = "existing-session"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        api_client.start_torrent(1)

        # Verify session ID was included in headers
        call_args = mock_post.call_args
        assert (
            call_args[1]["headers"]["X-Transmission-Session-Id"] == "existing-session"
        )

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_authentication_included(self, mock_post, api_client):
        """Test that authentication is included when credentials are set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        api_client.start_torrent(1)

        # Verify auth was included
        call_args = mock_post.call_args
        assert call_args[1]["auth"] == ("testuser", "testpass")

    @patch("src.transmission_qt_remote.api.transmission_api.requests.post")
    def test_no_authentication_when_not_set(self, mock_post):
        """Test that no authentication is included when credentials not set."""
        client = TransmissionAPIClient("http://localhost:9091/transmission/rpc")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        client.start_torrent(1)

        # Verify auth was None
        call_args = mock_post.call_args
        assert call_args[1]["auth"] is None
