# test_transmission_client.py

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from transmission_qt_remote.transmission_client import (
    TorrentDetailDialog,
    TransmissionClient,
    get_country_info,
)

# Use shared Qt application fixture from conftest.py


# Sample torrent data for testing
@pytest.fixture
def sample_torrent_data():
    return {
        "id": 1,
        "name": "Test Torrent",
        "status": 0,
        "totalSize": 1048576,  # 1MB
        "addedDate": 1609459200,
        "percentDone": 0.5,
        "peers": [
            {
                "address": "192.168.1.100",
                "clientName": "Test Client 1",
                "progress": 0.75,
            },
            {
                "address": "192.168.1.101",
                "clientName": "Test Client 2",
                "progress": 1.0,
            },
        ],
        "trackerStats": [{"seederCount": 10, "leecherCount": 5}],
        "rateDownload": 1024,
        "rateUpload": 512,
    }


# Test initializing the TransmissionClient
def test_transmission_client_init(app):
    # Create the TransmissionClient without mocking __init__
    client = TransmissionClient()

    # Assert the client was initialized correctly
    assert client.windowTitle() == "Transmission QT Remote"
    assert client.geometry().width() == 900
    assert client.geometry().height() == 500


# Test the fetch_torrents method
@patch("transmission_qt_remote.api.transmission_api.requests.post")
def test_fetch_torrents(mock_post, app, sample_torrent_data):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"arguments": {"torrents": [sample_torrent_data]}}

    mock_post.return_value = mock_response

    client = TransmissionClient()
    # Initialize api_client manually since we're not connecting
    from transmission_qt_remote.api import TransmissionAPIClient

    client.api_client = TransmissionAPIClient("http://test:9091/rpc", None)

    torrents = client.api_client.fetch_torrents()

    assert len(torrents) == 1
    assert torrents[0]["name"] == "Test Torrent"


# Test the refresh_data method
@patch("transmission_qt_remote.api.TransmissionAPIClient.fetch_torrents")
def test_refresh_data(mock_fetch_torrents, app, sample_torrent_data):
    # Given: A client with mocked torrent fetching and connected state
    mock_fetch_torrents.return_value = [sample_torrent_data]

    client = TransmissionClient()

    # Initialize api_client manually since we're not connecting
    from transmission_qt_remote.api import TransmissionAPIClient

    client.api_client = TransmissionAPIClient("http://test:9091/rpc", None)
    client.connection_manager._is_connected = True  # Simulate connected state

    # When: Refreshing data
    client.refresh_data()

    # Then: Check displayed_torrents was set correctly
    assert len(client.torrent_table.displayed_torrents) == 1
    assert client.torrent_table.displayed_torrents[0]["name"] == "Test Torrent"

    # Check table was updated correctly
    assert client.torrent_table.rowCount() == 1
    assert client.torrent_table.item(0, 0).text() == "Test Torrent"


# Test get_status_text method
def test_get_status_text(app, sample_torrent_data):
    client = TransmissionClient()
    dialog = TorrentDetailDialog(client, sample_torrent_data)
    assert dialog.get_status_text(0) == "Stopped"
    assert dialog.get_status_text(3) == "Downloading"
    assert dialog.get_status_text(99) == "Unknown"


# Test toggle_column method
def test_toggle_column(app):
    client = TransmissionClient()
    # Initially, all columns should be visible
    for col_name in client.torrent_table.visible_columns:
        assert client.torrent_table.visible_columns[col_name] is True

    # Toggle a column to be invisible
    client.torrent_table.toggle_column_visibility("Torrent Name", False)
    assert client.torrent_table.visible_columns["Torrent Name"] is False

    # Toggle it back to visible
    client.torrent_table.toggle_column_visibility("Torrent Name", True)
    assert client.torrent_table.visible_columns["Torrent Name"] is True


# Test TrackerButton
def test_tracker_button(app):
    from transmission_qt_remote.transmission_client import TrackerButton

    # Create a tracker button
    button = TrackerButton("example.com")

    # Test properties
    assert button.hostname == "example.com"
    assert button.text() == "example.com"
    assert button.isCheckable()

    # Test long hostname - we shortened the display name but keep full hostname in tooltip
    long_button = TrackerButton("very.long.tracker.hostname.example.com")
    assert long_button.text() == "very.long...."
    assert long_button.toolTip() == "very.long.tracker.hostname.example.com"


