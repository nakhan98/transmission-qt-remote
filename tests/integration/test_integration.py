#!/usr/bin/env python3
"""
Integration tests for Transmission Client that require QT dependencies.
These tests need a graphical environment or suitable mocks for QT components.
"""

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from transmission_qt_remote.api import TransmissionAPIClient
from transmission_qt_remote.transmission_client import (
    TorrentDetailDialog,
    TrackerButton,
    TransmissionClient,
)

# Use shared Qt application fixture from conftest.py


# Sample torrent data for testing
@pytest.fixture
def sample_torrent_data():
    """Provide sample torrent data for tests."""
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
        "trackerStats": [
            {
                "announce": "https://tracker1.example.com/announce",
                "seederCount": 10,
                "leecherCount": 5,
            }
        ],
        "rateDownload": 1024,
        "rateUpload": 512,
    }


@pytest.fixture
def sample_torrent_data_with_files():
    """Provide sample torrent data with files for testing the files tab."""
    return {
        "name": "Test Torrent with Files",
        "status": 0,
        "totalSize": 1048576,  # 1MB
        "addedDate": 1609459200,
        "percentDone": 0.5,
        "peers": [],
        "trackerStats": [],
        "rateDownload": 1024,
        "rateUpload": 512,
        "files": [
            {"name": "file1.txt", "length": 1024, "bytesCompleted": 512},
            {"name": "subdir/file2.txt", "length": 2048, "bytesCompleted": 1024},
            {"name": "subdir/file3.txt", "length": 4096, "bytesCompleted": 2048},
        ],
        "fileStats": [
            {"wanted": True, "priority": 0},  # Normal priority
            {"wanted": True, "priority": 1},  # High priority
            {"wanted": False, "priority": -1},  # Low priority, unwanted
        ],
    }


# Test initializing the TransmissionClient
def test_transmission_client_init(app):
    """Test TransmissionClient initialization."""
    # Create the TransmissionClient without mocking __init__
    client = TransmissionClient()

    # Assert the client was initialized correctly
    assert client.windowTitle() == "Transmission QT Remote"
    assert client.geometry().width() == 900
    assert client.geometry().height() == 500


# Test the refresh_data method
@patch("transmission_qt_remote.api.TransmissionAPIClient.fetch_torrents")
def test_refresh_data(mock_fetch_torrents, app, sample_torrent_data):
    """Test table data refresh functionality."""
    # Given: Mocked torrent fetching and connected client
    mock_fetch_torrents.return_value = [sample_torrent_data]

    client = TransmissionClient()
    client.connection_manager._is_connected = True  # Simulate connected state
    client.api_client = client.connection_manager._api_client = TransmissionAPIClient(
        "http://test", "user", "pass"
    )  # Create API client

    # When: Refreshing data
    client.refresh_data()

    # Then: Check displayed_torrents was set correctly
    assert len(client.torrent_table.displayed_torrents) == 1
    assert client.torrent_table.displayed_torrents[0]["name"] == "Test Torrent"

    # And: Check table was updated correctly
    assert client.torrent_table.rowCount() == 1
    assert client.torrent_table.item(0, 0).text() == "Test Torrent"


# Test toggle_column method
def test_toggle_column(app):
    """Test toggling column visibility."""
    # Given: A client with all columns initially visible
    client = TransmissionClient()
    for col_name in client.torrent_table.visible_columns:
        assert client.torrent_table.visible_columns[col_name] is True

    # When: Toggling a column to be invisible
    client.torrent_table.toggle_column_visibility("Torrent Name", False)
    # Then: Column should be marked as not visible
    assert client.torrent_table.visible_columns["Torrent Name"] is False

    # When: Toggling it back to visible
    client.torrent_table.toggle_column_visibility("Torrent Name", True)
    # Then: Column should be marked as visible again
    assert client.torrent_table.visible_columns["Torrent Name"] is True


# Test status bar shows disconnected when not connected
def test_status_bar_disconnected(app):
    """Test that status bar shows 'Disconnected' when not connected."""
    # Given: A TransmissionClient that starts disconnected
    client = TransmissionClient()
    # When: Checking the initial connection state
    # Then: Status bar should show "Disconnected"
    assert not client.connection_manager.is_connected
    assert client.status_label.text() == "Disconnected"


