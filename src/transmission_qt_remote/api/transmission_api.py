"""Transmission RPC API client for torrent operations."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from ..config import CONNECTION_TIMEOUT_SEC

logger = logging.getLogger(__name__)


class TransmissionAPIClient:
    """Client for Transmission RPC API operations.

    Handles all communication with the Transmission daemon via HTTP RPC calls.
    Manages session IDs automatically and provides high-level methods for
    torrent operations.
    """

    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize the Transmission API client."""
        super().__init__()
        self.url = url
        self.username = username
        self.password = password
        self.session_id = session_id
        self._timeout = CONNECTION_TIMEOUT_SEC
        """Initialize the Transmission API client.

        Args:
            url: Transmission RPC endpoint URL
            username: Optional authentication username
            password: Optional authentication password
            session_id: Optional existing session ID
        """
        self.url = url
        self.username = username
        self.password = password
        self.session_id = session_id
        self._timeout = CONNECTION_TIMEOUT_SEC

    def fetch_torrents(self) -> List[Dict[str, Any]]:
        """Fetch list of all torrents from Transmission.

        Returns:
            List of torrent dictionaries, empty list on error
        """
        try:
            response = self._make_request(
                "torrent-get",
                {
                    "fields": [
                        "id",
                        "name",
                        "status",
                        "percentDone",
                        "rateDownload",
                        "rateUpload",
                        "eta",
                        "sizeWhenDone",
                        "totalSize",
                        "peersConnected",
                        "peersSendingToUs",
                        "peersGettingFromUs",
                        "trackerStats",
                        "addedDate",
                        "doneDate",
                        "error",
                        "errorString",
                    ]
                },
            )

            if response and "arguments" in response:
                return response["arguments"].get("torrents", [])
            return []

        except requests.RequestException as e:
            logger.error(f"Failed to fetch torrents: {e}")
            return []

    def fetch_torrent_details(self, torrent_id: int) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific torrent.

        Args:
            torrent_id: ID of the torrent to fetch details for

        Returns:
            Torrent details dictionary, or None if not found or error
        """
        logger.debug(f"Fetching detailed data for torrent ID: {torrent_id}")
        try:
            response = self._make_request(
                "torrent-get",
                {
                    "ids": [torrent_id],
                    "fields": [
                        "id",
                        "name",
                        "status",
                        "percentDone",
                        "rateDownload",
                        "rateUpload",
                        "eta",
                        "sizeWhenDone",
                        "totalSize",
                        "peersConnected",
                        "peersSendingToUs",
                        "peersGettingFromUs",
                        "trackerStats",
                        "addedDate",
                        "doneDate",
                        "error",
                        "errorString",
                        "files",
                        "fileStats",
                        "metadataPercentComplete",
                    ],
                },
            )

            if response and "arguments" in response:
                torrents = response["arguments"].get("torrents", [])
                if torrents:
                    torrent = torrents[0]
                    logger.debug(f"Torrent data keys: {list(torrent.keys())}")
                    logger.info(
                        f"Retrieved detailed data for torrent: {torrent.get('name', 'Unknown')}"
                    )
                    if "files" in torrent:
                        logger.debug(f"Files count: {len(torrent['files'])}")
                    if "fileStats" in torrent:
                        logger.debug(f"FileStats count: {len(torrent['fileStats'])}")
                    return torrent
                logger.warning("No torrent data received from API")
                return None
            else:
                logger.error("No response or arguments from API")
                return None

        except requests.RequestException as e:
            logger.error(f"Network error fetching torrent details: {e}")
            return None

    def start_torrent(self, torrent_id: int) -> bool:
        """Start a torrent.

        Args:
            torrent_id: ID of the torrent to start

        Returns:
            True if successful, False otherwise
        """
        return self._execute_torrent_action(
            "torrent-start", torrent_id, "Torrent started"
        )

    def force_start_torrent(self, torrent_id: int) -> bool:
        """Force start a torrent (ignoring queue limits).

        Args:
            torrent_id: ID of the torrent to force start

        Returns:
            True if successful, False otherwise
        """
        return self._execute_torrent_action(
            "torrent-start", torrent_id, "Torrent force started", force=True
        )

    def pause_torrent(self, torrent_id: int) -> bool:
        """Pause/stop a torrent.

        Args:
            torrent_id: ID of the torrent to pause

        Returns:
            True if successful, False otherwise
        """
        return self._execute_torrent_action(
            "torrent-stop", torrent_id, "Torrent paused"
        )

    def verify_torrent(self, torrent_id: int) -> bool:
        """Verify torrent data integrity.

        Args:
            torrent_id: ID of the torrent to verify

        Returns:
            True if successful, False otherwise
        """
        return self._execute_torrent_action(
            "torrent-verify", torrent_id, "Torrent verification started"
        )

    def set_file_priority(
        self, torrent_id: int, file_indices: List[int], priority: int
    ) -> bool:
        """Set priority for specific files in a torrent.

        Args:
            torrent_id: ID of the torrent
            file_indices: List of file indices to modify
            priority: Priority value (-1=Low, 0=Normal, 1=High)

        Returns:
            True if successful, False otherwise
        """
        try:
            arguments = {"ids": [torrent_id]}
            if priority == -1:
                arguments["priority-low"] = file_indices
            elif priority == 0:
                arguments["priority-normal"] = file_indices
            elif priority == 1:
                arguments["priority-high"] = file_indices

            response = self._make_request("torrent-set", arguments)
            return response is not None

        except requests.RequestException as e:
            logger.error(f"Failed to set file priority: {e}")
            return False

    def set_file_wanted(
        self, torrent_id: int, file_indices: List[int], wanted: bool
    ) -> bool:
        """Set wanted status for specific files in a torrent.

        Args:
            torrent_id: ID of the torrent
            file_indices: List of file indices to modify
            wanted: Whether files should be wanted

        Returns:
            True if successful, False otherwise
        """
        try:
            arguments = {"ids": [torrent_id]}
            if wanted:
                arguments["files-wanted"] = file_indices
            else:
                arguments["files-unwanted"] = file_indices

            response = self._make_request("torrent-set", arguments)
            return response is not None

        except requests.RequestException as e:
            logger.error(f"Failed to set file wanted status: {e}")
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test connection to Transmission server.

        Returns:
            Tuple of (success: bool, message: str)
        """
        request_data = {"method": "session-get"}
        headers = {}
        if self.session_id:
            headers["X-Transmission-Session-Id"] = self.session_id

        auth = (
            (self.username, self.password) if self.username and self.password else None
        )

        try:
            response = requests.post(
                self.url,
                headers=headers,
                auth=auth,
                json=request_data,
                timeout=self._timeout,
            )

            # Handle session ID conflicts
            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                if self.session_id:
                    # Retry with new session ID
                    headers["X-Transmission-Session-Id"] = self.session_id
                    response = requests.post(
                        self.url,
                        headers=headers,
                        auth=auth,
                        json=request_data,
                        timeout=self._timeout,
                    )

            if response.status_code in {200, 409}:
                return True, "Successfully connected to Transmission."
            elif response.status_code == 401:
                if auth:
                    return (
                        False,
                        "Authentication failed. Please check your username and password.",
                    )
                else:
                    return (
                        False,
                        "Server requires authentication. Please configure credentials in Connection Settings.",
                    )
            else:
                return (
                    False,
                    f"Server returned status {response.status_code}: {response.text[:100]}",
                )
        except requests.RequestException as exc:
            return False, str(exc)

    def _execute_torrent_action(
        self, method: str, torrent_id: int, success_message: str, force: bool = False
    ) -> bool:
        """Execute a torrent action with proper error handling.

        Args:
            method: RPC method name
            torrent_id: ID of the torrent
            success_message: Message for successful operation
            force: Whether to force the action (for torrent-start)

        Returns:
            True if successful, False otherwise
        """
        try:
            request_data = {"method": method, "arguments": {"ids": [torrent_id]}}
            if force and method == "torrent-start":
                request_data["arguments"]["force"] = True

            response = self._make_request(method, request_data["arguments"])

            if response:
                logger.info(success_message)
                return True
            else:
                logger.error(f"Failed to execute {method}")
                return False

        except requests.RequestException as e:
            logger.error(f"Network error executing {method}: {e}")
            return False

    def _make_request(
        self, method: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the Transmission RPC API.

        Args:
            method: RPC method name
            arguments: Optional arguments for the method

        Returns:
            Response data as dictionary, or None on error
        """
        request_data: Dict[str, Any] = {"method": method}
        if arguments:
            request_data["arguments"] = arguments

        headers = {}
        if self.session_id:
            headers["X-Transmission-Session-Id"] = self.session_id

        auth = (
            (self.username, self.password) if self.username and self.password else None
        )

        try:
            response = requests.post(
                self.url,
                headers=headers,
                auth=auth,
                json=request_data,
                timeout=self._timeout,
            )

            # Handle session ID conflicts
            if response.status_code == 409:
                self.session_id = response.headers.get("X-Transmission-Session-Id")
                if self.session_id:
                    # Retry with new session ID
                    headers["X-Transmission-Session-Id"] = self.session_id
                    response = requests.post(
                        self.url,
                        headers=headers,
                        auth=auth,
                        json=request_data,
                        timeout=self._timeout,
                    )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(
                    f"RPC request failed with status {response.status_code}: {response.text}"
                )
                return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