# Test update_tracker_buttons method
def test_update_tracker_buttons(app):
    client = TransmissionClient()

    # Mock torrent data with tracker stats
    torrents = [
        {
            "name": "Test Torrent 1",
            "trackerStats": [
                {"announce": "https://tracker1.example.com/announce"},
                {"announce": "https://tracker2.example.com/announce"},
            ],
        },
        {
            "name": "Test Torrent 2",
            "trackerStats": [
                {"announce": "https://tracker2.example.com/announce"},
                {"announce": "https://tracker3.example.com/announce"},
            ],
        },
    ]

    # Update tracker buttons (now handled by torrent_table)
    client.torrent_table.update_tracker_options(torrents)

    # Check that tracker options were updated
    assert len(client.torrent_table.available_trackers) == 4  # "All" + 3 trackers
    assert "All" in client.torrent_table.available_trackers

    # Test adding another tracker
    new_torrents = torrents + [
        {
            "name": "Test Torrent 3",
            "trackerStats": [{"announce": "https://tracker4.example.com/announce"}],
        }
    ]

    # Update tracker buttons with new data
    client.torrent_table.update_tracker_options(new_torrents)

    # Check that the new tracker option was added
    assert len(client.torrent_table.available_trackers) == 5  # "All" + 4 trackers

    # Update with the same data shouldn't add duplicates
    client.torrent_table.update_tracker_options(new_torrents)
    assert (
        len(client.torrent_table.available_trackers) == 5
    )  # Should remain 5, no duplicates


# Test clear_filters method
def test_clear_filters(app):
    client = TransmissionClient()

    # Mock the select_tracker method to avoid side effects
    original_select_tracker = client.select_tracker
    client.select_tracker = MagicMock()

    try:
        # Set up filters
        client.search_box.setText("test")
        client.active_tracker = "tracker1.example.com"

        # Clear filters
        client.clear_filters()

        # Check that filters were cleared
        assert client.search_box.text() == ""

        # Check that "All" was selected
        client.select_tracker.assert_called_once_with("All")
    finally:
        # Restore original method
        client.select_tracker = original_select_tracker


# Test select_tracker method
def test_select_tracker(app):
    client = TransmissionClient()

    # Test selecting a tracker
    client.select_tracker("example.com")
    assert client.torrent_table.active_tracker == "example.com"

    # Test selecting "All"
    client.select_tracker("All")
    assert client.torrent_table.active_tracker is None

    # Test selecting a different tracker
    client.select_tracker("another.com")
    assert client.torrent_table.active_tracker == "another.com"


# Test the filter_table method
def test_filter_table(app, sample_torrent_data):
    # Given: Sample torrent data with tracker information
    sample_data_with_tracker = sample_torrent_data.copy()
    sample_data_with_tracker["trackerStats"] = [
        {
            "announce": "https://tracker1.example.com/announce",
            "seederCount": 10,
            "leecherCount": 5,
        },
        {
            "announce": "https://tracker2.example.com/announce",
            "seederCount": 5,
            "leecherCount": 2,
        },
    ]

    client = TransmissionClient()

    # Given: Client with displayed torrents and populated table
    client.torrent_table.displayed_torrents = [sample_data_with_tracker]
    client.torrent_table.update_torrents([sample_data_with_tracker])

    # Text search tests

    # When: Setting search term that matches torrent name
    client.torrent_table.filter_by_text("test")
    # Then: Row should not be hidden
    assert not client.torrent_table.isRowHidden(0)

    # When: Setting search term that doesn't match
    client.torrent_table.filter_by_text("nonexistent")
    # Then: Row should be hidden
    assert client.torrent_table.isRowHidden(0)

    # Tracker filter tests

    # Given: Search reset
    client.torrent_table.filter_by_text("")

    # When: Setting active tracker that matches torrent's tracker
    client.torrent_table.filter_by_tracker("tracker1.example.com")
    # Then: Row should not be hidden
    assert not client.torrent_table.isRowHidden(0)

    # When: Setting active tracker that doesn't match
    client.torrent_table.filter_by_tracker("nonexistent.tracker")
    # Then: Row should be hidden
    assert client.torrent_table.isRowHidden(0)

    # Combined filter tests

    # When: Setting both matching search and matching tracker
    client.torrent_table.filter_by_text("test")
    client.torrent_table.filter_by_tracker("tracker2.example.com")
    # Then: Row should not be hidden
    assert not client.torrent_table.isRowHidden(0)

    # When: Setting matching search but non-matching tracker
    client.torrent_table.filter_by_text("test")
    client.torrent_table.filter_by_tracker("nonexistent.tracker")
    assert client.torrent_table.isRowHidden(0)

    # Test clearing filters
    client.torrent_table.clear_filters()