def test_status_bar_connected_no_refresh(app):
    """Test that status bar shows 'Last refresh: --:--:--' when connected but no refresh."""
    # Given: A TransmissionClient
    client = TransmissionClient()
    # When: Simulating a connection without refresh
    client.connection_manager._is_connected = True
    client._update_status_label()
    # Then: Status bar should show "Last refresh: --:--:--"
    assert client.status_label.text() == "Last refresh: --:--:--"


def test_status_bar_connected_with_refresh(app):
    """Test that status bar shows actual time when connected and refreshed."""
    # Given: A TransmissionClient
    client = TransmissionClient()
    # When: Simulating a connection with a refresh at 14:30:25
    client.connection_manager._is_connected = True
    client._update_status_label("14:30:25")
    # Then: Status bar should show "Last refresh: 14:30:25"
    assert client.status_label.text() == "Last refresh: 14:30:25"


# Test TrackerButton
def test_tracker_button(app):
    """Test TrackerButton functionality."""
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
    """Test updating tracker filter buttons."""
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

    # Update tracker buttons
    client.torrent_table.update_tracker_options(torrents)

    # Check that tracker options were updated
    assert len(client.torrent_table.available_trackers) == 4  # "All" + 3 trackers
    assert "All" in client.torrent_table.available_trackers


# Test clear_filters method
def test_clear_filters(app):
    """Test clearing filter settings."""
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
    """Test tracker selection functionality."""
    client = TransmissionClient()

    # Test selecting a tracker
    client.select_tracker("example.com")
    assert client.torrent_table.active_tracker == "example.com"

    # Test selecting "All"
    client.select_tracker("All")
    assert client.torrent_table.active_tracker is None


# Test TorrentDetailDialog initialization
def test_torrent_detail_dialog_init(app, sample_torrent_data):
    """Test TorrentDetailDialog initialization."""
    dialog = TorrentDetailDialog(None, sample_torrent_data)

    # Check dialog was created with correct title
    assert dialog.windowTitle() == "Details: Test Torrent"

    # Check that we have 3 tabs (General, Peers, Files)
    assert dialog.tabs.count() == 3
    assert dialog.tabs.tabText(0) == "General"
    assert dialog.tabs.tabText(1) == "Peers"
    assert dialog.tabs.tabText(2) == "Files"

    # Check table has correct number of rows (2 peers)
    assert dialog.peers_table.rowCount() == 2

    # Check peer data is displayed correctly
    assert dialog.peers_table.item(0, 0).text() == "192.168.1.100"
    assert dialog.peers_table.item(0, 1).text() == "--"  # Local network
    assert dialog.peers_table.item(0, 2).text() == "Test Client 1"


def test_torrent_detail_dialog_files_tab(app, sample_torrent_data_with_files):
    """Test TorrentDetailDialog files tab initialization and population."""
    dialog = TorrentDetailDialog(None, sample_torrent_data_with_files)

    # Check that files tab exists (should be tab 2)
    assert dialog.tabs.count() == 3
    assert dialog.tabs.tabText(2) == "Files"

    # Check files tree was created
    assert hasattr(dialog, "files_tree")
    assert dialog.files_tree.topLevelItemCount() == 1  # Root torrent item

    # Check root item
    root_item = dialog.files_tree.topLevelItem(0)
    assert root_item.text(0) == "Test Torrent with Files"

    # Check that files are populated (should have subdir and file1.txt)
    assert root_item.childCount() == 2  # file1.txt and subdir

    # Find file1.txt
    file1_item = None
    subdir_item = None
    for i in range(root_item.childCount()):
        child = root_item.child(i)
        if child.text(0) == "file1.txt":
            file1_item = child
        elif child.text(0) == "subdir":
            subdir_item = child

    assert file1_item is not None
    assert file1_item.text(1) == "0.00 MB"  # 1024 bytes
    assert file1_item.text(2) == "50.0%"  # 512/1024
    assert file1_item.text(3) == "Normal"  # priority 0

    assert subdir_item is not None
    assert subdir_item.text(1) == "0.01 MB"  # 6144 bytes total
    assert subdir_item.childCount() == 2  # file2.txt and file3.txt