# Test on_torrent_double_clicked method
@patch.object(QMessageBox, "information")
def test_on_torrent_double_clicked(mock_info, app, sample_torrent_data):
    client = TransmissionClient()

    # Set up displayed torrents and update table
    client.torrent_table.displayed_torrents = [sample_torrent_data]
    client.torrent_table.update_torrents([sample_torrent_data])

    # Select the torrent in the table
    client.torrent_table.selectRow(0)

    # Test double-click handler (now takes torrent_id)
    client._on_torrent_double_clicked(sample_torrent_data["id"])

    # Check that QMessageBox.information was called
    mock_info.assert_called_once()


# Test TorrentDetailDialog initialization
def test_torrent_detail_dialog_init(app, sample_torrent_data):
    client = TransmissionClient()
    dialog = TorrentDetailDialog(client, sample_torrent_data)

    assert dialog.windowTitle() == f"Details: {sample_torrent_data['name']}"
    assert dialog.torrent == sample_torrent_data

    # Check that we have 3 tabs (General, Peers, Files)
    assert dialog.tabs.count() == 3
    assert dialog.tabs.tabText(0) == "General"
    assert dialog.tabs.tabText(1) == "Peers"
    assert dialog.tabs.tabText(2) == "Files"

    # Test peers table setup
    assert dialog.peers_table.rowCount() == 2
    assert dialog.peers_table.columnCount() == 4  # Now has 4 columns including Country
    assert dialog.peers_table.item(0, 0).text() == "192.168.1.100"
    assert dialog.peers_table.item(0, 1).text() == "--"  # Local network IP
    assert dialog.peers_table.item(0, 2).text() == "Test Client 1"
    assert dialog.peers_table.item(0, 3).text() == "75.00%"
    assert dialog.peers_table.item(1, 0).text() == "192.168.1.101"
    assert dialog.peers_table.item(1, 1).text() == "--"  # Local network IP
    assert dialog.peers_table.item(1, 2).text() == "Test Client 2"
    assert dialog.peers_table.item(1, 3).text() == "100.00%"


# Test TorrentDetailDialog get_status_text method
def test_torrent_detail_dialog_get_status_text(app, sample_torrent_data):
    client = TransmissionClient()
    dialog = TorrentDetailDialog(client, sample_torrent_data)

    assert dialog.get_status_text(0) == "Stopped"
    assert dialog.get_status_text(3) == "Downloading"
    assert dialog.get_status_text(99) == "Unknown"


# Test file priority API methods
@patch("transmission_qt_remote.api.transmission_api.requests.post")
def test_set_file_priority(mock_post, app):
    """Test setting file priority."""
    client = TransmissionClient()

    # Initialize api_client manually since we're not connecting
    from transmission_qt_remote.api import TransmissionAPIClient

    client.api_client = TransmissionAPIClient("http://test:9091/rpc", None)

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Test setting high priority
    result = client.api_client.set_file_priority(1, [0, 1], 1)
    assert result is True

    # Check the request was made correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    request_data = call_args[1]["json"]
    assert request_data["method"] == "torrent-set"
    assert request_data["arguments"]["ids"] == [1]
    assert request_data["arguments"]["priority-high"] == [0, 1]


@patch("transmission_qt_remote.api.transmission_api.requests.post")
def test_set_file_wanted(mock_post, app):
    """Test setting file wanted status."""
    client = TransmissionClient()

    # Initialize api_client manually since we're not connecting
    from transmission_qt_remote.api import TransmissionAPIClient

    client.api_client = TransmissionAPIClient("http://test:9091/rpc", None)

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    # Test setting files as wanted
    result = client.api_client.set_file_wanted(1, [0, 1], True)
    assert result is True

    # Check the request was made correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    request_data = call_args[1]["json"]
    assert request_data["method"] == "torrent-set"
    assert request_data["arguments"]["ids"] == [1]
    assert request_data["arguments"]["files-wanted"] == [0, 1]


@patch("transmission_qt_remote.api.transmission_api.requests.post")
def test_fetch_torrent_details(mock_post, app, sample_torrent_data):
    """Test fetching detailed torrent data."""
    client = TransmissionClient()

    # Initialize api_client manually since we're not connecting
    from transmission_qt_remote.api import TransmissionAPIClient

    client.api_client = TransmissionAPIClient("http://test:9091/rpc", None)

    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"arguments": {"torrents": [sample_torrent_data]}}
    mock_post.return_value = mock_response

    # Test fetching details
    result = client.api_client.fetch_torrent_details(1)
    assert result == sample_torrent_data

    # Check the request was made correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    request_data = call_args[1]["json"]
    assert request_data["method"] == "torrent-get"
    # Should request specific torrent by ID
    assert request_data["arguments"]["ids"] == [1]
    assert "files" in request_data["arguments"]["fields"]
    assert "fileStats" in request_data["arguments"]["fields"]


# Test the extract_hostname function
def test_extract_hostname():
    from transmission_qt_remote.transmission_client import extract_hostname

    # Test HTTP URL without port
    assert extract_hostname("http://example.com/announce") == "example.com"

    # Test HTTPS URL with port - now preserves port
    assert (
        extract_hostname("https://tracker.example.org:8080/announce")
        == "tracker.example.org:8080"
    )

    # Test UDP URL with port - now preserves port
    assert (
        extract_hostname("udp://tracker.example.net:6969/announce")
        == "tracker.example.net:6969"
    )

    # Test other protocol with port
    assert extract_hostname("wss://example.com:443/announce") == "example.com:443"

    # Test other protocol without port
    assert extract_hostname("wss://example.com/announce") == "example.com"

    # Test malformed URL
    assert extract_hostname("example.com") == "example.com"

    # Test same hostname with different ports
    assert extract_hostname("https://example.com:8080/announce") != extract_hostname(
        "https://example.com:9090/announce"
    )

    # Test empty string (shouldn't crash)
    assert extract_hostname("") == ""

    # Test exception handling
    # This will raise an exception because None doesn't have .startswith
    try:
        extract_hostname(None)
        assert False, "Should have raised an exception"
    except Exception:
        pass


# Test get_country_info function
@patch("transmission_qt_remote.dialogs.utils.ip2location_db")
def test_get_country_info(mock_db):
    # Setup the mock record response
    mock_record = MagicMock()
    mock_record.country_short = "US"
    mock_record.country_long = "United States"
    mock_db.get_all.return_value = mock_record

    # Test public IP address
    code, name = get_country_info("8.8.8.8")
    assert code == "US"
    assert name == "United States"

    # Test local IP address
    code, name = get_country_info("192.168.1.1")
    assert code == "--"
    assert name == "Local Network"

    # Test when database returns None
    mock_db.get_all.return_value = None
    code, name = get_country_info("8.8.8.8")
    assert code == "??"
    assert "Unknown" in name

    # Test dash country code (IP2Location specific)
    mock_record = MagicMock()
    mock_record.country_short = "-"
    mock_record.country_long = "-"
    mock_db.get_all.return_value = mock_record
    code, name = get_country_info("8.8.8.8")
    assert code == "??"
    assert "Unknown" in name

    # Test empty country code
    mock_record = MagicMock()
    mock_record.country_short = ""
    mock_record.country_long = ""
    mock_db.get_all.return_value = mock_record
    code, name = get_country_info("8.8.8.8")
    assert code == "??"
    assert "Unknown" in name

    # Test exception handling
    mock_db.get_all.side_effect = Exception("Error")
    code, name = get_country_info("8.8.8.8")
    assert code == "??"
    assert name == "Unknown"