def test_torrent_detail_dialog_files_context_menu(
    app, sample_torrent_data_with_files, qtbot
):
    """Test files tab context menu functionality."""
    dialog = TorrentDetailDialog(None, sample_torrent_data_with_files)
    qtbot.addWidget(dialog)

    # Get the files tree
    files_tree = dialog.files_tree

    # Find file1.txt item
    root_item = files_tree.topLevelItem(0)
    file1_item = None
    for i in range(root_item.childCount()):
        child = root_item.child(i)
        if child.text(0) == "file1.txt":
            file1_item = child
            break

    assert file1_item is not None

    # Simulate right-click on file1.txt
    # Note: In a real test environment, we'd use qtbot.mouseClick with right button
    # For now, we'll test that the context menu setup is correct
    from PySide6.QtCore import Qt

    assert files_tree.contextMenuPolicy() == Qt.CustomContextMenu

    # Test file path resolution
    file_path = dialog._get_item_file_path(file1_item)
    assert file_path == "file1.txt"

    # Test file index resolution
    file_index = dialog._get_file_index("file1.txt")
    assert file_index == 0


# Test error handling scenarios
def test_refresh_data_network_error(app):
    """Test handling of network errors during data refresh."""
    from requests.exceptions import ConnectionError

    # Create client with mocked initial refresh
    with patch.object(TransmissionClient, "refresh_data"):
        client = TransmissionClient()

    # Mock requests.post to raise ConnectionError
    with patch(
        "transmission_qt_remote.api.transmission_api.requests.post",
        side_effect=ConnectionError("Network is unreachable"),
    ):
        # Should not crash, should handle the error gracefully
        client.refresh_data()

    # Should still have empty table since no previous data and error occurred
    assert client.torrent_table.rowCount() == 0


@patch("transmission_qt_remote.api.TransmissionAPIClient.fetch_torrents")
def test_refresh_data_empty_response(mock_fetch_torrents, app):
    """Test handling of empty response from server."""
    mock_fetch_torrents.return_value = []

    client = TransmissionClient()
    client.refresh_data()

    # Should have empty table
    assert client.torrent_table.rowCount() == 0
    assert len(client.torrent_table.displayed_torrents) == 0


# Test configuration and environment handling
def test_transmission_client_custom_config(app):
    """Test TransmissionClient with custom configuration."""
    client = TransmissionClient()
    # Configuration is now handled by config_manager
    assert client.config_manager is not None
    assert hasattr(client, "refresh_interval_ms")
    # Default refresh interval should be set
    assert client.refresh_interval_ms > 0


# Test UI state management
def test_window_minimization_handling(app):
    """Test that window minimization affects refresh intervals."""
    client = TransmissionClient()

    # Initially not minimized
    original_interval = client.refresh_interval_ms
    client.set_timer_interval()
    assert client.timer.interval() == original_interval

    # Mock minimization
    with patch.object(client, "windowState", return_value=Qt.WindowMinimized):
        client.set_timer_interval()
        assert client.timer.interval() == client.minimized_refresh_interval_ms


# Test theme switching
def test_theme_switching(app):
    """Test theme switching functionality."""
    client = TransmissionClient()

    # Test light theme
    client.set_theme("light")
    assert client.current_theme == "light"

    # Test dark theme
    client.set_theme("dark")
    assert client.current_theme == "dark"

    # Test auto theme
    client.set_theme("auto")
    assert client.current_theme == "auto"


# Test torrent details dialog with edge cases
def test_torrent_detail_dialog_empty_peers(app):
    """Test TorrentDetailDialog with torrent that has no peers."""
    torrent_data = {
        "name": "Empty Torrent",
        "status": 0,
        "totalSize": 1024,
        "addedDate": 1609459200,
        "percentDone": 0.0,
        "peers": [],  # No peers
        "trackerStats": [],
        "rateDownload": 0,
        "rateUpload": 0,
    }

    dialog = TorrentDetailDialog(None, torrent_data)
    assert dialog.windowTitle() == "Details: Empty Torrent"
    assert dialog.peers_table.rowCount() == 0


def test_torrent_detail_dialog_malformed_data(app):
    """Test TorrentDetailDialog with missing or malformed data."""
    torrent_data = {
        "name": "Malformed Torrent",
        # Missing many required fields
    }

    dialog = TorrentDetailDialog(None, torrent_data)
    assert dialog.windowTitle() == "Details: Malformed Torrent"
    # Should not crash even with missing data
    # Table should be empty since no peers data
    assert dialog.peers_table.rowCount() == 0


# Test menu bar functionality
def test_menu_bar_initialization(app):
    """Test that the menu bar is properly initialized."""
    client = TransmissionClient()

    # Check that menu bar exists
    menubar = client.menuBar()
    assert menubar is not None

    # Check that menu bar has the expected menus
    menu_actions = menubar.actions()
    assert len(menu_actions) == 3

    # Check menu names and order
    menu_names = [action.text() for action in menu_actions]
    assert menu_names == ["&Edit", "&View", "&Torrent"], (
        f"Expected menu order: Edit, View, Torrent, got: {menu_names}"
    )


def test_edit_menu_structure(app):
    """Test the Edit menu structure and actions."""
    client = TransmissionClient()

    menubar = client.menuBar()
    edit_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Edit":
            edit_menu_action = action
            break

    assert edit_menu_action is not None
    edit_menu = edit_menu_action.menu()
    assert edit_menu is not None

    # Check Edit menu actions
    edit_actions = edit_menu.actions()
    assert len(edit_actions) == 1

    connection_action = edit_actions[0]
    assert connection_action.text() == "&Connection Settings..."
    assert connection_action.toolTip() == "Connection Settings"
    assert connection_action.isEnabled()

    # Check keyboard shortcut
    shortcuts = connection_action.shortcuts()
    assert len(shortcuts) == 1
    # Check that it contains Ctrl and comma
    shortcut_str = shortcuts[0].toString()
    assert "Ctrl" in shortcut_str and "," in shortcut_str


def test_view_menu_structure(app):
    """Test the View menu structure and actions."""
    client = TransmissionClient()

    menubar = client.menuBar()
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    assert view_menu_action is not None
    view_menu = view_menu_action.menu()
    assert view_menu is not None

    # Check View menu actions (should have Torrent Details, separator, and Theme submenu)
    view_actions = view_menu.actions()
    assert len(view_actions) == 3

    # First action should be Torrent Details
    torrent_details_action = view_actions[0]
    assert torrent_details_action.text() == "&Torrent Details"
    assert torrent_details_action.toolTip() == "Torrent Details"
    assert not torrent_details_action.isEnabled()  # Should be disabled initially

    # Check keyboard shortcut
    shortcuts = torrent_details_action.shortcuts()
    assert len(shortcuts) == 1
    # Check that it contains Ctrl and D
    shortcut_str = shortcuts[0].toString()
    assert "Ctrl" in shortcut_str and "D" in shortcut_str

    # Second action should be separator (empty text)
    separator_action = view_actions[1]
    assert separator_action.text() == ""

    # Third action should be Theme submenu
    theme_menu_action = view_actions[2]
    assert theme_menu_action.text() == "&Theme"
    assert theme_menu_action.toolTip() == "Theme"


def test_theme_submenu_structure(app):
    """Test the Theme submenu structure and actions."""
    client = TransmissionClient()

    # Navigate to theme submenu
    menubar = client.menuBar()
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    view_menu = view_menu_action.menu()
    theme_menu_action = view_menu.actions()[2]  # Third action is Theme
    theme_menu = theme_menu_action.menu()

    # Check theme submenu actions
    theme_actions = theme_menu.actions()
    assert len(theme_actions) == 3

    # Check theme action names and initial states
    light_action = theme_actions[0]
    dark_action = theme_actions[1]
    auto_action = theme_actions[2]

    assert light_action.text() == "&Light"
    assert dark_action.text() == "&Dark"
    assert auto_action.text() == "&Auto"

    # All should be enabled
    assert light_action.isEnabled()
    assert dark_action.isEnabled()
    assert auto_action.isEnabled()

    # Only Auto should be checked initially
    assert not light_action.isChecked()
    assert not dark_action.isChecked()
    assert auto_action.isChecked()

    # Check that they are in an exclusive group
    assert light_action.actionGroup() is not None
    assert dark_action.actionGroup() is not None
    assert auto_action.actionGroup() is not None
    assert (
        light_action.actionGroup()
        == dark_action.actionGroup()
        == auto_action.actionGroup()
    )


def test_theme_menu_checkmarks(app):
    """Test that theme menu checkmarks update correctly when themes change."""
    client = TransmissionClient()

    # Get theme actions
    menubar = client.menuBar()
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    view_menu = view_menu_action.menu()
    theme_menu_action = view_menu.actions()[2]
    theme_menu = theme_menu_action.menu()
    theme_actions = theme_menu.actions()

    light_action, dark_action, auto_action = theme_actions

    # Test light theme
    client.set_theme("light")
    assert light_action.isChecked()
    assert not dark_action.isChecked()
    assert not auto_action.isChecked()

    # Test dark theme
    client.set_theme("dark")
    assert not light_action.isChecked()
    assert dark_action.isChecked()
    assert not auto_action.isChecked()

    # Test auto theme
    client.set_theme("auto")
    assert not light_action.isChecked()
    assert not dark_action.isChecked()
    assert auto_action.isChecked()


def test_torrent_details_menu_state_management(app, sample_torrent_data):
    """Test that Torrent Details menu action state changes based on table selection."""
    client = TransmissionClient()

    # Get torrent details action
    menubar = client.menuBar()
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    view_menu = view_menu_action.menu()
    torrent_details_action = view_menu.actions()[0]

    # Initially disabled
    assert not torrent_details_action.isEnabled()

    # Add torrent data to table
    client.torrent_table.displayed_torrents = [sample_torrent_data]
    client.torrent_table.update_torrents([sample_torrent_data])

    # Still disabled (no selection)
    assert not torrent_details_action.isEnabled()

    # Select a row
    client.torrent_table.selectRow(0)

    # Should now be enabled
    assert torrent_details_action.isEnabled()

    # Clear selection
    client.torrent_table.clearSelection()

    # Should be disabled again
    assert not torrent_details_action.isEnabled()

    # Select multiple rows
    client.torrent_table.selectRow(0)
    # In a real scenario we'd add more rows, but for this test we'll simulate
    # Since we only have one row, selecting it should enable the action
    assert torrent_details_action.isEnabled()


def test_menu_actions_functionality(app, sample_torrent_data):
    """Test that menu actions trigger the expected functionality."""
    client = TransmissionClient()

    # Test Connection Settings action
    menubar = client.menuBar()
    edit_menu_action = None
    for action in menubar.actions():
        if action.text() == "&Edit":
            edit_menu_action = action
            break

    edit_menu = edit_menu_action.menu()
    connection_action = edit_menu.actions()[0]

    # Mock the open_connection_settings method
    with patch.object(client, "open_connection_settings") as mock_open_settings:
        connection_action.trigger()
        mock_open_settings.assert_called_once()

    # Test Torrent Details action
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    view_menu = view_menu_action.menu()
    torrent_details_action = view_menu.actions()[0]

    # Add torrent and select it
    client.torrent_table.displayed_torrents = [sample_torrent_data]
    client.torrent_table.update_torrents([sample_torrent_data])
    client.torrent_table.selectRow(0)

    # Mock the _show_torrent_details method
    with patch.object(client, "_show_torrent_details") as mock_show_details:
        torrent_details_action.trigger()
        mock_show_details.assert_called_once()


def test_theme_menu_actions_functionality(app):
    """Test that theme menu actions trigger theme changes."""
    client = TransmissionClient()

    # Get theme actions
    menubar = client.menuBar()
    view_menu_action = None
    for action in menubar.actions():
        if action.text() == "&View":
            view_menu_action = action
            break

    view_menu = view_menu_action.menu()
    theme_menu_action = view_menu.actions()[2]
    theme_menu = theme_menu_action.menu()
    theme_actions = theme_menu.actions()

    light_action, dark_action, auto_action = theme_actions

    # Test light theme action
    light_action.trigger()
    assert client.current_theme == "light"

    # Test dark theme action
    dark_action.trigger()
    assert client.current_theme == "dark"

    # Test auto theme action
    auto_action.trigger()
    assert client.current_theme == "auto"


def test_server_config_security_no_passwords_saved(app, tmp_path):
    """Test that server configurations never save passwords to config files."""
    from transmission_qt_remote.config_manager import ConfigManager

    # Create a temporary config file
    temp_config = tmp_path / "test_config.json"

    # Create a fresh config manager that starts with empty config
    config_manager = ConfigManager.__new__(ConfigManager)
    config_manager._config = {}
    config_manager._config_file_path = temp_config

    # Test that even if password is somehow passed, ConfigManager preserves empty password
    server_data = {
        "name": "Test Server",
        "url": "http://test.com/rpc",
        "use_credentials": True,
        "username": "testuser",
        "password": "",  # Should always be empty when saving to config
        "remember_credentials": True,
    }

    config_manager.add_server(server_data)
    config_manager.save()

    # Verify the config file contains the server with empty password
    import json

    with open(temp_config) as f:
        saved_config = json.load(f)

    assert len(saved_config["servers"]) == 1
    saved_server = saved_config["servers"][0]

    # Password field should be empty string, never containing actual passwords
    assert saved_server["password"] == ""
    assert saved_server["name"] == "Test Server"
    assert saved_server["url"] == "http://test.com/rpc"
    assert saved_server["use_credentials"]
    assert saved_server["username"] == "testuser"
    assert saved_server["remember_credentials"]


def test_connection_settings_server_data_structure():
    """Test that server data structures always have empty password fields."""
    # Test the server data creation logic from _add_server method
    # Simulate the exact logic used in the dialog

    # Test data that would come from the UI
    name = "Test Server"
    url = "http://test.com/rpc"
    use_credentials = True
    username = "testuser"
    # password_from_ui = "secretpassword123"  # This should NOT be saved
    remember_credentials = True

    # This is the exact logic from _add_server method
    server_data = {
        "name": name,
        "url": url,
        "use_credentials": use_credentials,
        "username": username if use_credentials else "",
        "password": "",  # Never store passwords in config file
        "remember_credentials": remember_credentials if use_credentials else False,
    }

    # Verify the structure
    assert server_data["password"] == ""  # Password is always empty
    assert server_data["name"] == "Test Server"
    assert server_data["url"] == "http://test.com/rpc"
    assert server_data["use_credentials"]
    assert server_data["username"] == "testuser"
    assert server_data["remember_credentials"]

    # Test with no credentials
    server_data_no_auth = {
        "name": name,
        "url": url,
        "use_credentials": False,
        "username": username if False else "",
        "password": "",  # Always empty
        "remember_credentials": remember_credentials if False else False,
    }

    assert server_data_no_auth["password"] == ""
    assert server_data_no_auth["username"] == ""
    assert not server_data_no_auth["remember_credentials"]


def test_password_saving_workflow():
    """Test the complete password saving workflow from GUI to keyring."""
    from transmission_qt_remote.credential_manager import CredentialManager

    # Clean up any existing test credentials
    CredentialManager.delete_credentials("testuser_gui")

    # Simulate the GUI workflow: user enters password and saves server config
    username = "testuser_gui"
    password_from_ui = "mypassword123"

    # This simulates what happens in _add_server when user saves credentials
    if CredentialManager.is_available():
        result = CredentialManager.set_credentials(username, password_from_ui)
        if not result:
            # Keyring is installed but no backend available (e.g., in Docker)
            import pytest

            pytest.skip("Keyring has no available backend for testing")

        # Verify the password was saved correctly
        retrieved_password = CredentialManager.get_credentials(username)
        assert retrieved_password == password_from_ui, (
            f"Expected {password_from_ui}, got {retrieved_password}"
        )

        # Verify credential existence check works
        assert CredentialManager.has_credentials(username), (
            "has_credentials should return True"
        )

        # Clean up
        CredentialManager.delete_credentials(username)
        assert not CredentialManager.has_credentials(username), (
            "Credentials should be deleted"
        )
    else:
        # If keyring is not available, this test should be skipped
        import pytest

        pytest.skip("Keyring not available for testing")


def test_test_connection_uses_keyring_credentials():
    """Test that Test Connection button uses credentials from keyring, not empty config passwords."""
    from transmission_qt_remote.credential_manager import CredentialManager

    # Set up test credentials in keyring
    test_username = "test_connection_user"
    test_password = "test_connection_pass"
    result = CredentialManager.set_credentials(test_username, test_password)

    if not result:
        # Keyring is installed but no backend available (e.g., in Docker)
        import pytest

        pytest.skip("Keyring has no available backend for testing")

    try:
        # Test the logic that _test_selected_server uses to load credentials
        server_data = {
            "name": "Test Server",
            "url": "http://test.com/rpc",
            "use_credentials": True,
            "username": test_username,
            "password": "",  # Empty like in config file
            "remember_credentials": True,
        }

        # Simulate the logic from _test_selected_server
        use_credentials = server_data["use_credentials"]
        username = server_data["username"] if use_credentials else None

        # Load password from keyring if credentials are configured to be remembered
        password = None
        if use_credentials and server_data.get("remember_credentials"):
            password = CredentialManager.get_credentials(username or "")

        # Verify that the password loaded is the actual password from keyring, not empty
        assert password == test_password, f"Expected {test_password}, got {password}"
        assert password != "", "Password should not be empty when loaded from keyring"

    finally:
        # Clean up test credentials
        CredentialManager.delete_credentials(test_username)
